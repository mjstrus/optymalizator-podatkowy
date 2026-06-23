"""Testy warstwy prezentacji dla waterfalla i reinwestycji (Unit 5/6 update)."""
import pytest

from optymalizator import ui_components as UI
from optymalizator.oszczednosci import RozbicieOszczednosci, LiniaOszczednosci
from optymalizator.reinwestycja import oblicz_reinwestycje


def test_formatuj_pln_signed():
    assert UI.formatuj_pln_signed(1234.5) == "+1 234,50 zł"
    assert UI.formatuj_pln_signed(-1000) == "-1 000,00 zł"
    assert UI.formatuj_pln_signed(0) == "0,00 zł"


def test_wiersze_waterfall():
    r = RozbicieOszczednosci(
        linie=[LiniaOszczednosci("ZUS JDG znika", 23000.0),
               LiniaOszczednosci("ZUS od etatu w spółce", -6000.0)],
        netto=17000.0, spzoo_wygrywa=True)
    wiersze = UI.wiersze_waterfall(r)
    assert len(wiersze) == 3   # 2 linie + wiersz podsumowania netto
    assert "Pozycja" in wiersze[0] and "Kwota" in wiersze[0]
    assert wiersze[0]["Kwota"].startswith("+")
    assert wiersze[1]["Kwota"].startswith("-")
    assert "netto" in wiersze[-1]["Pozycja"].lower()


def test_wiersze_alokacje_mix_oznaczony():
    w = oblicz_reinwestycje(100_000, marginalna_stawka=0.12)
    wiersze = UI.wiersze_alokacje(w)
    assert len(wiersze) == 3
    mix = next(r for r in wiersze if "mix" in r["Wariant"].lower())
    assert "⭐" in mix["Wariant"] or "rekom" in mix["Wariant"].lower()
