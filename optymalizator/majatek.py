"""Projekcja skumulowanego majątku w czasie (1 / 5 / 10 lat).

Porównuje formy nie tylko rocznym dochodem netto, ale tym, ile zostawiają
łącznie po latach. Dwa tryby:
- `stopa = 0`: prosty skumulowany dochód netto (lata × netto) — bez założeń
  inwestycyjnych, w pełni porównywalny między formami.
- `stopa > 0`: dochód netto odkładany corocznie i kapitalizowany (przyszła
  wartość renty rocznej) — ilustracja, wymaga założenia o pełnym odkładaniu.

Założenie: stały dochód netto w każdym roku (prognoza 2026 powtarzalna).
To ilustracja porównawcza, nie gwarancja ani doradztwo inwestycyjne.
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import Dostepnosc, WynikOptymalizacji


@dataclass
class ProjekcjaMajatku:
    forma: str
    rekomendowana: bool
    wartosci: dict[int, float]      # {rok: skumulowany majątek}


def _fv_renty(netto: float, lata: int, stopa: float) -> float:
    """Przyszła wartość renty rocznej (wpłata `netto` na koniec każdego roku)."""
    if stopa == 0:
        return netto * lata
    return netto * (((1 + stopa) ** lata - 1) / stopa)


def projekcja_majatku(wynik: WynikOptymalizacji,
                      lata: tuple[int, ...] = (1, 5, 10),
                      stopa: float = 0.0) -> list[ProjekcjaMajatku]:
    """Skumulowany majątek po zadanych latach dla każdej dostępnej formy."""
    proj = []
    for f in wynik.formy:
        if f.dostepnosc != Dostepnosc.DOSTEPNA:
            continue
        wartosci = {n: round(_fv_renty(f.dochod_netto, n, stopa), 2)
                    for n in lata}
        proj.append(ProjekcjaMajatku(f.nazwa, f.nazwa == wynik.werdykt, wartosci))
    return proj
