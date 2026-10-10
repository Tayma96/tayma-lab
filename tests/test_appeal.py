import openpyxl

from hakedis import appeal
from hakedis.modeller import Bulgu


def _b():
    return [Bulgu(kural="desi_farki", alt_tip="gonderi", platform="trendyol", siparis_no="ORNEK-TY-1",
                  tutar_tl=1234.5, guven=0.6, aciklama="Gönderi kargosu 5 desi...", kanit=[{"desi": 5}],
                  bulgu_id="TY-DES-0001", referans="TK1")]


def test_itiraz_metni_turkce_ve_tutar():
    m = appeal.itiraz_metni("trendyol", "desi_farki", _b(), "ÖRNEK Mağaza", "ORNEK-1", "Eylül 2026", "ek.xlsx")
    assert "Trendyol Satıcı Destek" in m and "ORNEK-TY-1" in m and "1.234,50 TL" in m
    assert "desi" in m and "ek.xlsx" in m and "SATICI EKLEMELİ" in m


def test_llm_varsayilan_kapali(ayar):
    assert appeal.llm_ile_iyilestir("metin", ayar) == "metin"


def test_kanit_excel(tmp_path):
    yol = tmp_path / "k.xlsx"
    appeal.kanit_excel(_b(), yol)
    wb = openpyxl.load_workbook(yol)
    assert wb.sheetnames == ["Ozet", "Kanitlar", "BILGI"]
    assert "ÖRNEK VERİ" in wb["BILGI"]["A2"].value
