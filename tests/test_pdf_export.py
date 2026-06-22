"""Testy Unit 6: generator brandowanego PDF."""
import pytest

from optymalizator.engine import run_optimization
from optymalizator.models import DaneKlienta
from optymalizator.narracja import Narracja
from optymalizator import pdf_export as PDF


@pytest.fixture
def wynik():
    return run_optimization(DaneKlienta(przychod=500_000, koszty=20_000,
                                        stawka_ryczaltu=0.12))


def _tytuly(sekcje):
    return [s["tytul"] for s in sekcje]


def test_sekcje_komplet_z_narracja(wynik):
    narracja = Narracja(uzasadnienie=["Punkt A", "Punkt B"],
                        matryca_ryzyk=[{"obszar": "Ryczałt", "opis": "..."}],
                        dostepna=True)
    sekcje = PDF.zbuduj_sekcje(wynik, narracja)
    tytuly = " ".join(_tytuly(sekcje)).lower()
    assert "werdykt" in tytuly
    assert "porówna" in tytuly      # tabela porównawcza
    assert "uzasadnien" in tytuly
    assert "ryzyk" in tytuly


def test_sekcje_degradacja_narracji_zachowuje_liczby(wynik):
    narracja = Narracja(dostepna=False, powod="Brak klucza API")
    sekcje = PDF.zbuduj_sekcje(wynik, narracja)
    tytuly = " ".join(_tytuly(sekcje)).lower()
    # tabela i werdykt nadal obecne mimo braku narracji
    assert "werdykt" in tytuly
    assert "porówna" in tytuly


def test_generuj_pdf_zwraca_poprawny_plik(wynik):
    dane = PDF.generuj_pdf(wynik, Narracja(uzasadnienie=["x"], dostepna=True))
    assert isinstance(dane, (bytes, bytearray))
    assert dane[:5] == b"%PDF-"
    assert len(dane) > 1000          # niepusty dokument


def test_generuj_pdf_bez_narracji_nadal_dziala(wynik):
    dane = PDF.generuj_pdf(wynik, narracja=None)
    assert dane[:5] == b"%PDF-"
    assert len(dane) > 1000
