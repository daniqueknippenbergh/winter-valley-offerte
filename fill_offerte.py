# -*- coding: utf-8 -*-
"""
fill_offerte.py
================
Vult de Winter Valley offerte-PDF (Canva-export) automatisch in met de
gegevens van een funnel-inzending, op basis van de berekeningen uit
offer_engine.py.

Werkwijze: voor pagina 3 (gegevens + programma) en pagina 16-17 (kosten)
wordt een transparante "overlay"-laag getekend (met reportlab) die over de
oorspronkelijke pagina heen wordt gelegd (met pypdf). De overige 14
pagina's van de offerte blijven precies zoals ze zijn.

Gebruik:
    python3 fill_offerte.py
(zie het voorbeeld onderaan -- vervang door echte lead-data uit Zapier)
"""

import io
from reportlab.pdfgen import canvas
from reportlab.lib.colors import Color
from pypdf import PdfReader, PdfWriter

from offer_engine import compute_breakdown, format_price

PAGE_W = 595.5
PAGE_H = 842.2499787

INK = Color(35 / 255, 31 / 255, 32 / 255)       # bijna-zwart, tekstkleur in het format
YELLOW_BG = Color(249 / 255, 195 / 255, 25 / 255)  # achtergrond van de gele kaarten
PINK_BG = Color(242 / 255, 178 / 255, 202 / 255)   # achtergrond van het programma-vak

FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


def y_from_top(bottom_pdf_top_origin):
    """pdfplumber geeft y-waarden vanaf de bovenkant van de pagina; reportlab
    tekent vanaf de onderkant. Converteer + kleine correctie voor de
    tekst-baseline."""
    return PAGE_H - bottom_pdf_top_origin + 2.2


def cover_rect(c, x0, top, x1, bottom, color, pad=1.5):
    """Tekent een rechthoek in paginakleur over een stuk originele tekst heen,
    zodat we daar overheen kunnen schrijven."""
    c.setFillColor(color)
    c.rect(x0 - pad, PAGE_H - bottom - pad, (x1 - x0) + 2 * pad, (bottom - top) + 2 * pad,
           stroke=0, fill=1)


def draw_text(c, x, top_baseline_bottom, text, size=11, font=FONT, color=INK):
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawString(x, y_from_top(top_baseline_bottom), text)


def draw_text_right(c, x_right_edge, top_baseline_bottom, text, size=11, font=FONT, color=INK):
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawRightString(x_right_edge, y_from_top(top_baseline_bottom), text)


# Vaste rechter-uitlijnposities van de twee prijskolommen, afgeleid van de
# statische voorbeeldwaarden die al in het format staan (bv. "1,00" en
# "0,00" sluiten steeds af op dezelfde x-positie).
PRICE_COL1_RIGHT = 411.4  # eerste "Prijs"-kolom (stuksprijs)
PRICE_COL2_RIGHT = 501.3  # tweede "Prijs"-kolom (totaalprijs)


# ---------------------------------------------------------------------------
# PAGINA 3 -- gegevens + programma
# ---------------------------------------------------------------------------

def build_page3_overlay(data):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))

    # --- Gegevens-blok (gele kaart) ---
    cover_rect(c, 245.0, 271.7, 360.0, 282.6, YELLOW_BG)
    draw_text(c, 245.0, 282.6, data["opdrachtgever"])

    cover_rect(c, 245.0, 288.9, 360.0, 299.9, YELLOW_BG)
    draw_text(c, 245.0, 299.9, data["datum"])

    cover_rect(c, 245.0, 306.2, 360.0, 317.2, YELLOW_BG)
    draw_text(c, 245.0, 317.2, data["tijd"])

    cover_rect(c, 245.0, 340.7, 360.0, 351.7, YELLOW_BG)
    draw_text(c, 245.0, 351.7, "%d gasten" % data["aantal_gasten"])

    # --- Programma-blok (roze kaart) ---
    # Hele tijden-/omschrijvingenblok afdekken en opnieuw opbouwen, want het
    # aantal regels varieert (met/zonder food).
    cover_rect(c, 124.0, 496.0, 405.0, 626.0, PINK_BG, pad=0)

    row_top = 502.9
    row_step = 18.75
    for label, value in data["schedule"]:
        row_bottom = row_top + 11.9
        draw_text(c, 132.1, row_bottom, value, size=11, font=FONT_BOLD)
        draw_text(c, 237.2, row_bottom, label, size=11)
        row_top += row_step

    c.showPage()
    c.save()
    buf.seek(0)
    return PdfReader(buf).pages[0]


# ---------------------------------------------------------------------------
# PAGINA 16 -- kosten: locatie + horeca
# ---------------------------------------------------------------------------

