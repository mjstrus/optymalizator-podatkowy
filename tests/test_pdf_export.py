"""Testy Unit 6: generator brandowanego PDF."""
import pytest

from optymalizator import pdf_export as PDF
from optymalizator.engine import run_optimization
from optymalizator.models import DaneKlienta
from optymalizator.narracja import Narracja


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


def test_sekcje_z_waterfall_i_reinwestycja():
    from optymalizator.models import Dostepnosc
    from optymalizator.oszczednosci import rozbij_przewage
    from optymalizator.reinwestycja import oblicz_reinwestycje
    w = run_optimization(DaneKlienta(przychod=800_000, koszty=30_000,
                                     stawka_ryczaltu=0.12, poziom_etatu=0.5))
    spzoo = next(f for f in w.formy if "z o.o" in f.nazwa.lower())
    jdg = max((f for f in w.formy if "z o.o" not in f.nazwa.lower()
               and f.dostepnosc == Dostepnosc.DOSTEPNA),
              key=lambda f: f.dochod_netto)
    rozb = rozbij_przewage(spzoo, jdg)
    rein = oblicz_reinwestycje(max(rozb.netto, 1.0), marginalna_stawka=0.12)
    sekcje = PDF.zbuduj_sekcje(w, None, rozbicie=rozb, reinwestycja=rein)
    tytuly = " ".join(s["tytul"] for s in sekcje).lower()
    assert "oszczędno" in tytuly       # waterfall
    assert "iii filaru" in tytuly      # sekcja IKE/IKZE
    dane = PDF.generuj_pdf(w, None, rozbicie=rozb, reinwestycja=rein)
    assert dane[:5] == b"%PDF-"
