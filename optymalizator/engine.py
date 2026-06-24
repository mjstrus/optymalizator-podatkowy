"""Silnik deterministyczny: run_optimization.

Czysta funkcja licząca cztery formy opodatkowania 2026, screening,
preferencje i werdykt — bez UI i bez LLM (R1, R2, R3, R4, R6, R7-liczby).

Wzór nadrzędny dla wszystkich form:
    dochod_netto = przychod − koszty − zus_spoleczny − zdrowotna − podatek
"""
from __future__ import annotations

from . import params_2026 as P
from .models import (
    DaneKlienta,
    Dostepnosc,
    FormaZUS,
    WynikEtat,
    WynikFormy,
    WynikOptymalizacji,
)


# --- ZUS społeczny (Krok 0) -------------------------------------------------
def _zus_spoleczny(dane: DaneKlienta) -> float:
    """Roczny ZUS społeczny wg formy. Podstawa emer.-rentowa jest stała
    (poniżej rocznego ograniczenia 282 600 zł), więc składka nie rośnie
    z dochodem (R5)."""
    # Zbieg tytułów: etat poza JDG z pensją ≥ minimalnej → tylko zdrowotna.
    if dane.etat_poza_jdg:
        return 0.0
    match dane.forma_zus:
        case FormaZUS.DUZY:
            return P.ZUS_DUZY_ROCZNY
        case FormaZUS.PREFERENCYJNY:
            return P.ZUS_PREFERENCYJNY_ROCZNY
        case FormaZUS.ULGA_NA_START | FormaZUS.ETAT_ZBIEG:
            return 0.0
        case FormaZUS.MALY_ZUS_PLUS:
            return _maly_zus_plus(dane)
    return P.ZUS_DUZY_ROCZNY


def _maly_zus_plus(dane: DaneKlienta) -> float:
    """Mały ZUS Plus: podstawa = 50% średniego miesięcznego dochodu z roku
    poprzedniego, ograniczona widełkami (od preferencyjnej do dużej), a składka
    liczona efektywną stawką społeczną. Uproszczenie MVP."""
    podstawa_mies = 0.5 * (dane.dochod_poprzedni_rok / 12)
    podstawa_mies = min(max(podstawa_mies, P.ZUS_MALY_PLUS_PODSTAWA_MIN),
                        P.ZUS_MALY_PLUS_PODSTAWA_MAX)
    skladka_mies = P.ZUS_SPOLECZNY_STAWKA_EFEKTYWNA * podstawa_mies
    skladka_mies = min(max(skladka_mies, P.ZUS_PREFERENCYJNY_MIES),
                       P.ZUS_DUZY_MIES)
    return round(skladka_mies * 12, 2)


# --- Negative screening (Krok 1) --------------------------------------------
def _screening(dane: DaneKlienta) -> dict[str, tuple[Dostepnosc, str | None]]:
    """Dostępność form wg R2."""
    wynik: dict[str, tuple[Dostepnosc, str | None]] = {
        "skala": (Dostepnosc.DOSTEPNA, None),
        "liniowy": (Dostepnosc.DOSTEPNA, None),
        "ryczalt": (Dostepnosc.DOSTEPNA, None),
        "spzoo": (Dostepnosc.DOSTEPNA, None),
    }
    if dane.byly_pracodawca:
        wynik["liniowy"] = (Dostepnosc.NIEDOSTEPNA,
                            "Były pracodawca w bieżącym/poprzednim roku.")
        wynik["ryczalt"] = (Dostepnosc.NIEDOSTEPNA,
                            "Były pracodawca w bieżącym/poprzednim roku.")
    if dane.przychod > P.RYCZALT_LIMIT_EUR * P.EUR_PLN:
        wynik["ryczalt"] = (Dostepnosc.NIEDOSTEPNA,
                            "Przychód powyżej limitu 2 mln EUR dla ryczałtu.")
    return wynik


# --- Podatek skali (z obsługą wspólnego rozliczenia, Krok 2) ----------------
def _podatek_skala_osoba(podstawa: float) -> float:
    if podstawa <= 0:
        return 0.0
    if podstawa <= P.SKALA_PROG:
        return max(0.0, P.SKALA_STAWKA_1 * podstawa - P.SKALA_KWOTA_ZMNIEJSZAJACA)
    return P.SKALA_PODATEK_PROG + P.SKALA_STAWKA_2 * (podstawa - P.SKALA_PROG)


