"""Generator brandowanego PDF (Abacus) — deliverable sesji doradczej (R11).

Sekcje budowane są jako struktura (`zbuduj_sekcje`) niezależna od fpdf2,
co czyni zawartość testowalną bez parsowania binarnego PDF.
"""
from __future__ import annotations

import os
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from . import ui_components as UI
from .models import Dostepnosc, WynikOptymalizacji
from .narracja import Narracja

# Branding (RGB)
NAVY = (13, 27, 42)        # #0d1b2a
NAVY_2 = (27, 45, 69)      # #1b2d45
SZARY = (90, 90, 90)

# Font Unicode dołączony do repo (DejaVuSans) — działa na każdym systemie
# (Windows/Linux/Streamlit Cloud) i ma pełen zestaw polskich znaków.
_FONTS = Path(__file__).resolve().parent.parent / "fonts"
DEJAVU = str(_FONTS / "DejaVuSans.ttf")
DEJAVU_BOLD = str(_FONTS / "DejaVuSans-Bold.ttf")

ZASTRZEZENIE = (
    "Dokument ma charakter doradczy i prognostyczny na rok 2026. Wynik dla sp. z o.o. "
    "zależy od przyjętego założenia wypłaty zysku. Nie stanowi wiążącej opinii "
    "podatkowej. Biuro Rachunkowe Abacus."
)


def zbuduj_sekcje(wynik: WynikOptymalizacji,
                  narracja: Narracja | None,
                  rozbicie=None, reinwestycja=None, majatek=None,
                  dane=None) -> list[dict]:
    """Zwróć uporządkowaną listę sekcji raportu (tytuł + treść)."""
    sekcje: list[dict] = []

    sekcje.append({"tytul": "Werdykt matematyczny", "typ": "tekst",
                   "tresc": UI.tekst_werdyktu(wynik)})

    # Parametry analizy — wszystkie wybrane opcje (audytowalność raportu).
    if dane is not None:
        sekcje.append({
            "tytul": "Parametry analizy (wybrane opcje)",
            "typ": "tabela",
            "tresc": UI.wiersze_parametry(dane),
            "kolumny": ["Parametr", "Wartość"],
            "szer": [110, 74],
        })

    sekcje.append({"tytul": "Tabela porównawcza form",
                   "typ": "tabela",
                   "tresc": _wiersze_tabeli(wynik)})

    # Skumulowany majątek po 1/5/10 latach.
    if majatek:
        wiersze_m = UI.wiersze_majatek(majatek)
        sekcje.append({
            "tytul": "Skumulowany dochód netto (1 / 5 / 10 lat)",
            "typ": "tabela",
            "tresc": wiersze_m,
            "kolumny": list(wiersze_m[0].keys()) if wiersze_m else [],
            "szer": None,
        })

    # Jawne założenia (np. sp. z o.o.)
    zalozenia = [f"{f.nazwa}: {f.zalozenia}" for f in wynik.formy if f.zalozenia]
    if zalozenia:
        sekcje.append({"tytul": "Założenia", "typ": "lista", "tresc": zalozenia})

    if narracja and narracja.dostepna:
        sekcje.append({"tytul": "Kluczowe uzasadnienie", "typ": "lista",
                       "tresc": narracja.uzasadnienie})
        if narracja.matryca_ryzyk:
            ryzyka = [f"{r.get('obszar', '')}: {r.get('opis', '')}".strip(": ")
                      for r in narracja.matryca_ryzyk]
            sekcje.append({"tytul": "Matryca ryzyk", "typ": "lista",
                           "tresc": ryzyka})
    else:
        powod = (narracja.powod if narracja else "Warstwa narracyjna pominięta.")
        sekcje.append({"tytul": "Kluczowe uzasadnienie", "typ": "tekst",
                       "tresc": f"Sekcja narracyjna niedostępna: {powod} "
                                "Liczby powyżej są kompletne."})

    # Waterfall oszczędności (Unit 7) — z widoczną linią etatu.
    if rozbicie is not None:
        sekcje.append({
            "tytul": "Oszczędności sp. z o.o. (waterfall brutto)",
            "typ": "tabela",
            "tresc": UI.wiersze_waterfall(rozbicie),
            "kolumny": ["Pozycja", "Kwota"],
            "szer": [130, 54],
        })

    # Reinwestycja (Unit 8) — rekomendacja + kompaktowe porównanie + projekcja.
    if reinwestycja is not None:
        sekcje.append({
            "tytul": "Reinwestycja oszczędności",
            "typ": "tekst",
            "tresc": (f"Podział oszczędności: "
                      f"{UI.formatuj_pln(reinwestycja.czesc_pracujaca)} "
                      f"pracujące w III filarze, "
                      f"{UI.formatuj_pln(reinwestycja.czesc_gotowka)} w gotówce."),
        })
        sekcje.append({
            "tytul": "Porównanie alokacji III filaru",
            "typ": "tabela",
            "tresc": UI.wiersze_alokacje(reinwestycja),
            "kolumny": ["Wariant", "IKE", "IKZE", "Gotówka (nadwyżka)"],
            "szer": [60, 42, 42, 42],
        })
        proj = [f"{p.stopa:.0%} przez {p.horyzont} lat → "
                f"{UI.formatuj_pln(p.wartosc_koncowa)} "
                f"(zysk {UI.formatuj_pln(p.zysk)})"
                for p in reinwestycja.projekcje]
        if proj:
            sekcje.append({"tytul": "Projekcja (widełki)", "typ": "lista",
                           "tresc": proj})
        sekcje.append({"tytul": "Zastrzeżenie inwestycyjne", "typ": "tekst",
                       "tresc": reinwestycja.disclaimer})

    return sekcje


