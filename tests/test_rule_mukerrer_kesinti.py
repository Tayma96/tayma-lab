from hakedis.rules import mukerrer_kesinti
from tests.conftest import kargo, kesinti, veri


def test_ayni_takip_no_iki_kez(ayar):
    vs = veri(kargolar=[kargo("K1", "S1", 2, 68.5, takip="T1"), kargo("K2", "S1", 2, 68.5, takip="T1"),
                        kargo("K3", "S2", 2, 68.5, takip="T2")])
    b = mukerrer_kesinti.kontrol(vs, ayar)
    assert len(b) == 1 and b[0].tutar_tl == 68.5 and b[0].kaynak_anahtarlar == ["kargo:K2"]


def test_gonderi_ve_iade_kargosu_mukerrer_degil(ayar):
    vs = veri(kargolar=[kargo("K1", "S1", 2, 68.5, takip="T1"), kargo("K2", "S1", 2, 68.5, tip="IADE", takip="T1")])
    assert mukerrer_kesinti.kontrol(vs, ayar) == []


def test_tekil_kesinti_tekrari(ayar):
    vs = veri(kesintiler=[kesinti("X1", "S1", "Platform Hizmet Bedeli", 8.49),
                          kesinti("X2", "S1", "Platform Hizmet Bedeli", 8.49),
                          kesinti("X3", "S1", "Platform Hizmet Bedeli", 8.49)])
    b = mukerrer_kesinti.kontrol(vs, ayar)
    assert b[0].tutar_tl == 16.98 and b[0].alt_tip == "kesinti"


def test_tekil_olmayan_tip_mukerrer_sayilmaz(ayar):
    vs = veri(kesintiler=[kesinti("X1", "S1", "Reklam Bedeli", 50), kesinti("X2", "S1", "Reklam Bedeli", 50)])
    assert mukerrer_kesinti.kontrol(vs, ayar) == []
