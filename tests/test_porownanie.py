"""Test porównania wariantów A/B."""
from optymalizator import ui_components as UI
from optymalizator.engine import run_optimization
from optymalizator.models import DaneKlienta


def test_wiersze_porownanie_roznica():
    w = run_optimization(DaneKlienta(przychod=500_000, koszty=20_000,
                                     stawka_ryczaltu=0.12))
    # baza = obecne netto minus 1000 na kazdej formie
    baza = {f.nazwa: f.dochod_netto - 1000 for f in w.formy}
    wiersze = UI.wiersze_porownanie(baza, w)
    assert len(wiersze) == len(w.formy)
    naglowki = set(wiersze[0])
    assert {"Forma", "Wariant A (bazowy)", "Wariant B (obecny)", "Różnica"} == naglowki
    # roznica dodatnia (B wyzsze o 1000) → zaczyna sie od +
    assert all(r["Różnica"].startswith("+") for r in wiersze)


def test_porownanie_brak_formy_w_bazie():
    w = run_optimization(DaneKlienta(przychod=500_000, koszty=20_000,
                                     stawka_ryczaltu=0.12))
    wiersze = UI.wiersze_porownanie({}, w)   # pusta baza
    assert all(r["Różnica"] == "—" for r in wiersze)
