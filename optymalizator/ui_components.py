"""Warstwa prezentacji — czyste funkcje formatujące wynik silnika.

Oddzielone od Streamlita, by były testowalne bez serwera.
"""
from __future__ import annotations

from .models import Dostepnosc, WynikOptymalizacji

# Branding Abacus
BRAND_NAVY_OD = "#0d1b2a"
BRAND_NAVY_DO = "#1b2d45"
BRAND_GRADIENT = f"linear-gradient(135deg, {BRAND_NAVY_OD}, {BRAND_NAVY_DO})"


def formatuj_pln(kwota: float) -> str:
    """Sformatuj kwotę w stylu polskim: spacja jako separator tysięcy,
    przecinek jako separator dziesiętny."""
    s = f"{kwota:,.2f}"  # 1,234,567.80
    s = s.replace(",", " ").replace(".", ",")
    return f"{s} zł"


def formatuj_pln_signed(kwota: float) -> str:
    """Jak formatuj_pln, ale z jawnym znakiem '+' dla wartości dodatnich."""
    znak = "+" if kwota > 0 else ""
    return znak + formatuj_pln(kwota)


def wiersze_waterfall(rozbicie) -> list[dict]:
    """Wiersze waterfalla oszczędności (Unit 7) — z jawnym znakiem kwoty."""
    wiersze = [
        {"Pozycja": linia.etykieta, "Kwota": formatuj_pln_signed(linia.kwota)}
        for linia in rozbicie.linie if linia.widoczna
    ]
    wiersze.append({"Pozycja": "Oszczędność netto (rocznie)",
                    "Kwota": formatuj_pln_signed(rozbicie.netto)})
    return wiersze


def wiersze_alokacje(reinwestycja) -> list[dict]:
    """Wiersze porównania alokacji III filaru (Unit 8); mix wyróżniony."""
    wiersze = []
    for a in reinwestycja.alokacje:
        nazwa = ("⭐ " + a.nazwa) if a.rekomendowana else a.nazwa
        wiersze.append({
            "Wariant": nazwa,
            "IKE": formatuj_pln(a.ike),
            "IKZE": formatuj_pln(a.ikze),
            "Gotówka (nadwyżka)": formatuj_pln(a.gotowka_dodatkowa),
        })
    return wiersze


_FORMA_ZUS_PL = {
    "duzy": "Duży ZUS", "maly_zus_plus": "Mały ZUS Plus",
    "preferencyjny": "Preferencyjny", "ulga_na_start": "Ulga na start",
    "etat_zbieg": "Etat (zbieg)",
}


def _tak_nie(v: bool) -> str:
    return "Tak" if v else "Nie"


def nota_majatek_spzoo(wynik: WynikOptymalizacji) -> str | None:
    """Jeśli część zysku sp. z o.o. zostaje w spółce — wyjaśnij skład „dochodu
    netto" (kieszeń + zatrzymane), żeby było to widoczne, nie schowane."""
    spzoo = next((f for f in wynik.formy if "z o.o" in f.nazwa.lower()), None)
    if not spzoo or not spzoo.zysk_zatrzymany:
        return None
    kieszen = spzoo.dochod_netto - spzoo.zysk_zatrzymany
    return (f"Dochód netto sp. z o.o. ({formatuj_pln(spzoo.dochod_netto)}) to "
            f"majątek łączny: {formatuj_pln(kieszen)} w kieszeni + "
            f"{formatuj_pln(spzoo.zysk_zatrzymany)} pozostawione w spółce "
            f"(kapitał/gotówka spółki; przyszła wypłata = 19% PIT).")


