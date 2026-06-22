"""Silnik deterministyczny: run_optimization.

Czysta funkcja licząca cztery formy opodatkowania 2026, screening,
preferencje i werdykt — bez UI i bez LLM (R1, R2, R3, R4, R6, R7-liczby).

Wzór nadrzędny dla wszystkich form:
    dochod_netto = przychod − koszty − zus_spoleczny − zdrowotna − podatek
"""
from __future__ import annotations

from . import params_2026 as P
from .models import (
    DaneKlienta,
    Dostepnosc,
    FormaZUS,
    WynikFormy,
    WynikOptymalizacji,
)


# --- ZUS społeczny (Krok 0) -------------------------------------------------
def _zus_spoleczny(dane: DaneKlienta) -> float:
    """Roczny ZUS społeczny wg formy. Podstawa emer.-rentowa jest stała
    (poniżej rocznego ograniczenia 282 600 zł), więc składka nie rośnie
    z dochodem (R5)."""
    match dane.forma_zus:
        case FormaZUS.DUZY:
            return P.ZUS_DUZY_ROCZNY
        case FormaZUS.PREFERENCYJNY:
            return P.ZUS_PREFERENCYJNY_ROCZNY
        case FormaZUS.ULGA_NA_START | FormaZUS.ETAT_ZBIEG:
            return 0.0
        case FormaZUS.MALY_ZUS_PLUS:
            return _maly_zus_plus(dane)
    return P.ZUS_DUZY_ROCZNY


def _maly_zus_plus(dane: DaneKlienta) -> float:
    """Mały ZUS Plus: podstawa = 50% średniego miesięcznego dochodu z roku
    poprzedniego, ograniczona widełkami (od preferencyjnej do dużej), a składka
    liczona efektywną stawką społeczną. Uproszczenie MVP."""
    podstawa_mies = 0.5 * (dane.dochod_poprzedni_rok / 12)
    podstawa_mies = min(max(podstawa_mies, P.ZUS_MALY_PLUS_PODSTAWA_MIN),
                        P.ZUS_MALY_PLUS_PODSTAWA_MAX)
    skladka_mies = P.ZUS_SPOLECZNY_STAWKA_EFEKTYWNA * podstawa_mies
    skladka_mies = min(max(skladka_mies, P.ZUS_PREFERENCYJNY_MIES),
                       P.ZUS_DUZY_MIES)
    return round(skladka_mies * 12, 2)


# --- Negative screening (Krok 1) --------------------------------------------
def _screening(dane: DaneKlienta) -> dict[str, tuple[Dostepnosc, str | None]]:
    """Dostępność form wg R2."""
    wynik: dict[str, tuple[Dostepnosc, str | None]] = {
        "skala": (Dostepnosc.DOSTEPNA, None),
        "liniowy": (Dostepnosc.DOSTEPNA, None),
        "ryczalt": (Dostepnosc.DOSTEPNA, None),
        "spzoo": (Dostepnosc.DOSTEPNA, None),
    }
    if dane.byly_pracodawca:
        wynik["liniowy"] = (Dostepnosc.NIEDOSTEPNA,
                            "Były pracodawca w bieżącym/poprzednim roku.")
        wynik["ryczalt"] = (Dostepnosc.NIEDOSTEPNA,
                            "Były pracodawca w bieżącym/poprzednim roku.")
    if dane.przychod > P.RYCZALT_LIMIT_EUR * P.EUR_PLN:
        wynik["ryczalt"] = (Dostepnosc.NIEDOSTEPNA,
                            "Przychód powyżej limitu 2 mln EUR dla ryczałtu.")
    return wynik


# --- Podatek skali (z obsługą wspólnego rozliczenia, Krok 2) ----------------
def _podatek_skala_osoba(podstawa: float) -> float:
    if podstawa <= 0:
        return 0.0
    if podstawa <= P.SKALA_PROG:
        return max(0.0, P.SKALA_STAWKA_1 * podstawa - P.SKALA_KWOTA_ZMNIEJSZAJACA)
    return P.SKALA_PODATEK_PROG + P.SKALA_STAWKA_2 * (podstawa - P.SKALA_PROG)


