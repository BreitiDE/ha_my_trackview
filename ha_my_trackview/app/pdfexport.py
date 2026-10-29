"""PDF-Export (A4 quer) mit Kopfzeile, Karte und Tabelle."""
from __future__ import annotations

import io
from datetime import datetime

from fpdf import FPDF

from render import hex_rgb

TEXT = {
    "de": {
        "trip": "Reise", "trips": "Reisen", "date": "Datum", "start": "Start", "end": "Ende",
        "duration": "Dauer", "driving": "Fahrzeit", "distance": "Strecke", "stages": "Etappen",
        "stage": "Etappe", "created": "Erstellt mit My TrackView am", "total": "Gesamt",
        "attrib": "Kartendaten (c) OpenStreetMap-Mitwirkende, ODbL",
        "running": "läuft", "unassigned": "nicht zugeordnet",
    },
    "en": {
        "trip": "Trip", "trips": "Trips", "date": "Date", "start": "Start", "end": "End",
        "duration": "Duration", "driving": "Driving time", "distance": "Distance", "stages": "Stages",
        "stage": "Stage", "created": "Created with My TrackView on", "total": "Total",
        "attrib": "Map data (c) OpenStreetMap contributors, ODbL",
        "running": "running", "unassigned": "unassigned",
    },
}

ACCENT = (206, 108, 0)
INK = (11, 11, 11)
INK2 = (82, 81, 78)
GRID = (225, 224, 217)


def _latin(s: str) -> str:
    rep = {"–": "-", "—": "-", "·": "·", "…": "...", "→": "->", "’": "'", "“": '"', "”": '"', "„": '"'}
    for a, b in rep.items():
        s = s.replace(a, b)
    return s.encode("latin-1", "replace").decode("latin-1")


class _PDF(FPDF):
    def __init__(self, lang: str, now: str):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.t = TEXT.get(lang, TEXT["en"])
        self.now = now
        self.set_auto_page_break(auto=True, margin=14)
        self.set_margins(10, 10, 10)

    def footer(self):
        self.set_y(-10)
        self.set_font("Helvetica", "", 7.5)
        self.set_text_color(*INK2)
        w = self.w - self.l_margin - self.r_margin
        self.cell(w - 20, 4, _latin(f"{self.t['attrib']}   ·   {self.t['created']} {self.now}"), align="L")
        self.cell(20, 4, f"{self.page_no()}/{{nb}}", align="R")


def build_pdf(*, lang: str, title: str, subtitle: str, facts: list[tuple[str, str]],
              map_png: bytes, table_head: list[str], table_rows: list[list[str]],
              swatches: list[str] | None, tz) -> bytes:
    now = datetime.now(tz).strftime("%d.%m.%Y %H:%M" if lang == "de" else "%Y-%m-%d %H:%M")
    pdf = _PDF(lang, now)
    pdf.alias_nb_pages()
    pdf.add_page()
    w = pdf.w - pdf.l_margin - pdf.r_margin

    # Kopfzeile
    pdf.set_fill_color(*ACCENT)
    pdf.rect(pdf.l_margin, 10, 3, 13, "F")
    pdf.set_xy(pdf.l_margin + 6, 10)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*INK)
    pdf.cell(w - 6, 7, _latin(title))
    pdf.set_xy(pdf.l_margin + 6, 17.5)
    pdf.set_font("Helvetica", "", 9.5)
    pdf.set_text_color(*INK2)
    pdf.cell(w - 6, 5, _latin(subtitle))

    # Kennzahlen
    y = 27
    n = max(1, len(facts))
    bw = w / n
    for i, (label, value) in enumerate(facts):
        x = pdf.l_margin + i * bw
        pdf.set_draw_color(*GRID)
        pdf.rect(x + (1 if i else 0), y, bw - 2, 14)
        pdf.set_xy(x + 4, y + 2)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*INK2)
        pdf.cell(bw - 8, 3.5, _latin(label))
        pdf.set_xy(x + 4, y + 6.5)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*INK)
        pdf.cell(bw - 8, 5.5, _latin(value))

    # Karte
    y = 45
    map_h = 112 if table_rows else 140
    pdf.image(io.BytesIO(map_png), x=pdf.l_margin, y=y, w=w, h=map_h)
    pdf.set_draw_color(*GRID)
    pdf.rect(pdf.l_margin, y, w, map_h)
    pdf.set_y(y + map_h + 5)

    # Tabelle
    if table_rows:
        cols = len(table_head)
        widths = [w / cols] * cols
        if swatches is not None:
            widths = [8] + [(w - 8) / (cols - 1)] * (cols - 1)

        def head():
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_text_color(*INK2)
            for i, h in enumerate(table_head):
                pdf.cell(widths[i], 6, _latin(h), border="B", align="L" if i < 2 else "R")
            pdf.ln(6)

        head()
        pdf.set_font("Helvetica", "", 8.5)
        for r_i, row in enumerate(table_rows):
            if pdf.get_y() > pdf.h - 22:
                pdf.add_page()
                head()
                pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*INK)
            y0 = pdf.get_y()
            for i, val in enumerate(row):
                if swatches is not None and i == 0:
                    pdf.set_fill_color(*hex_rgb(swatches[r_i]))
                    pdf.rect(pdf.get_x() + 1.5, y0 + 1.5, 4, 3, "F")
                    pdf.cell(widths[i], 6, "")
                    continue
                pdf.cell(widths[i], 6, _latin(val), align="L" if i < 2 else "R")
            pdf.ln(6)
            pdf.set_draw_color(*GRID)
            pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + w, pdf.get_y())
    out = pdf.output()
    return bytes(out)
