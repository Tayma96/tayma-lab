#!/usr/bin/env python3
"""
Satıcı Rehberi — günlük yazı üretici.

Akış:
  1. blog/topics.yaml içinden, blog/src/content/posts/<slug>.md dosyası henüz OLMAYAN ilk konuyu seçer.
  2. OPENAI_API_KEY (öncelikli) veya ANTHROPIC_API_KEY ile bir LLM'den yazı ister.
     Hiçbir anahtar yoksa ::notice:: basar ve 0 koduyla (başarılı) çıkar — iş "kırmızı" olmaz.
  3. Kalite kontrolleri: asgari kelime sayısı, yinelenen başlık yok, zorunlu uyarı metni,
     en az 3 ara başlık, yer tutucu/uydurma işareti yok, kaynak URL'leri erişilebilir.
  4. Markdown + frontmatter olarak yazar. --commit-push verilirse git commit + pull --rebase + push yapar.

Ortam değişkenleri:
  OPENAI_API_KEY / ANTHROPIC_API_KEY   (en az biri; yoksa temiz çıkış)
  LLM_PROVIDER      openai | anthropic  (ikisi de varsa tercih; varsayılan openai)
  OPENAI_MODEL      varsayılan: gpt-4.1-mini
  ANTHROPIC_MODEL   varsayılan: claude-sonnet-4-5
  MIN_WORDS         varsayılan: 800
  REQUIRE_REVIEW    "true" ise yazı draft: true olarak kaydedilir (yayına girmez, insan onayı bekler)
  SITE_BASE_URL     varsayılan: site.config.json'dan
Bağımlılık: PyYAML (pip install pyyaml). Geri kalanı standart kütüphane.
"""
from __future__ import annotations

import argparse
import datetime as dt
import difflib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

import yaml

BLOG = Path(__file__).resolve().parent.parent
POSTS = BLOG / "src" / "content" / "posts"
TOPICS = BLOG / "topics.yaml"
CONFIG = BLOG / "site.config.json"

DISCLAIMER = "bilgilendirme amaçlıdır, güncel kuralları platformdan doğrulayın"
DISCLAIMER_BLOCK = (
    "\n\n---\n\n> **Önemli:** Bu yazı bilgilendirme amaçlıdır, güncel kuralları platformdan doğrulayın. "
    "Oranlar, tutarlar ve süreler değişebilir; vergi ve hukuk konularında mali müşavirinize veya avukatınıza danışın.\n"
)
PLACEHOLDER_PATTERNS = [r"lorem ipsum", r"\[kaynak\]", r"\[link\]", r"\bTODO\b", r"\bXXX\b", r"example\.com", r"\[\.\.\.\]"]


# ---------------------------------------------------------------- yardımcılar
def log(msg: str) -> None:
    print(msg, flush=True)


