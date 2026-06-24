"""Generator brandowanego PDF (Abacus) — deliverable sesji doradczej (R11).

Sekcje budowane są jako struktura (`zbuduj_sekcje`) niezależna od fpdf2,
co czyni zawartość testowalną bez parsowania binarnego PDF.
"""
from __future__ import annotations

import datetime
import os
from io import BytesIO
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
AKCENT = (197, 160, 89)    # złoty akcent (rekomendacja)
JASNY = (240, 243, 248)


def _wykres_netto(wynik: WynikOptymalizacji) -> bytes | None:
    """Słupkowy wykres dochodu netto wg formy (rekomendacja wyróżniona)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None
    formy = [f for f in wynik.formy if f.dostepnosc == Dostepnosc.DOSTEPNA]
    nazwy = [f.nazwa for f in formy]
    netto = [f.dochod_netto for f in formy]
    kol = [(_h(AKCENT) if f.nazwa == wynik.werdykt else _h(NAVY_2)) for f in formy]
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    bars = ax.bar(nazwy, netto, color=kol, width=0.6)
    ax.set_title("Dochód netto wg formy opodatkowania", fontsize=12,
                 color=_h(NAVY), fontweight="bold")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(left=False)
    ax.set_yticks([])
    for b, v in zip(bars, netto, strict=False):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:,.0f} zł".replace(",", " "),
                ha="center", va="bottom", fontsize=9, color=_h(NAVY))
    ax.margins(y=0.18)
    return _png(fig)


def _wykres_majatek(majatek) -> bytes | None:
    """Liniowy wykres skumulowanego majątku 1/5/10 lat."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return None
    if not majatek:
        return None
    lata = sorted(next(iter(majatek)).wartosci.keys())
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    for p in majatek:
        y = [p.wartosci[r] for r in lata]
        akcent = p.rekomendowana
        ax.plot(lata, y, marker="o", linewidth=2.4 if akcent else 1.3,
                color=_h(AKCENT) if akcent else _h(NAVY_2),
                zorder=3 if akcent else 2, label=p.forma)
    ax.set_title("Skumulowany dochód netto w czasie", fontsize=12,
                 color=_h(NAVY), fontweight="bold")
    ax.set_xticks(lata)
    ax.set_xticklabels([f"{r} rok" if r == 1 else f"{r} lat" for r in lata])
    ax.spines[["top", "right"]].set_visible(False)
    ax.yaxis.set_major_formatter(
        lambda v, _p: f"{v / 1e6:.1f} mln" if v >= 1e6 else f"{v / 1e3:.0f} tys.")
    ax.legend(fontsize=8, frameon=False)
    return _png(fig)


