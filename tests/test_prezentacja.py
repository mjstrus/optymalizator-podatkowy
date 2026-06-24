"""Testy warstwy prezentacji dla waterfalla i reinwestycji (Unit 5/6 update)."""

from optymalizator import ui_components as UI
from optymalizator.oszczednosci import LiniaOszczednosci, RozbicieOszczednosci
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


def test_wiersze_parametry_zawiera_kluczowe_opcje():
    from optymalizator.models import DaneKlienta, FormaZUS, Ulgi
    d = DaneKlienta(przychod=400_000, koszty=50_000, stawka_ryczaltu=0.12,
                    forma_zus=FormaZUS.DUZY, art_176=True, etat_poza_jdg=True,
                    ulgi=Ulgi(liczba_dzieci=2, ikze_kwota=5_000))
    wiersze = UI.wiersze_parametry(d)
    teksty = {w["Parametr"]: w["Wartość"] for w in wiersze}
    assert teksty["Roczny przychód"] == "400 000,00 zł"
    assert teksty["Etat poza działalnością (zbieg)"] == "Tak"
    assert teksty["Liczba dzieci (ulga)"] == "2"
    assert "Forma ZUS" in teksty and "Duży" in teksty["Forma ZUS"]