def gh_output(**kv: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            for k, v in kv.items():
                f.write(f"{k}={v}\n")


def norm(s: str) -> str:
    s = s.replace("ı", "i").replace("İ", "i")
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return yaml.safe_load(m.group(1)) if m else {}


def existing_posts() -> list[dict]:
    out = []
    for p in sorted(POSTS.glob("*.md")):
        fm = read_frontmatter(p)
        out.append({"slug": p.stem, "title": fm.get("title", ""), "category": fm.get("category", "")})
    return out


def site_base() -> str:
    if os.environ.get("SITE_BASE_URL"):
        return os.environ["SITE_BASE_URL"].rstrip("/") + "/"
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    return cfg["siteUrl"].rstrip("/") + cfg["basePath"]


def pick_topic(forced: str | None) -> dict | None:
    topics = yaml.safe_load(TOPICS.read_text(encoding="utf-8"))["topics"]
    done = {p.stem for p in POSTS.glob("*.md")}
    for t in topics:
        if forced and t["slug"] != forced:
            continue
        if t.get("skip") or t["slug"] in done:
            continue
        return t
    return None


# ---------------------------------------------------------------- LLM
SYSTEM_PROMPT = """Sen Türkiye'deki pazaryeri (Trendyol, Hepsiburada vb.) satıcıları için yazan, titiz ve dürüst bir Türkçe içerik editörüsün.
KESİN KURALLAR:
- ASLA rakam, oran, tutar, tarih, süre veya ceza miktarı UYDURMA. Bir sayıyı yalnızca resmi/güvenilir bir kaynağa dayanıyorsan ve o kaynağı "sources" listesinde verdiysen yaz. Emin değilsen sayı yerine "satıcı panelinizdeki güncel değeri kontrol edin" gibi ifadeler kullan.
- Örnek hesaplamalarda gerçek oran gibi görünen sayılar yerine harfli değişkenler (ör. Satış fiyatı = F, komisyon oranı = k) veya açıkça "varsayımsal örnek" diye etiketlenmiş yuvarlak sayılar kullan.
- Platform politikalarını kesin bilmiyorsan "platformun güncel kurallarına göre değişebilir" diye belirt. Belirsizliği gizleme.
- Hukuki/vergisel konularda kesin hüküm verme; mali müşavir/avukat danışmanlığı öner.
- Kaynak olarak yalnızca var olduğundan emin olduğun, kalıcı resmi sayfaları ver (ör. mevzuat.gov.tr, gib.gov.tr, ebelge.gib.gov.tr, kvkk.gov.tr, ticaret.gov.tr, developers.trendyol.com, iys.org.tr). Emin değilsen kaynak verme; URL UYDURMA.
- Yazı özgün, pratik ve satıcının gerçek sorusuna cevap veren nitelikte olsun; dolgu cümle, anahtar kelime doldurma ve abartılı vaat yok.
- Yazının sonunda mutlaka şu cümle geçsin: "Bu yazı bilgilendirme amaçlıdır, güncel kuralları platformdan doğrulayın."
ÇIKTI: Yalnızca geçerli bir JSON nesnesi döndür, başka hiçbir metin yazma."""

USER_TEMPLATE = """Konu (çalışma başlığı): {title}
Kategori: {category}
Hedef anahtar kelimeler: {keywords}
Editör notu: {notes}
Bugünün tarihi: {today}

Sitedeki mevcut yazılar (uygunsa metin içinde 1-2 tanesine Markdown linkiyle iç bağlantı ver, URL'leri aynen kullan):
{internal}

İstenen JSON şeması:
{{
  "title": "SEO uyumlu, en fazla 70 karakter, Türkçe başlık",
  "description": "En fazla 155 karakterlik meta açıklama",
  "tags": ["3-6 kısa etiket"],
  "sources": [{{"title": "Kaynak adı", "url": "https://..."}}],
  "body_markdown": "Yazının gövdesi. H1 KULLANMA; ## ve ### ara başlıklar kullan (en az 4 adet ##). 1000-1400 kelime. Giriş paragrafı, adım adım bölümler, kontrol listesi, sık yapılan hatalar ve kısa bir SSS bölümü içersin. Sayı verdiğin her yerde kaynağa link ver."
}}"""


def http_json(url: str, headers: dict, payload: dict, timeout: int = 180) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:500]
        raise RuntimeError(f"LLM API HTTP {e.code}: {body}") from None