def _podatek_skala(dane: DaneKlienta, podstawa: float) -> float:
    if dane.wspolne_rozliczenie:
        wspolna = (max(0.0, podstawa) + max(0.0, dane.dochod_malzonka)) / 2
        return 2 * _podatek_skala_osoba(wspolna)
    return _podatek_skala_osoba(podstawa)


# --- Cztery formy -----------------------------------------------------------
def _danina(dochod: float) -> float:
    """Danina solidarnościowa: 4% od nadwyżki dochodu ponad 1 mln zł.
    Dotyczy skali i liniowego; nie dotyczy ryczałtu ani dywidendy sp. z o.o."""
    return P.DANINA_STAWKA * max(0.0, dochod - P.DANINA_PROG)


def _odliczenia_dochodowe(dane: DaneKlienta) -> float:
    """Odliczenia od podstawy opodatkowania wspólne dla skali i liniowego:
    IKZE (do limitu) oraz zwolnienie PIT-0 dla rodzin 4+."""
    odliczenia = min(dane.ulgi.ikze_kwota, P.IKZE_LIMIT_JDG)
    if dane.ulgi.ulga_4plus:
        odliczenia += P.ULGA_4PLUS_LIMIT
    return odliczenia


def _oblicz_skala(dane: DaneKlienta, zus: float) -> WynikFormy:
    D_zdrow = dane.przychod - dane.koszty - zus
    zdrowotna = max(0.09 * D_zdrow, P.ZDROWOTNA_MIN_ROCZNA)
    podstawa = D_zdrow - _odliczenia_dochodowe(dane)
    podatek = _podatek_skala(dane, podstawa)
    # Ulga prorodzinna to odliczenie od podatku; nadwyżka zwracana (do wysokości
    # składek) — dopuszczamy ujemny "podatek" (zwrot) i odejmujemy go w netto.
    podatek = podatek - _ulga_dzieci(dane, podatek, zus, zdrowotna)
    podatek += _danina(D_zdrow)
    netto = dane.przychod - dane.koszty - zus - zdrowotna - podatek
    return WynikFormy("Skala", round(podatek, 2), round(zdrowotna, 2),
                      round(zus, 2), round(netto, 2))


def _oblicz_liniowy(dane: DaneKlienta, zus: float) -> WynikFormy:
    D_zdrow = dane.przychod - dane.koszty - zus
    zdrowotna = max(P.LINIOWY_ZDROWOTNA_STAWKA * D_zdrow, P.ZDROWOTNA_MIN_ROCZNA)
    odliczenie = min(zdrowotna, P.LINIOWY_LIMIT_ODLICZENIA)
    podstawa = D_zdrow - odliczenie - _odliczenia_dochodowe(dane)
    stawka = 0.05 if dane.ulgi.ip_box else P.LINIOWY_STAWKA
    podatek = max(0.0, stawka * podstawa)
    podatek += _danina(D_zdrow)
    netto = dane.przychod - dane.koszty - zus - zdrowotna - podatek
    return WynikFormy("Liniowy", round(podatek, 2), round(zdrowotna, 2),
                      round(zus, 2), round(netto, 2))


def _ryczalt_zdrowotna(przychod: float) -> float:
    if przychod <= P.RYCZALT_PROG_NISKI:
        return P.RYCZALT_ZDROWOTNA_NISKI
    if przychod <= P.RYCZALT_PROG_SREDNI:
        return P.RYCZALT_ZDROWOTNA_SREDNI
    return P.RYCZALT_ZDROWOTNA_WYSOKI


def _oblicz_ryczalt(dane: DaneKlienta, zus: float) -> WynikFormy:
    # Koszty NIE wchodzą do podstawy ryczałtu.
    zdrowotna = _ryczalt_zdrowotna(dane.przychod)
    podstawa = dane.przychod - zus - 0.5 * zdrowotna
    stawka = dane.stawka_ryczaltu if dane.stawka_ryczaltu is not None else 0.12
    podatek = max(0.0, stawka * podstawa)
    netto = dane.przychod - dane.koszty - zus - zdrowotna - podatek
    return WynikFormy("Ryczałt", round(podatek, 2), round(zdrowotna, 2),
                      round(zus, 2), round(netto, 2))


