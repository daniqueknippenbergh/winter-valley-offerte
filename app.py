# -*- coding: utf-8 -*-
"""
app.py
======
Kleine webservice rond fill_offerte.py, zodat Zapier (of iets anders) deze
via een gewone POST-aanroep kan gebruiken om een ingevulde offerte-PDF te
krijgen.

Eindpunt:
    POST /maak-offerte
    Headers:  X-Api-Key: <jouw geheime sleutel>   (optioneel, zie onder)
    Body:     JSON met de lead-gegevens (zelfde velden als nu al naar
              Zapier gestuurd worden vanuit de funnel)
    Antwoord: de offerte als PDF-bestand (Content-Type: application/pdf)

Beveiliging:
    Zet op het hostingplatform een environment variable OFFERTE_API_KEY met
    een eigen geheime waarde. Is die gezet, dan moet elk verzoek de header
    "X-Api-Key" met diezelfde waarde meesturen, anders wordt het verzoek
    geweigerd (401). Niet gezet -> geen check (handig om snel te testen,
    maar zet 'm aan zodra dit live gaat).
"""

import os
from datetime import datetime

from flask import Flask, request, Response, jsonify

from fill_offerte import generate_offerte_bytes

app = Flask(__name__)

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "Offerte_Template_-_Winter_Valley_2026.pdf")
API_KEY = os.environ.get("OFFERTE_API_KEY")  # None = geen check


@app.get("/")
def health():
    """Simpel check-adres: als je dit in de browser opent en 'OK' ziet,
    draait de service. Handig om na het deployen te testen."""
    return "OK - offerte-service draait"


@app.post("/maak-offerte")
def maak_offerte():
    if API_KEY:
        if request.headers.get("X-Api-Key") != API_KEY:
            return jsonify({"error": "Ongeldige of ontbrekende API-key"}), 401

    lead = request.get_json(silent=True)
    if not lead:
        return jsonify({"error": "Geen (geldige) JSON-body ontvangen"}), 400

    try:
        data, pdf_bytes = generate_offerte_bytes(lead, TEMPLATE_PATH)
    except Exception as exc:  # noqa: BLE001 -- bewust breed, dit is een eindpunt
        return jsonify({"error": "Kon offerte niet genereren: %s" % str(exc)}), 500

    naam = (lead.get("firstName", "") + "_" + lead.get("lastName", "")).strip("_") or "Klant"
    veilige_naam = "".join(ch for ch in naam if ch.isalnum() or ch in ("_", "-")) or "Klant"
    bestandsnaam = "Offerte_Winter_Valley_%s_%s.pdf" % (
        veilige_naam, datetime.now().strftime("%Y%m%d")
    )

    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="%s"' % bestandsnaam},
    )


if __name__ == "__main__":
    # Lokaal testen: python3 app.py  (draait dan op http://localhost:8080)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
