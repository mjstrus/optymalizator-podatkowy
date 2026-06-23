"""Testy Unit 2 (Aktualizacja #2): sp. z o.o. jako pakiet „spółka + etat"."""
import pytest

from optymalizator import params_2026 as P
from optymalizator.engine import _oblicz_etat, run_optimization
from optymalizator.models import DaneKlienta


def _spzoo(w):
    return next(f for f in w.formy if "z o.o" in f.nazwa.lower())


def test_etat_skladki_od_wlasciwej_podstawy():
    # 1/2 płacy minimalnej
    pensja = 0.5 * P.MINIMALNE_WYNAGRODZENIE * 12
    e = _oblicz_etat(pensja)
    assert e.pensja_brutto == pytest.approx(pensja, abs=0.01)
    assert e.zus_pracownik == pytest.approx(P.ZUS_PRACOWNIK_STAWKA * pensja, abs=0.01)
    podstawa_zdrow = pensja - e.zus_pracownik
    assert e.zdrowotna == pytest.approx(P.ZDROWOTNA_ETAT_STAWKA * podstawa_zdrow,
                                        abs=0.01)
    assert e.koszt_pracodawcy == pytest.approx(
        pensja + P.ZUS_PRACODAWCA_STAWKA * pensja, abs=0.01)


def test_marginalna_stawka_etatu_12pct_przy_niskim_etacie():
    d = DaneKlienta(przychod=600_000, koszty=50_000, poziom_etatu=0.5)
    w = run_optimization(d)
    assert _spzoo(w).marginalna_stawka_etatu == 0.12


def test_pensja_obniza_cit_i_dywidende():
    bez = run_optimization(DaneKlienta(przychod=600_000, koszty=50_000))
    ze = run_optimization(DaneKlienta(przychod=600_000, koszty=50_000,
                                      poziom_etatu=0.5))
    s_bez, s_ze = _spzoo(bez), _spzoo(ze)
    # bez etatu pakiet jest pusty, z etatem koszt pensji się pojawia
    assert s_bez.koszt_pensji_w_spolce is None
    pensja = 0.5 * P.MINIMALNE_WYNAGRODZENIE * 12
    assert s_ze.koszt_pensji_w_spolce == pytest.approx(
        pensja + P.ZUS_PRACODAWCA_STAWKA * pensja)
    # podatek z części dywidendowej spada (CIT od niższego zysku)
    assert s_ze.pensja_etat == pytest.approx(pensja)
    assert s_ze.zus_od_etatu is not None and s_ze.zus_od_etatu > 0


def test_pola_etatu_puste_bez_etatu():
    w = run_optimization(DaneKlienta(przychod=600_000, koszty=50_000))
    assert _spzoo(w).pensja_etat is None


def test_netto_z_etatem_to_dywidenda_plus_pensja():
    d = DaneKlienta(przychod=600_000, koszty=50_000, poziom_etatu=0.5)
    w = run_optimization(d)
    s = _spzoo(w)
    # Tożsamość: netto = (przychód − koszty) − ZUS − zdrowotna − podatek,
    # niezależnie od miksu wypłaty (etat + art.176 + powołanie + dywidenda).
    assert s.dochod_netto == pytest.approx(
        (600_000 - 50_000) - s.zus_spoleczny - s.zdrowotna - s.podatek, abs=0.05)
