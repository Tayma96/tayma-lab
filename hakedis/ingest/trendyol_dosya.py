"""Trendyol dosya okuyucu.

Beklenen dosyalar (klasör: <girdi>/trendyol/). Kolon adları Trendyol Partner API
yanıt alanlarını taklit eder (bkz. docs/KAYNAKLAR.md):

- siparisler(.csv|.xlsx)      getShipmentPackages (v2/orders) satırları, satır başına 1 ürün.
                               Panel Excel'i ise config.kolon_eslemesi.trendyol_siparis_excel ile eşlenir.
- urunler(.csv|.xlsx)          filterProducts: barcode, title, dimensionalWeight (desi)
- settlements(.csv)            Cari hesap ekstresi - settlements (Sale, Return, CommissionNegative, ...)
- otherfinancials(.csv)        Cari hesap ekstresi - otherfinancials (DeductionInvoices, PaymentOrder, FinancialItem)
                               + transactionTypeCode kolonu (sorguda kullanılan tip)
- kargo_fatura_detay(.csv)     cargo-invoice/{invoiceSerialNumber}/items
- claims(.csv)                 getClaims satırları (claimItemStatus)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from hakedis.ingest.okuyucu import oku_opsiyonel


def oku(klasor: Path | str, ayar: dict[str, Any]) -> dict[str, pd.DataFrame]:
    klasor = Path(klasor)
    eslesme = (ayar.get("kolon_eslemesi") or {}).get("trendyol_siparis_excel")
    return {
        "siparisler": oku_opsiyonel(klasor, "siparisler", eslesme),
        "urunler": oku_opsiyonel(klasor, "urunler"),
        "settlements": oku_opsiyonel(klasor, "settlements"),
        "otherfinancials": oku_opsiyonel(klasor, "otherfinancials"),
        "kargo": oku_opsiyonel(klasor, "kargo_fatura_detay"),
        "claims": oku_opsiyonel(klasor, "claims"),
    }
