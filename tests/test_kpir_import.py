"""Testy importu KPiR (PDF). Próbka zawiera dane klienta — pomijane gdy brak."""
import os

import pytest

from optymalizator.kpir_import import ImportKPiR, kwota_pl, parsuj_kpir

PROBKA = "kpir - przykład.pdf"
_ma_probke = os.path.exists(PROBKA)
wymaga_probki = pytest.mark.skipif(not _ma_probke, reason="brak próbki KPiR")


def test_kwota_pl_rozne_separatory():
    assert kwota_pl("5 207 580,87") == pytest.approx(5_207_580.87)
    assert kwota_pl("1 627 651,10") == pytest.approx(1_627_651.10)
    assert kwota_pl("0.00") == pytest.approx(0.0)
    assert kwota_pl("493011,34") == pytest.approx(493_011.34)


@wymaga_probki
def test_parsuje_przychod_i_koszty():
    w = parsuj_kpir(PROBKA)
    assert w.przychod == pytest.approx(5_207_580.87)
    # koszty z uwzgl. różnicy remanentowej (podatkowo właściwe)
    assert w.koszty == pytest.approx(4_635_139.45)
    assert w.dochod == pytest.approx(572_441.42)


@wymaga_probki
def test_kontrola_spojnosci_ksiegowej():
    w = parsuj_kpir(PROBKA)
    # przychód - koszty == dochód → odczyt wiarygodny
    assert w.spojnosc is True
    assert w.ostrzezenia == []


@wymaga_probki
def test_pelny_odczyt_podsumowania():
    w = parsuj_kpir(PROBKA)
    assert w.pola["wydatki"] == pytest.approx(3_086_918.43)
    assert w.pola["zakupy_towarow"] == pytest.approx(1_627_651.10)
    assert w.pola["koszty_uz_przychodu"] == pytest.approx(4_714_569.53)
    assert w.pola["roznica_remanentowa"] == pytest.approx(79_430.08)


@wymaga_probki
def test_parsuje_z_bytes():
    with open(PROBKA, "rb") as f:
        dane = f.read()
    w = parsuj_kpir(dane)
    assert w.przychod == pytest.approx(5_207_580.87)


def test_pusty_pdf_zwraca_ostrzezenie_bez_crasha():
    # Bytes niebędące PDF-em → łagodny błąd, nie wyjątek w górę.
    w = parsuj_kpir(b"to nie jest pdf")
    assert isinstance(w, ImportKPiR)
    assert w.przychod is None
    assert w.ostrzezenia  # jest komunikat
