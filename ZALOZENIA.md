# Założenia i uproszczenia modelu

Dokument zbiera **świadome uproszczenia** silnika i miejsca **do potwierdzenia
przez księgowego/doradcę podatkowego** przed pilotażem. Narzędzie jest
deterministyczne i przetestowane (82 testy), ale poprawność *reguł* podatkowych
2026 wymaga walidacji merytorycznej na realnych przypadkach.

> Narzędzie ma charakter doradczy i prognostyczny na rok 2026. Nie stanowi
> wiążącej opinii podatkowej.

## Składki ZUS

- **Duży ZUS** liczony jako stała roczna (12 × stawka miesięczna), podstawa
  emerytalno-rentowa poniżej rocznego limitu 282 600 zł — składka nie rośnie
  z dochodem. *Do potwierdzenia: stawki 2026.*
- **Mały ZUS Plus** — uproszczenie: podstawa = 50% średniego miesięcznego
  dochodu z roku poprzedniego, ograniczona widełkami, składka liczona
  **efektywną stawką z Dużego ZUS** (zawiera FP, którego Mały ZUS Plus zwykle
  nie obejmuje). Wartość traktować jako przybliżenie. *Do potwierdzenia.*
- **Ulga na start / Etat-zbieg** → ZUS społeczny = 0 (uproszczenie; zbieg z
  etatem zależy od podstawy z etatu — nie modelowane).

## Składka zdrowotna

- Minimum roczne **5 072,90 zł** = 1×314,96 (styczeń) + 11×432,54 — zaszyte
  i pokryte testem (nie 12×432,54).
- Skala 9%, liniowy 4,9% (limit odliczenia 14 100 zł), ryczałt wg progów.

## Podatek dochodowy

- **Danina solidarnościowa** 4% od nadwyżki dochodu ponad 1 mln zł — naliczana
  dla skali i liniowego, podstawa = dochód po ZUS. **Dla wspólnego rozliczenia
  liczona od dochodu podatnika, nie modeluje osobnej daniny małżonka.**
- **Ulga prorodzinna** — kwoty progowe, nadwyżka zwracana do wysokości składek
  (uproszczony limit zwrotu = ZUS + zdrowotna).
- **PIT-0 dla rodzin 4+** — zwolnienie do 85 528 zł stosowane na skali i
  liniowym; **nie stosowane w ryczałcie** (uproszczenie).
- **IKZE** — odliczane na skali i liniowym do limitu JDG 16 956 zł;
  **nie stosowane w ryczałcie**; brak twardego capowania odliczenia wysokością
  dochodu skali (do rozważenia).

## Sp. z o.o. (pakiet „spółka + etat")

- **Wypłata zoptymalizowana (nie 100% dywidendy).** Silnik wypełnia I próg skali
  (12%) najtańszymi kanałami, bo powyżej progu dywidenda (26,3%) bije skalę 32%:
  1) **najem prywatnego majątku do spółki** — czynsz to koszt spółki, u
  właściciela ryczałt od najmu: 8,5% do 100 000 zł, 12,5% powyżej, bez ZUS i
  zdrowotnej (najtańszy kanał na pierwszych 100 tys.); 2) **art. 176 KSH** —
  świadczenia wspólnika: skala PIT, bez ZUS i zdrowotnej (domyślnie do 120 000 zł);
  3) **wynagrodzenie z powołania zarządu** — skala PIT + 9% zdrowotnej, bez ZUS
  (wypełnia resztę I progu); 4) **dywidenda** — reszta (CIT 9% + 19%).
  *Warunki: czynsz najmu musi odpowiadać realnemu majątkowi i stawce rynkowej;
  świadczenia art. 176 — realne, w umowie spółki, wycenione rynkowo; powołanie —
  uchwała. Wszystko do potwierdzenia przez doradcę. Próg najmu 100 tys. liczony
  per właściciel (przy parze do rozbicia osobno).*
- **Etat wspólnika** (poziom 1/4…pełny) jako ułamek **płacy minimalnej**:
  pensja jest kosztem spółki (obniża CIT i dywidendę) i dochodem skali u
  pracownika. Składki ZUS pracownika/pracodawcy wg stawek ustawowych
  (wypadkowa przyjęta typowo 1,67%). *Do potwierdzenia stawka wypadkowa.*
- **Jednoosobowa sp. z o.o.** — doliczona zdrowotna + ZUS wspólnika.
- **Struktura 2-osobowa** (np. 99/1) bywa kwestionowana przez ZUS — pokazywane
  jako ryzyko, nie ukrywane.
- **Małżonek wnoszony do spółki (R15)** — porównanie na poziomie pary:
  - **Formy JDG** = klient na danej formie + małżonek na własnej najlepszej JDG
    (dwie OSOBNE działalności, sumowane po opodatkowaniu). Kolumny tabeli
    (podatek/zdrowotna/ZUS) też są couple-level. ZUS małżonka liczony wg jego
    **wskazanej formy ZUS** (Duży / Mały ZUS Plus / itd.) — co pokazuje, że jego
    składki z JDG **znikają** po wniesieniu do spółki.
  - **Sp. z o.o.** = jeden podmiot z dwoma wspólnikami: każdy ma **własny art. 176
    (do I progu)**, **własny etat** i **własną progresję skali** (pełne 2-osobowe
    optimum). Wymaga wgranego KPiR / danych małżonka.
- **Art. 176 KSH** — modelowany liczbowo: świadczenia wspólnika to koszt spółki
  (obniżają CIT i dywidendę), u wspólnika opodatkowane skalą, **bez ZUS i bez
  zdrowotnej**. Kwota: auto do I progu skali (120 000 zł) lub podana przez
  doradcę. *Warunki prawne (zapis w umowie spółki, realność i wycena świadczeń)
  do potwierdzenia — US/ZUS mogą kwestionować pozorne świadczenia.*

## Zbieg tytułów (etat poza działalnością)

- Flaga „etat poza JDG" (klient i osobno małżonek): pensja ≥ minimalnej z innego
  tytułu → z działalności płacona **tylko składka zdrowotna, bez ZUS
  społecznego** (`zus_spoleczny = 0` dla skali/liniowego/ryczałtu tej osoby).
  *Założenie: pensja z etatu ≥ minimalnego wynagrodzenia (warunek zbiegu).*

## Reinwestycja (III filar)

- Projekcja jest **ilustracją**, nie doradztwem inwestycyjnym (disclaimer
  obowiązkowy). Wzrost liczony jako lokata jednorazowa (1+r)^N — bez modelu
  corocznych wpłat.
- Limity 2026: IKE 28 260, IKZE etat 11 304, IKZE JDG 16 956 (×2 dla pary).
  Stopa zwrotu ograniczona do 2–8% realnie.
- **PPK** liczone informacyjnie; nie wpięte w pełny bilans kosztów spółki.

## Import KPiR

- Tylko **PDF tekstowe** (eksport z programu). Skany wymagają OCR — poza scope.
- Parser czyta **etykietowane podsumowanie roczne** (nie siatkę miesięczną),
  dopasowanie tolerancyjne na różne układy + kontrola spójności
  (przychód − koszty = dochód). **Zweryfikowany na jednym układzie**
  (Rachmistrz GT/InsERT) — inne programy wymagają testu na próbce.
- Wartości zawsze **do potwierdzenia przez doradcę** przed liczeniem.

## Poza zakresem MVP

- Estoński CIT i ewentualna piąta forma.
- Automatyczne pobieranie stawki ryczałtu z PKWiU.
- Rozliczenia wsteczne / korekty.
- Persystencja danych (narzędzie bezstanowe).