def _wiersze_tabeli(wynik: WynikOptymalizacji) -> list[dict]:
    """Czyste wiersze do PDF (bez emoji — niedostępnych w foncie Arial)."""
    wiersze = []
    for f in wynik.formy:
        nazwa = f.nazwa + (" (rekomendacja)" if f.nazwa == wynik.werdykt else "")
        status = ("Dostępna" if f.dostepnosc == Dostepnosc.DOSTEPNA
                  else "NIEDOSTĘPNA")
        wiersze.append({
            "Forma": nazwa,
            "Podatek": UI.formatuj_pln(f.podatek),
            "Zdrowotna": UI.formatuj_pln(f.zdrowotna),
            "ZUS": UI.formatuj_pln(f.zus_spoleczny),
            "Dochód netto": UI.formatuj_pln(f.dochod_netto),
            "Status": status,
        })
    return wiersze


class _Raport(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self._unicode = os.path.exists(DEJAVU)
        if self._unicode:
            self.add_font("DejaVu", "", DEJAVU)
            self.add_font("DejaVu", "B", DEJAVU_BOLD if os.path.exists(DEJAVU_BOLD)
                          else DEJAVU)
            self._font = "DejaVu"
        else:  # awaryjnie font core (latin-1) — polskie znaki zastąpione
            self._font = "Helvetica"

    def _txt(self, s: str) -> str:
        # Emoji spoza fontu Arial → czytelny zamiennik (np. gwiazdka rekomendacji).
        s = s.replace("⭐ ", "» ").replace("⭐", "»")
        # Fallback dla fontów core (latin-1) — zachowaj czytelność bez crasha.
        if self._unicode:
            return s
        return s.encode("latin-1", "replace").decode("latin-1")

    def header(self):
        self.set_fill_color(*NAVY)
        self.rect(0, 0, self.w, 28, style="F")
        self.set_fill_color(*NAVY_2)
        self.rect(0, 22, self.w, 6, style="F")
        self.set_xy(12, 7)
        self.set_text_color(255, 255, 255)
        self.set_font(self._font, "B", 18)
        self.cell(0, 8, self._txt("Optymalizator Podatkowy 2026"),
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_x(12)
        self.set_font(self._font, "", 10)
        self.set_text_color(169, 192, 224)
        self.cell(0, 5, self._txt("Biuro Rachunkowe Abacus · porównanie form opodatkowania JDG"))
        self.set_y(36)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-22)
        self.set_draw_color(*NAVY_2)
        self.line(12, self.get_y(), self.w - 12, self.get_y())
        self.set_y(-19)
        self.set_font(self._font, "", 7.5)
        self.set_text_color(*SZARY)
        self.multi_cell(0, 4, self._txt(ZASTRZEZENIE))


def generuj_pdf(wynik: WynikOptymalizacji,
                narracja: Narracja | None = None,
                rozbicie=None, reinwestycja=None, majatek=None,
                dane=None) -> bytes:
    """Wygeneruj brandowany PDF jako bytes."""
    sekcje = zbuduj_sekcje(wynik, narracja, rozbicie=rozbicie,
                           reinwestycja=reinwestycja, majatek=majatek, dane=dane)
    pdf = _Raport()
    pdf.set_auto_page_break(auto=True, margin=28)
    pdf.add_page()
    pdf.set_left_margin(12)
    pdf.set_right_margin(12)

    for s in sekcje:
        pdf.set_font(pdf._font, "B", 13)
        pdf.set_text_color(*NAVY)
        pdf.ln(2)
        pdf.cell(0, 8, pdf._txt(s["tytul"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font(pdf._font, "", 10)

        if s["typ"] == "tekst":
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 5.5, pdf._txt(s["tresc"]))
        elif s["typ"] == "lista":
            for poz in s["tresc"]:
                pdf.set_x(pdf.l_margin)
                pdf.multi_cell(0, 5.5, pdf._txt(f"-  {poz}"))
        elif s["typ"] == "tabela":
            _rysuj_tabele(pdf, s["tresc"], s.get("kolumny"), s.get("szer"))
        pdf.ln(1)

    return bytes(pdf.output())


def _rysuj_tabele(pdf: _Raport, wiersze: list[dict],
                  kolumny: list[str] | None = None,
                  szer: list[float] | None = None) -> None:
    if not wiersze:
        return
    if kolumny is None:
        kolumny = ["Forma", "Podatek", "Zdrowotna", "ZUS", "Dochód netto", "Status"]
        szer = [42, 28, 28, 26, 32, 28]
    if szer is None:
        szer = [186 / len(kolumny)] * len(kolumny)
    # Nagłówek
    pdf.set_font(pdf._font, "B", 9)
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(255, 255, 255)
    for k, w in zip(kolumny, szer, strict=False):
        pdf.cell(w, 7, pdf._txt(k), border=0, fill=True, align="C")
    pdf.ln()
    # Wiersze
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(pdf._font, "", 9)
    for i, r in enumerate(wiersze):
        pdf.set_fill_color(*( (240, 243, 248) if i % 2 == 0 else (255, 255, 255)))
        for k, w in zip(kolumny, szer, strict=False):
            pdf.cell(w, 6.5, pdf._txt(str(r.get(k, ""))), border=0, fill=True)
        pdf.ln()
