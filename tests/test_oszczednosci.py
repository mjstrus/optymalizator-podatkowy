"""Testy Unit 7: rozbicie przewagi sp. z o.o. + waterfall oszczędności."""
import pytest

from optymalizator.engine import run_optimization
from optymalizator.models import DaneKlienta, Dostepnosc
from optymalizator.oszczednosci import rozbij_przewage, RozbicieOszczednosci


def _spzoo(w):
    return next(f for f in w.formy if "z o.o" in f.nazwa.lower())


def _najlepsza_jdg(w):
    jdg = [f for f in w.formy
           if "z o.o" not in f.nazwa.lower()
           and f.dostepnosc == Dostepnosc.DOSTEPNA]
    return max(jdg, key=lambda f: f.dochod_netto)


def test_suma_linii_rowna_roznicy_netto():
    w = run_optimization(DaneKlienta(przychod=800_000, koszty=30_000,
                                     stawka_ryczaltu=0.12, poziom_etatu=0.5))
    spzoo, jdg = _spzoo(w), _najlepsza_jdg(w)
    r = rozbij_przewage(spzoo, jdg)
    assert isinstance(r, RozbicieOszczednosci)
    assert sum(l.kwota for l in r.linie) == pytest.approx(r.netto, abs=0.01)
    assert r.netto == pytest.approx(spzoo.dochod_netto - jdg.dochod_netto, abs=0.01)


def test_linia_zus_od_etatu_obecna_i_niezerowa():
    w = run_optimization(DaneKlienta(przychod=800_000, koszty=30_000,
                                     stawka_ryczaltu=0.12, poziom_etatu=0.5))
    r = rozbij_przewage(_spzoo(w), _najlepsza_jdg(w))
    etat = [l for l in r.linie if "etatu" in l.etykieta.lower()
            and "zus" in l.etykieta.lower()]
    assert etat and etat[0].kwota != 0
    assert etat[0].widoczna is True


def test_guardrail_linia_etatu_zawsze_obecna_nawet_zerowa():
    # poziom_etatu = 0 → brak etatu, ale linia musi być (z flagą widoczna).
    w = run_optimization(DaneKlienta(przychod=800_000, koszty=30_000,
                                     stawka_ryczaltu=0.12))
    r = rozbij_przewage(_spzoo(w), _najlepsza_jdg(w))
    etat = [l for l in r.linie if "etatu" in l.etykieta.lower()
            and "zus" in l.etykieta.lower()]
    assert etat and etat[0].widoczna is True


def test_blok_malzonka_gdy_podany():
    w = run_optimization(DaneKlienta(przychod=800_000, koszty=30_000,
                                     stawka_ryczaltu=0.12, poziom_etatu=0.5))
    wm = run_optimization(DaneKlienta(przychod=400_000, koszty=20_000,
                                      stawka_ryczaltu=0.12, poziom_etatu=0.5))
    spzoo, jdg = _spzoo(w), _najlepsza_jdg(w)
    spzoo_m, jdg_m = _spzoo(wm), _najlepsza_jdg(wm)
    r = rozbij_przewage(spzoo, jdg, spzoo_malzonek=spzoo_m, jdg_malzonek=jdg_m)
    assert any("małżon" in l.etykieta.lower() for l in r.linie)
    # netto = suma wszystkich linii (klient + małżonek)
    assert sum(l.kwota for l in r.linie) == pytest.approx(r.netto, abs=0.01)
