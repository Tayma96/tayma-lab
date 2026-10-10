import pandas as pd

from hakedis.rules import dayanaksiz_kesinti
from tests.conftest import kesinti, siparis, veri

T = pd.Timestamp


def test_termin_icinde_kargolanana_ceza(ayar):
    vs = veri(siparisler=[siparis("S1", sevk_tarihi=T("2026-08-02"), termin_tarihi=T("2026-08-03"))],
              kesintiler=[kesinti("X1", "S1", "Termin Gecikme Bedeli", 45)])
    b = dayanaksiz_kesinti.kontrol(vs, ayar)
    assert len(b) == 1 and b[0].alt_tip == "termin_cezasi" and b[0].tutar_tl == 45


def test_gec_kargolanana_ceza_hakli(ayar):
    vs = veri(siparisler=[siparis("S1", sevk_tarihi=T("2026-08-05"), termin_tarihi=T("2026-08-03"))],
              kesintiler=[kesinti("X1", "S1", "Termin Gecikme Bedeli", 45)])
    assert dayanaksiz_kesinti.kontrol(vs, ayar) == []


def test_teslim_edilene_tedarik_cezasi(ayar):
    vs = veri(siparisler=[siparis("S1")], kesintiler=[kesinti("X1", "S1", "Tedarik Edememe Bedeli", 120)])
    assert dayanaksiz_kesinti.kontrol(vs, ayar)[0].alt_tip == "tedarik_cezasi"


def test_tedarik_edilemeyene_ceza_hakli(ayar):
    vs = veri(siparisler=[siparis("S1", durum="TEDARIK_EDILEMEDI")],
              kesintiler=[kesinti("X1", "S1", "Tedarik Edememe Bedeli", 120)])
    assert dayanaksiz_kesinti.kontrol(vs, ayar) == []


def test_bilinmeyen_tip_dusuk_guven(ayar):
    vs = veri(siparisler=[siparis("S1")], kesintiler=[kesinti("X1", None, "Gizemli Bedel", 95),
                                                      kesinti("X2", None, "Reklam Bedeli", 500)])
    b = dayanaksiz_kesinti.kontrol(vs, ayar)
    assert len(b) == 1 and b[0].alt_tip == "bilinmeyen_tip" and b[0].guven < ayar["esikler"]["min_guven"]
