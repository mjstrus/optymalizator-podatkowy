"""Unit 7: rozbicie przewagi sp. z o.o. i waterfall oszczędności (R12, R13).

Tożsamość: dla każdej formy `netto = przychód − koszty − ZUS − zdrowotna −
podatek`. Przy tych samych przychodach/kosztach różnica netto rozkłada się
dokładnie na składniki — dzięki temu suma linii waterfalla zawsze domyka się
do różnicy netto.

Waterfall prezentowany BRUTTO: pełny ZUS/zdrowotna z JDG „znika" (+), a osobne,
obowiązkowe linie ZUS/zdrowotnej od etatu w spółce „dochodzą" (−). Guardrail:
linia etatu zawsze obecna (z flagą widoczności), by liczba brutto nie myliła.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .models import WynikFormy


@dataclass
class LiniaOszczednosci:
    etykieta: str
    kwota: float                 # ze znakiem: + przewaga spółki, − koszt spółki
    widoczna: bool = True


@dataclass
class RozbicieOszczednosci:
    linie: list[LiniaOszczednosci] = field(default_factory=list)
    netto: float = 0.0           # suma linii = różnica netto (spółka − JDG)
    spzoo_wygrywa: bool = False


def _linie_pary(spzoo: WynikFormy, jdg: WynikFormy,
                prefiks: str = "") -> list[LiniaOszczednosci]:
    """Pięć linii waterfalla dla jednej osoby (klient lub małżonek)."""
    return [
        LiniaOszczednosci(f"{prefiks}ZUS społeczny JDG znika",
                          round(jdg.zus_spoleczny, 2)),
        LiniaOszczednosci(f"{prefiks}ZUS od etatu w spółce",
                          round(-spzoo.zus_spoleczny, 2)),
        LiniaOszczednosci(f"{prefiks}Składka zdrowotna JDG znika",
                          round(jdg.zdrowotna, 2)),
        LiniaOszczednosci(f"{prefiks}Zdrowotna od etatu w spółce",
                          round(-spzoo.zdrowotna, 2)),
        LiniaOszczednosci(f"{prefiks}Różnica podatku (PIT/CIT)",
                          round(jdg.podatek - spzoo.podatek, 2)),
    ]


def rozbij_przewage(spzoo: WynikFormy, jdg: WynikFormy, *,
                    spzoo_malzonek: WynikFormy | None = None,
                    jdg_malzonek: WynikFormy | None = None
                    ) -> RozbicieOszczednosci:
    """Zbuduj waterfall oszczędności sp. z o.o. względem najlepszej JDG.
    Opcjonalnie dokłada analogiczny blok dla małżonka (R15)."""
    linie = _linie_pary(spzoo, jdg)
    if spzoo_malzonek is not None and jdg_malzonek is not None:
        linie += _linie_pary(spzoo_malzonek, jdg_malzonek, prefiks="Małżonek: ")

    netto = round(sum(linia.kwota for linia in linie), 2)
    return RozbicieOszczednosci(linie=linie, netto=netto,
                                spzoo_wygrywa=netto > 0)
