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
    SZ = 11
    F = FONT_BOLD

    # --- Gegevens-blok (gele kaart) ---
    # Alle waarden afdekken en herdrukken in hetzelfde lettertype (Helvetica-Bold)
    # zodat opdrachtgever, datum, tijd, locatie, gasten en contactpersoon
    # allemaal hetzelfde uiterlijk hebben.

    cover_rect(c, 245.0, 271.7, 420.0, 282.6, YELLOW_BG)
    draw_text(c, 245.0, 282.6, data["opdrachtgever"], size=SZ, font=F)

    cover_rect(c, 245.0, 288.9, 420.0, 299.9, YELLOW_BG)
    draw_text(c, 245.0, 299.9, data["datum"], size=SZ, font=F)

    cover_rect(c, 245.0, 306.2, 420.0, 317.2, YELLOW_BG)
    draw_text(c, 245.0, 317.2, data["tijd"], size=SZ, font=F)

    # Locatie: originele Canva-tekst afdekken en herdrukken in Helvetica-Bold
    cover_rect(c, 245.0, 323.4, 420.0, 334.4, YELLOW_BG)
    draw_text(c, 245.0, 334.4, "Ekkersweijer 7, 5681 RZ Best", size=SZ, font=F)

    cover_rect(c, 245.0, 340.7, 420.0, 351.7, YELLOW_BG)
    draw_text(c, 245.0, 351.7, "%d gasten" % data["aantal_gasten"], size=SZ, font=F)

    # Contactpersoon: originele Canva-tekst afdekken en herdrukken
    cover_rect(c, 245.0, 358.0, 420.0, 368.9, YELLOW_BG)
    draw_text(c, 245.0, 368.9, "Milan Sch\u00f6ningh", size=SZ, font=F)

    # --- Programma-blok (roze kaart) ---
    cover_rect(c, 124.0, 496.0, 405.0, 626.0, PINK_BG, pad=0)

    row_top = 502.9
    row_step = 18.75
    for label, value in data["schedule"]:
        row_bottom = row_top + 11.9
        draw_text(c, 132.1, row_bottom, value, size=SZ, font=F)
        draw_text(c, 237.2, row_bottom, label, size=SZ, font=F)
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
    SZ = 10.5
    F = FONT_BOLD
    EUR1 = 331.5
    EUR2 = 419.4

    # === LOCATIE ===
    # Lijn op y=317.6 -- NIET afdekken

    # Locatiehuur: stuk + beschrijving afdekken en herdrukken (lettertype fix)
    # col1 € + ruimte afdekken (geen prijs in col1)
    cover_rect(c, 86.5, 333.8, 300.0, 345.8, YELLOW_BG, pad=0)
    cover_rect(c, 329.5, 333.8, 414.0, 345.8, YELLOW_BG, pad=0)
    draw_text(c, 86.5, 344.8, "1", size=SZ, font=F)
    draw_text(c, 118.6, 344.8, "Locatiehuur | Winter Valley", size=SZ, font=F)
    draw_text_right(c, PRICE_COL2_RIGHT, 344.8, format_price(data["room_price"]), size=SZ, font=F)

    # Bemande garderobe: stuk + beschrijving afdekken (lettertype fix) -- col1 BEHOUDEN (1,00 pp)
    cover_rect(c, 86.5, 351.6, 300.0, 363.6, YELLOW_BG, pad=0)
    cover_rect(c, 385.6, 351.6, 413.4, 363.6, YELLOW_BG, pad=0)
    draw_text(c, 86.5, 362.6, str(guests), size=SZ, font=F)
    draw_text(c, 118.6, 362.6, "Bemande garderobe | per persoon", size=SZ, font=F)
    draw_text_right(c, PRICE_COL1_RIGHT, 362.6, "1,00", size=SZ, font=F)
    draw_text_right(c, PRICE_COL2_RIGHT, 362.6, format_price(data["garderobe_total"]), size=SZ, font=F)

    # Eindschoonmaak: stuk + beschrijving afdekken (lettertype fix)
    # col1 volledig weghalen (€ + Nader te bepalen), alleen col2 n.t.b.
    cover_rect(c, 86.5, 376.1, 300.0, 388.0, YELLOW_BG, pad=0)
    cover_rect(c, 329.5, 366.6, 414.0, 396.6, YELLOW_BG, pad=0)
    cover_rect(c, 450.0, 366.6, 503.0, 396.6, YELLOW_BG, pad=0)
    draw_text(c, 86.5, 387.1, "1", size=SZ, font=F)
    draw_text(c, 118.6, 387.1, "Eindschoonmaak nacalculatie", size=SZ, font=F)
    draw_text_right(c, PRICE_COL2_RIGHT, 382.6, "n.t.b.", size=SZ, font=F)

    # Wees-element "1" onder Eindschoonmaak
    cover_rect(c, 86.5, 400.8, 115.0, 412.8, YELLOW_BG, pad=0)

    # Techniek col1 "Prijs"-header weghalen (x=332.5-355.7, y=599.0-610.0)
    cover_rect(c, 330.5, 599.0, 357.0, 610.5, YELLOW_BG, pad=0)

    # === HORECA ===
    # Lijn op y=488.7 -- NIET afdekken
    # Horeca: col1 pp-prijs BEHOUDEN voor alle rijen

    # Foodcorners
    cover_rect(c, 86.5, 490.5, 503.0, 512.3, YELLOW_BG, pad=0)
    draw_text(c, 86.5, 510.3, str(guests), size=SZ, font=F)
    draw_text(c, 118.6, 510.3, "Foodcorners", size=SZ, font=F)
    draw_text(c, EUR1, 510.3, "\u20ac", size=SZ, font=F)
    draw_text(c, EUR2, 510.3, "\u20ac", size=SZ, font=F)
    if data["has_food"]:
        draw_text_right(c, PRICE_COL1_RIGHT, 510.3, format_price(data["food_pp"]), size=SZ, font=F)
        draw_text_right(c, PRICE_COL2_RIGHT, 510.3, format_price(data["food_total"]), size=SZ, font=F)
    else:
        draw_text_right(c, PRICE_COL1_RIGHT, 510.3, "n.v.t.", size=SZ, font=F)
        draw_text_right(c, PRICE_COL2_RIGHT, 510.3, "n.v.t.", size=SZ, font=F)

    # Drankarrangement
    cover_rect(c, 86.5, 517.1, 503.0, 529.1, YELLOW_BG, pad=0)
    draw_text(c, 86.5, 528.1, str(guests), size=SZ, font=F)
    draw_text(c, 118.6, 528.1, data["drink_name"], size=SZ, font=F)
    draw_text(c, EUR1, 528.1, "\u20ac", size=SZ, font=F)
    draw_text(c, EUR2, 528.1, "\u20ac", size=SZ, font=F)
    draw_text_right(c, PRICE_COL1_RIGHT, 528.1, format_price(data["drink_pp"]), size=SZ, font=F)
    draw_text_right(c, PRICE_COL2_RIGHT, 528.1, format_price(data["drink_total"]), size=SZ, font=F)

    # Extra horeca-regel (bv. Welkomsglas prosecco)
    if data["extras_lines"]:
        extra = data["extras_lines"][0]
        cover_rect(c, 86.5, 534.8, 503.0, 546.8, YELLOW_BG, pad=0)
        draw_text(c, 86.5, 545.8, str(extra["qty"]), size=SZ, font=F)
        draw_text(c, 118.6, 545.8, extra["name"], size=SZ, font=F)
        if extra["pricePerPerson"] is not None:
            draw_text(c, EUR1, 545.8, "\u20ac", size=SZ, font=F)
            draw_text_right(c, PRICE_COL1_RIGHT, 545.8, format_price(extra["pricePerPerson"]), size=SZ, font=F)
        draw_text(c, EUR2, 545.8, "\u20ac", size=SZ, font=F)
        draw_text_right(c, PRICE_COL2_RIGHT, 545.8, format_price(extra["amount"]), size=SZ, font=F)
    else:
        cover_rect(c, 417.4, 534.8, 428.6, 545.8, YELLOW_BG, pad=0)

    # === TECHNIEK ===
    # Lijn op y=617.9 -- NIET afdekken (cover start op y=619.5)
    # Volledige rij afdekken: tekst + col1 (WEGHALEN) + col2 (fix font)
    cover_rect(c, 116.6, 619.5, 503.0, 652.0, YELLOW_BG, pad=0)
    draw_text(c, 118.6, 634.0, "Uitgebreide licht en geluid", size=SZ, font=F)
    draw_text(c, 118.6, 647.0, "set incl. DJ gear", size=SZ, font=F)
    draw_text(c, EUR2, 639.6, "\u20ac", size=SZ, font=F)
    draw_text_right(c, PRICE_COL2_RIGHT, 639.6, "0,00", size=SZ, font=F)

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
    SZ = 10.5
    F = FONT_BOLD
    EUR2 = 419.4   # x-positie €-teken tweede prijskolom

    # === PERSONEEL ===
    # Lijn op y=184.7 -- NIET afdekken (cover start op y=186.0)
    # Col1 "Prijs"-header weghalen (er staan geen prijzen onder in col1)
    cover_rect(c, 330.5, 165.7, 357.0, 177.0, YELLOW_BG, pad=0)
    cover_rect(c, 86.5, 186.0, 503.0, 258.0, YELLOW_BG, pad=0)

    # Event manager: stuk, nieuwe tijd, €-teken col2, totaalprijs
    draw_text(c, 86.5, 206.4, "1", size=SZ, font=F)
    draw_text(c, 118.6, 206.4, "Event manager | " + data["manager_tijd"], size=SZ, font=F)
    draw_text(c, EUR2, 206.4, "\u20ac", size=SZ, font=F)
    draw_text_right(c, PRICE_COL2_RIGHT, 206.4, format_price(data["event_manager_total"]), size=SZ, font=F)

    # F&B manager
    draw_text(c, 86.5, 222.9, "1", size=SZ, font=F)
    draw_text(c, 118.6, 222.9, "F\u0026B manager | " + data["manager_tijd"], size=SZ, font=F)
    draw_text(c, EUR2, 222.9, "\u20ac", size=SZ, font=F)
    draw_text_right(c, PRICE_COL2_RIGHT, 222.9, format_price(data["fb_manager_total"]), size=SZ, font=F)

    # Medewerker sanitair
    draw_text(c, 86.5, 239.4, "1", size=SZ, font=F)
    draw_text(c, 118.6, 239.4, "Medewerker sanitair | " + data["tijd"], size=SZ, font=F)
    draw_text(c, EUR2, 239.4, "\u20ac", size=SZ, font=F)
    if data["sanitair_included"]:
        draw_text_right(c, PRICE_COL2_RIGHT, 239.4, format_price(data["sanitair_total"]), size=SZ, font=F)
    else:
        draw_text_right(c, PRICE_COL2_RIGHT, 239.4, "n.v.t.", size=SZ, font=F)

    # === ENTERTAINMENT ===
    # Lijn op y=335.8 -- NIET afdekken
    # Headers (y=316.9-327.9) boven de lijn: apart afdekken, dan herdrukken
    cover_rect(c, 86.5, 316.9, 503.0, 328.9, YELLOW_BG, pad=0)
    draw_text(c, 86.5, 327.9, "Stuk", size=SZ, font=F)
    draw_text(c, 118.8, 327.9, "Omschrijving", size=SZ, font=F)
    draw_text(c, 420.0, 327.9, "Prijs", size=SZ, font=F)

    # Content rijen (start RUIM na lijn y=335.8)
    cover_rect(c, 86.5, 337.0, 503.0, 432.0, YELLOW_BG, pad=0)

    rows = data["entertainment_rows"]
    if not rows:
        draw_text(c, 86.5, 360.0, "Geen extra entertainment gekozen", size=SZ, font=F)
    else:
        compact = len(rows) > 3
        row_top = 348.0
        for name in rows:
            step = 17.0 if compact else 31.6
            bottom = row_top + 11.0
            draw_text(c, 86.5, bottom, "1", size=SZ, font=F)
            draw_text(c, 118.6, bottom, name, size=SZ, font=F)
            draw_text_right(c, PRICE_COL2_RIGHT, bottom, "Prijs op aanvraag", size=SZ, font=F)
            row_top += step

    # === TOTAAL ===
    # Lijn op y=493.5 -- NIET afdekken
    # Totaal-labels zijn originele Canva-font; afdekken en herdrukken in Helvetica-Bold
    # zodat het lettertype overeenkomt met mijn getallen.
    # Labels liggen BOVEN de lijn (y=472.4-483.4): apart afdekken
    cover_rect(c, 113.6, 472.4, 450.0, 484.4, YELLOW_BG, pad=0)
    draw_text(c, 119.3, 483.4, "Omschrijving", size=SZ, font=F)
    draw_text(c, 420.5, 483.4, "Prijs", size=SZ, font=F)

    # Rijen ONDER de lijn (y=504.3-564.8): afdekken en herdrukken
    cover_rect(c, 113.6, 503.3, 450.0, 565.8, YELLOW_BG, pad=0)
    draw_text(c, 114.6, 515.3, "Totaalprijs exclusief btw", size=SZ, font=F)
    draw_text(c, 114.6, 531.8, "btw laag 9 %", size=SZ, font=F)
    draw_text(c, 114.6, 548.3, "btw hoog 21 %", size=SZ, font=F)
    draw_text(c, 114.6, 564.8, "Totaalprijs inclusief btw", size=SZ, font=F)

    # €-tekens en getallen
    EUR2_TOT = 415.4  # €-positie in totaal-sectie (iets anders dan kosten-tabel)
    PCOL2_TOT = 501.3
    draw_text(c, EUR2_TOT, 515.3, "\u20ac", size=SZ, font=F)
    draw_text_right(c, PCOL2_TOT, 515.3, format_price(data["subtotal_excl_btw"]), size=SZ, font=F)
    draw_text(c, EUR2_TOT, 531.8, "\u20ac", size=SZ, font=F)
    draw_text_right(c, PCOL2_TOT, 531.8, format_price(data["btw_laag"]), size=SZ, font=F)
    draw_text(c, EUR2_TOT, 548.3, "\u20ac", size=SZ, font=F)
    draw_text_right(c, PCOL2_TOT, 548.3, format_price(data["btw_hoog"]), size=SZ, font=F)
    draw_text(c, EUR2_TOT, 564.8, "\u20ac", size=SZ, font=F)
    draw_text_right(c, PCOL2_TOT, 564.8, format_price(data["totaal_incl_btw"]), size=SZ, font=F)

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