def _oblicz_etat(pensja_brutto: float) -> WynikEtat:
    """Rozlicz pensję wspólnika na etacie w spółce (składki + PIT skali)."""
    zus_prac = P.ZUS_PRACOWNIK_STAWKA * pensja_brutto
    zus_pracodawca = P.ZUS_PRACODAWCA_STAWKA * pensja_brutto
    podstawa_zdrow = pensja_brutto - zus_prac
    zdrowotna = P.ZDROWOTNA_ETAT_STAWKA * podstawa_zdrow
    podstawa_pit = max(0.0, podstawa_zdrow - P.KUP_ETAT_ROCZNE)
    pit = _podatek_skala_osoba(podstawa_pit)   # zdrowotna nieodliczana (Polski Ład)
    netto = pensja_brutto - zus_prac - zdrowotna - pit
    marginalna = P.SKALA_STAWKA_2 if podstawa_pit > P.SKALA_PROG else P.SKALA_STAWKA_1
    return WynikEtat(
        pensja_brutto=round(pensja_brutto, 2),
        zus_pracownik=round(zus_prac, 2),
        zus_pracodawca=round(zus_pracodawca, 2),
        zdrowotna=round(zdrowotna, 2),
        pit=round(pit, 2),
        netto=round(netto, 2),
        marginalna_stawka=marginalna,
        koszt_pracodawcy=round(pensja_brutto + zus_pracodawca, 2),
        podstawa_pit=round(podstawa_pit, 2),
    )


def _ekstrakcja_osoby(zysk_dost: float, *, poziom_etatu: float, art_176: bool,
                      art_176_kwota: float | None, powolanie_zarzad: bool) -> dict:
    """Zoptymalizowana wypłata dla JEDNEGO wspólnika z dostępnego zysku.
    Wypełnia jego I próg skali (12%) najtańszymi kanałami: etat → art.176 →
    powołanie. Każdy wspólnik ma WŁASNĄ progresję skali."""
    etat = None
    koszt_etatu = etat_podstawa = zus_prac = zus_pracodawca = zdrow_etat = pensja = 0.0
    if poziom_etatu > 0:
        pensja = poziom_etatu * P.MINIMALNE_WYNAGRODZENIE * 12
        etat = _oblicz_etat(pensja)
        koszt_etatu = etat.koszt_pracodawcy
        etat_podstawa = etat.podstawa_pit
        zus_prac, zus_pracodawca, zdrow_etat = (
            etat.zus_pracownik, etat.zus_pracodawca, etat.zdrowotna)

    dost = max(0.0, zysk_dost - koszt_etatu)
    room_12 = max(0.0, P.SKALA_PROG - etat_podstawa)

    swiadczenia = 0.0
    if art_176:
        art_k = art_176_kwota if art_176_kwota is not None else room_12
        swiadczenia = max(0.0, min(art_k, room_12, dost))
        dost -= swiadczenia
    powolanie = 0.0
    if powolanie_zarzad:
        powolanie = max(0.0, min(room_12 - swiadczenia, dost))
        dost -= powolanie

    return {
        "koszt_spolki": koszt_etatu + swiadczenia + powolanie,
        "scale_income": etat_podstawa + swiadczenia + powolanie,
        "zdrowotna": zdrow_etat + P.ZDROWOTNA_ETAT_STAWKA * powolanie,
        "zus": zus_prac + zus_pracodawca,
        "swiadczenia": swiadczenia, "powolanie": powolanie, "pensja": pensja,
        "etat": etat,
    }


