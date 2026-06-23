"""Warstwa narracyjna (Claude API).

Generuje „Kluczowe Uzasadnienie" (max 3 punkty) i „Matrycę Ryzyk" z GOTOWYCH
liczb silnika. Model NIE liczy — dostaje wynik jako dane (R8).
Graceful degradation: brak klucza / awaria API → placeholdery + flaga, liczby
pozostają użyteczne (UI/PDF nadal pokazują tabelę i werdykt).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

from .models import Dostepnosc, WynikOptymalizacji

MODEL = "claude-sonnet-4-6"
MAX_PUNKTOW = 3

SYSTEM_PROMPT = (
    "Jesteś doradcą podatkowym biura Abacus. Otrzymujesz GOTOWE, policzone liczby "
    "i piszesz wyłącznie warstwę narracyjną dla klienta. "
    "BEZWZGLĘDNY ZAKAZ: nie przeliczaj, nie licz, nie modyfikuj żadnych kwot — "
    "traktuj podane liczby jako prawdę ostateczną. "
    "Styl menedżerski, zwroty per „Pan/Pani”. "
    "Zwróć WYŁĄCZNIE poprawny JSON o kształcie: "
    '{"uzasadnienie": ["...", "...", "..."], '
    '"matryca_ryzyk": [{"obszar": "...", "opis": "..."}]}. '
    f"Maksymalnie {MAX_PUNKTOW} punkty uzasadnienia."
)


@dataclass
class Narracja:
    uzasadnienie: list[str] = field(default_factory=list)
    matryca_ryzyk: list[dict] = field(default_factory=list)
    dostepna: bool = False
    powod: str | None = None


def _dane_dla_modelu(wynik: WynikOptymalizacji) -> dict:
    """Serializuj gotowe liczby — to wejście narracji, nie do przeliczeń."""
    return {
        "werdykt": wynik.werdykt,
        "roznica_do_drugiej_zl": wynik.roznica_do_drugiej,
        "formy": [
            {
                "nazwa": f.nazwa,
                "podatek": f.podatek,
                "zdrowotna": f.zdrowotna,
                "zus_spoleczny": f.zus_spoleczny,
                "dochod_netto": f.dochod_netto,
                "dostepna": f.dostepnosc == Dostepnosc.DOSTEPNA,
                "powod_niedostepnosci": f.powod_niedostepnosci,
                "zalozenia": f.zalozenia,
            }
            for f in wynik.formy
        ],
    }


def _placeholder(powod: str) -> Narracja:
    return Narracja(
        uzasadnienie=["Warstwa narracyjna niedostępna — poniżej kompletne liczby."],
        matryca_ryzyk=[],
        dostepna=False,
        powod=powod,
    )


def generuj_narracje(wynik: WynikOptymalizacji, klient=None,
                     kontekst: str = "") -> Narracja:
    """Zwróć narrację dla gotowego wyniku. `klient` (np. anthropic.Anthropic)
    można wstrzyknąć — ułatwia testy. `kontekst` to dodatkowe informacje o
    kliencie (specyfika, wymagania, oczekiwania) — model dopasuje narrację,
    ale NADAL nie liczy."""
    if klient is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return _placeholder("Brak klucza ANTHROPIC_API_KEY — narracja pominięta.")
        try:
            import anthropic
            klient = anthropic.Anthropic()
        except Exception as e:  # import lub inicjalizacja
            return _placeholder(f"Nie udało się zainicjować klienta API: {e}")

    dane = _dane_dla_modelu(wynik)
    tresc = ("Oto gotowe liczby (NIE przeliczaj ich). Napisz uzasadnienie i "
             "matrycę ryzyk jako JSON.\n\n"
             + json.dumps(dane, ensure_ascii=False, indent=2))
    if kontekst.strip():
        tresc += ("\n\nDodatkowe informacje o kliencie (uwzględnij w uzasadnieniu "
                  "i ryzykach, ale NIE przeliczaj liczb):\n" + kontekst.strip())
    try:
        resp = klient.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": tresc}],
        )
        tekst = resp.content[0].text
        parsed = _parsuj_json(tekst)
    except Exception as e:
        return _placeholder(f"Awaria API: {e}")

    uzasadnienie = list(parsed.get("uzasadnienie", []))[:MAX_PUNKTOW]
    ryzyka = list(parsed.get("matryca_ryzyk", []))
    return Narracja(uzasadnienie=uzasadnienie, matryca_ryzyk=ryzyka,
                    dostepna=True, powod=None)


def _parsuj_json(tekst: str) -> dict:
    """Wyłuskaj obiekt JSON z odpowiedzi (model bywa rozmowny)."""
    try:
        return json.loads(tekst)
    except json.JSONDecodeError:
        start = tekst.find("{")
        end = tekst.rfind("}")
        if start != -1 and end != -1:
            return json.loads(tekst[start:end + 1])
        raise
