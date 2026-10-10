"""Hepsiburada dosya okuyucu (klasör: <girdi>/hepsiburada/).

Kolon adları ÖRNEKTİR ve doğrulanmalıdır. Muhasebe dosyası, Hepsiburada
"Kayıt Bazlı Muhasebe Servisi" (GET /transactions/merchantId/{merchantId})
alanlarını (transactionId, transactionDate, paymentDate, type, amount,
orderNumber) taklit eder; desi / takip no / paymentStatus kolonları varsayımdır.

- siparisler(.csv|.xlsx)
- urunler(.csv|.xlsx)
- muhasebe_islemleri(.csv|.xlsx)
- iadeler(.csv|.xlsx)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from hakedis.ingest.okuyucu import oku_opsiyonel


def oku(klasor: Path | str, ayar: dict[str, Any]) -> dict[str, pd.DataFrame]:
    klasor = Path(klasor)
    return {
        "siparisler": oku_opsiyonel(klasor, "siparisler"),
        "urunler": oku_opsiyonel(klasor, "urunler"),
        "islemler": oku_opsiyonel(klasor, "muhasebe_islemleri"),
        "iadeler": oku_opsiyonel(klasor, "iadeler"),
    }
