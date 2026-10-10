import pandas as pd
import pytest

from hakedis import billing, tahsilat
from hakedis.takip import GecersizGecis, Vaka, VakaDefteri
from tests.conftest import hareket, veri


def defter():
    d = VakaDefteri([Vaka("TY-IKO-0001", "trendyol", "iade_komisyonu", "S1", 150.0),
                     Vaka("TY-DES-0001", "trendyol", "desi_farki", "S2", 40.0),
                     Vaka("TY-MUK-0001", "trendyol", "mukerrer_kesinti", "S3", 60.0)])
    for v in d.vakalar.values():
        v.gecis("itiraz_edildi", "2026-10-12")
    return d


def test_gecersiz_gecis():
    v = Vaka("X", "trendyol", "desi_farki", "S", 10.0)
    with pytest.raises(GecersizGecis):
        v.gecis("tahsil_edildi", "2026-10-10")


def test_kaydet_yukle(tmp_path):
    d = defter()
    d.kaydet(tmp_path)
    d2 = VakaDefteri.yukle(tmp_path)
    assert d2.vakalar["TY-IKO-0001"].durum == "itiraz_edildi"
    assert (tmp_path / "vakalar.csv").exists()


def test_tahsilat_tespiti_tam_kismi_ve_eslesmeyen(ayar):
    d = defter()
    sonraki = veri(hareketler=[
        hareket("S1", "CommissionNegative", islem_id="D1", tutar=150.0),
        hareket("S2", "FinancialItem", islem_id="D2", tutar=20.0),       # kısmi
        hareket("S1", "FinancialItem", islem_id="D3", tutar=99.0),       # S1 için desi vakası yok -> eşleşmez
    ])
    es = tahsilat.tespit_et(d, sonraki, ayar, "2026-11-04")
    assert d.vakalar["TY-IKO-0001"].durum == "tahsil_edildi"
    assert d.vakalar["TY-DES-0001"].tahsil_tutari == 20.0 and d.vakalar["TY-DES-0001"].durum == "tahsil_edildi"
    assert d.vakalar["TY-MUK-0001"].durum == "itiraz_edildi"
    assert es.vaka_id.isna().sum() == 1


def test_red_sonrasi_duzeltme_kabule_doner(ayar):
    d = defter()
    tahsilat.sonuclari_uygula(d, pd.DataFrame([{"platform": "trendyol", "siparis_no": "S3",
                                                "kural": "mukerrer_kesinti", "sonuc": "red"}]), "2026-10-20")
    assert d.vakalar["TY-MUK-0001"].durum == "red"
    tahsilat.tespit_et(d, veri(hareketler=[hareket("S3", "FinancialItem", tutar=60.0)]), ayar, "2026-11-04")
    assert d.vakalar["TY-MUK-0001"].durum == "tahsil_edildi"


def test_ucret_kademeli(ayar):
    u = billing.ucret_hesapla(60000, ayar)
    assert u["net_ucret"] == 50000 * 0.25 + 10000 * 0.20
    assert u["kdv"] == round(u["net_ucret"] * 0.20, 2)


def test_ucret_kural_ozel_orani(ayar):
    u = billing.ucret_kalemlerden([("iade_komisyonu", 1000), ("odenmeyen_hakedis", 1000)], ayar)
    assert u["net_ucret"] == 250 + 100 and u["tahsil_tutari"] == 2000


def test_fatura_taslagi_sadece_tahsil_edilenler(ayar):
    d = defter()
    tahsilat.tespit_et(d, veri(hareketler=[hareket("S1", "CommissionNegative", tutar=150.0)]), ayar, "2026-11-04")
    f = billing.fatura_taslagi(d, {"ad": "ÖRNEK", "id": "0"}, "Ekim", ayar, "TASLAK-1")
    assert [k["vaka_id"] for k in f["kalemler"]] == ["TY-IKO-0001"] and f["hesap"]["net_ucret"] == 37.5
    assert "TASLAK" in f["durum"]
    assert billing.fatura_taslagi(d, {"ad": "ÖRNEK", "id": "0"}, "Ekim", ayar, "TASLAK-2") is None  # çift fatura yok
