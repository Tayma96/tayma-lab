"""CSV/XLSX okuma yardımcıları.

CSV dosyalarında '#' ile başlayan satırlar yorum kabul edilir (örnek verilerdeki
"ÖRNEK VERİ" etiketi bu şekilde tutulur). XLSX dosyalarında 'BILGI' sayfası
atlanır, ilk veri sayfası okunur.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def bul(klasor: Path, ad: str) -> Path | None:
    """`ad` (uzantısız) için .csv veya .xlsx dosyasını bulur."""
    for uzanti in (".csv", ".xlsx"):
        yol = klasor / f"{ad}{uzanti}"
        if yol.exists():
            return yol
    return None


def oku_tablo(yol: Path | str, kolon_eslemesi: dict[str, str] | None = None) -> pd.DataFrame:
    yol = Path(yol)
    if yol.suffix.lower() == ".csv":
        df = pd.read_csv(yol, comment="#", dtype=str, keep_default_na=False, encoding="utf-8")
    elif yol.suffix.lower() in (".xlsx", ".xlsm"):
        sayfalar = pd.read_excel(yol, sheet_name=None, dtype=str, keep_default_na=False)
        veri_sayfalari = [ad for ad in sayfalar if ad.upper() != "BILGI"]
        if not veri_sayfalari:
            raise ValueError(f"{yol}: veri sayfası bulunamadı")
        df = sayfalar[veri_sayfalari[0]]
    else:
        raise ValueError(f"Desteklenmeyen dosya türü: {yol}")
    df.columns = [str(c).strip() for c in df.columns]
    if kolon_eslemesi:
        df = df.rename(columns={k: v for k, v in kolon_eslemesi.items() if k in df.columns})
    return df.replace({"": None})


def oku_opsiyonel(klasor: Path, ad: str, kolon_eslemesi: dict[str, str] | None = None) -> pd.DataFrame:
    yol = bul(klasor, ad)
    if yol is None:
        return pd.DataFrame()
    return oku_tablo(yol, kolon_eslemesi)