def call_openai(system: str, user: str) -> str:
    model = os.environ.get("OPENAI_MODEL") or "gpt-4.1-mini"
    data = http_json(
        "https://api.openai.com/v1/chat/completions",
        {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
        {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"},
            "temperature": 0.4,
        },
    )
    return data["choices"][0]["message"]["content"]


def call_anthropic(system: str, user: str) -> str:
    model = os.environ.get("ANTHROPIC_MODEL") or "claude-sonnet-4-5"
    data = http_json(
        "https://api.anthropic.com/v1/messages",
        {"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"},
        {"model": model, "max_tokens": 6000, "system": system, "temperature": 0.4,
         "messages": [{"role": "user", "content": user}]},
    )
    return "".join(b.get("text", "") for b in data.get("content", []))


def choose_provider() -> str | None:
    has_o, has_a = bool(os.environ.get("OPENAI_API_KEY")), bool(os.environ.get("ANTHROPIC_API_KEY"))
    pref = (os.environ.get("LLM_PROVIDER") or "").lower()
    if pref == "anthropic" and has_a:
        return "anthropic"
    if pref == "openai" and has_o:
        return "openai"
    return "openai" if has_o else ("anthropic" if has_a else None)


def parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


# ---------------------------------------------------------------- kalite
def url_ok(u: str) -> bool:
    """Kaynak URL kontrolü. Uydurma alan adları (DNS çözülmüyor) ve 404/410 dönen sayfalar elenir.
    Bazı resmi siteler (ör. *.gov.tr) yurt dışı sunuculardan zaman aşımına uğrayabildiği için,
    alan adı çözülüyor ama bağlantı kurulamıyorsa kaynak korunur (doğrulanamadı notuyla)."""
    import socket
    from urllib.parse import urlparse
    if not re.match(r"^https?://", u):
        return False
    host = urlparse(u).hostname or ""
    try:
        socket.getaddrinfo(host, 443)
    except OSError:
        return False
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(u, method=method, headers={"User-Agent": "Mozilla/5.0 (SaticiRehberiBot link-check)"})
            with urllib.request.urlopen(req, timeout=15) as r:
                if r.status < 400:
                    return True
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return False
            if e.code in (401, 403, 405, 429) or e.code >= 500:
                return True  # bot engeli / geçici hata: var sayılır
        except Exception:
            continue
    log(f"Uyarı: {u} doğrulanamadı (bağlantı yok) ama alan adı mevcut; korunuyor.")
    return True


def quality_check(post: dict, existing: list[dict], min_words: int) -> list[str]:
    errs = []
    body = post.get("body_markdown", "")
    words = len(re.findall(r"\w+", body, re.U))
    if words < min_words:
        errs.append(f"Çok kısa: {words} kelime (asgari {min_words}).")
    title = post.get("title", "").strip()
    if not title:
        errs.append("Başlık yok.")
    for e in existing:
        if norm(e["title"]) == norm(title) or difflib.SequenceMatcher(None, norm(e["title"]), norm(title)).ratio() > 0.9:
            errs.append(f"Yinelenen/çok benzer başlık: '{title}' ~ '{e['title']}'")
    if norm(DISCLAIMER) not in norm(body):
        errs.append("Zorunlu uyarı metni yok.")
    if len(re.findall(r"^## ", body, re.M)) < 3:
        errs.append("En az 3 adet '##' ara başlık gerekli.")
    if re.search(r"^# ", body, re.M):
        errs.append("Gövdede H1 (#) kullanılmamalı.")
    for pat in PLACEHOLDER_PATTERNS:
        if re.search(pat, body, re.I):
            errs.append(f"Yer tutucu/şüpheli ifade bulundu: {pat}")
    if not post.get("description"):
        errs.append("Meta açıklama yok.")
    return errs


def yaml_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def write_post(topic: dict, post: dict, draft: bool) -> Path:
    today = dt.datetime.now(dt.timezone.utc).astimezone(dt.timezone(dt.timedelta(hours=3))).date().isoformat()
    desc = post["description"].strip()
    if len(desc) > 160:
        desc = desc[:157].rsplit(" ", 1)[0] + "…"
    tags = [str(t).strip() for t in post.get("tags", []) if str(t).strip()][:6]
    lines = [
        "---",
        f"title: {yaml_str(post['title'].strip())}",
        f"description: {yaml_str(desc)}",
        f"date: {today}",
        f"category: {yaml_str(topic.get('category', 'Genel'))}",
        f"tags: [{', '.join(yaml_str(t) for t in tags)}]",
        f"draft: {'true' if draft else 'false'}",
        "aiGenerated: true",
        "sources:",
    ]
    for s in post.get("sources", []):
        lines.append(f"  - title: {yaml_str(s['title'])}\n    url: {yaml_str(s['url'])}")
    if not post.get("sources"):
        lines[-1] = "sources: []"
    lines.append("---")
    path = POSTS / f"{topic['slug']}.md"
    path.write_text("\n".join(lines) + "\n\n" + post["body_markdown"].strip() + "\n", encoding="utf-8")
    return path


def git(*args: str) -> None:
    log("+ git " + " ".join(args))
    subprocess.run(["git", *args], check=True, cwd=BLOG)


def commit_push(path: Path, title: str) -> None:
    git("add", str(path))
    git("commit", "-m", f"blog: yeni yazı — {title}")
    for attempt in range(1, 6):
        try:
            git("pull", "--rebase", "origin", "main")
            git("push", "origin", "HEAD:main")
            return
        except subprocess.CalledProcessError:
            log(f"Push denemesi {attempt} başarısız; tekrar denenecek…")
            subprocess.run(["git", "rebase", "--abort"], cwd=BLOG)
            time.sleep(5 * attempt)
    raise SystemExit("Push 5 denemede başarısız oldu.")


# ---------------------------------------------------------------- ana akış
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", help="Belirli bir slug'ı üret")
    ap.add_argument("--commit-push", action="store_true", help="Yazıyı commit edip main'e push et")
    ap.add_argument("--no-link-check", action="store_true")
    args = ap.parse_args()

    gh_output(generated="false")
    provider = choose_provider()
    if not provider:
        log("::notice title=Yazı üretilmedi::OPENAI_API_KEY veya ANTHROPIC_API_KEY tanımlı değil. "
            "Repo > Settings > Secrets and variables > Actions altından ekleyin. İş başarıyla (atlanarak) tamamlandı.")
        return 0

    topic = pick_topic(args.topic)
    if not topic:
        log("::notice title=Konu kalmadı::topics.yaml içinde yazılmamış konu yok. Yeni konular ekleyin.")
        return 0
    log(f"Seçilen konu: {topic['slug']} — sağlayıcı: {provider}")

    existing = existing_posts()
    base = site_base()
    internal = "\n".join(f"- {e['title']}: {base}yazilar/{e['slug']}/" for e in existing) or "- (henüz yok)"
    user = USER_TEMPLATE.format(
        title=topic["title"], category=topic.get("category", "Genel"),
        keywords=", ".join(topic.get("keywords", [])), notes=topic.get("notes", "-"),
        today=dt.date.today().isoformat(), internal=internal,
    )
    min_words = int(os.environ.get("MIN_WORDS", "800"))
    call = call_openai if provider == "openai" else call_anthropic

    post, errs = None, ["henüz denenmedi"]
    for attempt in range(1, 3):
        prompt = user if attempt == 1 else user + "\n\nÖnceki denemen şu kontrollerden kaldı, düzelt:\n- " + "\n- ".join(errs)
        try:
            post = parse_json(call(SYSTEM_PROMPT, prompt))
        except (RuntimeError, ValueError, KeyError) as e:
            errs = [f"API/JSON hatası: {e}"]
            log(f"Deneme {attempt}: {errs[0]}")
            continue
        body = post.get("body_markdown", "")
        if norm(DISCLAIMER) not in norm(body):
            post["body_markdown"] = body.rstrip() + DISCLAIMER_BLOCK
        if not args.no_link_check:
            good = []
            for s in post.get("sources", []) or []:
                if isinstance(s, dict) and s.get("url") and url_ok(s["url"]):
                    good.append({"title": str(s.get("title") or s["url"]), "url": s["url"]})
                else:
                    log(f"Erişilemeyen/geçersiz kaynak çıkarıldı: {s}")
            post["sources"] = good
        errs = quality_check(post, existing, min_words)
        if not errs:
            break
        log(f"Deneme {attempt} kalite kontrolünden kaldı: {errs}")

    if errs:
        log("::error title=Kalite kontrolü başarısız::" + " | ".join(errs))
        return 1

    draft = os.environ.get("REQUIRE_REVIEW", "").lower() in ("1", "true", "yes")
    path = write_post(topic, post, draft)
    log(f"Yazıldı: {path.relative_to(BLOG)} (draft={draft})")
    gh_output(generated="true", slug=topic["slug"], title=post["title"].replace("\n", " "))
    if args.commit_push:
        commit_push(path, post["title"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
