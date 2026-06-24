"""Silnik Optymalizacji Podatkowej 2026 — UI Streamlit (Abacus).

Uruchomienie:  streamlit run app.py
Narzędzie bezstanowe: liczy „tu i teraz", nie zapisuje danych klientów.
"""
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# Wczytaj .env z katalogu app.py (niezależnie od bieżącego katalogu roboczego),
# a dla pewności także standardowym przeszukiwaniem od bieżącego katalogu.
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(_ENV_PATH, override=True)
load_dotenv(override=False)

# Streamlit Community Cloud: klucz podawany w Settings → Secrets (st.secrets).
if not os.environ.get("ANTHROPIC_API_KEY"):
    try:
        if "ANTHROPIC_API_KEY" in st.secrets:
            os.environ["ANTHROPIC_API_KEY"] = str(st.secrets["ANTHROPIC_API_KEY"])
    except Exception:
        pass  # brak pliku secrets lokalnie — to normalne

_KLUCZ_OK = bool(os.environ.get("ANTHROPIC_API_KEY"))

from optymalizator import params_2026 as P
from optymalizator import ui_components as UI
from optymalizator.engine import run_optimization
from optymalizator.kpir_import import parsuj_kpir
from optymalizator.majatek import projekcja_majatku
from optymalizator.models import DaneKlienta, FormaZUS, Ulgi
from optymalizator.narracja import generuj_narracje
from optymalizator.oszczednosci import rozbij_przewage
from optymalizator.pdf_export import generuj_pdf
from optymalizator.reinwestycja import oblicz_reinwestycje

st.set_page_config(page_title="Optymalizator Podatkowy 2026 — Abacus",
                   page_icon="📊", layout="wide")