def _oblicz_spzoo(dane: DaneKlienta, dodatkowy_zysk: float = 0.0) -> WynikFormy:
    """Sp. z o.o. liczona przez ZOPTYMALIZOWANY miks wypłaty (nie 100% dywidendy):
    art. 176 KSH (bez ZUS/zdrow.) → powołanie zarządu (skala+9% zdrow.) →
    dywidenda jako reszta. Przy R15 (`dodatkowy_zysk` z działalności małżonka)
    spółka ma DWÓCH wspólników — każdy z własnym art. 176, etatem i progresją."""
    zysk0 = dane.przychod - dane.koszty + dodatkowy_zysk
    dwoje = dodatkowy_zysk != 0 and dane.malzonek_do_spolki

    osoby = [_ekstrakcja_osoby(
        zysk0, poziom_etatu=dane.poziom_etatu, art_176=dane.art_176,
        art_176_kwota=dane.art_176_kwota, powolanie_zarzad=dane.powolanie_zarzad)]
    zysk = zysk0 - osoby[0]["koszt_spolki"]
    if dwoje:
        o2 = _ekstrakcja_osoby(
            zysk, poziom_etatu=dane.poziom_etatu, art_176=dane.art_176,
            art_176_kwota=dane.art_176_kwota, powolanie_zarzad=dane.powolanie_zarzad)
        osoby.append(o2)
        zysk -= o2["koszt_spolki"]

    cit = max(0.0, P.CIT_STAWKA * zysk)
    zysk_po_cit = zysk - cit
    dywidenda = max(0.0, zysk_po_cit)               # pełna wypłata reszty
    pit_dyw = P.DYWIDENDA_STAWKA * dywidenda

    # Każdy wspólnik rozlicza skalę osobno (własna progresja).
    pit_skala = sum(_podatek_skala_osoba(o["scale_income"]) for o in osoby)
    zdrowotna = sum(o["zdrowotna"] for o in osoby)
    zus = sum(o["zus"] for o in osoby)
    swiadczenia = sum(o["swiadczenia"] for o in osoby)
    powolanie = sum(o["powolanie"] for o in osoby)

    zalozenia_jedno = None
    if dane.jednoosobowa_spzoo and not dwoje:
        zdrowotna += P.SPZOO_JEDNOOSOBOWA_ZDROWOTNA_ROCZNA
        zus += P.SPZOO_JEDNOOSOBOWA_ZUS_ROCZNY
        zalozenia_jedno = "Jednoosobowa sp. z o.o.: doliczona zdrowotna i ZUS wspólnika."

    podatek = cit + pit_dyw + pit_skala
    netto = zysk0 - zus - zdrowotna - podatek       # tożsamość (pełna wypłata)

    czesci = []
    if swiadczenia > 0:
        czesci.append(f"art. 176 KSH {swiadczenia:,.0f} zł")
    if powolanie > 0:
        czesci.append(f"powołanie zarządu {powolanie:,.0f} zł")
    pensje = sum(o["pensja"] for o in osoby)
    if pensje > 0:
        czesci.append(f"etat {pensje:,.0f} zł")
    if dywidenda > 0:
        czesci.append(f"dywidenda {dywidenda:,.0f} zł")
    zalozenia = ("Wypłata zoptymalizowana"
                 + (" (2 wspólników)" if dwoje else "") + ": "
                 + ", ".join(czesci) + ".")
    if zalozenia_jedno:
        zalozenia = zalozenia_jedno + " " + zalozenia

    etat1 = osoby[0]["etat"]
    return WynikFormy(
        "Sp. z o.o.", round(podatek, 2), round(zdrowotna, 2),
        round(zus, 2), round(netto, 2), zalozenia=zalozenia,
        pensja_etat=(round(pensje, 2) if pensje > 0 else None),
        zus_od_etatu=(round(zus, 2) if pensje > 0 else None),
        zdrowotna_od_etatu=(round(zdrowotna, 2) if pensje > 0 else None),
        koszt_pensji_w_spolce=(etat1.koszt_pracodawcy if etat1 else None),
        marginalna_stawka_etatu=(etat1.marginalna_stawka if etat1 else None),
        swiadczenia_art176=(round(swiadczenia, 2) if dane.art_176 else None),
        wyplata_powolanie=(round(powolanie, 2) if powolanie > 0 else None),
        wyplata_dywidenda=round(dywidenda, 2),
    )


# --- Ulgi pomocnicze --------------------------------------------------------
def _ulga_dzieci(dane: DaneKlienta, podatek: float, zus: float,
                 zdrowotna: float) -> float:
    """Ulga prorodzinna wg progów na kolejne dzieci. Nadwyżka ponad podatek
    jest zwracana do wysokości zapłaconych składek (ZUS + zdrowotna)."""
    naliczona = 0.0
    for i in range(1, dane.ulgi.liczba_dzieci + 1):
        if i <= 2:
            naliczona += P.ULGA_DZIECKO_1_2
        elif i == 3:
            naliczona += P.ULGA_DZIECKO_3
        else:
            naliczona += P.ULGA_DZIECKO_4
    # Efektywnie odliczalne: podatek + limit zwrotu (składki).
    return min(naliczona, max(0.0, podatek) + zus + zdrowotna)


