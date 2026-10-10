"""Kural motoru. Her kural modülü `kontrol(vs, ayar) -> list[Bulgu]` sağlar."""
from __future__ import annotations

from typing import Any, Callable

from hakedis.modeller import Bulgu, VeriSeti
from hakedis.rules import (
    dayanaksiz_kesinti, desi_farki, iade_komisyonu, iptal_kargo, mukerrer_kesinti, odenmeyen_hakedis,
)

KURALLAR: dict[str, Callable[[VeriSeti, dict[str, Any]], list[Bulgu]]] = {
    "iade_komisyonu": iade_komisyonu.kontrol,
    "desi_farki": desi_farki.kontrol,
    "iptal_kargo": iptal_kargo.kontrol,
    "mukerrer_kesinti": mukerrer_kesinti.kontrol,
    "dayanaksiz_kesinti": dayanaksiz_kesinti.kontrol,
    "odenmeyen_hakedis": odenmeyen_hakedis.kontrol,
}

KURAL_BASLIKLARI = {
    "iade_komisyonu": "İadede geri verilmeyen komisyon",
    "desi_farki": "Hatalı (fazla) desi ile kesilen kargo",
    "iptal_kargo": "İptal / teslim edilemeyen siparişe kesilen kargo",
    "mukerrer_kesinti": "Mükerrer (çift) kesinti",
    "dayanaksiz_kesinti": "Dayanağı olmayan hizmet / ceza bedeli",
    "odenmeyen_hakedis": "Teslim edilen siparişin ödenmeyen hakedişi",
}


def tum_kurallari_calistir(vs: VeriSeti, ayar: dict[str, Any]) -> list[Bulgu]:
    bulgular: list[Bulgu] = []
    kural_ayar = ayar.get("kurallar") or {}
    for ad, fonk in KURALLAR.items():
        if (kural_ayar.get(ad) or {}).get("aktif", True):
            bulgular.extend(fonk(vs, ayar))
    return bulgular
