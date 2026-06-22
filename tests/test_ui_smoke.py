"""Testy Unit 5: warstwa prezentacji (bez uruchamiania serwera Streamlit)."""
import py_compile

import pytest

from optymalizator.engine import run_optimization
from optymalizator.models import DaneKlienta, Dostepnosc
from optymalizator import ui_components as UI


def test_formatuj_pln():
    assert UI.formatuj_pln(1234567.8) == "1 234 567,80 zł"
    assert UI.formatuj_pln(0) == "0,00 zł"
    assert UI.formatuj_pln(-50) == "-50,00 zł"


def test_tabela_porownawcza_ma_wiersz_na_kazda_forme():
    w = run_optimization(DaneKlienta(przychod=300_000, koszty=50_000,
                                     stawka_ryczaltu=0.12))
    tabela = UI.tabela_porownawcza(w)
    assert len(tabela) == 4
    naglowki = {"Forma", "Podatek", "Zdrowotna", "ZUS", "Dochód netto", "Status"}
    assert naglowki.issubset(tabela[0].keys())


def test_tabela_oznacza_niedostepne():
    w = run_optimization(DaneKlienta(przychod=300_000, koszty=50_000,
                                     stawka_ryczaltu=0.12, byly_pracodawca=True))
    tabela = UI.tabela_porownawcza(w)
    rycz = next(r for r in tabela if "Ryczałt" in r["Forma"])
    assert "NIEDOSTĘPNA" in rycz["Status"].upper()


def test_sprawdz_braki_wykrywa_brak_przychodu():
    braki = UI.sprawdz_braki(przychod=None, koszty=10_000, charakter_uslug="IT")
    assert any("przych" in b.lower() for b in braki)


def test_sprawdz_braki_komplet_danych_pusta_lista():
    braki = UI.sprawdz_braki(przychod=100_000, koszty=10_000,
                             charakter_uslug="IT")
    assert braki == []


def test_app_kompiluje_sie():
    # Smoke: skrypt Streamlit parsuje się bez błędów składni.
    py_compile.compile("app.py", doraise=True)