def wiersze_parametry(dane) -> list[dict]:
    """Wszystkie wybrane parametry/opcje analizy — do sekcji audytowej raportu."""
    u = dane.ulgi
    forma = _FORMA_ZUS_PL.get(getattr(dane.forma_zus, "value", dane.forma_zus),
                              str(dane.forma_zus))
    w = [
        ("Roczny przychód", formatuj_pln(dane.przychod)),
        ("Roczne koszty", formatuj_pln(dane.koszty)),
        ("Charakter usług / PKWiU", dane.charakter_uslug or "—"),
        ("Stawka ryczałtu", f"{(dane.stawka_ryczaltu or 0):.1%}"),
        ("Forma ZUS", forma),
        ("Etat poza działalnością (zbieg)", _tak_nie(dane.etat_poza_jdg)),
        ("Były pracodawca", _tak_nie(dane.byly_pracodawca)),
        ("Wspólne rozliczenie z małżonkiem", _tak_nie(dane.wspolne_rozliczenie)),
    ]
    if dane.wspolne_rozliczenie:
        w.append(("• Dochód małżonka (po ZUS)", formatuj_pln(dane.dochod_malzonka)))
    w.append(("Małżonek wnoszony do spółki", _tak_nie(dane.malzonek_do_spolki)))
    if dane.malzonek_do_spolki:
        w.append(("• Przychód małżonka", formatuj_pln(dane.malzonek_przychod)))
        w.append(("• Koszty małżonka", formatuj_pln(dane.malzonek_koszty)))
    w += [
        ("Jednoosobowa sp. z o.o.", _tak_nie(dane.jednoosobowa_spzoo)),
        ("Poziom etatu wspólnika",
         f"{dane.poziom_etatu:.0%}" if dane.poziom_etatu else "brak"),
        ("Art. 176 KSH (świadczenia)",
         ("Tak — " + (formatuj_pln(dane.art_176_kwota) if dane.art_176_kwota
                      else "auto do I progu")) if dane.art_176 else "Nie"),
        ("Wynagrodzenie z powołania", _tak_nie(dane.powolanie_zarzad)),
        ("Najem majątku do spółki (czynsz)", formatuj_pln(dane.najem_do_spolki)),
        ("Wypłata zysku dywidendą", f"{dane.wyplata_dywidendy_pct:.0%}"),
        ("Liczba dzieci (ulga)", str(u.liczba_dzieci)),
        ("Ulga 4+ (PIT-0)", _tak_nie(u.ulga_4plus)),
        ("IP-Box (5%)", _tak_nie(u.ip_box)),
        ("Wpłata IKZE", formatuj_pln(u.ikze_kwota)),
    ]
    return [{"Parametr": p, "Wartość": v} for p, v in w]


def wiersze_rozbicie_malzonkowie(wynik: WynikOptymalizacji) -> list[dict]:
    """Rozbicie dochodu netto na małżonka 1 (klient) i 2 — dla form JDG (R15).
    Sp. z o.o. pomijana (dochód wspólny, jeden podmiot)."""
    wiersze = []
    for f in wynik.formy:
        if f.dochod_netto_klient is None:
            continue
        nazwa = ("⭐ " + f.nazwa) if f.nazwa == wynik.werdykt else f.nazwa
        wiersze.append({
            "Forma": nazwa,
            "Małżonek 1 (klient)": formatuj_pln(f.dochod_netto_klient),
            "Małżonek 2": formatuj_pln(f.dochod_netto_malzonek),
            "Razem": formatuj_pln(f.dochod_netto),
        })
    return wiersze


def wiersze_majatek(projekcja) -> list[dict]:
    """Wiersze tabeli skumulowanego majątku (1/5/10 lat); rekomendacja z gwiazdką."""
    wiersze = []
    for p in projekcja:
        nazwa = ("⭐ " + p.forma) if p.rekomendowana else p.forma
        wiersz = {"Forma": nazwa}
        for rok, wartosc in p.wartosci.items():
            wiersz[f"Po {rok} latach" if rok > 1 else "Po 1 roku"] = \
                formatuj_pln(wartosc)
        wiersze.append(wiersz)
    return wiersze


def tabela_porownawcza(wynik: WynikOptymalizacji) -> list[dict]:
    """Zbuduj wiersze tabeli porównawczej (R7) — gotowe do renderu."""
    wiersze = []
    for f in wynik.formy:
        status = ("✅ Dostępna" if f.dostepnosc == Dostepnosc.DOSTEPNA
                  else f"⛔ NIEDOSTĘPNA — {f.powod_niedostepnosci or ''}".strip())
        wiersze.append({
            "Forma": ("⭐ " + f.nazwa) if f.nazwa == wynik.werdykt else f.nazwa,
            "Podatek": formatuj_pln(f.podatek),
            "Zdrowotna": formatuj_pln(f.zdrowotna),
            "ZUS": formatuj_pln(f.zus_spoleczny),
            "Dochód netto": formatuj_pln(f.dochod_netto),
            "Status": status,
        })
    return wiersze


def sprawdz_braki(przychod, koszty, charakter_uslug) -> list[str]:
    """Walidacja R9: zwróć listę konkretnych braków (ankieta uzupełniająca).
    Pusta lista = dane kompletne, można liczyć."""
    braki: list[str] = []
    if przychod is None or przychod == "":
        braki.append("Podaj roczny przychód (zł).")
    if koszty is None or koszty == "":
        braki.append("Podaj roczne koszty uzyskania przychodu (zł).")
    if not charakter_uslug:
        braki.append("Wskaż charakter usług / kod PKWiU (dla stawki ryczałtu).")
    return braki


def tekst_werdyktu(wynik: WynikOptymalizacji) -> str:
    """Werdykt matematyczny (R7) — jedno zdanie z różnicą kwotową."""
    return (f"Rekomendowana forma: {wynik.werdykt}. "
            f"Przewaga nad drugą opcją: {formatuj_pln(wynik.roznica_do_drugiej)} "
            f"rocznie.")
