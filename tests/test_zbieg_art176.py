"""Testy: zbieg tytułów (etat poza JDG) + art. 176 KSH w sp. z o.o."""
import pytest

from optymalizator import params_2026 as P
from optymalizator.engine import run_optimization
from optymalizator.models import DaneKlienta, Dostepnosc


def _forma(w, frag):
    return next(f for f in w.formy if frag.lower() in f.nazwa.lower())


# --- Zbieg tytułów: etat poza JDG → brak ZUS społecznego --------------------
def test_etat_poza_jdg_zeruje_zus_spoleczny():
    w = run_optimization(DaneKlienta(przychod=300_000, koszty=50_000,
                                     stawka_ryczaltu=0.12, etat_poza_jdg=True))
    assert _forma(w, "skala").zus_spoleczny == 0.0
    assert _forma(w, "liniow").zus_spoleczny == 0.0
    assert _forma(w, "rycz").zus_spoleczny == 0.0


def test_zbieg_zwieksza_netto():
    base = dict(przychod=300_000, koszty=50_000, stawka_ryczaltu=0.12)
    bez = run_optimization(DaneKlienta(**base))
    ze = run_optimization(DaneKlienta(**base, etat_poza_jdg=True))
    assert _forma(ze, "skala").dochod_netto > _forma(bez, "skala").dochod_netto


# --- Art. 176 KSH -----------------------------------------------------------
def test_art176_auto_do_pierwszego_progu():
    d = DaneKlienta(przychod=600_000, koszty=50_000, art_176=True)
    w = run_optimization(d)
    spzoo = _forma(w, "z o.o")
    # świadczenia = min(zysk, próg 120 000); PIT skali od tej kwoty bez ZUS
    assert spzoo.swiadczenia_art176 == pytest.approx(P.SKALA_PROG)


def test_art176_poprawia_netto_spzoo():
    # Pełna dywidenda (bez kanałów) vs art.176 — art.176 musi dać wyższe netto.
    base = dict(przychod=600_000, koszty=50_000)
    bez = run_optimization(DaneKlienta(**base, art_176=False, powolanie_zarzad=False))
    ze = run_optimization(DaneKlienta(**base, art_176=True))
    assert _forma(ze, "z o.o").dochod_netto > _forma(bez, "z o.o").dochod_netto


def test_art176_kwota_podana_przez_doradce():
    d = DaneKlienta(przychod=600_000, koszty=50_000, art_176=True,
                    art_176_kwota=80_000)
    spzoo = _forma(run_optimization(d), "z o.o")
    assert spzoo.swiadczenia_art176 == pytest.approx(80_000)


def test_art176_zachowuje_tozsamosc_waterfalla():
    from optymalizator.oszczednosci import rozbij_przewage
    w = run_optimization(DaneKlienta(przychod=900_000, koszty=40_000,
                                     byly_pracodawca=True, art_176=True))
    spzoo = _forma(w, "z o.o")
    jdg = max((f for f in w.formy if "z o.o" not in f.nazwa.lower()
               and f.dostepnosc == Dostepnosc.DOSTEPNA),
              key=lambda f: f.dochod_netto)
    r = rozbij_przewage(spzoo, jdg)
    assert sum(linia.kwota for linia in r.linie) == pytest.approx(r.netto, abs=0.01)