# --- Branding ---------------------------------------------------------------
st.markdown(
    f"""
    <div style="background:{UI.BRAND_GRADIENT};padding:24px 28px;border-radius:12px;
                margin-bottom:8px;">
      <h1 style="color:#fff;margin:0;font-size:28px;">Optymalizator Podatkowy 2026</h1>
      <p style="color:#a9c0e0;margin:4px 0 0;">Biuro Rachunkowe Abacus · porównanie 4 form opodatkowania JDG</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Formularz wejściowy ----------------------------------------------------
with st.sidebar:
    st.header("Dane klienta")

    st.session_state.setdefault("przychod", None)
    st.session_state.setdefault("koszty", None)

    # Import z KPiR (PDF) — wypełnia przychód i koszty do POTWIERDZENIA.
    plik = st.file_uploader("Import z KPiR (PDF)", type=["pdf"])
    if plik is not None and st.session_state.get("_kpir_plik") != plik.name:
        wczytany = parsuj_kpir(plik.getvalue())
        st.session_state["_kpir_plik"] = plik.name
        if wczytany.przychod is not None:
            st.session_state["przychod"] = float(wczytany.przychod)
        if wczytany.koszty is not None:
            st.session_state["koszty"] = float(wczytany.koszty)
        if wczytany.przychod is not None and wczytany.koszty is not None:
            znak = "✅ spójne księgowo" if wczytany.spojnosc else "⚠️ sprawdź ręcznie"
            st.success(f"Wczytano z KPiR ({znak}). Zweryfikuj poniższe pola.")
        for o in wczytany.ostrzezenia:
            st.warning(o)

    przychod = st.number_input("Roczny przychód (zł)", min_value=0.0,
                               step=10_000.0, key="przychod")
    koszty = st.number_input("Roczne koszty (zł)", min_value=0.0,
                             step=5_000.0, key="koszty")

    charakter = st.text_input("Charakter usług / PKWiU", value="")
    stawka_ryczaltu = st.number_input("Stawka ryczałtu", min_value=0.0,
                                      max_value=0.20, value=0.12, step=0.005,
                                      format="%.3f",
                                      help="Sugerowana stawka — wskaż właściwą dla PKWiU.")

    forma_zus = st.selectbox(
        "Forma ZUS",
        options=list(FormaZUS),
        format_func=lambda f: {
            FormaZUS.DUZY: "Duży ZUS",
            FormaZUS.MALY_ZUS_PLUS: "Mały ZUS Plus",
            FormaZUS.PREFERENCYJNY: "Preferencyjny",
            FormaZUS.ULGA_NA_START: "Ulga na start",
            FormaZUS.ETAT_ZBIEG: "Etat (zbieg)",
        }[f],
    )
    dochod_poprzedni = 0.0
    if forma_zus == FormaZUS.MALY_ZUS_PLUS:
        dochod_poprzedni = st.number_input("Dochód z poprzedniego roku (zł)",
                                           min_value=0.0, value=80_000.0,
                                           step=10_000.0)

    st.subheader("Flagi")
    byly_pracodawca = st.checkbox("Były pracodawca (blokuje ryczałt i liniowy)")
    etat_poza_jdg = st.checkbox(
        "Klient ma etat poza działalnością (pensja ≥ minimalnej)",
        help="Zbieg tytułów — z działalności płacona tylko składka zdrowotna, "
             "bez ZUS społecznego.")
    # --- Małżonek: wspólne rozliczenie i/lub wniesienie do spółki ----------
    st.subheader("Małżonek")
    wspolne = st.checkbox("Wspólne rozliczenie z małżonkiem (tylko skala)")
    malzonek_do_spolki = st.checkbox(
        "Małżonek wnoszony do spółki (oboje na JDG → wspólna sp. z o.o.)")

    dochod_malzonka = 0.0
    etat_malzonek = False
    malzonek_przychod = 0.0
    malzonek_koszty = 0.0

    # Dane małżonka potrzebne dla OBU opcji — niezależne od wspólnego rozliczenia.
    if wspolne or malzonek_do_spolki:
        st.session_state.setdefault("dochod_malzonka", 0.0)
        st.session_state.setdefault("_malzonek_przychod", 0.0)
        st.session_state.setdefault("_malzonek_koszty", 0.0)
        plik_m = st.file_uploader("Import KPiR małżonka (PDF, opcjonalnie)",
                                  type=["pdf"], key="kpir_malzonek")
        if plik_m is not None and \
                st.session_state.get("_kpir_malzonek_plik") != plik_m.name:
            wm = parsuj_kpir(plik_m.getvalue())
            st.session_state["_kpir_malzonek_plik"] = plik_m.name
            dochod_m = wm.dochod
            if dochod_m is None and None not in (wm.przychod, wm.koszty):
                dochod_m = wm.przychod - wm.koszty
            if dochod_m is not None:
                st.session_state["dochod_malzonka"] = float(dochod_m)
            if wm.przychod is not None:
                st.session_state["_malzonek_przychod"] = float(wm.przychod)
            if wm.koszty is not None:
                st.session_state["_malzonek_koszty"] = float(wm.koszty)
            st.success("Wczytano KPiR małżonka. Zweryfikuj pola poniżej.")
            for o in wm.ostrzezenia:
                st.warning(o)
        etat_malzonek = st.checkbox(
            "Małżonek ma etat poza działalnością (≥ min.)",
            help="Zbieg tytułów — małżonek nie płaci ZUS społecznego z działalności.")

    if malzonek_do_spolki:
        malzonek_przychod = st.number_input(
            "Przychód małżonka — rocznie (zł)", min_value=0.0, step=10_000.0,
            key="_malzonek_przychod")
        malzonek_koszty = st.number_input(
            "Koszty małżonka — rocznie (zł)", min_value=0.0, step=5_000.0,
            key="_malzonek_koszty")

    if wspolne:
        dochod_malzonka = st.number_input(
            "Dochód małżonka — do wspólnego rozliczenia (zł)", min_value=0.0,
            step=10_000.0, key="dochod_malzonka")
        if etat_malzonek:
            zus_malzonka = 0.0
            st.caption("Zbieg: ZUS społeczny małżonka z działalności = 0.")
        else:
            zus_malzonka = st.number_input(
                "ZUS społeczny małżonka — rocznie (zł)", min_value=0.0,
                value=0.0, step=1_000.0,
                help="Pomniejsza dochód małżonka do wspólnego rozliczenia. "
                     "Zostaw 0, jeśli małżonek nie prowadzi działalności.")
        dochod_malzonka = max(0.0, dochod_malzonka - zus_malzonka)

    st.subheader("Pozostałe")
    jednoosobowa = st.checkbox("Jednoosobowa sp. z o.o.")
    st.caption("Sp. z o.o. liczona przez zoptymalizowany miks wypłaty "
               "(art. 176 → powołanie → dywidenda), nie 100% dywidendy.")
    art176 = st.checkbox("Art. 176 KSH (świadczenia wspólnika)", value=True,
                         help="Skala PIT, bez ZUS i bez zdrowotnej — najtańszy "
                              "kanał, domyślnie do I progu (120 000 zł).")
    art176_kwota = None
    if art176:
        _kw = st.number_input(
            "Kwota świadczeń art. 176 — rocznie (0 = auto do I progu)",
            min_value=0.0, value=0.0, step=10_000.0)
        art176_kwota = _kw if _kw > 0 else None
    powolanie_zarzad = st.checkbox(
        "Wynagrodzenie z powołania zarządu", value=True,
        help="Skala PIT + 9% zdrowotnej, bez ZUS — wypełnia resztę I progu.")

    st.subheader("Ulgi i preferencje")
    liczba_dzieci = st.number_input("Liczba dzieci", min_value=0, value=0, step=1)
    ulga_4plus = st.checkbox("Ulga 4+ (PIT-0 dla rodzin)")
    ip_box = st.checkbox("IP-Box (5% na liniowym)")
    ikze = st.number_input("Wpłata na IKZE (zł)", min_value=0.0, value=0.0,
                           step=1_000.0)

    # --- Pokrętła doradcy (kategoria C): przeliczają wynik na żywo ----------
    st.subheader("Sp. z o.o. — struktura i reinwestycja")
    poziom_etatu = st.selectbox(
        "Poziom etatu wspólnika",
        options=[0.0, 0.25, 0.5, 0.75, 1.0],
        index=2,
        format_func=lambda v: {0.0: "Bez etatu (czysta dywidenda)", 0.25: "1/4",
                               0.5: "1/2 (rekomendowane)", 0.75: "3/4",
                               1.0: "Pełny"}[v],
    )
    proporcja = st.slider("Część oszczędności pracująca w III filarze",
                          min_value=0.0, max_value=1.0, value=0.5, step=0.05)
    stopy_pct = st.slider("Stopy zwrotu projekcji (% realnie)",
                          min_value=2, max_value=8, value=(4, 6))
    stopy_zwrotu = tuple(s / 100 for s in stopy_pct)

    st.subheader("Dodatkowe informacje")
    dodatkowe_info = st.text_area(
        "Specyfika, wymagania i oczekiwania klienta",
        placeholder="np. plany sukcesji, sezonowość, planowane inwestycje, "
                    "preferencja prostoty rozliczeń, kredyt hipoteczny, "
                    "zatrudnianie pracowników...",
        help="Trafia do warstwy AI (uzasadnienie + matryca ryzyk). "
             "Nie wpływa na liczby.")

    licz = st.button("Policz formy", type="primary", width="stretch")

    st.divider()
    if _KLUCZ_OK:
        st.caption("🔑 Klucz API: wykryty — narracja AI aktywna.")
    else:
        st.caption(f"🔑 Klucz API: BRAK. Szukano w: {_ENV_PATH} "
                   f"(istnieje: {_ENV_PATH.exists()}).")

# --- Walidacja R9 + obliczenia ----------------------------------------------
braki = UI.sprawdz_braki(przychod, koszty, charakter)
if braki:
    st.warning("Uzupełnij dane, zanim policzymy:")
    for b in braki:
        st.markdown(f"- {b}")
    st.stop()

dane = DaneKlienta(
    przychod=przychod,
    koszty=koszty,
    stawka_ryczaltu=stawka_ryczaltu,
    charakter_uslug=charakter,
    forma_zus=forma_zus,
    dochod_poprzedni_rok=dochod_poprzedni,
    byly_pracodawca=byly_pracodawca,
    wspolne_rozliczenie=wspolne,
    dochod_malzonka=dochod_malzonka,
    jednoosobowa_spzoo=jednoosobowa,
    art_176=art176,
    art_176_kwota=art176_kwota,
    powolanie_zarzad=powolanie_zarzad,
    etat_poza_jdg=etat_poza_jdg,
    etat_poza_jdg_malzonek=etat_malzonek,
    malzonek_do_spolki=malzonek_do_spolki,
    malzonek_przychod=malzonek_przychod,
    malzonek_koszty=malzonek_koszty,
    poziom_etatu=poziom_etatu,
    ulgi=Ulgi(liczba_dzieci=int(liczba_dzieci), ulga_4plus=ulga_4plus,
              ip_box=ip_box, ikze_kwota=ikze),
)

try:
    wynik = run_optimization(dane)
except Exception as e:  # awaria rdzenia nie może zostawić pustego ekranu
    st.error(f"Nie udało się policzyć form: {e}")
    st.stop()

# --- Werdykt ----------------------------------------------------------------
st.success(UI.tekst_werdyktu(wynik))

if wspolne and wynik.werdykt in ("Liniowy", "Ryczałt"):
    st.warning("Uwaga: wspólne rozliczenie z małżonkiem przysługuje wyłącznie "
               "przy skali podatkowej. Przy rekomendowanym podatku liniowym lub "
               "ryczałcie nie można rozliczyć się wspólnie — opcja wpływa tu "
               "tylko na wariant Skala.")

# --- Tabela porównawcza -----------------------------------------------------
st.subheader("Tabela porównawcza")
st.dataframe(UI.tabela_porownawcza(wynik), width="stretch",
             hide_index=True)

# Założenia sp. z o.o. (jawne — R6)
for f in wynik.formy:
    if f.zalozenia:
        st.caption(f"ℹ️ {f.nazwa}: {f.zalozenia}")

# --- Rozbicie na małżonków (R15) --------------------------------------------
if malzonek_do_spolki:
    rozb_malz = UI.wiersze_rozbicie_malzonkowie(wynik)
    if rozb_malz:
        st.subheader("Rozbicie dochodu: Małżonek 1 i Małżonek 2 (formy JDG)")
        st.dataframe(rozb_malz, width="stretch", hide_index=True)
        st.caption("Dwie OSOBNE działalności liczone niezależnie, sumowane po "
                   "opodatkowaniu. Sp. z o.o. pominięta — to jeden podmiot "
                   "(dochód wspólny).")

# --- Skumulowany majątek po 1 / 5 / 10 latach -------------------------------
st.subheader("Skumulowany dochód netto w czasie")
majatek = projekcja_majatku(wynik, lata=(1, 5, 10), stopa=0.0)
st.dataframe(UI.wiersze_majatek(majatek), width="stretch",
             hide_index=True)
st.caption("Suma dochodu netto przy stałej prognozie 2026. Kapitalizację "
           "odłożonych oszczędności pokazuje sekcja reinwestycji poniżej.")

# --- Warstwa narracyjna (Unit 4) — graceful degradation ---------------------
st.subheader("Kluczowe uzasadnienie i matryca ryzyk")


@st.cache_data(show_spinner="Generuję uzasadnienie…")
def _narracja_cached(_wynik, sygnatura, kontekst):
    # `sygnatura` i `kontekst` (hashowalne) wymuszają cache po liczbach i treści;
    # `_wynik` pomijany w hashowaniu. Ruch suwakiem nie wywołuje API.
    return generuj_narracje(_wynik, kontekst=kontekst)


_sygn = tuple((f.nazwa, f.podatek, f.dochod_netto) for f in wynik.formy)
narracja = _narracja_cached(wynik, _sygn, dodatkowe_info)
if narracja.dostepna:
    for punkt in narracja.uzasadnienie:
        st.markdown(f"- {punkt}")
    if narracja.matryca_ryzyk:
        st.markdown("**Matryca ryzyk:**")
        st.dataframe(narracja.matryca_ryzyk, width="stretch",
                     hide_index=True)
else:
    st.info(f"Warstwa narracyjna (AI) niedostępna: {narracja.powod} "
            "Liczby powyżej są kompletne i niezależne od niej.")

# --- Oszczędności sp. z o.o. + reinwestycja (Unit 7 + 8) --------------------
rozbicie = None
reinwestycja = None
if wynik.werdykt.lower().startswith("sp. z o.o"):
    from optymalizator.models import Dostepnosc
    spzoo = next(f for f in wynik.formy if "z o.o" in f.nazwa.lower())
    jdg_dostepne = [f for f in wynik.formy if "z o.o" not in f.nazwa.lower()
                    and f.dostepnosc == Dostepnosc.DOSTEPNA]
    if jdg_dostepne:
        jdg = max(jdg_dostepne, key=lambda f: f.dochod_netto)
        rozbicie = rozbij_przewage(spzoo, jdg)

        st.subheader("Oszczędności sp. z o.o. (waterfall brutto)")
        st.caption("Pełny ZUS/zdrowotna z JDG znika (+), składki od etatu "
                   "w spółce dochodzą (−).")
        st.dataframe(UI.wiersze_waterfall(rozbicie), width="stretch",
                     hide_index=True)

        if rozbicie.netto > 0:
            reinwestycja = oblicz_reinwestycje(
                rozbicie.netto,
                marginalna_stawka=spzoo.marginalna_stawka_etatu or 0.12,
                proporcja=proporcja, stopy_zwrotu=stopy_zwrotu,
                para=malzonek_do_spolki, etat=poziom_etatu > 0,
                pensja_etat=spzoo.pensja_etat)

            st.subheader("Reinwestycja oszczędności")
            st.write(f"Podział: **{UI.formatuj_pln(reinwestycja.czesc_pracujaca)}** "
                     f"pracujące w III filarze, "
                     f"**{UI.formatuj_pln(reinwestycja.czesc_gotowka)}** w gotówce.")
            st.dataframe(UI.wiersze_alokacje(reinwestycja),
                         width="stretch", hide_index=True)
            for p in reinwestycja.projekcje:
                st.markdown(f"- **{p.stopa:.0%}** przez {p.horyzont} lat → "
                            f"{UI.formatuj_pln(p.wartosc_koncowa)} "
                            f"(zysk {UI.formatuj_pln(p.zysk)})")
            if reinwestycja.ppk:
                st.caption(f"PPK (etat): pracownik "
                           f"{UI.formatuj_pln(reinwestycja.ppk['wplata_pracownik'])}, "
                           f"pracodawca "
                           f"{UI.formatuj_pln(reinwestycja.ppk['wplata_pracodawca'])} "
                           f"rocznie + dopłaty państwa.")
            st.info(reinwestycja.disclaimer)

# --- Eksport PDF (Unit 6) ---------------------------------------------------
st.subheader("Raport dla klienta")
try:
    pdf_bytes = generuj_pdf(wynik, narracja, rozbicie=rozbicie,
                            reinwestycja=reinwestycja, majatek=majatek, dane=dane)
    st.download_button("⬇️ Pobierz brandowany PDF", data=pdf_bytes,
                       file_name="optymalizacja_podatkowa_2026.pdf",
                       mime="application/pdf", type="primary")
except Exception as e:
    st.error(f"Nie udało się wygenerować PDF: {e}. Liczby powyżej są kompletne.")

st.caption(f"Minimum składki zdrowotnej 2026: "
           f"{UI.formatuj_pln(P.ZDROWOTNA_MIN_ROCZNA)} · narzędzie bezstanowe, "
           f"dane nie są zapisywane.")
