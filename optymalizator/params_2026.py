"""Stałe podatkowe i składkowe na rok 2026 — JEDNO źródło prawdy.

Aktualizacja na 2027 = zmiana wyłącznie w tym pliku.
Wartości zweryfikowane (ZUS, Obwieszczenie MF z 12.12.2025 M.P. poz. 1274, GUS).
Wszystkie kwoty roczne, chyba że nazwa wskazuje inaczej (_MIES).
"""

# --- Wynagrodzenia / przeciętne ---------------------------------------------
MINIMALNE_WYNAGRODZENIE = 4_806.00          # zł/mies brutto
PRZECIETNE_WYNAGRODZENIE = 9_420.00         # zł/mies (prognozowane 2026)
PRZECIETNE_SEKTOR_IVQ = 9_228.64            # zł/mies — podstawa zdrowotnej ryczałtu

# --- Skala podatkowa --------------------------------------------------------
SKALA_PROG = 120_000                         # próg II stawki
SKALA_STAWKA_1 = 0.12
SKALA_STAWKA_2 = 0.32
SKALA_KWOTA_ZMNIEJSZAJACA = 3_600            # 12% × 30 000 kwoty wolnej
SKALA_PODATEK_PROG = 10_800                  # 12%×120 000 − 3 600 = 14 400−3 600

# Wspólne rozliczenie małżonków
WSPOLNE_PROG = 240_000                        # podwojony próg II stawki
WSPOLNE_KWOTA_WOLNA = 60_000                  # podwojona kwota wolna

# --- Składka zdrowotna ------------------------------------------------------
# Rok składkowy zdrowotny luty 2026 – styczeń 2027.
ZDROWOTNA_STYCZEN = 314.96                    # styczeń 2026 (koniec starego roku)
ZDROWOTNA_MIN_MIES = 432.54                   # luty–grudzień 2026
# KRYTYCZNE: minimum roczne = 1×314,96 + 11×432,54 (NIE 12×432,54)
ZDROWOTNA_MIN_ROCZNA = round(ZDROWOTNA_STYCZEN + 11 * ZDROWOTNA_MIN_MIES, 2)  # 5 072,90

# Liniowy
LINIOWY_STAWKA = 0.19
LINIOWY_ZDROWOTNA_STAWKA = 0.049
LINIOWY_LIMIT_ODLICZENIA = 14_100            # limit odliczenia zdrowotnej

# Ryczałt — zdrowotna miesięczna od 60/100/180% przeciętnego (9 228,64 zł)
RYCZALT_ZDROWOTNA_NISKI_MIES = 498.35        # przychód ≤ 60 000
RYCZALT_ZDROWOTNA_SREDNI_MIES = 830.58       # 60 000 < przychód ≤ 300 000
RYCZALT_ZDROWOTNA_WYSOKI_MIES = 1_495.04     # przychód > 300 000
RYCZALT_ZDROWOTNA_NISKI = round(RYCZALT_ZDROWOTNA_NISKI_MIES * 12, 2)    # 5 980,20
RYCZALT_ZDROWOTNA_SREDNI = round(RYCZALT_ZDROWOTNA_SREDNI_MIES * 12, 2)  # 9 966,96
RYCZALT_ZDROWOTNA_WYSOKI = round(RYCZALT_ZDROWOTNA_WYSOKI_MIES * 12, 2)  # 17 940,48
RYCZALT_PROG_NISKI = 60_000
RYCZALT_PROG_SREDNI = 300_000

# --- ZUS społeczny ----------------------------------------------------------
ZUS_DUZY_MIES = 1_926.76                      # z chorobowym + FP, podstawa 5 652,00
ZUS_DUZY_PODSTAWA_MIES = 5_652.00
ZUS_PREFERENCYJNY_MIES = 456.18              # preferencyjny / mały ZUS minimum
ZUS_PREFERENCYJNY_PODSTAWA_MIES = 1_441.80
ZUS_MALY_PLUS_PODSTAWA_MIN = 1_441.80
ZUS_MALY_PLUS_PODSTAWA_MAX = 5_652.00
ZUS_OGRANICZENIE_PODSTAWY = 282_600          # roczne ograniczenie emer.-rentowej

# Roczne kwoty ZUS społecznego (uproszczenie 12 × stawka)
ZUS_DUZY_ROCZNY = round(ZUS_DUZY_MIES * 12, 2)             # 23 121,12
ZUS_PREFERENCYJNY_ROCZNY = round(ZUS_PREFERENCYJNY_MIES * 12, 2)  # 5 474,16

# --- Sp. z o.o. -------------------------------------------------------------
CIT_STAWKA = 0.09                            # mały podatnik
CIT_STAWKA_STANDARD = 0.19
DYWIDENDA_STAWKA = 0.19                      # podatek od dywidendy
# Efektywne netto z zysku: (1−0,09)×(1−0,19) = 0,91×0,81 = 0,7371
DYWIDENDA_MNOZNIK_NETTO = round((1 - CIT_STAWKA) * (1 - DYWIDENDA_STAWKA), 4)  # 0,7371

# Jednoosobowa sp. z o.o. — wspólnik traktowany jak ZUS + zdrowotna
SPZOO_JEDNOOSOBOWA_ZDROWOTNA_ROCZNA = round(ZDROWOTNA_MIN_ROCZNA, 2)
SPZOO_JEDNOOSOBOWA_ZUS_ROCZNY = ZUS_DUZY_ROCZNY

# Efektywna stawka ZUS społecznego (z Dużego ZUS): składka / podstawa.
ZUS_SPOLECZNY_STAWKA_EFEKTYWNA = round(ZUS_DUZY_MIES / ZUS_DUZY_PODSTAWA_MIES, 4)

# --- Ulgi i preferencje (R3) ------------------------------------------------
# Ulga prorodzinna (kwoty roczne wg liczby dzieci).
ULGA_DZIECKO_1_2 = 1_112.04          # na 1. i 2. dziecko
ULGA_DZIECKO_3 = 2_000.04            # na 3. dziecko
ULGA_DZIECKO_4 = 2_700.00            # na 4. i każde kolejne
# PIT-0 dla rodzin 4+: zwolnienie przychodu do limitu (na podatnika).
ULGA_4PLUS_LIMIT = 85_528
# IKZE — roczny limit wpłaty dla prowadzących działalność (1,8× przeciętne).
IKZE_LIMIT_JDG = round(1.8 * PRZECIETNE_WYNAGRODZENIE, 2)   # 16 956,00

# --- Negative screening -----------------------------------------------------
RYCZALT_LIMIT_EUR = 2_000_000                # limit przychodu dla ryczałtu (EUR)
EUR_PLN = 4.30                               # kurs orientacyjny do limitu
