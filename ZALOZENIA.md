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

- Domyślnie liczona z **jawnym założeniem wypłaty 100% zysku dywidendą**
  (mnożnik efektywny 0,7371). Inny % wypłaty → inny wynik (pokazywane jawnie).
- **Etat wspólnika** (poziom 1/4…pełny) jako ułamek **płacy minimalnej**:
  pensja jest kosztem spółki (obniża CIT i dywidendę) i dochodem skali u
  pracownika. Składki ZUS pracownika/pracodawcy wg stawek ustawowych
  (wypadkowa przyjęta typowo 1,67%). *Do potwierdzenia stawka wypadkowa.*
- **Jednoosobowa sp. z o.o.** — doliczona zdrowotna + ZUS wspólnika.
- **Struktura 2-osobowa** (np. 99/1) bywa kwestionowana przez ZUS — pokazywane
  jako ryzyko, nie ukrywane.
- **Art. 176 KSH** — sygnalizowany jako opcja w założeniach, bez osobnego
  modelu liczbowego.

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