def build_page16_overlay(data):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))

    guests = data["aantal_gasten"]

    # LOCATIE -- Locatiehuur
    draw_text_right(c, PRICE_COL1_RIGHT, 344.8, format_price(data["room_price"]), size=10.5)
    draw_text_right(c, PRICE_COL2_RIGHT, 344.8, format_price(data["room_price"]), size=10.5)

    # LOCATIE -- Bemande garderobe (pp blijft 1,00 zoals al in het format
    # staat; alleen het aantal gasten + de totaalprijs vullen we aan)
    cover_rect(c, 88.5, 351.6, 110.1, 362.6, YELLOW_BG)
    draw_text(c, 88.5, 362.6, str(guests), size=10.5)
    draw_text_right(c, PRICE_COL2_RIGHT, 362.6, format_price(data["garderobe_total"]), size=10.5)

    # HORECA -- Foodcorners
    cover_rect(c, 86.5, 499.3, 108.1, 510.3, YELLOW_BG)
    if data["has_food"]:
        draw_text(c, 86.5, 510.3, str(guests), size=10.5)
        draw_text_right(c, PRICE_COL1_RIGHT, 510.3, format_price(data["food_pp"]), size=10.5)
        draw_text_right(c, PRICE_COL2_RIGHT, 510.3, format_price(data["food_total"]), size=10.5)
    else:
        draw_text(c, 86.5, 510.3, "-", size=10.5)
        draw_text_right(c, PRICE_COL1_RIGHT, 510.3, "n.v.t.", size=10.5)
        draw_text_right(c, PRICE_COL2_RIGHT, 510.3, "n.v.t.", size=10.5)

    # HORECA -- Drankarrangement (omschrijving + stuk eerst afdekken, want
    # de naam varieert: "Drank basis" of "Drank compleet")
    cover_rect(c, 86.5, 517.1, 230.0, 528.1, YELLOW_BG)
    draw_text(c, 86.5, 528.1, str(guests), size=10.5)
    draw_text(c, 118.6, 528.1, data["drink_name"], size=10.5)
    draw_text_right(c, PRICE_COL1_RIGHT, 528.1, format_price(data["drink_pp"]), size=10.5)
    draw_text_right(c, PRICE_COL2_RIGHT, 528.1, format_price(data["drink_total"]), size=10.5)

    # HORECA -- extra losse regel (bv. Welkomsglas prosecco), als gekozen
    if data["extras_lines"]:
        extra = data["extras_lines"][0]
        draw_text(c, 86.5, 545.8, str(extra["qty"]), size=10.5)
        draw_text(c, 118.6, 545.8, extra["name"], size=10.5)
        if extra["pricePerPerson"] is not None:
            draw_text_right(c, PRICE_COL1_RIGHT, 545.8, "\u20ac" + format_price(extra["pricePerPerson"]), size=10.5)
        draw_text_right(c, PRICE_COL2_RIGHT, 545.8, format_price(extra["amount"]), size=10.5)
    else:
        # Verborgen "weesregel" uit het originele Canva-format (een los
        # €-symbool zonder omschrijving) -- alleen zichtbaar als er geen
        # extra horeca-regel wordt ingevuld.
        cover_rect(c, 419.4, 534.8, 426.6, 545.8, YELLOW_BG)

    # Verborgen "weesregel" uit het originele Canva-format: een los "1"tje
    # zonder omschrijving, direct onder Eindschoonmaak nacalculatie.
    cover_rect(c, 88.5, 400.8, 92.7, 411.8, YELLOW_BG)

    c.showPage()
    c.save()
    buf.seek(0)
    return PdfReader(buf).pages[0]


# ---------------------------------------------------------------------------
# PAGINA 17 -- kosten: personeel + entertainment + totaal
# ---------------------------------------------------------------------------

