"""Testy: % wypłaty dywidendy + zysk zatrzymany w sp. z o.o."""

from optymalizator.engine import run_optimization
from optymalizator.models import DaneKlienta


def _spzoo(w):
    return next(f for f in w.formy if "z o.o" in f.nazwa.lower())


def test_zatrzymanie_obniza_podatek_i_podnosi_majatek():
    base = dict(przychod=800_000, koszty=50_000)
    pelna = run_optimization(DaneKlienta(**base, wyplata_dywidendy_pct=1.0))
    polowa = run_optimization(DaneKlienta(**base, wyplata_dywidendy_pct=0.5))
    s100, s50 = _spzoo(pelna), _spzoo(polowa)
    # mniej dywidendy → niższy podatek i wyższy majątek łączny (mniej 19%)
    assert s50.podatek < s100.podatek
    assert s50.dochod_netto > s100.dochod_netto
    assert s50.zysk_zatrzymany is not None and s50.zysk_zatrzymany > 0


def test_pelna_wyplata_brak_zatrzymania():
    s = _spzoo(run_optimization(DaneKlienta(przychod=600_000, koszty=50_000,
                                            wyplata_dywidendy_pct=1.0)))
    assert s.zysk_zatrzymany is None
