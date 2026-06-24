"""Testy: najem prywatnego majątku do sp. z o.o. jako kanał wypłaty."""
import pytest

from optymalizator.engine import _ryczalt_najmu, run_optimization
from optymalizator.models import DaneKlienta


def _spzoo(w):
    return next(f for f in w.formy if "z o.o" in f.nazwa.lower())


def test_ryczalt_najmu_progi():
    assert _ryczalt_najmu(100_000) == pytest.approx(0.085 * 100_000)        # 8 500
    assert _ryczalt_najmu(200_000) == pytest.approx(0.085 * 100_000
                                                    + 0.125 * 100_000)      # 21 000
    assert _ryczalt_najmu(0) == 0.0


def test_najem_poprawia_netto_spzoo():
    base = dict(przychod=600_000, koszty=50_000)
    bez = run_optimization(DaneKlienta(**base))
    ze = run_optimization(DaneKlienta(**base, najem_do_spolki=100_000))
    assert _spzoo(ze).dochod_netto > _spzoo(bez).dochod_netto


def test_najem_bez_zus_i_zdrowotnej():
    # Sam najem (bez etatu/powołania) nie generuje ZUS ani zdrowotnej.
    d = DaneKlienta(przychod=600_000, koszty=50_000, art_176=False,
                    powolanie_zarzad=False, najem_do_spolki=80_000)
    s = _spzoo(run_optimization(d))
    assert s.zus_spoleczny == 0.0
    assert s.zdrowotna == 0.0
    assert s.wyplata_najem == pytest.approx(80_000)


def test_najem_w_tozsamosci_netto():
    d = DaneKlienta(przychod=600_000, koszty=50_000, najem_do_spolki=120_000)
    s = _spzoo(run_optimization(d))
    assert s.dochod_netto == pytest.approx(
        (600_000 - 50_000) - s.zus_spoleczny - s.zdrowotna - s.podatek, abs=0.1)
