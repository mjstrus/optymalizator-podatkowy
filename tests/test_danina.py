"""Testy daniny solidarnościowej (4% od dochodu ponad 1 mln zł)."""
import pytest

from optymalizator import params_2026 as P
from optymalizator.engine import _danina, run_optimization
from optymalizator.models import DaneKlienta


def _forma(w, frag):
    return next(f for f in w.formy if frag.lower() in f.nazwa.lower())


def test_helper_danina():
    assert _danina(1_200_000) == pytest.approx(0.04 * 200_000)   # 8 000
    assert _danina(1_000_000) == 0.0
    assert _danina(500_000) == 0.0


def test_skala_dolicza_danine_przy_wysokim_dochodzie():
    d = DaneKlienta(przychod=2_000_000, koszty=0)
    w = run_optimization(d)
    D = 2_000_000 - P.ZUS_DUZY_ROCZNY
    podatek_bez_daniny = P.SKALA_PODATEK_PROG + P.SKALA_STAWKA_2 * (D - P.SKALA_PROG)
    danina = P.DANINA_STAWKA * (D - P.DANINA_PROG)
    assert _forma(w, "skala").podatek == pytest.approx(podatek_bez_daniny + danina,
                                                       rel=1e-6)


def test_liniowy_dolicza_danine_przy_wysokim_dochodzie():
    d = DaneKlienta(przychod=2_000_000, koszty=0)
    w = run_optimization(d)
    D = 2_000_000 - P.ZUS_DUZY_ROCZNY
    odliczenie = min(P.LINIOWY_ZDROWOTNA_STAWKA * D, P.LINIOWY_LIMIT_ODLICZENIA)
    podatek_bez = P.LINIOWY_STAWKA * (D - odliczenie)
    danina = P.DANINA_STAWKA * (D - P.DANINA_PROG)
    assert _forma(w, "liniow").podatek == pytest.approx(podatek_bez + danina,
                                                        rel=1e-6)


def test_ryczalt_bez_daniny():
    d = DaneKlienta(przychod=2_000_000, koszty=0, stawka_ryczaltu=0.12)
    w = run_optimization(d)
    rycz = _forma(w, "rycz")
    podstawa = 2_000_000 - P.ZUS_DUZY_ROCZNY - 0.5 * P.RYCZALT_ZDROWOTNA_WYSOKI
    # podatek = sama stawka × podstawa, bez doliczonej daniny
    assert rycz.podatek == pytest.approx(0.12 * podstawa, rel=1e-6)


def test_spzoo_bez_daniny():
    # Sp. z o.o. nie podlega daninie — podatek = CIT + PIT(art.176) + PIT dywidendy,
    # bez 4% od nadwyżki ponad 1 mln (inaczej kwota byłaby wyższa).
    d = DaneKlienta(przychod=2_000_000, koszty=0)
    w = run_optimization(d)
    spzoo = _forma(w, "z o.o")
    swiadcz = P.SKALA_PROG                       # art.176 domyślnie do I progu
    zysk = 2_000_000 - swiadcz
    cit = P.CIT_STAWKA * zysk
    pit_dyw = P.DYWIDENDA_STAWKA * (zysk - cit)
    pit_skala = P.SKALA_STAWKA_1 * swiadcz - P.SKALA_KWOTA_ZMNIEJSZAJACA
    assert spzoo.podatek == pytest.approx(cit + pit_dyw + pit_skala, rel=1e-6)


def test_brak_daniny_ponizej_progu():
    d = DaneKlienta(przychod=500_000, koszty=20_000)
    w = run_optimization(d)
    D = 500_000 - 20_000 - P.ZUS_DUZY_ROCZNY
    podatek_bez = P.SKALA_PODATEK_PROG + P.SKALA_STAWKA_2 * (D - P.SKALA_PROG)
    assert _forma(w, "skala").podatek == pytest.approx(podatek_bez, rel=1e-6)
