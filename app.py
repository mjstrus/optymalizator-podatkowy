"""Silnik Optymalizacji Podatkowej 2026 — UI Streamlit (Abacus).

Uruchomienie:  streamlit run app.py
Narzędzie bezstanowe: liczy „tu i teraz", nie zapisuje danych klientów.
"""
import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # wczytaj ANTHROPIC_API_KEY z pliku .env (jeśli istnieje)

from optymalizator.engine import run_optimization
from optymalizator.models import DaneKlienta, FormaZUS, Ulgi
from optymalizator import ui_components as UI
from optymalizator import params_2026 as P
from optymalizator.narracja import generuj_narracje
from optymalizator.pdf_export import generuj_pdf
from optymalizator.kpir_import import parsuj_kpir

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

    st.session_state.setdefault("przychod", 300_000.0)
    st.session_state.setdefault("koszty", 50_000.0)

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

    charakter = st.text_input("Charakter usług / PKWiU", value="usługi IT")
    stawka_ryczaltu = st.number_input("Stawka ryczałtu", min_value=0.0,
                                      max_value=0.20, value=0.12, step=0.005,
                                      format="%.3f")

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
    wspolne = st.checkbox("Wspólne rozliczenie z małżonkiem")
    dochod_malzonka = 0.0
    if wspolne:
        dochod_malzonka = st.number_input("Dochód małżonka (zł)", min_value=0.0,
                                          value=0.0, step=10_000.0)
    jednoosobowa = st.checkbox("Jednoosobowa sp. z o.o.")
    art176 = st.checkbox("Ścieżka art. 176 KSH")

    st.subheader("Ulgi i preferencje")
    liczba_dzieci = st.number_input("Liczba dzieci", min_value=0, value=0, step=1)
    ulga_4plus = st.checkbox("Ulga 4+ (PIT-0 dla rodzin)")
    ip_box = st.checkbox("IP-Box (5% na liniowym)")
    ikze = st.number_input("Wpłata na IKZE (zł)", min_value=0.0, value=0.0,
                           step=1_000.0)

    licz = st.button("Policz formy", type="primary", use_container_width=True)

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
    ulgi=Ulgi(liczba_dzieci=int(liczba_dzieci), ulga_4plus=ulga_4plus,
              ip_box=ip_box, ikze_kwota=ikze),
)

wynik = run_optimization(dane)

# --- Werdykt ----------------------------------------------------------------
st.success(UI.tekst_werdyktu(wynik))

# --- Tabela porównawcza -----------------------------------------------------
st.subheader("Tabela porównawcza")
st.dataframe(UI.tabela_porownawcza(wynik), use_container_width=True,
             hide_index=True)

# Założenia sp. z o.o. (jawne — R6)
for f in wynik.formy:
    if f.zalozenia:
        st.caption(f"ℹ️ {f.nazwa}: {f.zalozenia}")

# --- Warstwa narracyjna (Unit 4) — graceful degradation ---------------------
st.subheader("Kluczowe uzasadnienie i matryca ryzyk")
narracja = generuj_narracje(wynik)
if narracja.dostepna:
    for punkt in narracja.uzasadnienie:
        st.markdown(f"- {punkt}")
    if narracja.matryca_ryzyk:
        st.markdown("**Matryca ryzyk:**")
        st.dataframe(narracja.matryca_ryzyk, use_container_width=True,
                     hide_index=True)
else:
    st.info(f"Warstwa narracyjna (AI) niedostępna: {narracja.powod} "
            "Liczby powyżej są kompletne i niezależne od niej.")

# --- Eksport PDF (Unit 6) ---------------------------------------------------
st.subheader("Raport dla klienta")
pdf_bytes = generuj_pdf(wynik, narracja)
st.download_button("⬇️ Pobierz brandowany PDF", data=pdf_bytes,
                   file_name="optymalizacja_podatkowa_2026.pdf",
                   mime="application/pdf", type="primary")

st.caption(f"Minimum składki zdrowotnej 2026: "
           f"{UI.formatuj_pln(P.ZDROWOTNA_MIN_ROCZNA)} · narzędzie bezstanowe, "
           f"dane nie są zapisywane.")
