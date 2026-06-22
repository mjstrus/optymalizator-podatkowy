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
    art_176: bool = False                  # ścieżka art. 176 KSH
    wyplata_dywidendy_pct: float = 1.0     # założenie wypłaty zysku (R6)

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


@dataclass
class WynikFormy:
    """Wynik dla jednej formy opodatkowania."""
    nazwa: str
    podatek: float
    zdrowotna: float
    zus_spoleczny: float
    dochod_netto: float
    dostepnosc: Dostepnosc = Dostepnosc.DOSTEPNA
    powod_niedostepnosci: str | None = None
    zalozenia: str | None = None           # np. założenie wypłaty dla sp. z o.o.


@dataclass
class WynikOptymalizacji:
    """Wynik całego porównania (kontrakt współdzielony UI + PDF)."""
    formy: list[WynikFormy]
    werdykt: str                           # nazwa najkorzystniejszej formy
    roznica_do_drugiej: float              # przewaga kwotowa nad drugą opcją
