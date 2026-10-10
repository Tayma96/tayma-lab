"""Bulguların puanlanması, çakışma önleme ve itiraz eşiği kararları."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from hakedis.modeller import Bulgu

KISALTMA = {
    "iade_komisyonu": "IKO", "desi_farki": "DES", "iptal_kargo": "IPK",
    "mukerrer_kesinti": "MUK", "dayanaksiz_kesinti": "DYK", "odenmeyen_hakedis": "ODH",
}
PLATFORM_KISA = {"trendyol": "TY", "hepsiburada": "HB"}


def oncelik(beklenen: float) -> str:
    if beklenen >= 100:
        return "yuksek"
    if beklenen >= 30:
        return "orta"
    return "dusuk"


def puanla(bulgular: list[Bulgu], ayar: dict[str, Any]) -> list[Bulgu]:
    es = ayar.get("esikler") or {}
    min_bulgu = float(es.get("min_bulgu_tutari_tl", 10))
    min_guven = float(es.get("min_guven", 0.5))
    min_paket = float(es.get("min_paket_tutari_tl", 250))
    min_donem = float(es.get("min_donem_tutari_tl", 500))
    sira = {k: i for i, k in enumerate(ayar.get("kural_onceligi") or [])}

    sirali = sorted(bulgular, key=lambda b: (sira.get(b.kural, 99), -b.tutar_tl, b.platform, str(b.siparis_no)))
    sayac: dict[tuple[str, str], int] = defaultdict(int)
    alinan: set[str] = set()
    for b in sirali:
        anahtar = (b.platform, b.kural)
        sayac[anahtar] += 1
        b.bulgu_id = f"{PLATFORM_KISA.get(b.platform, b.platform[:2].upper())}-{KISALTMA.get(b.kural, 'GEN')}-{sayac[anahtar]:04d}"
        b.beklenen_tl = round(b.tutar_tl * b.guven, 2)
        b.oncelik = oncelik(b.beklenen_tl)
        if any(k in alinan for k in b.kaynak_anahtarlar):
            b.karar = "cakisma"
            continue
        alinan.update(b.kaynak_anahtarlar)
        if b.guven < min_guven:
            b.karar = "incelenmeli"
        elif b.tutar_tl < min_bulgu:
            b.karar = "esik_alti"
        else:
            b.karar = "aday"

    paket_toplam: dict[tuple[str, str], float] = defaultdict(float)
    for b in sirali:
        if b.karar == "aday":
            paket_toplam[(b.platform, b.kural)] += b.tutar_tl
    for b in sirali:
        if b.karar == "aday":
            b.karar = "dosyalanacak" if paket_toplam[(b.platform, b.kural)] >= min_paket else "devreden"

    donem_toplam = sum(b.tutar_tl for b in sirali if b.karar == "dosyalanacak")
    if donem_toplam < min_donem:
        for b in sirali:
            if b.karar == "dosyalanacak":
                b.karar = "donem_esik_alti"
    return sorted(sirali, key=lambda b: b.bulgu_id)


def paketler(bulgular: list[Bulgu]) -> dict[tuple[str, str], list[Bulgu]]:
    p: dict[tuple[str, str], list[Bulgu]] = defaultdict(list)
    for b in bulgular:
        if b.karar == "dosyalanacak":
            p[(b.platform, b.kural)].append(b)
    return dict(sorted(p.items()))
