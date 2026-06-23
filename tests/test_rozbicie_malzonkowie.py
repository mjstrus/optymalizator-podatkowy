"""Testy: rozbicie dochodu na małżonka 1 (klient) i 2 przy R15."""
import pytest

from optymalizator import ui_components as UI
from optymalizator.engine import run_optimization
from optymalizator.models import DaneKlienta


def _forma(w, frag):
    return next(f for f in w.formy if frag.lower() in f.nazwa.lower())


def test_jdg_ma_rozbicie_na_dwoje():
    d = DaneKlienta(przychod=600_000, koszty=50_000, stawka_ryczaltu=0.12,
                    malzonek_do_spolki=True, malzonek_przychod=300_000,
                    malzonek_koszty=30_000)
    w = run_optimization(d)
    lin = _forma(w, "liniow")
    assert lin.dochod_netto_klient is not None
    assert lin.dochod_netto_malzonek is not None
    assert lin.dochod_netto == pytest.approx(
        lin.dochod_netto_klient + lin.dochod_netto_malzonek, abs=0.01)


def test_spzoo_dochod_wspolny_bez_rozbicia():
    d = DaneKlienta(przychod=600_000, koszty=50_000,
                    malzonek_do_spolki=True, malzonek_przychod=300_000,
                    malzonek_koszty=30_000)
    spzoo = _forma(run_optimization(d), "z o.o")
    assert spzoo.dochod_netto_klient is None  # spółka = jeden podmiot


def test_brak_r15_brak_rozbicia():
    w = run_optimization(DaneKlienta(przychod=600_000, koszty=50_000,
                                     stawka_ryczaltu=0.12))
    assert _forma(w, "liniow").dochod_netto_klient is None


def test_ui_wiersze_rozbicia_malzonkowie():
    d = DaneKlienta(przychod=600_000, koszty=50_000, stawka_ryczaltu=0.12,
                    malzonek_do_spolki=True, malzonek_przychod=300_000,
                    malzonek_koszty=30_000)
    wiersze = UI.wiersze_rozbicie_malzonkowie(run_optimization(d))
    assert wiersze  # są wiersze dla form JDG
    naglowki = set(wiersze[0].keys())
    assert {"Forma", "Małżonek 1 (klient)", "Małżonek 2", "Razem"} <= naglowki
