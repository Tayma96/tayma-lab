import pandas as pd
import pytest

from hakedis import normalize
from hakedis.ingest import api_istemci, trendyol_dosya
from hakedis.ingest.okuyucu import oku_tablo


def test_csv_yorum_satirlari_atlanir(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text("# ÖRNEK VERİ\nx,y\n1,2\n", encoding="utf-8")
    df = oku_tablo(p)
    assert list(df.columns) == ["x", "y"] and len(df) == 1


def test_excel_kolon_eslemesi_ve_bilgi_sayfasi(tmp_path, ayar):
    p = tmp_path / "trendyol" / "siparisler.xlsx"
    p.parent.mkdir()
    with pd.ExcelWriter(p) as w:
        pd.DataFrame({"BILGI": ["ÖRNEK"]}).to_excel(w, sheet_name="BILGI", index=False)
        pd.DataFrame([{"Sipariş Numarası": "ORNEK-1", "Barkod": "B", "Sipariş Statüsü": "Cancelled",
                       "Faturalanacak Tutar": "100", "Komisyon Oranı": "15"}]).to_excel(w, sheet_name="S", index=False)
    vs = normalize.trendyol(trendyol_dosya.oku(p.parent, ayar))
    r = vs.siparisler.iloc[0]
    assert r.siparis_no == "ORNEK-1" and r.durum == "IPTAL" and r.komisyon_orani == 0.15


def test_api_istemcisi_ag_cagrisi_yapmaz():
    ist = api_istemci.TrendyolOkumaIstemcisi(999)
    planlar = ist.settlements(pd.Timestamp("2026-07-01").to_pydatetime(),
                              pd.Timestamp("2026-08-01").to_pydatetime(), ["Sale", "Return"])
    assert len(planlar) == 3  # 15 günlük pencereler
    assert all(p.metod == "GET" for p in planlar)
    with pytest.raises(api_istemci.CanliApiKapali):
        planlar[0].calistir()
    assert api_istemci.CANLI_API_KAPALI is True
