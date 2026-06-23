"""Testy R15: małżonek wnoszony do spółki (model na poziomie pary)."""
import pytest

from optymalizator.engine import run_optimization
from optymalizator.models import DaneKlienta


def _forma(w, frag):
    return next(f for f in w.formy if frag.lower() in f.nazwa.lower())


def test_spzoo_wciaga_zysk_malzonka():
    # Z małżonkiem w spółce zysk spółki rośnie → wyższe netto sp. z o.o.
    base = dict(przychod=600_000, koszty=50_000)
    bez = run_optimization(DaneKlienta(**base))
    ze = run_optimization(DaneKlienta(
        **base, malzonek_do_spolki=True,
        malzonek_przychod=300_000, malzonek_koszty=30_000))
    assert _forma(ze, "z o.o").dochod_netto > _forma(bez, "z o.o").dochod_netto


def test_formy_jdg_sa_na_poziomie_pary():
    # Przy małżonku w spółce formy JDG = klient + samodzielny najlepszy wynik
    # małżonka → wyższe netto niż bez flagi (która liczy tylko klienta).
    base = dict(przychod=600_000, koszty=50_000, stawka_ryczaltu=0.12)
    bez = run_optimization(DaneKlienta(**base))
    ze = run_optimization(DaneKlienta(
        **base, malzonek_do_spolki=True,
        malzonek_przychod=300_000, malzonek_koszty=30_000))
    assert _forma(ze, "liniow").dochod_netto > _forma(bez, "liniow").dochod_netto


def test_brak_flagi_brak_zmiany():
    base = dict(przychod=600_000, koszty=50_000, stawka_ryczaltu=0.12)
    a = run_optimization(DaneKlienta(**base))
    b = run_optimization(DaneKlienta(**base, malzonek_przychod=300_000,
                                     malzonek_koszty=30_000))  # bez flagi
    assert _forma(a, "z o.o").dochod_netto == pytest.approx(
        _forma(b, "z o.o").dochod_netto)


def test_werdykt_na_poziomie_pary_jest_spojny():
    d = DaneKlienta(przychod=600_000, koszty=50_000, stawka_ryczaltu=0.12,
                    malzonek_do_spolki=True, malzonek_przychod=300_000,
                    malzonek_koszty=30_000)
    w = run_optimization(d)
    # werdykt = forma o najwyższym netto spośród dostępnych
    najlepsza = max((f for f in w.formy
                     if f.dostepnosc.value == "dostepna"),
                    key=lambda f: f.dochod_netto)
    assert w.werdykt == najlepsza.nazwa
