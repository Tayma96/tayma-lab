"""İtiraz (düzeltme talebi) metni ve kanıt Excel'i üretimi.

Şablon tabanlıdır; LLM ile iyileştirme isteğe bağlıdır ve bu iskelette
HİÇBİR LLM / ağ çağrısı yapılmaz. Üretilen metinler TASLAKTIR; hiçbir yere
gönderilmez. Gönderim, satıcı tarafından satıcı paneli üzerinden ve satıcının
kendi kontrolünden sonra yapılmalıdır.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from hakedis.modeller import Bulgu
from hakedis.rules import KURAL_BASLIKLARI

PLATFORM_ADI = {"trendyol": "Trendyol", "hepsiburada": "Hepsiburada"}

SEBEP = {
    "iade_komisyonu": ("müşteri iadesi kabul edilerek satış bedeli hakedişimizden düşüldüğü halde, satış "
                       "sırasında kesilen komisyonun iadesi yapılmamış ya da eksik yapılmıştır"),
    "desi_farki": ("kargo faturasında, ürünlerin sistemde kayıtlı desi değerlerinden daha yüksek desi "
                   "üzerinden ücretlendirme yapılmıştır"),
    "iptal_kargo": ("iptal edilen / tedarik edilemeyen ve kargoya hiç verilmeyen siparişler için gönderi "
                    "kargo bedeli kesilmiştir"),
    "mukerrer_kesinti": "aynı gönderi veya aynı sipariş için aynı bedel birden fazla kez kesilmiştir",
    "dayanaksiz_kesinti": ("kesilen hizmet/ceza bedellerinin dayanağı sipariş kayıtlarıyla örtüşmemektedir "
                           "(termin içinde kargoya verilen ya da teslim edilen siparişler)"),
    "odenmeyen_hakedis": "teslim edilmiş ve vadesi geçmiş siparişlerin hakediş ödemesi yapılmamıştır",
}
TALEP = {
    "iade_komisyonu": "eksik komisyon iadesinin düzeltme kaydı ile hakedişimize yansıtılması",
    "desi_farki": ("kargo bedellerinin ürünlerin kayıtlı desi değerine göre yeniden hesaplanması ve "
                   "farkın iadesi"),
    "iptal_kargo": "hatalı kesilen kargo bedellerinin iadesi",
    "mukerrer_kesinti": "mükerrer kesilen tutarların iadesi",
    "dayanaksiz_kesinti": "dayanaksız kesilen bedellerin iptali ve iadesi",
    "odenmeyen_hakedis": "ödenmeyen hakedişlerin bir sonraki ödeme döneminde ödenmesi",
}
EK_NOT = {
    "desi_farki": ("[SATICI EKLEMELİ: Mümkünse paketlenmiş ürünün ölçü/tartı fotoğrafı ve kargo fişi "
                   "eklenmelidir.]"),
    "dayanaksiz_kesinti": "[SATICI EKLEMELİ: Kargo teslim fişi / takip ekranı görüntüsü eklenebilir.]",
}


def _tl(x: float) -> str:
    s = f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") + " TL"


def itiraz_metni(platform: str, kural: str, bulgular: list[Bulgu], satici_adi: str, satici_id: str,
                 donem: str, ek_dosya: str) -> str:
    toplam = sum(b.tutar_tl for b in bulgular)
    satirlar = "\n".join(f"- Sipariş {b.siparis_no or '-'} (ref: {b.referans or '-'}): {b.aciklama} "
                         f"Talep: {_tl(b.tutar_tl)}" for b in bulgular)
    ek = EK_NOT.get(kural, "")
    return f"""Konu: {KURAL_BASLIKLARI[kural]} - {len(bulgular)} kayıt, toplam {_tl(toplam)} düzeltme talebi

Merhaba {PLATFORM_ADI.get(platform, platform)} Satıcı Destek Ekibi,

{satici_adi} (Satıcı ID: {satici_id}) olarak {donem} dönemine ait hakediş ve kesinti kayıtlarımızı kontrol ettik. Aşağıda listelenen {len(bulgular)} kayıtta {SEBEP[kural]}.

Kayıtlar:
{satirlar}

Toplam talep edilen tutar: {_tl(toplam)}

Talebimiz: {TALEP[kural]}. Sipariş, kargo ve cari hesap ekstresi satırlarını içeren kanıt tablosu ekteki "{ek_dosya}" dosyasındadır.
{ek}
Kayıtların incelenmesini ve uygun görülen tutarların bir sonraki hakediş döneminde düzeltme kaydı ile yansıtılmasını rica ederiz.

Saygılarımızla,
{satici_adi}
"""


def llm_ile_iyilestir(metin: str, ayar: dict[str, Any]) -> str:
    """İsteğe bağlı LLM adımı. Varsayılan kapalı; bu iskelette çağrı uygulanmamıştır."""
    if not (ayar.get("llm") or {}).get("aktif"):
        return metin
    raise NotImplementedError("LLM entegrasyonu bu iskelette yok; şablon metni kullanın.")


def kanit_excel(bulgular: list[Bulgu], yol: Path, ornek_veri: bool = True) -> None:
    ozet = pd.DataFrame([{
        "bulgu_id": b.bulgu_id, "platform": b.platform, "kural": b.kural, "alt_tip": b.alt_tip,
        "siparis_no": b.siparis_no, "referans": b.referans, "talep_tutari_tl": round(b.tutar_tl, 2),
        "guven": b.guven, "aciklama": b.aciklama,
    } for b in bulgular])
    kanit = pd.DataFrame([{"bulgu_id": b.bulgu_id, **k} for b in bulgular for k in b.kanit])
    bilgi = pd.DataFrame({"BILGI": [
        "ÖRNEK VERİ - SENTETİK. Gerçek satıcı/sipariş bilgisi içermez." if ornek_veri else
        "Otomatik üretilmiş kanıt tablosu.",
        "Bu dosya otomatik hazırlanmış bir TASLAKTIR; hiçbir yere gönderilmemiştir.",
        "Gönderim kararı ve kontrolü satıcıya aittir.",
    ]})
    yol.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(yol, engine="openpyxl") as w:
        ozet.to_excel(w, sheet_name="Ozet", index=False)
        kanit.to_excel(w, sheet_name="Kanitlar", index=False)
        bilgi.to_excel(w, sheet_name="BILGI", index=False)
