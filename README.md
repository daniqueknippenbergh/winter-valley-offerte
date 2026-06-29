# Winter Valley -- Offerte-service

Dit mapje bevat alles om automatisch ingevulde offerte-PDF's te genereren
op basis van een funnel-inzending, en dit als een online "knopje" (URL)
beschikbaar te maken zodat Zapier het kan aanroepen.

Bestanden:
- `app.py` -- de webservice (1 eindpunt: `POST /maak-offerte`)
- `fill_offerte.py` -- vult de PDF in
- `offer_engine.py` -- alle prijzen/staffels/planninglogica (hier pas je
  bedragen aan als er iets wijzigt)
- `Offerte_Template_-_Winter_Valley_2026.pdf` -- het basis-format
- `requirements.txt`, `Procfile` -- nodig voor het hostingplatform

---

## Stap 1 -- hosten op Render.com (aanbevolen, geen command line nodig)

1. Ga naar https://render.com en maak een gratis account.
2. Klik op **New +** -> **Web Service**.
3. Kies de optie om een **map/zip te uploaden** (of zet dit mapje eerst in
   een eigen GitHub-repository en koppel die -- mag allebei).
4. Vul in:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: Free (voor nu prima; let op: de gratis versie
     "slaapt" na inactiviteit en heeft dan ~30-60 sec. opstarttijd bij de
     eerste aanvraag na een stille periode)
5. Voeg bij **Environment Variables** een eigen sleutel toe:
   - Key: `OFFERTE_API_KEY`
   - Value: verzin een lang, willekeurig wachtwoord (bv. via
     https://1password.com/password-generator) en bewaar dit veilig --
     je hebt het in Stap 2 weer nodig.
6. Klik **Create Web Service** en wacht tot de status "Live" is.
7. Je krijgt een URL zoals `https://winter-valley-offerte.onrender.com`.
   Open die URL in je browser -- zie je "OK - offerte-service draait"?
   Dan werkt de service.

---

## Stap 2 -- de stap in Zapier toevoegen

Ga naar jullie bestaande Zap (degene die nu de bevestigingsmail stuurt) en
voeg **tussen** de trigger en de mail-stap een nieuwe stap toe:

1. **App**: Webhooks by Zapier
2. **Event**: POST
3. Instellingen:
   - **URL**: `https://winter-valley-offerte.onrender.com/maak-offerte`
     (jouw eigen Render-URL + `/maak-offerte`)
   - **Payload Type**: json
   - **Data**: koppel hier dezelfde velden die nu al naar de bestaande
     webhook gaan (firstName, lastName, email, guests, date, startTime,
     endTime, durationHours, drink, drinkAddons, noService, package,
     addons, ...) -- dit zijn exact de velden die de funnel al verstuurt.
   - **Headers**: voeg toe `X-Api-Key` met als waarde de geheime sleutel
     uit Stap 1.
4. Test deze stap in Zapier -- je zou nu een PDF-bestand als resultaat
   moeten zien (Zapier herkent de PDF-response automatisch als bestand).
5. Ga naar je mail-stap (Gmail/Outlook) en voeg bij **Attachment** het
   bestand uit deze nieuwe stap toe.
6. Publiceer de Zap.

---

## Als er later iets verandert aan prijzen/logica

Pas `offer_engine.py` (en/of `fill_offerte.py`) aan, en zet de bijgewerkte
bestanden opnieuw op Render (nieuwe versie uploaden, of een `git push` als
je voor de GitHub-koppeling gekozen hebt). Render herstart de service
automatisch -- de URL en de Zapier-koppeling blijven hetzelfde, dus in
Zapier hoef je niets aan te passen.

## Belangrijke aanname om te checken

In `offer_engine.py` staat een aanname over de BTW-verdeling (9% laag /
21% hoog) -- dit is geen fiscaal advies, check dit met de boekhouding
voordat dit echt naar klanten gaat (zie de opmerking boven in dat
bestand).