def _podatek_skala(dane: DaneKlienta, podstawa: float) -> float:
    if dane.wspolne_rozliczenie:
        wspolna = (max(0.0, podstawa) + max(0.0, dane.dochod_malzonka)) / 2
        return 2 * _podatek_skala_osoba(wspolna)
    return _podatek_skala_osoba(podstawa)


# --- Cztery formy -----------------------------------------------------------
def _odliczenia_dochodowe(dane: DaneKlienta) -> float:
    """Odliczenia od podstawy opodatkowania wspólne dla skali i liniowego:
    IKZE (do limitu) oraz zwolnienie PIT-0 dla rodzin 4+."""
    odliczenia = min(dane.ulgi.ikze_kwota, P.IKZE_LIMIT_JDG)
    if dane.ulgi.ulga_4plus:
        odliczenia += P.ULGA_4PLUS_LIMIT
    return odliczenia


def _oblicz_skala(dane: DaneKlienta, zus: float) -> WynikFormy:
    D_zdrow = dane.przychod - dane.koszty - zus
    zdrowotna = max(0.09 * D_zdrow, P.ZDROWOTNA_MIN_ROCZNA)
    podstawa = D_zdrow - _odliczenia_dochodowe(dane)
    podatek = _podatek_skala(dane, podstawa)
    # Ulga prorodzinna to odliczenie od podatku; nadwyżka zwracana (do wysokości
    # składek) — dopuszczamy ujemny "podatek" (zwrot) i odejmujemy go w netto.
    podatek = podatek - _ulga_dzieci(dane, podatek, zus, zdrowotna)
    netto = dane.przychod - dane.koszty - zus - zdrowotna - podatek
    return WynikFormy("Skala", round(podatek, 2), round(zdrowotna, 2),
                      round(zus, 2), round(netto, 2))


def _oblicz_liniowy(dane: DaneKlienta, zus: float) -> WynikFormy:
    D_zdrow = dane.przychod - dane.koszty - zus
    zdrowotna = max(P.LINIOWY_ZDROWOTNA_STAWKA * D_zdrow, P.ZDROWOTNA_MIN_ROCZNA)
    odliczenie = min(zdrowotna, P.LINIOWY_LIMIT_ODLICZENIA)
    podstawa = D_zdrow - odliczenie - _odliczenia_dochodowe(dane)
    stawka = 0.05 if dane.ulgi.ip_box else P.LINIOWY_STAWKA
    podatek = max(0.0, stawka * podstawa)
    netto = dane.przychod - dane.koszty - zus - zdrowotna - podatek
    return WynikFormy("Liniowy", round(podatek, 2), round(zdrowotna, 2),
                      round(zus, 2), round(netto, 2))


def _ryczalt_zdrowotna(przychod: float) -> float:
    if przychod <= P.RYCZALT_PROG_NISKI:
        return P.RYCZALT_ZDROWOTNA_NISKI
    if przychod <= P.RYCZALT_PROG_SREDNI:
        return P.RYCZALT_ZDROWOTNA_SREDNI
    return P.RYCZALT_ZDROWOTNA_WYSOKI


def _oblicz_ryczalt(dane: DaneKlienta, zus: float) -> WynikFormy:
    # Koszty NIE wchodzą do podstawy ryczałtu.
    zdrowotna = _ryczalt_zdrowotna(dane.przychod)
    podstawa = dane.przychod - zus - 0.5 * zdrowotna
    stawka = dane.stawka_ryczaltu if dane.stawka_ryczaltu is not None else 0.12
    podatek = max(0.0, stawka * podstawa)
    netto = dane.przychod - dane.koszty - zus - zdrowotna - podatek
    return WynikFormy("Ryczałt", round(podatek, 2), round(zdrowotna, 2),
                      round(zus, 2), round(netto, 2))


