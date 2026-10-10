"""ornek_veri/ üzerinde uçtan uca: ekilen her hata bulunmalı, fazlası olmamalı."""
from pathlib import Path

import pandas as pd

from hakedis import normalize, puanlama
from hakedis.cli import main
from hakedis.rules import tum_kurallari_calistir

KOK = Path(__file__).resolve().parent.parent
ORNEK = KOK / "ornek_veri"


def test_ekilen_hatalar_birebir_bulunur(ayar):
    vs = normalize.klasorden_yukle(ORNEK, ayar)
    assert vs.siparisler.siparis_no.nunique() == 200
    bulgular = puanlama.puanla(tum_kurallari_calistir(vs, ayar), ayar)
    beklenen = pd.read_csv(ORNEK / "beklenen_bulgular.csv", comment="#")
    anahtar = lambda p, k, s, t: (p, k, s if isinstance(s, str) else "-", round(float(t), 2))  # noqa: E731
    bulunan = {anahtar(b.platform, b.kural, b.siparis_no, b.tutar_tl) for b in bulgular}
    hedef = {anahtar(*r) for r in beklenen[["platform", "kural", "siparis_no", "tutar_tl"]].itertuples(index=False)}
    assert bulunan == hedef
    assert not any(b.karar == "cakisma" for b in bulgular)


def test_cli_scan_ve_simule(tmp_path):
    assert main(["scan", "--input", str(ORNEK), "--out", str(tmp_path / "s")]) == 0
    for ad in ("OZET.md", "bulgular.csv", "bulgular.xlsx", "vakalar.csv", "ozet.json"):
        assert (tmp_path / "s" / ad).exists()
    assert any((tmp_path / "s" / "itiraz").glob("*_itiraz.txt"))
    assert main(["simule", "--input", str(ORNEK), "--sonraki", str(ORNEK / "sonraki_donem"),
                 "--out", str(tmp_path / "m")]) == 0
    vt = pd.read_csv(tmp_path / "m" / "vakalar.csv")
    assert (vt.durum == "tahsil_edildi").any() and (tmp_path / "m" / "fatura_taslagi.json").exists()
    assert (vt.tahsil_tutari <= vt.talep_tutari + 0.01).all()
