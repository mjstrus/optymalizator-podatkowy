"""Import KPiR z PDF — odczyt podsumowania księgi przychodów i rozchodów.

Strategia: czytamy etykietowany blok podsumowania (przychód, koszty, dochód…),
a NIE rozbicie miesięczne — siatka miesięczna bywa nieczytelna przy ekstrakcji
tekstu z różnych programów księgowych. Dopasowanie jest tolerancyjne (odporne na
zniekształcenia fontów typu „Przychód"→„Przvch?d") i uzupełnione kontrolą
spójności księgowej (przychód − koszty = dochód).

Zasada: parser PROPONUJE liczby, doradca je POTWIERDZA w UI (filozofia R9).
Obsługuje tylko PDF tekstowe (eksport z programu) — skany wymagałyby OCR.
"""
from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass, field

try:
    import pdfplumber
except Exception:  # pragma: no cover - zależność opcjonalna przy imporcie
    pdfplumber = None

# Kwota: separator tysięcy = spacja; część dziesiętna po ',' lub '.'.
_KWOTA = re.compile(r"(\d[\d ]*[.,]\d{2})")


def kwota_pl(s: str) -> float:
    """Sparsuj polską kwotę do float, tolerując mieszane separatory."""
    s = s.replace("\xa0", " ").replace(" ", "")
    if "," in s:                     # przecinek = część dziesiętna
        s = s.replace(".", "").replace(",", ".")
    return float(s)


@dataclass
class ImportKPiR:
    przychod: float | None = None
    koszty: float | None = None          # z uwzgl. różnicy remanentowej (preferowane)
    dochod: float | None = None
    pola: dict[str, float] = field(default_factory=dict)
    spojnosc: bool = False               # przychód − koszty == dochód
    ostrzezenia: list[str] = field(default_factory=list)


def _normalizuj(txt: str) -> str:
    txt = unicodedata.normalize("NFKD", txt)
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return txt.lower().replace("\xa0", " ")


def _pary_kwot(n: str) -> list[tuple[str, float]]:
    """Lista (kontekst_przed_kwotą, wartość) dla wszystkich kwot w tekście."""
    pary = []
    for m in _KWOTA.finditer(n):
        ctx = n[max(0, m.start() - 30):m.start()].strip()
        try:
            pary.append((ctx, kwota_pl(m.group(1))))
        except ValueError:
            continue
    return pary


def _znajdz(pary, *, musi, bez=()) -> float | None:
    """Pierwsza kwota, której kontekst pasuje do wszystkich wzorców `musi`
    i nie zawiera żadnego z fragmentów `bez`."""
    for ctx, val in pary:
        if all(re.search(p, ctx) for p in musi) and not any(b in ctx for b in bez):
            return val
    return None


def _wczytaj_tekst(zrodlo) -> str:
    if pdfplumber is None:
        raise RuntimeError("Brak biblioteki pdfplumber.")
    if isinstance(zrodlo, (bytes, bytearray)):
        strumien = io.BytesIO(zrodlo)
    elif hasattr(zrodlo, "read"):
        strumien = zrodlo
    else:
        strumien = zrodlo  # ścieżka
    czesci = []
    with pdfplumber.open(strumien) as pdf:
        for p in pdf.pages:
            czesci.append(p.extract_text() or "")
    return "\n".join(czesci)


def parsuj_kpir(zrodlo) -> ImportKPiR:
    """Sparsuj PDF KPiR (ścieżka / bytes / file-like) → ImportKPiR.
    Nie rzuca wyjątków na złym wejściu — zwraca wynik z ostrzeżeniami."""
    wynik = ImportKPiR()
    try:
        txt = _wczytaj_tekst(zrodlo)
    except Exception as e:
        wynik.ostrzezenia.append(f"Nie udało się odczytać PDF: {e}")
        return wynik

    if not txt.strip():
        wynik.ostrzezenia.append(
            "PDF nie zawiera tekstu — prawdopodobnie skan (wymaga OCR). "
            "Wprowadź dane ręcznie.")
        return wynik

    n = _normalizuj(txt)
    pary = _pary_kwot(n)

    # Pełny odczyt podsumowania (etykiety tolerancyjne).
    pola: dict[str, float] = {}

    def ustaw(klucz, *, musi, bez=()):
        v = _znajdz(pary, musi=musi, bez=bez)
        if v is not None:
            pola[klucz] = v
        return v

    przychod = ustaw("przychod", musi=[r"prz.{0,2}ch"],
                     bez=["koszt", "doch", "uz."])
    ustaw("zakupy_towarow", musi=[r"zakup"])
    ustaw("wydatki", musi=[r"wydatki"])
    ustaw("koszty_uz_przychodu", musi=[r"uz\.przych"])
    koszty_reman = ustaw("koszty_z_remanentem",
                         musi=[r"koszt", r"uwzgl", r"reman"])
    ustaw("roznica_remanentowa", musi=[r"nica.*reman|nicareman"])
    dochod_reman = ustaw("dochod_z_remanentem", musi=[r"doch", r"uwzgl"])
    ustaw("dochod_podstawowy", musi=[r"doch"], bez=["uwzgl"])

    wynik.pola = pola

    # Wartości dla optymalizatora (preferuj wersje z różnicą remanentową).
    wynik.przychod = przychod
    wynik.koszty = koszty_reman if koszty_reman is not None else \
        pola.get("koszty_uz_przychodu")
    wynik.dochod = dochod_reman if dochod_reman is not None else \
        pola.get("dochod_podstawowy")

    # Kontrola spójności księgowej: przychód − koszty = dochód.
    if None not in (wynik.przychod, wynik.koszty, wynik.dochod):
        wynik.spojnosc = abs(wynik.przychod - wynik.koszty - wynik.dochod) < 0.5
        if not wynik.spojnosc:
            wynik.ostrzezenia.append(
                "Odczytane liczby nie domykają się księgowo "
                "(przychód − koszty ≠ dochód) — zweryfikuj ręcznie.")

    if wynik.przychod is None:
        wynik.ostrzezenia.append("Nie znaleziono przychodu — wprowadź ręcznie.")
    if wynik.koszty is None:
        wynik.ostrzezenia.append("Nie znaleziono kosztów — wprowadź ręcznie.")

    return wynik
