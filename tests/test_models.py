"""Testy Unit 1: stałe podatkowe 2026 + modele danych.

Test-first: stałe to regresja na zweryfikowanych liczbach 2026,
modele walidują dane wejściowe zgodnie z R9.
"""
import pytest

from optymalizator import params_2026 as P
from optymalizator.models import (
    DaneKlienta,
    FormaZUS,
    WynikFormy,
    WynikOptymalizacji,
    Dostepnosc,
)


# --- Stałe 2026 (regresja na liczbach) --------------------------------------

def test_stale_skala():
    assert P.SKALA_PROG == 120_000
    assert P.SKALA_STAWKA_1 == 0.12
    assert P.SKALA_STAWKA_2 == 0.32
    assert P.SKALA_KWOTA_ZMNIEJSZAJACA == 3_600
    # podwójna kwota wolna i próg wspólnego rozliczenia
    assert P.WSPOLNE_PROG == 240_000


def test_stale_zdrowotna_minimum_roczne():
    # KRYTYCZNE: 1×314,96 (styczeń) + 11×432,54 (luty–grudzień)
    assert P.ZDROWOTNA_STYCZEN == pytest.approx(314.96)
    assert P.ZDROWOTNA_MIN_MIES == pytest.approx(432.54)
    assert P.ZDROWOTNA_MIN_ROCZNA == pytest.approx(5_072.90)
    # suma kontrolna: NIE 12×432,54
    assert P.ZDROWOTNA_MIN_ROCZNA != pytest.approx(12 * 432.54)


def test_stale_liniowy_limit_odliczenia():
    assert P.LINIOWY_LIMIT_ODLICZENIA == 14_100
    assert P.LINIOWY_STAWKA == 0.19
    assert P.LINIOWY_ZDROWOTNA_STAWKA == pytest.approx(0.049)


def test_stale_ryczalt_zdrowotna_progi():
    # roczne kwoty zdrowotnej ryczałtu = 12 × stawka miesięczna
    assert P.RYCZALT_ZDROWOTNA_NISKI == pytest.approx(498.35 * 12)
    assert P.RYCZALT_ZDROWOTNA_SREDNI == pytest.approx(830.58 * 12)
    assert P.RYCZALT_ZDROWOTNA_WYSOKI == pytest.approx(1_495.04 * 12)


def test_stale_zus():
    assert P.ZUS_DUZY_MIES == pytest.approx(1_926.76)
    assert P.ZUS_PREFERENCYJNY_MIES == pytest.approx(456.18)
    assert P.ZUS_OGRANICZENIE_PODSTAWY == 282_600


def test_stale_spzoo():
    assert P.CIT_STAWKA == 0.09
    assert P.DYWIDENDA_MNOZNIK_NETTO == pytest.approx(0.7371)


# --- Modele danych ----------------------------------------------------------

def test_dane_klienta_minimalne_poprawne():
    d = DaneKlienta(przychod=200_000, koszty=50_000)
    assert d.przychod == 200_000
    assert d.forma_zus == FormaZUS.DUZY  # domyślnie

def test_dane_klienta_odrzuca_brak_przychodu():
    # R9: brak przychodu zatrzymuje
    with pytest.raises((ValueError, TypeError)):
        DaneKlienta(przychod=None, koszty=0)  # type: ignore[arg-type]

def test_dane_klienta_odrzuca_ujemny_przychod():
    with pytest.raises(ValueError):
        DaneKlienta(przychod=-1, koszty=0)

def test_dane_klienta_odrzuca_ujemne_koszty():
    with pytest.raises(ValueError):
        DaneKlienta(przychod=100_000, koszty=-5)


def test_wynik_formy_kontrakt():
    w = WynikFormy(
        nazwa="Liniowy",
        podatek=10_000,
        zdrowotna=5_072.90,
        zus_spoleczny=23_121.12,
        dochod_netto=100_000,
        dostepnosc=Dostepnosc.DOSTEPNA,
    )
    assert w.dostepnosc == Dostepnosc.DOSTEPNA


def test_wynik_optymalizacji_kontrakt():
    formy = [
        WynikFormy("Skala", 1, 5072.90, 1, 90_000, Dostepnosc.DOSTEPNA),
        WynikFormy("Liniowy", 1, 5072.90, 1, 95_000, Dostepnosc.DOSTEPNA),
    ]
    wo = WynikOptymalizacji(formy=formy, werdykt="Liniowy", roznica_do_drugiej=5_000)
    assert wo.werdykt == "Liniowy"
    assert wo.roznica_do_drugiej == 5_000
