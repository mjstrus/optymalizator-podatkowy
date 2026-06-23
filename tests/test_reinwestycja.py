"""Testy Unit 8: moduł reinwestycji IKE/IKZE/PPK (R14, R16)."""
import pytest

from optymalizator import params_2026 as P
from optymalizator.reinwestycja import oblicz_reinwestycje, WynikReinwestycji


def _alok(w, nazwa):
    return next(a for a in w.alokacje if nazwa.lower() in a.nazwa.lower())


def test_trzy_alokacje_mix_rekomendowany():
    w = oblicz_reinwestycje(100_000, marginalna_stawka=0.12)
    assert isinstance(w, WynikReinwestycji)
    assert len(w.alokacje) == 3
    assert w.rekomendacja.rekomendowana is True
    assert "mix" in w.rekomendacja.nazwa.lower()


def test_podzial_proporcja_50_50():
    w = oblicz_reinwestycje(100_000, marginalna_stawka=0.12, proporcja=0.5)
    assert w.czesc_pracujaca == pytest.approx(50_000)
    assert w.czesc_gotowka == pytest.approx(50_000)


def test_proporcja_60_40():
    w = oblicz_reinwestycje(100_000, marginalna_stawka=0.12, proporcja=0.6)
    assert w.czesc_pracujaca == pytest.approx(60_000)
    assert w.czesc_gotowka == pytest.approx(40_000)


def test_niski_etat_mix_glownie_ike():
    w = oblicz_reinwestycje(100_000, marginalna_stawka=0.12)
    mix = _alok(w, "mix")
    assert mix.ike > mix.ikze


def test_wysoki_etat_ikze_w_pierwszej_kolejnosci():
    w = oblicz_reinwestycje(100_000, marginalna_stawka=0.32)
    mix = _alok(w, "mix")
    assert mix.ikze == pytest.approx(P.IKZE_LIMIT_ETAT)


def test_nadwyzka_ponad_limity_wraca_do_gotowki():
    # invest 50 000 > IKE 28 260 + IKZE 11 304
    w = oblicz_reinwestycje(100_000, marginalna_stawka=0.12)
    mix = _alok(w, "mix")
    assert mix.gotowka_dodatkowa > 0


def test_para_podwaja_limity():
    w = oblicz_reinwestycje(200_000, marginalna_stawka=0.32, para=True)
    mix = _alok(w, "mix")
    assert mix.ikze == pytest.approx(2 * P.IKZE_LIMIT_ETAT)
    assert mix.ike <= 2 * P.IKE_LIMIT + 0.01


def test_stopa_poza_zakresem_przycieta():
    w = oblicz_reinwestycje(100_000, marginalna_stawka=0.12,
                            stopy_zwrotu=(0.01, 0.12))
    stopy = sorted(p.stopa for p in w.projekcje)
    assert stopy[0] == pytest.approx(0.02)    # 1% → 2%
    assert stopy[-1] == pytest.approx(0.08)   # 12% → 8%


def test_brak_etatu_ppk_niedostepne():
    w = oblicz_reinwestycje(100_000, marginalna_stawka=0.19, etat=False)
    assert w.ppk is None


def test_projekcja_zwraca_widelki_i_disclaimer():
    w = oblicz_reinwestycje(100_000, marginalna_stawka=0.12,
                            stopy_zwrotu=(0.04, 0.06), horyzont=10)
    assert len(w.projekcje) == 2
    # wyższa stopa → wyższa wartość końcowa
    p = sorted(w.projekcje, key=lambda x: x.stopa)
    assert p[1].wartosc_koncowa > p[0].wartosc_koncowa
    assert "doradztw" in w.disclaimer.lower()
