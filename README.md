# Optymalizator Podatkowy 2026 — Abacus

Narzędzie doradcze dla biura rachunkowego Abacus. Dla danej jednoosobowej działalności
(JDG) porównuje **cztery formy opodatkowania na rok 2026** — skala, podatek liniowy,
ryczałt i sp. z o.o. — wskazuje najkorzystniejszą i generuje brandowany PDF na sesję
doradczą z klientem.

## Zasada architektoniczna

**Cała matematyka jest deterministyczna (Python), a model językowy generuje wyłącznie
warstwę narracyjną** (uzasadnienie + matryca ryzyk) na podstawie gotowych liczb. Dzięki
temu poprawność rekomendacji nie zależy od modelu — silnik jest pokryty testami i działa
niezależnie od UI oraz LLM.

Narzędzie jest **bezstanowe**: liczy „tu i teraz" i nie zapisuje danych klientów
(brak bazy/persystencji → brak ryzyk RODO).

## Funkcje

- Deterministyczny silnik 4 form wg parametrów 2026 (jedno źródło prawdy: `params_2026.py`).
- Negative screening: były pracodawca blokuje ryczałt i liniowy; przychód > 2 mln EUR blokuje ryczałt.
- Wspólne rozliczenie małżonków, ulgi (prorodzinna, PIT-0 dla rodzin 4+, IP-Box, IKZE).
- Poprawny rok składkowy zdrowotny (minimum roczne 5 072,90 zł), formy ZUS (Duży / Mały ZUS Plus / Preferencyjny / Ulga na start / Etat-zbieg).
- Sp. z o.o. z jawnym założeniem wypłaty zysku oraz wyjątkiem jednoosobowej spółki.
- UI Streamlit w brandingu Abacus + eksport brandowanego PDF.
- Warstwa narracyjna Claude API z graceful degradation (brak klucza/awaria → liczby zostają).

## Wymagania

- Python 3.12+
- Windows (PDF używa fontu Arial z `C:\Windows\Fonts`; na innych systemach następuje fallback)

## Instalacja

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (PowerShell/CMD)
pip install -r requirements.txt
```

## Uruchomienie

```bash
streamlit run app.py
```

Aby włączyć warstwę narracyjną (AI), ustaw klucz API:

```bash
set ANTHROPIC_API_KEY=sk-ant-...   # Windows
```

Bez klucza narzędzie nadal działa — pokazuje tabelę, werdykt i PDF, a sekcje narracyjne
oznacza jako niedostępne.

## Testy

```bash
pytest -q
```

## Struktura

```
app.py                      # UI Streamlit
optymalizator/
  params_2026.py            # stałe podatkowe/składkowe 2026 (jedno miejsce zmiany)
  models.py                 # modele wejścia/wyjścia (dataclasses)
  engine.py                 # run_optimization — deterministyczny rdzeń
  narracja.py               # warstwa narracyjna Claude API
  ui_components.py          # czyste funkcje prezentacji (testowalne)
  pdf_export.py             # generator brandowanego PDF (fpdf2)
tests/                      # 44 testy (test-first)
```

## Zastrzeżenie

Wynik ma charakter doradczy i prognostyczny na rok 2026. Wynik dla sp. z o.o. zależy od
przyjętego założenia wypłaty zysku. Dokument nie stanowi wiążącej opinii podatkowej.
