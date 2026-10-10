"""Veri toplama katmanı.

- dosya okuyucular (CSV / XLSX) -> ham DataFrame'ler
- api_istemci: Trendyol / Hepsiburada okuma API'leri için TASLAK istemciler.
  Bu iskelette hiçbir ağ çağrısı yapılmaz.
"""
from hakedis.ingest.okuyucu import oku_tablo  # noqa: F401
