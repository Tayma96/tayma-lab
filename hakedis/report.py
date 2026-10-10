"""Bulgu özeti, çıktı dosyaları ve Markdown raporları."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from hakedis import appeal
from hakedis.billing import ucret_kalemlerden
from hakedis.modeller import Bulgu, VeriSeti
from hakedis.puanlama import paketler
from hakedis.rules import KURAL_BASLIKLARI

ORNEK_UYARI = ("> **ÖRNEK VERİ / SİMÜLASYON** - Bu çıktı tamamen sentetik örnek veriden üretilmiştir. "
               "Satıcı, sipariş ve tutarlar gerçek değildir. Hiçbir pazaryerine, satıcıya veya kişiye "
               "hiçbir şey gönderilmemiştir.")
KARAR_ACIKLAMA = {
    "dosyalanacak": "İtiraz paketine girer",
    "devreden": "Paket eşiğinin altında, sonraki döneme devreder",
    "esik_alti": "Tekil bulgu eşiğinin altında",
    "incelenmeli": "Güven düşük, manuel inceleme",
    "cakisma": "Başka bir kural aynı satırı zaten talep etti (çifte sayım engellendi)",
    "donem_esik_alti": "Dönem toplamı eşiğin altında",
}


def tl(x: float) -> str:
    return appeal._tl(float(x))


def bulgu_tablosu(bulgular: list[Bulgu]) -> pd.DataFrame:
    kol = ["bulgu_id", "platform", "kural", "alt_tip", "siparis_no", "referans", "tutar_tl", "guven",
           "beklenen_tl", "oncelik", "karar", "aciklama"]
    if not bulgular:
        return pd.DataFrame(columns=kol)
    return pd.DataFrame([b.sozluk() for b in bulgular])[kol]


def kategori_ozeti(bulgular: list[Bulgu]) -> pd.DataFrame:
    df = bulgu_tablosu(bulgular)
    satirlar = []
    for kural, baslik in KURAL_BASLIKLARI.items():
        d = df[df.kural == kural]
        dos = d[d.karar == "dosyalanacak"]
        satirlar.append({
            "kural": kural, "kategori": baslik, "tespit_sayisi": len(d),
            "tespit_tutari_tl": round(d.tutar_tl.sum(), 2), "dosyalanacak_sayisi": len(dos),
            "dosyalanacak_tutar_tl": round(dos.tutar_tl.sum(), 2),
            "beklenen_tl_tahmin": round(dos.beklenen_tl.sum(), 2),
        })
    ozet = pd.DataFrame(satirlar)
    toplam = {"kural": "TOPLAM", "kategori": "TOPLAM"} | {
        k: round(ozet[k].sum(), 2) for k in ozet.columns if k not in ("kural", "kategori")}
    return pd.concat([ozet, pd.DataFrame([toplam])], ignore_index=True)


def tarama_ciktilarini_yaz(cikti: Path, vs: VeriSeti, bulgular: list[Bulgu], ayar: dict[str, Any],
                           satici: dict[str, str], donem: str, ornek: bool) -> dict[str, Any]:
    cikti.mkdir(parents=True, exist_ok=True)
    tablo = bulgu_tablosu(bulgular)
    tablo.to_csv(cikti / "bulgular.csv", index=False)
    kat = kategori_ozeti(bulgular)
    kat.to_csv(cikti / "kategori_ozeti.csv", index=False)
    with pd.ExcelWriter(cikti / "bulgular.xlsx", engine="openpyxl") as w:
        kat.to_excel(w, sheet_name="Ozet", index=False)
        tablo.to_excel(w, sheet_name="Bulgular", index=False)
        pd.DataFrame({"BILGI": [ORNEK_UYARI.strip("> *") if ornek else "Otomatik tarama çıktısı",
                                "Tahmini değerler (güven, beklenen, ücret) tahmindir."]}).to_excel(
            w, sheet_name="BILGI", index=False)

    paket_listesi = []
    itiraz_klasoru = cikti / "itiraz"
    for (platform, kural), bl in paketler(bulgular).items():
        ad = f"{platform}_{kural}"
        ek = f"{ad}_kanit.xlsx"
        metin = appeal.itiraz_metni(platform, kural, bl, satici["ad"], satici["id"], donem, ek)
        metin = appeal.llm_ile_iyilestir(metin, ayar)
        itiraz_klasoru.mkdir(parents=True, exist_ok=True)
        baslik = ("# TASLAK - GÖNDERİLMEDİ. " + ("ÖRNEK VERİ (sentetik). " if ornek else "")
                  + "Gönderim kararı satıcıya aittir.\n\n")
        (itiraz_klasoru / f"{ad}_itiraz.txt").write_text(baslik + metin, encoding="utf-8")
        appeal.kanit_excel(bl, itiraz_klasoru / ek, ornek_veri=ornek)
        paket_listesi.append({"paket": ad, "platform": platform, "kural": kural, "kayit_sayisi": len(bl),
                              "toplam_tl": round(sum(b.tutar_tl for b in bl), 2)})

    toplam_siparis = int(vs.siparisler[["platform", "siparis_no"]].drop_duplicates().shape[0]) \
        if not vs.siparisler.empty else 0
    platform_siparis = vs.siparisler.groupby("platform").siparis_no.nunique().to_dict() \
        if not vs.siparisler.empty else {}
    dosyalanacak = tablo[tablo.karar == "dosyalanacak"]
    geri_alinabilir = round(float(dosyalanacak.tutar_tl.sum()), 2)
    beklenen = round(float(dosyalanacak.beklenen_tl.sum()), 2)
    karar = tablo.groupby("karar").agg(sayi=("bulgu_id", "count"), tutar_tl=("tutar_tl", "sum")).round(2)
    ozet = {
        "ornek_veri": ornek, "satici": satici, "donem": donem,
        "analiz_tarihi": str((ayar.get("genel") or {}).get("analiz_tarihi")),
        "toplam_siparis": toplam_siparis, "platform_siparis": platform_siparis,
        "toplam_bulgu": len(tablo), "toplam_tespit_tl": round(float(tablo.tutar_tl.sum()), 2),
        "geri_alinabilir_tl": geri_alinabilir, "beklenen_tl_tahmin": beklenen,
        "tahmini_ucret_tam_kabul": ucret_kalemlerden(list(zip(dosyalanacak.kural, dosyalanacak.tutar_tl)), ayar),
        "tahmini_ucret_guven_agirlikli": ucret_kalemlerden(
            list(zip(dosyalanacak.kural, dosyalanacak.beklenen_tl)), ayar),
        "karar_dagilimi": {k: {"sayi": int(v.sayi), "tutar_tl": float(v.tutar_tl)} for k, v in karar.iterrows()},
        "paketler": paket_listesi,
        "kategoriler": kat.to_dict(orient="records"),
    }
    (cikti / "ozet.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=2), encoding="utf-8")
    (cikti / "OZET.md").write_text(ozet_md(ozet), encoding="utf-8")
    return ozet


def ozet_md(o: dict[str, Any]) -> str:
    satir = []
    if o["ornek_veri"]:
        satir += [ORNEK_UYARI, ""]
    satir += [f"# Hakediş tarama özeti - {o['satici']['ad']}", "",
              f"- Dönem: {o['donem']}  |  Analiz tarihi: {o['analiz_tarihi']}",
              f"- Taranan sipariş: **{o['toplam_siparis']}** "
              f"({', '.join(f'{k}: {v}' for k, v in o['platform_siparis'].items())})",
              f"- Toplam bulgu: {o['toplam_bulgu']} / tespit edilen tutar: {tl(o['toplam_tespit_tl'])}",
              f"- **İtiraza hazır (geri alınabilir) tutar: {tl(o['geri_alinabilir_tl'])}**",
              f"- Güven ağırlıklı beklenen geri kazanım (tahmin): {tl(o['beklenen_tl_tahmin'])}", "",
              "## Kategori bazında", "",
              "| Kategori | Tespit | Tespit TL | İtiraza hazır | İtiraza hazır TL | Beklenen TL (tahmin) |",
              "|---|---:|---:|---:|---:|---:|"]
    for k in o["kategoriler"]:
        b = "**" if k["kural"] == "TOPLAM" else ""
        satir.append(f"| {b}{k['kategori']}{b} | {k['tespit_sayisi']} | {tl(k['tespit_tutari_tl'])} | "
                     f"{k['dosyalanacak_sayisi']} | {tl(k['dosyalanacak_tutar_tl'])} | {tl(k['beklenen_tl_tahmin'])} |")
    satir += ["", "## Karar dağılımı", "", "| Karar | Açıklama | Adet | Tutar |", "|---|---|---:|---:|"]
    for k, v in o["karar_dagilimi"].items():
        satir.append(f"| {k} | {KARAR_ACIKLAMA.get(k, '')} | {v['sayi']} | {tl(v['tutar_tl'])} |")
    u1, u2 = o["tahmini_ucret_tam_kabul"], o["tahmini_ucret_guven_agirlikli"]
    satir += ["", "## Tahmini başarı ücreti (TAHMİN)", "",
              f"- Tüm itirazlar kabul edilirse: net ücret {tl(u1['net_ucret'])} + KDV {tl(u1['kdv'])} "
              f"(satıcıya kalan: {tl(u1['saticiya_kalan_net'])})",
              f"- Güven ağırlıklı senaryo: net ücret {tl(u2['net_ucret'])} + KDV {tl(u2['kdv'])}",
              "- Ücret yalnızca geri ödeme sonraki hakedişte görüldüğünde faturalanır.", "",
              "## İtiraz paketleri (TASLAK, gönderilmedi)", ""]
    for p in o["paketler"]:
        satir.append(f"- `itiraz/{p['paket']}_itiraz.txt` + `itiraz/{p['paket']}_kanit.xlsx`: "
                     f"{p['kayit_sayisi']} kayıt, {tl(p['toplam_tl'])}")
    return "\n".join(satir) + "\n"


def simulasyon_md(ozet: dict[str, Any], vaka_tablosu: pd.DataFrame, eslesmeler: pd.DataFrame,
                  fatura: dict[str, Any] | None) -> str:
    s = [ORNEK_UYARI, "", "# Uçtan uca simülasyon (örnek veri)", "",
         "Varsayımlar (SİMÜLASYON): satıcının itiraza hazır tüm paketleri kendi paneli üzerinden gönderdiği "
         "varsayılmıştır; pazaryeri yanıtları ve sonraki dönem düzeltme kayıtları SENTETİKTİR "
         "(varsayımsal kabul oranları, gerçek başarı oranı değildir).", "",
         "## Vaka durumları", "", "| Durum | Adet | Talep TL | Tahsil TL |", "|---|---:|---:|---:|"]
    for durum, g in vaka_tablosu.groupby("durum"):
        s.append(f"| {durum} | {len(g)} | {tl(g.talep_tutari.sum())} | {tl(g.tahsil_tutari.sum())} |")
    s.append(f"| **Toplam** | {len(vaka_tablosu)} | {tl(vaka_tablosu.talep_tutari.sum())} | "
             f"{tl(vaka_tablosu.tahsil_tutari.sum())} |")
    s += ["", "## Kategori bazında tahsilat", "", "| Kategori | Vaka | Talep TL | Tahsil TL | Tahsil oranı |",
          "|---|---:|---:|---:|---:|"]
    for kural, g in vaka_tablosu.groupby("kural"):
        oran = g.tahsil_tutari.sum() / g.talep_tutari.sum() if g.talep_tutari.sum() else 0
        s.append(f"| {KURAL_BASLIKLARI.get(kural, kural)} | {len(g)} | {tl(g.talep_tutari.sum())} | "
                 f"{tl(g.tahsil_tutari.sum())} | %{oran * 100:.0f} |")
    if not eslesmeler.empty:
        es = eslesmeler[eslesmeler.vaka_id.isna()]
        s += ["", f"Eşleşmeyen düzeltme kaydı: {len(es)} adet ({tl(es.tutar.sum())}) - vaka ile ilişkisi "
                  "olmadığı için ücretlendirilmez."]
    s += ["", "## Başarı ücreti fatura taslağı", ""]
    if fatura:
        h = fatura["hesap"]
        s += [f"- Fatura no: `{fatura['fatura_no']}` ({fatura['durum']})",
              f"- Tahsil edilen (hakedişe yansıyan) toplam: **{tl(h['tahsil_tutari'])}**",
              f"- Kademeli orana (%25 / hacim üstü %20) tabi tutar: {tl(h['standart_kademe_tutari'] + h['hacim_kademe_tutari'])}",
              f"- Özel oranlı tutar (ödenmeyen hakediş, %10): {tl(h['ozel_oranli_tutar'])} -> ücret {tl(h['ozel_oranli_ucret'])}",
              f"- Net ücret: {tl(h['net_ucret'])} (efektif oran %{h['efektif_oran'] * 100:.1f})",
              f"- KDV: {tl(h['kdv'])}  |  Toplam fatura: **{tl(h['toplam_ucret'])}**",
              f"- Satıcıya net kalan: {tl(h['saticiya_kalan_net'])}",
              f"- Ödeme yöntemi: {fatura['odeme_yontemi']}"]
    else:
        s.append("- Tahsil edilen vaka yok; fatura oluşmadı.")
    return "\n".join(s) + "\n"
