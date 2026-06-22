"""Warstwa prezentacji — czyste funkcje formatujące wynik silnika.

Oddzielone od Streamlita, by były testowalne bez serwera.
"""
from __future__ import annotations

from .models import Dostepnosc, WynikOptymalizacji

# Branding Abacus
BRAND_NAVY_OD = "#0d1b2a"
BRAND_NAVY_DO = "#1b2d45"
BRAND_GRADIENT = f"linear-gradient(135deg, {BRAND_NAVY_OD}, {BRAND_NAVY_DO})"


def formatuj_pln(kwota: float) -> str:
    """Sformatuj kwotę w stylu polskim: spacja jako separator tysięcy,
    przecinek jako separator dziesiętny."""
    s = f"{kwota:,.2f}"  # 1,234,567.80
    s = s.replace(",", " ").replace(".", ",")
    return f"{s} zł"


def tabela_porownawcza(wynik: WynikOptymalizacji) -> list[dict]:
    """Zbuduj wiersze tabeli porównawczej (R7) — gotowe do renderu."""
    wiersze = []
    for f in wynik.formy:
        status = ("✅ Dostępna" if f.dostepnosc == Dostepnosc.DOSTEPNA
                  else f"⛔ NIEDOSTĘPNA — {f.powod_niedostepnosci or ''}".strip())
        wiersze.append({
            "Forma": ("⭐ " + f.nazwa) if f.nazwa == wynik.werdykt else f.nazwa,
            "Podatek": formatuj_pln(f.podatek),
            "Zdrowotna": formatuj_pln(f.zdrowotna),
            "ZUS": formatuj_pln(f.zus_spoleczny),
            "Dochód netto": formatuj_pln(f.dochod_netto),
            "Status": status,
        })
    return wiersze


def sprawdz_braki(przychod, koszty, charakter_uslug) -> list[str]:
    """Walidacja R9: zwróć listę konkretnych braków (ankieta uzupełniająca).
    Pusta lista = dane kompletne, można liczyć."""
    braki: list[str] = []
    if przychod is None or przychod == "":
        braki.append("Podaj roczny przychód (zł).")
    if koszty is None or koszty == "":
        braki.append("Podaj roczne koszty uzyskania przychodu (zł).")
    if not charakter_uslug:
        braki.append("Wskaż charakter usług / kod PKWiU (dla stawki ryczałtu).")
    return braki


def tekst_werdyktu(wynik: WynikOptymalizacji) -> str:
    """Werdykt matematyczny (R7) — jedno zdanie z różnicą kwotową."""
    return (f"Rekomendowana forma: {wynik.werdykt}. "
            f"Przewaga nad drugą opcją: {formatuj_pln(wynik.roznica_do_drugiej)} "
            f"rocznie.")
