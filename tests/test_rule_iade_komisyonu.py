from hakedis import config
from hakedis.rules import iade_komisyonu
from tests.conftest import hareket, veri


def _vs(iade_kom, claim="KABUL", iade_var=True):
    h = [hareket("S1", "SATIS", tutar=1000, komisyon_tutari=150, satici_hakedis=850)]
    if iade_var:
        h.append(hareket("S1", "IADE", tutar=-1000, komisyon_tutari=iade_kom, satici_hakedis=-(1000 - iade_kom)))
    return veri(hareketler=h, iadeler=[{"siparis_no": "S1", "durum": claim}])


def test_hic_iade_edilmeyen_komisyon(ayar):
    b = iade_komisyonu.kontrol(_vs(0.0), ayar)
    assert len(b) == 1 and b[0].tutar_tl == 150.0 and b[0].alt_tip == "hic_iade_edilmedi"


def test_eksik_iade(ayar):
    b = iade_komisyonu.kontrol(_vs(100.0), ayar)
    assert b[0].tutar_tl == 50.0 and b[0].alt_tip == "eksik_iade"


def test_tam_iade_bulgu_yok(ayar):
    assert iade_komisyonu.kontrol(_vs(150.0), ayar) == []


def test_reddedilen_iade_bulgu_yok(ayar):
    assert iade_komisyonu.kontrol(_vs(0.0, claim="RED"), ayar) == []


def test_iade_kaydi_yoksa_kayip_yok(ayar):
    assert iade_komisyonu.kontrol(_vs(0.0, iade_var=False), ayar) == []


def test_politika_kapatilabilir(ayar):
    a = config.guncelle(ayar, **{"kurallar.iade_komisyonu.iadede_komisyon_iade_edilir": False})
    assert iade_komisyonu.kontrol(_vs(0.0), a) == []
