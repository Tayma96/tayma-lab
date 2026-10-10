"""Komut satırı arayüzü.

    python -m hakedis scan    --input ornek_veri/ --out cikti/
    python -m hakedis simule  --input ornek_veri/ --sonraki ornek_veri/sonraki_donem/ --out cikti/ornek_sonuc/
    python -m hakedis tahsilat --vakalar cikti/ --sonraki <klasor> --out cikti/
    python -m hakedis durum   --vakalar cikti/ --vaka TY-IKO-0001 --yeni itiraz_edildi

Hiçbir komut ağ çağrısı yapmaz veya bir şey göndermez.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from hakedis import billing, config, normalize, puanlama, report, tahsilat
from hakedis.ingest.okuyucu import bul, oku_tablo
from hakedis.rules import tum_kurallari_calistir
from hakedis.takip import VakaDefteri


def _ornek_mi(girdi: Path) -> bool:
    return (girdi / "OKUBENI_ORNEK_VERI.md").exists()


def _satici(args) -> dict[str, str]:
    return {"ad": args.satici_adi, "id": args.satici_id}


def tara(girdi: Path, cikti: Path, ayar: dict, satici: dict, donem: str):
    vs = normalize.klasorden_yukle(girdi, ayar)
    bulgular = puanlama.puanla(tum_kurallari_calistir(vs, ayar), ayar)
    ozet = report.tarama_ciktilarini_yaz(cikti, vs, bulgular, ayar, satici, donem, _ornek_mi(girdi))
    tarih = str(config.analiz_tarihi(ayar))
    defter = VakaDefteri.bulgulardan(bulgular, tarih)
    defter.kaydet(cikti)
    return vs, bulgular, ozet, defter


def cmd_scan(args) -> int:
    ayar = config.yukle(args.config)
    _, _, ozet, defter = tara(Path(args.input), Path(args.out), ayar, _satici(args), args.donem)
    print(f"Taranan sipariş: {ozet['toplam_siparis']}  |  bulgu: {ozet['toplam_bulgu']}  |  "
          f"itiraza hazır: {report.tl(ozet['geri_alinabilir_tl'])}  |  vaka: {len(defter.vakalar)}")
    print(f"Çıktılar: {args.out} (OZET.md, bulgular.xlsx, itiraz/, vakalar.csv). Hiçbir şey gönderilmedi.")
    return 0


def _tahsilat_uygula(defter: VakaDefteri, sonraki: Path, ayar: dict, tarih: str):
    sonuc_yolu = bul(sonraki, "itiraz_sonuclari")
    if sonuc_yolu:
        tahsilat.sonuclari_uygula(defter, oku_tablo(sonuc_yolu), tarih)
    sonraki_vs = normalize.klasorden_yukle(sonraki, ayar)
    return tahsilat.tespit_et(defter, sonraki_vs, ayar, tarih)


def cmd_simule(args) -> int:
    ayar = config.yukle(args.config)
    girdi, cikti, sonraki = Path(args.input), Path(args.out), Path(args.sonraki)
    _, _, ozet, defter = tara(girdi, cikti, ayar, _satici(args), args.donem)
    # SİMÜLASYON VARSAYIMI: satıcı tüm paketleri kendi paneli üzerinden gönderdi.
    for v in defter.vakalar.values():
        v.gecis("itiraz_edildi", args.itiraz_tarihi, "SİMÜLASYON: satıcı tarafından panelden gönderildi varsayımı")
    eslesmeler = _tahsilat_uygula(defter, sonraki, ayar, args.tahsilat_tarihi)
    fatura = billing.fatura_taslagi(defter, _satici(args), args.donem, ayar, args.fatura_no)
    defter.kaydet(cikti)
    eslesmeler.to_csv(cikti / "tahsilat_eslesmeleri.csv", index=False)
    if fatura:
        (cikti / "fatura_taslagi.json").write_text(json.dumps(fatura, ensure_ascii=False, indent=2), encoding="utf-8")
    vt = defter.tablo()
    (cikti / "SIMULASYON.md").write_text(report.simulasyon_md(ozet, vt, eslesmeler, fatura), encoding="utf-8")
    print(f"Vaka: {len(vt)}  |  tahsil edilen: {report.tl(vt.tahsil_tutari.sum())}  |  "
          f"ücret (KDV hariç): {report.tl(fatura['hesap']['net_ucret']) if fatura else '0'}")
    return 0


def cmd_tahsilat(args) -> int:
    ayar = config.yukle(args.config)
    defter = VakaDefteri.yukle(Path(args.vakalar))
    tarih = str(config.analiz_tarihi(ayar))
    es = _tahsilat_uygula(defter, Path(args.sonraki), ayar, tarih)
    fatura = billing.fatura_taslagi(defter, _satici(args), args.donem, ayar, args.fatura_no)
    out = Path(args.out)
    defter.kaydet(out)
    es.to_csv(out / "tahsilat_eslesmeleri.csv", index=False)
    if fatura:
        (out / "fatura_taslagi.json").write_text(json.dumps(fatura, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Eşleşen düzeltme: {int(es.vaka_id.notna().sum()) if not es.empty else 0}")
    return 0


def cmd_durum(args) -> int:
    defter = VakaDefteri.yukle(Path(args.vakalar))
    defter.gecis(args.vaka, args.yeni, args.tarih or str(pd.Timestamp.today().date()), args.not_ or "")
    defter.kaydet(Path(args.vakalar))
    print(f"{args.vaka}: {defter.vakalar[args.vaka].durum}")
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hakedis", description="Pazaryeri hakediş geri kazanım tarayıcısı (offline)")
    p.add_argument("--config", default=None, help="config.yaml yolu")
    p.add_argument("--satici-adi", default="ÖRNEK Mağaza Ltd. (sentetik)")
    p.add_argument("--satici-id", default="ORNEK-999000001")
    p.add_argument("--donem", default="Temmuz-Eylül 2026")
    p.add_argument("--fatura-no", default="TASLAK-2026-0001")
    alt = p.add_subparsers(dest="komut", required=True)

    s = alt.add_parser("scan", help="Dosyaları tara, bulgu + itiraz taslağı üret")
    s.add_argument("--input", required=True)
    s.add_argument("--out", required=True)
    s.set_defaults(f=cmd_scan)

    m = alt.add_parser("simule", help="Tarama + varsayımsal itiraz + sonraki dönem tahsilat + fatura taslağı")
    m.add_argument("--input", required=True)
    m.add_argument("--sonraki", required=True)
    m.add_argument("--out", required=True)
    m.add_argument("--itiraz-tarihi", default="2026-10-12")
    m.add_argument("--tahsilat-tarihi", default="2026-11-04")
    m.set_defaults(f=cmd_simule)

    t = alt.add_parser("tahsilat", help="Sonraki dönem verisinde geri ödemeleri tespit et")
    t.add_argument("--vakalar", required=True)
    t.add_argument("--sonraki", required=True)
    t.add_argument("--out", required=True)
    t.set_defaults(f=cmd_tahsilat)

    d = alt.add_parser("durum", help="Vaka durumunu elle güncelle")
    d.add_argument("--vakalar", required=True)
    d.add_argument("--vaka", required=True)
    d.add_argument("--yeni", required=True, choices=["itiraz_edildi", "kabul", "red", "tahsil_edildi"])
    d.add_argument("--tarih")
    d.add_argument("--not", dest="not_")
    d.set_defaults(f=cmd_durum)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    # global seçenekler alt komuttan önce de sonra da verilebilsin diye varsayılanlar korunur
    return args.f(args)
