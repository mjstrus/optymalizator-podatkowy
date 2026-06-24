"""Typowane modele wejścia/wyjścia silnika (stdlib dataclasses).

Rdzeń finansowy nie zależy od bibliotek zewnętrznych — walidacja R9
realizowana w __post_init__.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FormaZUS(str, Enum):
    DUZY = "duzy"
    MALY_ZUS_PLUS = "maly_zus_plus"
    PREFERENCYJNY = "preferencyjny"
    ULGA_NA_START = "ulga_na_start"
    ETAT_ZBIEG = "etat_zbieg"


class Dostepnosc(str, Enum):
    DOSTEPNA = "dostepna"
    NIEDOSTEPNA = "niedostepna"


@dataclass
class Ulgi:
    """Preferencje i ulgi (R3)."""
    liczba_dzieci: int = 0
    ulga_4plus: bool = False
    ip_box: bool = False           # stawka 5%
    ikze_kwota: float = 0.0


@dataclass
class DaneKlienta:
    """Dane wejściowe silnika. Walidacja R9 w __post_init__."""
    przychod: float
    koszty: float
    # ryczałt: doradca wskazuje stawkę (np. 0.12, 0.085, 0.15)
    stawka_ryczaltu: float | None = None
    charakter_uslug: str | None = None

    forma_zus: FormaZUS = FormaZUS.DUZY
    # Dochód z poprzedniego roku — podstawa wyliczenia Małego ZUS Plus.
    dochod_poprzedni_rok: float = 0.0

    # Flagi
    byly_pracodawca: bool = False          # blokuje ryczałt i liniowy (R2)
    wspolne_rozliczenie: bool = False
    dochod_malzonka: float = 0.0
    jednoosobowa_spzoo: bool = False
    # Sp. z o.o. liczona przez zoptymalizowany miks wypłaty (nie 100% dywidendy):
    # art. 176 (obligatoryjnie) → powołanie zarządu → dywidenda jako reszta.
    art_176: bool = True                   # świadczenia art. 176 KSH (domyślnie tak)
    art_176_kwota: float | None = None     # roczna kwota świadczeń; None = auto do I progu
    powolanie_zarzad: bool = True          # wynagrodzenie z powołania (wypełnia I próg)
    najem_do_spolki: float = 0.0           # roczny czynsz najmu majątku do spółki
    wyplata_dywidendy_pct: float = 1.0     # założenie wypłaty zysku (R6)
    # Zbieg tytułów: etat poza JDG (pensja ≥ minimalnej) → brak ZUS społecznego.
    etat_poza_jdg: bool = False
    etat_poza_jdg_malzonek: bool = False

    # R15: małżonek wnoszony do spółki jako wspólnik (model na poziomie pary).
    malzonek_do_spolki: bool = False
    malzonek_przychod: float = 0.0
    malzonek_koszty: float = 0.0
    malzonek_forma_zus: FormaZUS = FormaZUS.DUZY     # ZUS małżonka na własnej JDG
    malzonek_dochod_poprzedni_rok: float = 0.0       # dla Małego ZUS Plus małżonka
    # Sp. z o.o. jako pakiet „spółka + etat" (R6 rozszerzone). Ułamek płacy
    # minimalnej jako pensja wspólnika; 0.0 = czysta dywidenda (bez etatu).
    poziom_etatu: float = 0.0

    ulgi: Ulgi = field(default_factory=Ulgi)

    def __post_init__(self) -> None:
        if self.przychod is None or self.koszty is None:
            raise ValueError("R9: przychód i koszty są wymagane.")
        if self.przychod < 0:
            raise ValueError("Przychód nie może być ujemny.")
        if self.koszty < 0:
            raise ValueError("Koszty nie mogą być ujemne.")
        if self.dochod_malzonka < 0:
            raise ValueError("Dochód małżonka nie może być ujemny.")
        if self.dochod_poprzedni_rok < 0:
            raise ValueError("Dochód z poprzedniego roku nie może być ujemny.")
        if not 0.0 <= self.wyplata_dywidendy_pct <= 1.0:
            raise ValueError("Wypłata dywidendy musi być w zakresie 0–1.")
        if not 0.0 <= self.poziom_etatu <= 1.0:
            raise ValueError("Poziom etatu musi być w zakresie 0–1.")


@dataclass
class WynikEtat:
    """Rozliczenie pensji wspólnika na etacie w sp. z o.o."""
    pensja_brutto: float
    zus_pracownik: float
    zus_pracodawca: float
    zdrowotna: float
    pit: float
    netto: float
    marginalna_stawka: float
    koszt_pracodawcy: float                 # pensja brutto + ZUS pracodawcy
    podstawa_pit: float = 0.0               # podstawa opodatkowania skalą


@dataclass
class WynikFormy:
    """Wynik dla jednej formy opodatkowania.

    Składniki (podatek / zdrowotna / zus_spoleczny) są kontraktem publicznym
    (R12) — służą do policzenia źródeł przewagi w rozbiciu oszczędności.
    """
    nazwa: str
    podatek: float
    zdrowotna: float
    zus_spoleczny: float
    dochod_netto: float
    dostepnosc: Dostepnosc = Dostepnosc.DOSTEPNA
    powod_niedostepnosci: str | None = None
    zalozenia: str | None = None           # np. założenie wypłaty dla sp. z o.o.
    # Pakiet „spółka + etat" (wypełniane tylko dla sp. z o.o. z etatem)
    pensja_etat: float | None = None
    zus_od_etatu: float | None = None
    zdrowotna_od_etatu: float | None = None
    koszt_pensji_w_spolce: float | None = None
    marginalna_stawka_etatu: float | None = None
    swiadczenia_art176: float | None = None   # kwota świadczeń art. 176 KSH
    # Miks wypłaty ze sp. z o.o. (kanały ekstrakcji)
    wyplata_powolanie: float | None = None    # wynagrodzenie z powołania zarządu
    wyplata_najem: float | None = None        # czynsz najmu majątku do spółki
    wyplata_dywidenda: float | None = None    # dywidenda (reszta)
    # Rozbicie pary przy R15 (tylko formy JDG; sp. z o.o. = dochód wspólny).
    dochod_netto_klient: float | None = None
    dochod_netto_malzonek: float | None = None


@dataclass
class WynikOptymalizacji:
    """Wynik całego porównania (kontrakt współdzielony UI + PDF)."""
    formy: list[WynikFormy]
    werdykt: str                           # nazwa najkorzystniejszej formy
    roznica_do_drugiej: float              # przewaga kwotowa nad drugą opcją
