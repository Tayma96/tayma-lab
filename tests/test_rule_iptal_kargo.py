from hakedis.rules import iptal_kargo
from tests.conftest import kargo, siparis, veri


def test_iptal_siparise_kargo(ayar):
    vs = veri(siparisler=[siparis("S1", durum="IPTAL")], kargolar=[kargo("K1", "S1", 2, 68.5)])
    b = iptal_kargo.kontrol(vs, ayar)
    assert len(b) == 1 and b[0].tutar_tl == 68.5 and b[0].alt_tip == "iptal"
    assert b[0].guven == ayar["guven"]["iptal_kargo_iptal"]


def test_teslim_edilen_siparis_bulgu_yok(ayar):
    vs = veri(siparisler=[siparis("S1")], kargolar=[kargo("K1", "S1", 2, 68.5)])
    assert iptal_kargo.kontrol(vs, ayar) == []


def test_teslim_edilemeyen_dusuk_guven(ayar):
    vs = veri(siparisler=[siparis("S1", durum="TESLIM_EDILEMEDI")], kargolar=[kargo("K1", "S1", 2, 68.5)])
    b = iptal_kargo.kontrol(vs, ayar)
    assert b[0].alt_tip == "teslim_edilemedi" and b[0].guven < ayar["esikler"]["min_guven"]


def test_iade_kargosu_sayilmaz(ayar):
    vs = veri(siparisler=[siparis("S1", durum="IPTAL")], kargolar=[kargo("K1", "S1", 2, 68.5, tip="IADE")])
    assert iptal_kargo.kontrol(vs, ayar) == []
