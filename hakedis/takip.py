"""Vaka takibi: acik -> itiraz_edildi -> kabul / red -> tahsil_edildi."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd

from hakedis.modeller import Bulgu

DURUMLAR = ["acik", "itiraz_edildi", "kabul", "red", "tahsil_edildi"]
GECISLER = {
    "acik": {"itiraz_edildi"},
    "itiraz_edildi": {"kabul", "red"},
    "kabul": {"tahsil_edildi"},
    "red": {"kabul"},  # pazaryeri sonradan düzeltme kaydı atarsa
    "tahsil_edildi": set(),
}


class GecersizGecis(ValueError):
    pass


@dataclass
class Vaka:
    vaka_id: str
    platform: str
    kural: str
    siparis_no: str | None
    talep_tutari: float
    durum: str = "acik"
    tahsil_tutari: float = 0.0
    tahsil_referanslari: list[str] = field(default_factory=list)
    faturalandi: bool = False
    fatura_no: str | None = None
    tarihce: list[dict] = field(default_factory=list)

    def gecis(self, yeni: str, tarih: str, not_: str = "") -> None:
        if yeni not in GECISLER.get(self.durum, set()):
            raise GecersizGecis(f"{self.vaka_id}: {self.durum} -> {yeni} geçişine izin yok")
        self.tarihce.append({"tarih": tarih, "eski": self.durum, "yeni": yeni, "not": not_})
        self.durum = yeni


class VakaDefteri:
    def __init__(self, vakalar: list[Vaka] | None = None):
        self.vakalar: dict[str, Vaka] = {v.vaka_id: v for v in (vakalar or [])}

    @classmethod
    def bulgulardan(cls, bulgular: list[Bulgu], tarih: str) -> "VakaDefteri":
        vakalar = []
        for b in bulgular:
            if b.karar != "dosyalanacak":
                continue
            v = Vaka(b.bulgu_id, b.platform, b.kural, b.siparis_no, round(b.tutar_tl, 2))
            v.tarihce.append({"tarih": tarih, "eski": None, "yeni": "acik", "not": "tarama ile oluşturuldu"})
            vakalar.append(v)
        return cls(vakalar)

    def gecis(self, vaka_id: str, yeni: str, tarih: str, not_: str = "") -> None:
        self.vakalar[vaka_id].gecis(yeni, tarih, not_)

    def tablo(self) -> pd.DataFrame:
        return pd.DataFrame([{
            "vaka_id": v.vaka_id, "platform": v.platform, "kural": v.kural, "siparis_no": v.siparis_no,
            "talep_tutari": v.talep_tutari, "durum": v.durum, "tahsil_tutari": round(v.tahsil_tutari, 2),
            "tahsil_referanslari": ";".join(v.tahsil_referanslari), "faturalandi": v.faturalandi,
            "fatura_no": v.fatura_no,
        } for v in self.vakalar.values()])

    def kaydet(self, klasor: Path) -> None:
        klasor.mkdir(parents=True, exist_ok=True)
        self.tablo().to_csv(klasor / "vakalar.csv", index=False)
        with open(klasor / "vakalar.json", "w", encoding="utf-8") as f:
            json.dump([asdict(v) for v in self.vakalar.values()], f, ensure_ascii=False, indent=2)

    @classmethod
    def yukle(cls, klasor: Path) -> "VakaDefteri":
        with open(Path(klasor) / "vakalar.json", encoding="utf-8") as f:
            return cls([Vaka(**d) for d in json.load(f)])