def _oblicz_spzoo(dane: DaneKlienta) -> WynikFormy:
    zysk = dane.przychod - dane.koszty
    cit = max(0.0, P.CIT_STAWKA * zysk)
    zysk_po_cit = zysk - cit
    dywidenda = max(0.0, zysk_po_cit) * dane.wyplata_dywidendy_pct
    pit_dyw = P.DYWIDENDA_STAWKA * dywidenda
    podatek = cit + pit_dyw

    # Jednoosobowa: wspólnik płaci dodatkową zdrowotną + ZUS (R6).
    if dane.jednoosobowa_spzoo:
        zdrowotna = P.SPZOO_JEDNOOSOBOWA_ZDROWOTNA_ROCZNA
        zus = P.SPZOO_JEDNOOSOBOWA_ZUS_ROCZNY
        zalozenia = ("Jednoosobowa sp. z o.o.: doliczona składka zdrowotna i ZUS "
                     "wspólnika.")
    else:
        zdrowotna = 0.0
        zus = 0.0
        zalozenia = None

    zalozenie_wyplaty = f"Założenie wypłaty {dane.wyplata_dywidendy_pct:.0%} zysku dywidendą."
    if dane.art_176:
        zalozenie_wyplaty += " Rozważ ścieżkę art. 176 KSH (świadczenia wspólnika)."
    zalozenia = (zalozenia + " " if zalozenia else "") + zalozenie_wyplaty

    # Netto wspólnika = zysk po CIT − PIT od dywidendy − ZUS − zdrowotna.
    netto = zysk_po_cit - pit_dyw - zus - zdrowotna
    return WynikFormy("Sp. z o.o.", round(podatek, 2), round(zdrowotna, 2),
                      round(zus, 2), round(netto, 2), zalozenia=zalozenia)


# --- Ulgi pomocnicze --------------------------------------------------------
def _ulga_dzieci(dane: DaneKlienta, podatek: float, zus: float,
                 zdrowotna: float) -> float:
    """Ulga prorodzinna wg progów na kolejne dzieci. Nadwyżka ponad podatek
    jest zwracana do wysokości zapłaconych składek (ZUS + zdrowotna)."""
    naliczona = 0.0
    for i in range(1, dane.ulgi.liczba_dzieci + 1):
        if i <= 2:
            naliczona += P.ULGA_DZIECKO_1_2
        elif i == 3:
            naliczona += P.ULGA_DZIECKO_3
        else:
            naliczona += P.ULGA_DZIECKO_4
    # Efektywnie odliczalne: podatek + limit zwrotu (składki).
    return min(naliczona, max(0.0, podatek) + zus + zdrowotna)


# --- Punkt wejścia ----------------------------------------------------------
def run_optimization(dane: DaneKlienta) -> WynikOptymalizacji:
    """Policz cztery formy, zastosuj screening i wyłoń werdykt."""
    zus = _zus_spoleczny(dane)

    formy = [
        _oblicz_skala(dane, zus),
        _oblicz_liniowy(dane, zus),
        _oblicz_ryczalt(dane, zus),
        _oblicz_spzoo(dane),
    ]

    # Screening: oznacz niedostępne formy.
    screening = _screening(dane)
    klucz = {"Skala": "skala", "Liniowy": "liniowy",
             "Ryczałt": "ryczalt", "Sp. z o.o.": "spzoo"}
    for f in formy:
        dost, powod = screening[klucz[f.nazwa]]
        f.dostepnosc = dost
        f.powod_niedostepnosci = powod

    # Werdykt tylko spośród dostępnych form.
    dostepne = [f for f in formy if f.dostepnosc == Dostepnosc.DOSTEPNA]
    dostepne_sort = sorted(dostepne, key=lambda f: f.dochod_netto, reverse=True)
    najlepsza = dostepne_sort[0]
    roznica = (najlepsza.dochod_netto - dostepne_sort[1].dochod_netto
               if len(dostepne_sort) > 1 else 0.0)

    return WynikOptymalizacji(
        formy=formy,
        werdykt=najlepsza.nazwa,
        roznica_do_drugiej=round(roznica, 2),
    )
