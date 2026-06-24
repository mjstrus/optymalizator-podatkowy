"""Test noty o zysku zatrzymanym w sp. z o.o."""
from optymalizator import ui_components as UI
from optymalizator.engine import run_optimization
from optymalizator.models import DaneKlienta


def test_nota_gdy_zatrzymanie():
    w = run_optimization(DaneKlienta(przychod=900_000, koszty=50_000,
                                     wyplata_dywidendy_pct=0.2))
    nota = UI.nota_majatek_spzoo(w)
    assert nota and "zatrzymane" not in nota.lower() or "pozostawione" in nota.lower()
    assert "w kieszeni" in nota and "spółce" in nota


def test_brak_noty_przy_pelnej_wyplacie():
    w = run_optimization(DaneKlienta(przychod=900_000, koszty=50_000,
                                     wyplata_dywidendy_pct=1.0))
    assert UI.nota_majatek_spzoo(w) is None
