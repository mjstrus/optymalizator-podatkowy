"""Testy dopracowania: ulgi (R3) + Mały ZUS Plus (R5)."""
import pytest

from optymalizator import params_2026 as P
from optymalizator.engine import _zus_spoleczny, run_optimization
from optymalizator.models import DaneKlienta, FormaZUS, Ulgi


def _forma(w, fragment):
    return next(f for f in w.formy if fragment.lower() in f.nazwa.lower())


# --- Ulga prorodzinna (skala, progowa) --------------------------------------
def test_ulga_dzieci_zmniejsza_podatek_skali():
    base = dict(przychod=200_000, koszty=20_000)
    bez = run_optimization(DaneKlienta(**base))
    z2 = run_optimization(DaneKlienta(**base, ulgi=Ulgi(liczba_dzieci=2)))
    spadek = _forma(bez, "skala").podatek - _forma(z2, "skala").podatek
    assert spadek == pytest.approx(2 * P.ULGA_DZIECKO_1_2)


def test_ulga_dzieci_progi_trojka_i_czworka():
    base = dict(przychod=300_000, koszty=20_000)
    bez = run_optimization(DaneKlienta(**base))
    z4 = run_optimization(DaneKlienta(**base, ulgi=Ulgi(liczba_dzieci=4)))
    oczek = 2 * P.ULGA_DZIECKO_1_2 + P.ULGA_DZIECKO_3 + P.ULGA_DZIECKO_4
    spadek = _forma(bez, "skala").podatek - _forma(z4, "skala").podatek
    assert spadek == pytest.approx(oczek)


def test_ulga_dzieci_moze_dac_zwrot_ponad_podatek():
    # Niski podatek + dużo dzieci → ulga większa niż podatek → wyższe netto.
    base = dict(przychod=60_000, koszty=10_000)
    bez = run_optimization(DaneKlienta(**base))
    z4 = run_optimization(DaneKlienta(**base, ulgi=Ulgi(liczba_dzieci=4)))
    assert _forma(z4, "skala").dochod_netto > _forma(bez, "skala").dochod_netto


# --- PIT-0 dla rodzin 4+ (zwolnienie przychodu) -----------------------------
def test_ulga_4plus_zmniejsza_podstawe_skali():
    # Podstawa dobrana tak, by w obu wariantach pozostać w I progu (12%),
    # więc oszczędność = 12% × limitu zwolnienia.
    base = dict(przychod=141_121.12, koszty=0)
    bez = run_optimization(DaneKlienta(**base))
    z = run_optimization(DaneKlienta(**base, ulgi=Ulgi(ulga_4plus=True)))
    spadek = _forma(bez, "skala").podatek - _forma(z, "skala").podatek
    assert spadek == pytest.approx(P.SKALA_STAWKA_1 * P.ULGA_4PLUS_LIMIT)


# --- IKZE (limit odliczenia) ------------------------------------------------
def test_ikze_capped_na_limicie():
    base = dict(przychod=300_000, koszty=20_000)
    bez = run_optimization(DaneKlienta(**base))
    duze = run_optimization(DaneKlienta(**base, ulgi=Ulgi(ikze_kwota=999_999)))
    spadek = _forma(bez, "liniow").podatek - _forma(duze, "liniow").podatek
    assert spadek == pytest.approx(P.LINIOWY_STAWKA * P.IKZE_LIMIT_JDG)


# --- Mały ZUS Plus ----------------------------------------------------------
def test_maly_zus_plus_zalezy_od_dochodu():
    niski = DaneKlienta(przychod=200_000, koszty=20_000,
                        forma_zus=FormaZUS.MALY_ZUS_PLUS,
                        dochod_poprzedni_rok=30_000)
    wysoki = DaneKlienta(przychod=200_000, koszty=20_000,
                         forma_zus=FormaZUS.MALY_ZUS_PLUS,
                         dochod_poprzedni_rok=200_000)
    assert _zus_spoleczny(niski) < _zus_spoleczny(wysoki)


def test_maly_zus_plus_w_widelkach():
    d = DaneKlienta(przychod=200_000, koszty=20_000,
                    forma_zus=FormaZUS.MALY_ZUS_PLUS,
                    dochod_poprzedni_rok=80_000)
    zus_mies = _zus_spoleczny(d) / 12
    assert P.ZUS_PREFERENCYJNY_MIES <= zus_mies <= P.ZUS_DUZY_MIES
