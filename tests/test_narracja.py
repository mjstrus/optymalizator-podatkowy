"""Testy Unit 4: warstwa narracyjna LLM (mock API, bez realnych wywołań)."""
import json

import pytest

from optymalizator.engine import run_optimization
from optymalizator.models import DaneKlienta
from optymalizator.narracja import generuj_narracje


@pytest.fixture
def wynik():
    return run_optimization(DaneKlienta(przychod=500_000, koszty=20_000,
                                        stawka_ryczaltu=0.12))


class _FakeMessages:
    def __init__(self, payload, capture):
        self._payload = payload
        self._capture = capture

    def create(self, **kwargs):
        self._capture.update(kwargs)
        text = json.dumps(self._payload, ensure_ascii=False)
        return type("Resp", (), {"content": [type("B", (), {"text": text})()]})()


class _FakeClient:
    def __init__(self, payload, capture):
        self.messages = _FakeMessages(payload, capture)


def test_generuje_max_3_punkty_i_ryzyka(wynik):
    payload = {
        "uzasadnienie": ["Punkt 1", "Punkt 2", "Punkt 3", "Punkt 4 (nadmiarowy)"],
        "matryca_ryzyk": [
            {"obszar": "Ryczałt", "opis": "Brak odliczenia kosztów."},
        ],
    }
    capture = {}
    n = generuj_narracje(wynik, klient=_FakeClient(payload, capture))
    assert n.dostepna is True
    assert len(n.uzasadnienie) <= 3            # przycięte do 3 (R7)
    assert len(n.matryca_ryzyk) >= 1


def test_prompt_zawiera_liczby_i_zakaz_przeliczania(wynik):
    capture = {}
    payload = {"uzasadnienie": ["x"], "matryca_ryzyk": []}
    generuj_narracje(wynik, klient=_FakeClient(payload, capture))
    # liczby przekazane modelowi jako dane
    tresc = json.dumps(capture, ensure_ascii=False, default=str)
    assert wynik.werdykt in tresc
    # zakaz przeliczania w instrukcji systemowej
    assert "nie przelicz" in tresc.lower() or "nie licz" in tresc.lower()


def test_graceful_degradation_przy_awarii_api(wynik):
    class _Padajacy:
        class messages:
            @staticmethod
            def create(**kwargs):
                raise RuntimeError("API niedostępne")

    n = generuj_narracje(wynik, klient=_Padajacy())
    assert n.dostepna is False
    assert n.powod is not None
    # liczby muszą zostać użyteczne — placeholdery, nie crash
    assert isinstance(n.uzasadnienie, list)


def test_graceful_degradation_bez_klucza(monkeypatch, wynik):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    n = generuj_narracje(wynik, klient=None)
    assert n.dostepna is False
    assert "klucz" in (n.powod or "").lower()