def _najlepsza_jdg_malzonka(dane: DaneKlienta) -> WynikFormy | None:
    """Samodzielny najlepszy wynik małżonka na JDG (skala/liniowy/ryczałt) —
    bez sp. z o.o., bez R15. Uwzględnia ZUS małżonka wg jego formy."""
    malzonek = DaneKlienta(
        przychod=dane.malzonek_przychod,
        koszty=dane.malzonek_koszty,
        stawka_ryczaltu=dane.stawka_ryczaltu,
        forma_zus=dane.malzonek_forma_zus,
        dochod_poprzedni_rok=dane.malzonek_dochod_poprzedni_rok,
        etat_poza_jdg=dane.etat_poza_jdg_malzonek,
    )
    w = run_optimization(malzonek)
    jdg = [f for f in w.formy if f.nazwa != "Sp. z o.o."
           and f.dostepnosc == Dostepnosc.DOSTEPNA]
    return max(jdg, key=lambda f: f.dochod_netto, default=None)


# --- Punkt wejścia ----------------------------------------------------------
def run_optimization(dane: DaneKlienta) -> WynikOptymalizacji:
    """Policz cztery formy, zastosuj screening i wyłoń werdykt."""
    zus = _zus_spoleczny(dane)

    # R15: małżonek wnoszony do spółki → porównanie na poziomie PARY.
    # JDG (klient na danej formie) + samodzielny najlepszy wynik małżonka;
    # sp. z o.o. wciąga zysk z działalności małżonka.
    dodatkowy_zysk = 0.0
    malzonek_jdg = None
    if dane.malzonek_do_spolki:
        dodatkowy_zysk = dane.malzonek_przychod - dane.malzonek_koszty
        malzonek_jdg = _najlepsza_jdg_malzonka(dane)

    formy = [
        _oblicz_skala(dane, zus),
        _oblicz_liniowy(dane, zus),
        _oblicz_ryczalt(dane, zus),
        _oblicz_spzoo(dane, dodatkowy_zysk=dodatkowy_zysk),
    ]
    if dane.malzonek_do_spolki and malzonek_jdg is not None:
        # Formy JDG na poziomie PARY: klient + samodzielny najlepszy wynik
        # małżonka. Kolumny (podatek/zdrowotna/ZUS) też sumują oboje (B).
        for f in formy:
            if f.nazwa != "Sp. z o.o.":
                f.dochod_netto_klient = f.dochod_netto
                f.dochod_netto_malzonek = malzonek_jdg.dochod_netto
                f.dochod_netto = round(f.dochod_netto + malzonek_jdg.dochod_netto, 2)
                f.podatek = round(f.podatek + malzonek_jdg.podatek, 2)
                f.zdrowotna = round(f.zdrowotna + malzonek_jdg.zdrowotna, 2)
                f.zus_spoleczny = round(f.zus_spoleczny + malzonek_jdg.zus_spoleczny, 2)

    # Screening: oznacz niedostępne formy.
    screening = _screening(dane)
    klucz = {"Skala": "skala", "Liniowy": "liniowy",
             "Ryczałt": "ryczalt", "Sp. z o.o.": "spzoo"}
    for f in formy:
        dost, powod = screening[klucz[f.nazwa]]
        f.dostepnosc = dost
        f.powod_niedostepnosci = powod

    # Werdykt tylko spośród dostępnych form.
    dostepne = [f for f in formy if f.dostepnosc == Dostepnosc.DOSTEPNA]
    dostepne_sort = sorted(dostepne, key=lambda f: f.dochod_netto, reverse=True)
    najlepsza = dostepne_sort[0]
    roznica = (najlepsza.dochod_netto - dostepne_sort[1].dochod_netto
               if len(dostepne_sort) > 1 else 0.0)

    return WynikOptymalizacji(
        formy=formy,
        werdykt=najlepsza.nazwa,
        roznica_do_drugiej=round(roznica, 2),
    )
