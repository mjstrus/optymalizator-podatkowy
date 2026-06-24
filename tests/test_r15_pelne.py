"""Testy R15: ZUS małżonka + tabela couple-level + 2-osobowe optimum spółki."""
import pytest

from optymalizator.engine import run_optimization
from optymalizator.models import DaneKlienta, FormaZUS


def _f(w, frag):
    return next(f for f in w.formy if frag.lower() in f.nazwa.lower())


def _base():
    return dict(przychod=600_000, koszty=50_000, stawka_ryczaltu=0.12,
                malzonek_do_spolki=True, malzonek_przychod=400_000,
                malzonek_koszty=40_000)


# A) ZUS małżonka wpływa na jego samodzielny wynik (i couple-level)
def test_zus_malzonka_wplywa_na_wynik():
    duzy = run_optimization(DaneKlienta(**_base(),
                                        malzonek_forma_zus=FormaZUS.DUZY))
    plus = run_optimization(DaneKlienta(**_base(),
                                        malzonek_forma_zus=FormaZUS.MALY_ZUS_PLUS,
                                        malzonek_dochod_poprzedni_rok=30_000))
    # Mały ZUS Plus małżonka → niższy ZUS → wyższe couple-netto na liniowym
    assert _f(plus, "liniow").dochod_netto > _f(duzy, "liniow").dochod_netto


# B) Tabela couple-level: kolumny ZUS/podatek/zdrowotna sumują oboje
def test_kolumny_couple_level():
    w = run_optimization(DaneKlienta(**_base()))
    lin = _f(w, "liniow")
    # ZUS liniowego (para) = ZUS klienta + ZUS małżonka (dwie osobne JDG)
    from optymalizator import params_2026 as P
    assert lin.zus_spoleczny == pytest.approx(2 * P.ZUS_DUZY_ROCZNY, abs=1.0)


# C) 2-osobowe optimum spółki: dwa art. 176 → wyższe świadczenia niż dla jednej osoby
def test_dwa_art176_w_spolce_pary():
    para = run_optimization(DaneKlienta(**_base()))
    jedno = run_optimization(DaneKlienta(przychod=600_000, koszty=50_000,
                                         stawka_ryczaltu=0.12))
    # para: dwa progi art.176 → świadczenia ~2× próg; jedna osoba ~1×
    assert _f(para, "z o.o").swiadczenia_art176 > _f(jedno, "z o.o").swiadczenia_art176


def test_dwa_etaty_w_spolce_pary():
    para = run_optimization(DaneKlienta(**_base(), poziom_etatu=0.5))
    jedno = run_optimization(DaneKlienta(przychod=600_000, koszty=50_000,
                                         stawka_ryczaltu=0.12, poziom_etatu=0.5))
    # dwa etaty → ~2× ZUS od etatów niż przy jednej osobie
    assert _f(para, "z o.o").zus_spoleczny > 1.5 * _f(jedno, "z o.o").zus_spoleczny


def test_tozsamosc_netto_spzoo_para():
    w = run_optimization(DaneKlienta(**_base(), poziom_etatu=0.5))
    s = _f(w, "z o.o")
    zysk0 = (600_000 - 50_000) + (400_000 - 40_000)
    assert s.dochod_netto == pytest.approx(
        zysk0 - s.zus_spoleczny - s.zdrowotna - s.podatek, abs=0.1)