def build_page17_overlay(data):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))

    # PERSONEEL
    draw_text_right(c, PRICE_COL1_RIGHT, 206.4, format_price(data["event_manager_total"]), size=10.5)
    draw_text_right(c, PRICE_COL2_RIGHT, 206.4, format_price(data["event_manager_total"]), size=10.5)

    draw_text_right(c, PRICE_COL1_RIGHT, 222.9, format_price(data["fb_manager_total"]), size=10.5)
    draw_text_right(c, PRICE_COL2_RIGHT, 222.9, format_price(data["fb_manager_total"]), size=10.5)

    if data["sanitair_included"]:
        draw_text_right(c, PRICE_COL1_RIGHT, 239.4, format_price(data["sanitair_total"]), size=10.5)
        draw_text_right(c, PRICE_COL2_RIGHT, 239.4, format_price(data["sanitair_total"]), size=10.5)
    else:
        draw_text_right(c, PRICE_COL1_RIGHT, 239.4, "n.v.t.", size=10.5)
        draw_text_right(c, PRICE_COL2_RIGHT, 239.4, "n.v.t.", size=10.5)

    # De medewerker sanitair is alleen aanwezig tijdens het event zelf
    # (geen half uur ervoor/erna zoals bij event-/F&B-manager) -- dus de
    # statische "17:30 - 00:30" vervangen door de echte event-tijden.
    cover_rect(c, 234.8, 228.4, 303.4, 239.4, YELLOW_BG)
    draw_text(c, 234.8, 239.4, data["tijd"], size=10.5)

    # Verborgen "weesregel" uit het originele Canva-format: een los "1"tje
    # zonder omschrijving, direct onder Medewerker sanitair.
    cover_rect(c, 86.5, 245.0, 90.7, 256.0, YELLOW_BG)

    # ENTERTAINMENT -- volledige sectie afdekken en opnieuw opbouwen
    # (variabel aantal regels, afhankelijk van gekozen addons)
    cover_rect(c, 86.5, 316.0, 510.0, 432.0, YELLOW_BG, pad=0)
    draw_text(c, 86.5, 327.9, "Stuk", size=10.5, font=FONT_BOLD)
    draw_text(c, 118.8, 327.9, "Omschrijving", size=10.5, font=FONT_BOLD)
    draw_text(c, 332.5, 327.9, "Prijs", size=10.5, font=FONT_BOLD)
    draw_text(c, 420.0, 327.9, "Prijs", size=10.5, font=FONT_BOLD)
    c.setStrokeColor(INK)
    c.line(86.5, y_from_top(330.5) - 1, 503.0, y_from_top(330.5) - 1)

    rows = data["entertainment_rows"]
    if not rows:
        draw_text(c, 86.5, 354.0, "Geen extra entertainment gekozen", size=10.5)
    else:
        compact = len(rows) > 3
        row_top = 343.0
        for name in rows:
            if compact:
                bottom = row_top + 11.0
                draw_text(c, 86.5, bottom, "1", size=10.5)
                draw_text(c, 118.6, bottom, name, size=10.5)
                draw_text_right(c, PRICE_COL1_RIGHT, bottom, "Op aanvraag", size=10.5)
                draw_text_right(c, PRICE_COL2_RIGHT, bottom, "Op aanvraag", size=10.5)
                row_top += 17.0
            else:
                bottom = row_top + 11.0
                draw_text(c, 86.5, bottom, "1", size=10.5)
                draw_text(c, 118.6, bottom, name, size=10.5)
                draw_text_right(c, PRICE_COL1_RIGHT, bottom, "Prijs op aanvraag", size=10.5)
                draw_text_right(c, PRICE_COL2_RIGHT, bottom, "Prijs op aanvraag", size=10.5)
                row_top += 31.6

    # TOTAAL
    draw_text_right(c, 497.0, 515.3, format_price(data["subtotal_excl_btw"]), size=10.5, font=FONT_BOLD)
    draw_text_right(c, 497.0, 531.8, format_price(data["btw_laag"]), size=10.5, font=FONT_BOLD)
    draw_text_right(c, 497.0, 548.3, format_price(data["btw_hoog"]), size=10.5, font=FONT_BOLD)
    draw_text_right(c, 497.0, 564.8, format_price(data["totaal_incl_btw"]), size=10.5, font=FONT_BOLD)

    c.showPage()
    c.save()
    buf.seek(0)
    return PdfReader(buf).pages[0]


# ---------------------------------------------------------------------------
# Samenvoegen met het originele template
# ---------------------------------------------------------------------------

def generate_offerte(lead, template_path, output_path):
    data, pdf_bytes = generate_offerte_bytes(lead, template_path)

    with open(output_path, "wb") as f:
        f.write(pdf_bytes)

    return data


def generate_offerte_bytes(lead, template_path):
    """Zelfde als generate_offerte(), maar geeft de PDF terug als bytes in
    het geheugen (geen bestand op schijf) -- handig voor een webservice."""
    data = compute_breakdown(lead)

    reader = PdfReader(template_path)
    writer = PdfWriter()

    overlays = {
        2: build_page3_overlay(data),
        15: build_page16_overlay(data),
        16: build_page17_overlay(data),
    }

    for i, page in enumerate(reader.pages):
        if i in overlays:
            page.merge_page(overlays[i])
        writer.add_page(page)

    out_buf = io.BytesIO()
    writer.write(out_buf)
    return data, out_buf.getvalue()


if __name__ == "__main__":
    example_lead = {
        "firstName": "Lisa", "lastName": "de Vries",
        "email": "lisa@example.com", "phone": "0612345678", "company": "Acme BV",
        "guests": 220, "date": "2026-12-18",
        "startTime": "18:00", "endTime": "00:00", "durationHours": 6,
        "eventType": "kerst",
        "drink": "compleet", "drinkAddons": ["prosecco"], "noService": False,
        "package": "foodbasis",
        "addons": ["karikaturist", "vrskisim"],
    }
    result = generate_offerte(
        example_lead,
        "/mnt/user-data/uploads/Offerte_Template_-_Winter_Valley_2026.pdf",
        "/home/claude/Offerte_Voorbeeld.pdf",
    )
    print("Klaar. Berekende waarden:")
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