def _png(fig) -> bytes:
    import matplotlib.pyplot as plt
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def _h(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)

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

    nota = UI.nota_majatek_spzoo(wynik)
    if nota:
        sekcje.append({"tytul": "Skład dochodu netto sp. z o.o.",
                       "typ": "tekst", "tresc": nota})

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
        mix = reinwestycja.rekomendacja
        nadw = (f", nadwyżka {UI.formatuj_pln(mix.gotowka_dodatkowa)} do gotówki"
                if mix.gotowka_dodatkowa > 0 else "")
        sekcje.append({
            "tytul": "Co odkładamy do III filaru (IKE / IKZE)",
            "typ": "tekst",
            "tresc": (f"Z {UI.formatuj_pln(reinwestycja.czesc_pracujaca)} "
                      f"pracujących w III filarze rekomendujemy (mix wg progu): "
                      f"IKE {UI.formatuj_pln(mix.ike)} + "
                      f"IKZE {UI.formatuj_pln(mix.ikze)}{nadw}. "
                      f"W gotówce pozostaje "
                      f"{UI.formatuj_pln(reinwestycja.czesc_gotowka)}."),
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
        self._cover = False
        self._unicode = os.path.exists(DEJAVU)
        if self._unicode:
            self.add_font("DejaVu", "", DEJAVU)
            self.add_font("DejaVu", "B", DEJAVU_BOLD if os.path.exists(DEJAVU_BOLD)
                          else DEJAVU)
            self._font = "DejaVu"
        else:  # awaryjnie font core (latin-1) — polskie znaki zastąpione
            self._font = "Helvetica"

    def okladka(self, wynik: WynikOptymalizacji) -> None:
        """Strona tytułowa: gradient navy, tytuł, werdykt, data."""
        self._cover = True
        self.set_auto_page_break(False)        # tekst przy dole nie łamie strony
        self.add_page()
        # Pionowy gradient navy.
        krokow = int(self.h)
        for i in range(krokow):
            t = i / krokow
            r = int(NAVY[0] + (NAVY_2[0] - NAVY[0]) * t)
            g = int(NAVY[1] + (NAVY_2[1] - NAVY[1]) * t)
            b = int(NAVY[2] + (NAVY_2[2] - NAVY[2]) * t)
            self.set_fill_color(r, g, b)
            self.rect(0, i, self.w, 1.0, style="F")
        # Złoty pasek akcentu.
        self.set_fill_color(*AKCENT)
        self.rect(0, 96, self.w, 1.2, style="F")
        self.set_text_color(255, 255, 255)
        self.set_xy(0, 104)
        self.set_font(self._font, "B", 30)
        self.cell(0, 16, self._txt("Analiza Optymalizacji"), align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.cell(0, 16, self._txt("Podatkowej 2026"), align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(6)
        self.set_font(self._font, "", 13)
        self.set_text_color(169, 192, 224)
        self.cell(0, 8, self._txt("Porównanie czterech form opodatkowania JDG"),
                  align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        # Werdykt na okładce.
        self.ln(10)
        self.set_font(self._font, "B", 15)
        self.set_text_color(*AKCENT)
        self.cell(0, 9, self._txt(f"Rekomendacja: {wynik.werdykt}"), align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        # Stopka okładki.
        self.set_xy(0, self.h - 30)
        self.set_font(self._font, "B", 13)
        self.set_text_color(255, 255, 255)
        self.cell(0, 7, self._txt("Biuro Rachunkowe Abacus"), align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font(self._font, "", 10)
        self.set_text_color(169, 192, 224)
        data = datetime.date.today().strftime("%d.%m.%Y")
        self.cell(0, 6, self._txt(f"Dokument doradczy · {data}"), align="C")
        self._cover = False
        self.set_auto_page_break(True, margin=28)

    def _txt(self, s: str) -> str:
        # Emoji spoza fontu Arial → czytelny zamiennik (np. gwiazdka rekomendacji).
        s = s.replace("⭐ ", "» ").replace("⭐", "»")
        # Fallback dla fontów core (latin-1) — zachowaj czytelność bez crasha.
        if self._unicode:
            return s
        return s.encode("latin-1", "replace").decode("latin-1")

    def header(self):
        if self._cover:
            return
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
        if self._cover:
            return
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
    # Wykresy wstrzykiwane po właściwych sekcjach.
    wykresy = {"Tabela porównawcza form": _wykres_netto(wynik)}
    if majatek:
        wykresy["Skumulowany dochód netto (1 / 5 / 10 lat)"] = _wykres_majatek(majatek)

    pdf = _Raport()
    pdf.set_auto_page_break(auto=True, margin=28)
    pdf.okladka(wynik)            # strona tytułowa
    pdf.add_page()
    pdf.set_left_margin(12)
    pdf.set_right_margin(12)

    for s in sekcje:
        # Nagłówek sekcji ze złotym akcentem.
        pdf.ln(3)
        pdf.set_fill_color(*AKCENT)
        pdf.rect(pdf.l_margin, pdf.get_y() + 1, 3, 6.5, style="F")
        pdf.set_xy(pdf.l_margin + 5, pdf.get_y())
        pdf.set_font(pdf._font, "B", 13)
        pdf.set_text_color(*NAVY)
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

        # Wykres po danej sekcji.
        png = wykresy.get(s["tytul"])
        if png:
            pdf.ln(2)
            pdf.image(BytesIO(png), x=pdf.l_margin, w=186)
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
