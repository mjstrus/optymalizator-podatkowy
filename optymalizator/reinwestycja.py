"""Unit 8: moduł reinwestycji oszczędności w III filar (R14, R16).

Dzieli oszczędność na część gotówkową i „pracującą", liczy TRZY alokacje
(IKE-only / IKZE-only / mix wg progu) na tych samych danych — mix oznaczony
jako rekomendacja. Projekcja wzrostu części pracującej w widełkach stóp zwrotu
(walidowanych do 2–8% realnie). PPK tylko przy etacie.

Disclaimer „nie stanowi doradztwa inwestycyjnego" zwracany z wynikiem.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import params_2026 as P

DISCLAIMER = ("Projekcja ma charakter ilustracyjny i NIE stanowi doradztwa "
              "inwestycyjnego. Rzeczywiste stopy zwrotu mogą się różnić.")

STOPA_MIN = 0.02
STOPA_MAX = 0.08


@dataclass
class Alokacja:
    nazwa: str
    ike: float
    ikze: float
    gotowka_dodatkowa: float        # nadwyżka ponad limity → wraca do gotówki
    rekomendowana: bool = False

    @property
    def zainwestowane(self) -> float:
        return round(self.ike + self.ikze, 2)


@dataclass
class Projekcja:
    stopa: float
    horyzont: int
    wartosc_koncowa: float
    zysk: float


@dataclass
class WynikReinwestycji:
    oszczednosc: float
    proporcja: float
    czesc_pracujaca: float
    czesc_gotowka: float
    alokacje: list[Alokacja] = field(default_factory=list)
    rekomendacja: Alokacja | None = None
    projekcje: list[Projekcja] = field(default_factory=list)
    ppk: dict | None = None
    disclaimer: str = DISCLAIMER


def _limity(para: bool, etat: bool) -> tuple[float, float]:
    mnoznik = 2 if para else 1
    ike_max = P.IKE_LIMIT * mnoznik
    # Wspólnik na etacie nie jest „prowadzącym działalność" → limit etatowy.
    ikze_jedn = P.IKZE_LIMIT_ETAT if etat else P.IKZE_LIMIT_JDG
    return ike_max, ikze_jedn * mnoznik


def _alokuj(nazwa, invest, ike_max, ikze_max, *, kolejnosc) -> Alokacja:
    """`kolejnosc`: 'ike' lub 'ikze' — który instrument napełniamy najpierw."""
    if kolejnosc == "ikze":
        ikze = min(invest, ikze_max)
        reszta = invest - ikze
        ike = min(reszta, ike_max)
    else:
        ike = min(invest, ike_max)
        reszta = invest - ike
        ikze = min(reszta, ikze_max)
    gotowka = round(invest - ike - ikze, 2)
    return Alokacja(nazwa, round(ike, 2), round(ikze, 2), max(0.0, gotowka))


def oblicz_reinwestycje(oszczednosc: float, *, marginalna_stawka: float,
                        proporcja: float = 0.5,
                        stopy_zwrotu: tuple[float, ...] = (0.04, 0.06),
                        horyzont: int = 10, para: bool = False,
                        etat: bool = True,
                        pensja_etat: float | None = None) -> WynikReinwestycji:
    """Policz reinwestycję oszczędności. Stopy zwrotu przycinane do 2–8% (R16)."""
    czesc_pracujaca = round(oszczednosc * proporcja, 2)
    czesc_gotowka = round(oszczednosc - czesc_pracujaca, 2)
    ike_max, ikze_max = _limity(para, etat)

    invest = czesc_pracujaca
    ike_only = _alokuj("IKE-only", invest, ike_max, 0.0, kolejnosc="ike")
    ikze_only = _alokuj("IKZE-only", invest, 0.0, ikze_max, kolejnosc="ikze")
    # Mix wg progu: wysoka stawka (liniowy/32%) → najpierw IKZE; 12% → IKE.
    kolejnosc = "ikze" if marginalna_stawka >= 0.19 else "ike"
    mix = _alokuj("Mix wg progu", invest, ike_max, ikze_max, kolejnosc=kolejnosc)
    mix.rekomendowana = True

    # Projekcja części faktycznie zainwestowanej (mix), w widełkach stóp.
    stopy = sorted({min(max(s, STOPA_MIN), STOPA_MAX) for s in stopy_zwrotu})
    invested = mix.zainwestowane
    projekcje = []
    for s in stopy:
        koncowa = invested * (1 + s) ** horyzont
        projekcje.append(Projekcja(s, horyzont, round(koncowa, 2),
                                   round(koncowa - invested, 2)))

    # PPK tylko przy etacie (część pracodawcy jest kosztem spółki).
    ppk = None
    if etat and pensja_etat:
        ppk = {
            "wplata_pracownik": round(P.PPK_PRACOWNIK * pensja_etat, 2),
            "wplata_pracodawca": round(P.PPK_PRACODAWCA * pensja_etat, 2),
            "doplata_powitalna": P.PPK_WPLATA_POWITALNA,
            "doplata_roczna": P.PPK_DOPLATA_ROCZNA,
        }

    return WynikReinwestycji(
        oszczednosc=round(oszczednosc, 2),
        proporcja=proporcja,
        czesc_pracujaca=czesc_pracujaca,
        czesc_gotowka=czesc_gotowka,
        alokacje=[ike_only, ikze_only, mix],
        rekomendacja=mix,
        projekcje=projekcje,
        ppk=ppk,
    )
