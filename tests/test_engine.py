"""Testy Unit 2: silnik deterministyczny run_optimization.

Test-first — to rdzeń finansowy, poprawność liczb jest krytyczna.
Scenariusze 1:1 z planu (sekcja Unit 2 / Scenariusze testowe).
"""
import pytest

from optymalizator import params_2026 as P
from optymalizator.engine import run_optimization
from optymalizator.models import DaneKlienta, FormaZUS, Dostepnosc


def _forma(wynik, fragment):
    """Znajdź WynikFormy po fragmencie nazwy."""
    for f in wynik.formy:
        if fragment.lower() in f.nazwa.lower():
            return f
    raise AssertionError(f"Brak formy {fragment} w {[f.nazwa for f in wynik.formy]}")


# Scenariusz 1: wysoki dochód, niskie koszty → ryczałt korzystniejszy
def test_wysoki_dochod_niskie_koszty_ryczalt_wygrywa():
    d = DaneKlienta(przychod=500_000, koszty=20_000, stawka_ryczaltu=0.12)
    w = run_optimization(d)
    rycz = _forma(w, "rycz")
    skala = _forma(w, "skala")
    liniowy = _forma(w, "liniow")
    assert rycz.dochod_netto > skala.dochod_netto
    assert rycz.dochod_netto > liniowy.dochod_netto
    assert "rycz" in w.werdykt.lower()


# Scenariusz 2: wysokie koszty → skala/liniowy biją ryczałt
def test_wysokie_koszty_skala_bije_ryczalt():
    d = DaneKlienta(przychod=300_000, koszty=200_000, stawka_ryczaltu=0.12)
    w = run_optimization(d)
    assert _forma(w, "skala").dochod_netto > _forma(w, "rycz").dochod_netto
    assert _forma(w, "liniow").dochod_netto > _forma(w, "rycz").dochod_netto


# Scenariusz 3: byly_pracodawca → ryczałt i liniowy NIEDOSTĘPNE
def test_byly_pracodawca_blokuje_ryczalt_i_liniowy():
    d = DaneKlienta(przychod=300_000, koszty=50_000, stawka_ryczaltu=0.12,
                    byly_pracodawca=True)
    w = run_optimization(d)
    assert _forma(w, "rycz").dostepnosc == Dostepnosc.NIEDOSTEPNA
    assert _forma(w, "liniow").dostepnosc == Dostepnosc.NIEDOSTEPNA
    assert _forma(w, "skala").dostepnosc == Dostepnosc.DOSTEPNA
    # werdykt tylko spośród dostępnych
    assert w.werdykt.lower() in ("skala", "sp. z o.o.")


# Scenariusz 4: przychód > 2 mln EUR → ryczałt NIEDOSTĘPNY
def test_przychod_powyzej_2mln_eur_blokuje_ryczalt():
    d = DaneKlienta(przychod=10_000_000, koszty=100_000, stawka_ryczaltu=0.12)
    w = run_optimization(d)
    assert _forma(w, "rycz").dostepnosc == Dostepnosc.NIEDOSTEPNA


# Scenariusz 5: wspólne rozliczenie, małżonek bez dochodu → skala zyskuje
def test_wspolne_rozliczenie_zwieksza_korzysc_skali():
    base = dict(przychod=300_000, koszty=50_000, stawka_ryczaltu=0.12)
    bez = run_optimization(DaneKlienta(**base))
    ze = run_optimization(DaneKlienta(**base, wspolne_rozliczenie=True,
                                      dochod_malzonka=0))
    assert _forma(ze, "skala").dochod_netto > _forma(bez, "skala").dochod_netto


# Scenariusz 6: dochód bardzo niski / strata → zdrowotna = minimum 5 072,90
def test_strata_zdrowotna_to_minimum():
    d = DaneKlienta(przychod=10_000, koszty=20_000, stawka_ryczaltu=0.12)
    w = run_optimization(d)
    assert _forma(w, "skala").zdrowotna == pytest.approx(P.ZDROWOTNA_MIN_ROCZNA)
    assert _forma(w, "skala").zdrowotna != pytest.approx(12 * P.ZDROWOTNA_MIN_MIES)


# Scenariusz 7: liniowy, zdrowotna > 14 100 → odliczenie capped
def test_liniowy_odliczenie_zdrowotnej_capped():
    d = DaneKlienta(przychod=400_000, koszty=20_000)
    w = run_optimization(d)
    lin = _forma(w, "liniow")
    D = 400_000 - 20_000 - P.ZUS_DUZY_ROCZNY
    assert lin.zdrowotna > P.LINIOWY_LIMIT_ODLICZENIA  # zapłacona przekracza limit
    oczek_podatek = P.LINIOWY_STAWKA * (D - P.LINIOWY_LIMIT_ODLICZENIA)
    assert lin.podatek == pytest.approx(oczek_podatek, rel=1e-6)


# Scenariusz 8: ryczałt II próg → 50% zdrowotnej pomniejsza przychód
def test_ryczalt_50pct_zdrowotnej_pomniejsza_podstawe():
    d = DaneKlienta(przychod=200_000, koszty=10_000, stawka_ryczaltu=0.12)
    w = run_optimization(d)
    rycz = _forma(w, "rycz")
    assert rycz.zdrowotna == pytest.approx(P.RYCZALT_ZDROWOTNA_SREDNI)
    podstawa = 200_000 - P.ZUS_DUZY_ROCZNY - 0.5 * P.RYCZALT_ZDROWOTNA_SREDNI
    assert rycz.podatek == pytest.approx(0.12 * podstawa, rel=1e-6)


# Scenariusz 9: jednoosobowa sp. z o.o. → doliczona zdrowotna + ZUS
def test_jednoosobowa_spzoo_gorsza_od_wieloosobowej():
    base = dict(przychod=400_000, koszty=100_000)
    wielo = run_optimization(DaneKlienta(**base))
    jedno = run_optimization(DaneKlienta(**base, jednoosobowa_spzoo=True))
    f_jedno = _forma(jedno, "z o.o")
    f_wielo = _forma(wielo, "z o.o")
    assert f_jedno.zus_spoleczny > 0
    assert f_jedno.zdrowotna > 0
    assert f_jedno.dochod_netto < f_wielo.dochod_netto


# Scenariusz 10: dochód > 282 600 → podstawa ZUS ograniczona (składka flat)
def test_zus_nie_rosnie_z_dochodem():
    d = DaneKlienta(przychod=1_000_000, koszty=0, forma_zus=FormaZUS.DUZY)
    w = run_optimization(d)
    assert _forma(w, "skala").zus_spoleczny == pytest.approx(P.ZUS_DUZY_ROCZNY)


# Weryfikacja: werdykt zwraca poprawną różnicę do drugiej opcji
def test_werdykt_roznica_do_drugiej():
    d = DaneKlienta(przychod=500_000, koszty=20_000, stawka_ryczaltu=0.12)
    w = run_optimization(d)
    dostepne = sorted(
        [f.dochod_netto for f in w.formy if f.dostepnosc == Dostepnosc.DOSTEPNA],
        reverse=True,
    )
    assert w.roznica_do_drugiej == pytest.approx(dostepne[0] - dostepne[1])
