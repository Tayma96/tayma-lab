from hakedis import config
from hakedis.modeller import Bulgu
from hakedis.puanlama import paketler, puanla


def B(kural, tutar, guven=0.9, anahtar=None, platform="trendyol", sip="S"):
    return Bulgu(kural=kural, alt_tip="x", platform=platform, siparis_no=sip, tutar_tl=tutar, guven=guven,
                 aciklama="", kaynak_anahtarlar=[anahtar or f"{kural}:{sip}:{tutar}"])


def test_esikler_ve_kararlar(ayar):
    a = config.guncelle(ayar, **{"esikler.min_donem_tutari_tl": 0})
    b = puanla([B("iade_komisyonu", 300), B("iade_komisyonu", 5, sip="S2"), B("desi_farki", 50, guven=0.3),
                B("desi_farki", 40, sip="S3")], a)
    karar = {(x.kural, x.siparis_no): x.karar for x in b}
    assert karar[("iade_komisyonu", "S")] == "dosyalanacak"
    assert karar[("iade_komisyonu", "S2")] == "esik_alti"
    assert karar[("desi_farki", "S")] == "incelenmeli"
    assert karar[("desi_farki", "S3")] == "devreden"  # paket toplamı 40 < 250


def test_cakisma_cift_sayimi_engeller(ayar):
    b = puanla([B("desi_farki", 600, anahtar="kargo:K1"), B("iptal_kargo", 600, anahtar="kargo:K1")], ayar)
    karar = {x.kural: x.karar for x in b}
    assert karar["iptal_kargo"] == "dosyalanacak" and karar["desi_farki"] == "cakisma"


def test_donem_esigi(ayar):
    b = puanla([B("iade_komisyonu", 300)], ayar)  # 300 < 500
    assert b[0].karar == "donem_esik_alti"


def test_beklenen_ve_id(ayar):
    b = puanla([B("mukerrer_kesinti", 1000, guven=0.9)], ayar)
    assert b[0].beklenen_tl == 900 and b[0].bulgu_id == "TY-MUK-0001" and b[0].oncelik == "yuksek"
    assert list(paketler(b)) == [("trendyol", "mukerrer_kesinti")]
