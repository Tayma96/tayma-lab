from hakedis import config
from hakedis.rules import desi_farki
from hakedis.rules.ortak import tarife
from tests.conftest import kargo, siparis, veri


def _vs(fatura_desi, urun_desi=1.4, adet=1, tip="GONDERI", tutar=None):
    tutar = tarife(fatura_desi, config.yukle()) if tutar is None else tutar
    return veri(siparisler=[siparis("S1", adet=adet)],
                urunler=[{"barkod": "B1", "urun_desi": urun_desi}],
                kargolar=[kargo("K1", "S1", fatura_desi, tutar, tip=tip)])


def test_fazla_desi_farki_tarifeye_gore(ayar):
    b = desi_farki.kontrol(_vs(5), ayar)  # ürün 1.4 -> 2 desi
    assert len(b) == 1
    assert b[0].tutar_tl == round(tarife(5, ayar) - tarife(2, ayar), 2)
    assert b[0].kanit[0]["beklenen_desi"] == 2


def test_dogru_desi_bulgu_yok(ayar):
    assert desi_farki.kontrol(_vs(2), ayar) == []


def test_tolerans(ayar):
    a = config.guncelle(ayar, **{"kurallar.desi_farki.tolerans_desi": 1})
    assert desi_farki.kontrol(_vs(3), a) == []
    assert len(desi_farki.kontrol(_vs(4), a)) == 1


def test_coklu_adet_paket_desisi(ayar):
    # 2 adet x 1.4 = 2.8 -> 3 desi; 3 desi faturası doğru
    assert desi_farki.kontrol(_vs(3, adet=2), ayar) == []


def test_iade_kargosu_dusuk_guven(ayar):
    b = desi_farki.kontrol(_vs(5, tip="IADE"), ayar)
    assert b[0].alt_tip == "iade_kargosu" and b[0].guven == ayar["guven"]["desi_farki_iade"]


def test_faturalanan_tutar_tarifeden_dusukse_bulgu_yok(ayar):
    assert desi_farki.kontrol(_vs(5, tutar=10.0), ayar) == []
