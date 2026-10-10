import pandas as pd

from hakedis.rules import odenmeyen_hakedis
from tests.conftest import hareket, siparis, veri

T = pd.Timestamp


def _satis(odendi, odeme_tarihi):
    return hareket("S1", "SATIS", tutar=1000, komisyon_tutari=150, satici_hakedis=850, odendi=odendi,
                   odeme_no="P1" if odendi else None, odeme_tarihi=T(odeme_tarihi))


def test_vadesi_gecmis_odenmemis(ayar):
    vs = veri(siparisler=[siparis("S1")], hareketler=[_satis(False, "2026-09-02")])
    b = odenmeyen_hakedis.kontrol(vs, ayar)
    assert len(b) == 1 and b[0].tutar_tl == 850 and b[0].alt_tip == "odeme_yok"


def test_odenmis(ayar):
    vs = veri(siparisler=[siparis("S1")], hareketler=[_satis(True, "2026-09-02")])
    assert odenmeyen_hakedis.kontrol(vs, ayar) == []


def test_vadesi_gelmemis(ayar):
    vs = veri(siparisler=[siparis("S1")], hareketler=[_satis(False, "2026-10-07")])
    assert odenmeyen_hakedis.kontrol(vs, ayar) == []


def test_satis_kaydi_yok_tahmin(ayar):
    vs = veri(siparisler=[siparis("S1", teslim_tarihi=T("2026-08-04"))])
    b = odenmeyen_hakedis.kontrol(vs, ayar)
    assert b[0].alt_tip == "satis_kaydi_yok" and b[0].tutar_tl == 850.0


def test_yeni_teslim_kayit_bekleniyor(ayar):
    vs = veri(siparisler=[siparis("S1", teslim_tarihi=T("2026-10-05"))])
    assert odenmeyen_hakedis.kontrol(vs, ayar) == []


def test_iptal_siparis_kontrol_edilmez(ayar):
    vs = veri(siparisler=[siparis("S1", durum="IPTAL")])
    assert odenmeyen_hakedis.kontrol(vs, ayar) == []
