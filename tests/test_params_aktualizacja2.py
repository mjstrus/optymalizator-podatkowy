"""Testy Unit 1 (Aktualizacja #2): stałe III filaru + składki od etatu."""
from optymalizator import params_2026 as P


def test_limity_trzeciego_filaru_2026():
    assert P.IKE_LIMIT == 28_260
    assert P.IKZE_LIMIT_ETAT == 11_304          # etat / nieprowadzący działalności
    assert P.IKZE_LIMIT_JDG == 16_956           # działalność (art. 8 ust. 6)


def test_ppk_stawki():
    assert P.PPK_PRACOWNIK == 0.02
    assert P.PPK_PRACODAWCA == 0.015


def test_skladki_zus_od_etatu():
    # pracownik: emerytalna 9,76 + rentowa 1,5 + chorobowa 2,45 = 13,71%
    assert round(P.ZUS_PRACOWNIK_STAWKA, 4) == 0.1371
    # pracodawca: emerytalna 9,76 + rentowa 6,5 + wypadkowa + FP/FGŚP
    assert P.ZUS_PRACODAWCA_STAWKA > P.ZUS_PRACOWNIK_STAWKA
    assert P.ZDROWOTNA_ETAT_STAWKA == 0.09
