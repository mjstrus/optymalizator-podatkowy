"""Testy projekcji skumulowanego majątku po 1 / 5 / 10 latach."""
import pytest

from optymalizator.engine import run_optimization
from optymalizator.majatek import ProjekcjaMajatku, projekcja_majatku
from optymalizator.models import DaneKlienta


def test_skumulowany_bez_wzrostu_to_netto_razy_lata():
    w = run_optimization(DaneKlienta(przychod=400_000, koszty=50_000,
                                     stawka_ryczaltu=0.12))
    proj = projekcja_majatku(w, lata=(1, 5, 10), stopa=0.0)
    assert all(isinstance(p, ProjekcjaMajatku) for p in proj)
    skala = next(p for p in proj if p.forma == "Skala")
    netto = next(f for f in w.formy if f.nazwa == "Skala").dochod_netto
    assert skala.wartosci[1] == pytest.approx(netto)
    assert skala.wartosci[5] == pytest.approx(5 * netto)
    assert skala.wartosci[10] == pytest.approx(10 * netto)


def test_tylko_dostepne_formy():
    w = run_optimization(DaneKlienta(przychod=300_000, koszty=50_000,
                                     stawka_ryczaltu=0.12, byly_pracodawca=True))
    proj = projekcja_majatku(w)
    nazwy = {p.forma for p in proj}
    assert "Ryczałt" not in nazwy and "Liniowy" not in nazwy
    assert "Skala" in nazwy


def test_rekomendacja_oznaczona():
    w = run_optimization(DaneKlienta(przychod=500_000, koszty=20_000,
                                     stawka_ryczaltu=0.12))
    proj = projekcja_majatku(w)
    rek = [p for p in proj if p.rekomendowana]
    assert len(rek) == 1 and rek[0].forma == w.werdykt


def test_wzrost_kapitalizuje_przy_dodatniej_stopie():
    w = run_optimization(DaneKlienta(przychod=400_000, koszty=50_000,
                                     stawka_ryczaltu=0.12))
    proj = projekcja_majatku(w, lata=(1, 5, 10), stopa=0.05)
    skala = next(p for p in proj if p.forma == "Skala")
    netto = next(f for f in w.formy if f.nazwa == "Skala").dochod_netto
    # FV renty rocznej: po 10 latach więcej niż 10× netto (kapitalizacja)
    assert skala.wartosci[10] > 10 * netto
    assert skala.wartosci[1] == pytest.approx(netto)  # po 1 roku bez wzrostu


def test_wyzsze_netto_wyzszy_majatek():
    w = run_optimization(DaneKlienta(przychod=500_000, koszty=20_000,
                                     stawka_ryczaltu=0.12))
    proj = projekcja_majatku(w, lata=(10,))
    najlepszy = max(proj, key=lambda p: p.wartosci[10])
    assert najlepszy.forma == w.werdykt
