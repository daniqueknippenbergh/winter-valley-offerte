# -*- coding: utf-8 -*-
"""
offer_engine.py
================
Reken- en planninglogica voor de Winter Valley offerte-generator.

Dit bestand is een 1-op-1 Python-vertaling van de prijs- en tijdlogica die
al in de funnel (Nwinter-valley-funnel.html) staat, zodat het bedrag dat de
klant in de funnel zag overeenkomt met wat er straks in de formele offerte-
PDF staat.

Input: een "lead"-dict met precies dezelfde velden die de funnel nu al naar
Zapier stuurt (zie sendLeadToSEM() in de funnel). Output: een platte dict
met alle waarden die in de offerte-PDF moeten worden ingevuld.

LET OP -- aannames die je moet nakijken voordat dit live gaat:
1. BTW-verdeling (9% laag / 21% hoog): er is een redelijke aanname
   gemaakt (zie VAT_LOW_CATEGORIES hieronder). Dit is geen fiscaal advies
   -- check de juiste verdeling met jullie boekhouder/accountant voordat
   dit naar klanten gaat.
"""

from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# WV_CONFIG -- 1-op-1 gekopieerd uit de funnel (zelfde bedragen/staffels)
# ---------------------------------------------------------------------------

ROOMS = [
    {"id": "wintertuin",        "name": "Wintertuin",     "min": 50,  "max": 150,  "price": 1750},
    {"id": "wunderbar",         "name": "Wunderbar",      "min": 151, "max": 300,  "price": 2500},
    {"id": "mainstage",         "name": "Main stage",     "min": 301, "max": 599,  "price": 7500},
    {"id": "heelwintervalley",  "name": "Winter Valley",  "min": 600, "max": 3000, "price": 12500},
]

DRINK_PRICE_PER_PERSON_PER_HOUR = {
    "basis": {
        1: 13.45, 1.5: 16.55, 2: 20.15, 2.5: 23.30, 3: 26.90, 3.5: 30.00,
        4: 33.15, 4.5: 36.25, 5: 39.35, 5.5: 42.45, 6: 45.55, 6.5: 48.65,
        7: 51.75, 7.5: 54.85, 8: 57.95,
    },
    "compleet": {
        1: 17.90, 1.5: 21.00, 2: 24.60, 2.5: 27.75, 3: 31.35, 3.5: 34.45,
        4: 37.60, 4.5: 40.70, 5: 43.80, 5.5: 46.90, 6: 50.00, 6.5: 53.10,
        7: 56.20, 7.5: 59.30, 8: 62.40,
    },
}
DRINK_NAMES = {"basis": "Drank basis", "compleet": "Drank compleet"}

DRINK_EXTRAS = {
    "prosecco": {"name": "Welkomsglas prosecco", "price": 4.65, "type": "perPerson"},
}

DISCOUNT_TIERS = [
    {"min": 0,    "uitserveren": 0,  "halenBar": 12},
    {"min": 1000, "uitserveren": 3,  "halenBar": 15},
    {"min": 1250, "uitserveren": 4,  "halenBar": 16},
    {"min": 1500, "uitserveren": 5,  "halenBar": 17},
    {"min": 1750, "uitserveren": 6,  "halenBar": 18},
    {"min": 2000, "uitserveren": 7,  "halenBar": 19},
    {"min": 2250, "uitserveren": 8,  "halenBar": 20},
    {"min": 2500, "uitserveren": 9,  "halenBar": 21},
    {"min": 2750, "uitserveren": 10, "halenBar": 22},
    {"min": 3000, "uitserveren": 10, "halenBar": 22},
]

FOOD_TIERS = [
    {"min": 0,    "pricePerPerson": 38.95},
    {"min": 1000, "pricePerPerson": 36.95},
    {"min": 1250, "pricePerPerson": 35.40},
    {"min": 1500, "pricePerPerson": 33.85},
]
FOOD_HOURS = 2.5
FOOD_NAME = "Foodcorners"

OTHER_COSTS_PER_PERSON = [
    {"name": "Bemande garderobe", "price": 1.0},
    {"name": "Techniek",         "price": 0.0},
    {"name": "Parkeren",         "price": 0.0},
]
OTHER_COSTS_HOURLY = [
    {"name": "Event manager", "perHour": 65, "flat": 195},
    {"name": "F&B manager",   "perHour": 65, "flat": 195},
]

SANITAIR_MIN_GUESTS = 200
SANITAIR_PRICE_PER_UUR = 16.25

# Addons (entertainment) -- naam + type, voor in de ENTERTAINMENT-sectie.
# Prijs blijft altijd "op aanvraag" in de offerte, dus de bedragen hier
# worden niet gebruikt voor de offerte-PDF, alleen de namen.
ADDON_NAMES = {
    "skigondel": "Ski gondel photobooth",
    "snowboardrodeo": "Snowboard rodeo",
    "video360": "360 graden video",
    "spijkerslaan": "Spijker slaan",
    "sneeuwbalgooien": "Sneeuwbal gooien",
    "vrskisim": "VR ski simulator",
    "karikaturist": "Karikaturist",
    "visagist": "Winterse glittermeid",
    "allrounddj": "Allround DJ",
}

# Welke kostenposten vallen onder het lage (9%) BTW-tarief.
# AANNAME -- check dit met de boekhouding! Standaard Nederlandse regel is
# vaak: eten + niet-alcoholische dranken op locatie = 9%, locatiehuur,
# personeel en alcoholische drank = 21%. Hier is dat als uitgangspunt
# genomen, met de volledige Drankarrangement-regel toch onder 21% omdat
# het arrangement alcohol bevat.
VAT_LOW_RATE = 0.09
VAT_HIGH_RATE = 0.21
VAT_LOW_LINE_KEYS = {"foodcorners"}  # alleen food-regel onder 9%


def round2(value):
    return round(value + 1e-9, 2)


def get_drink_price_per_person(drink_id, hours):
    if not drink_id:
        return 0.0
    rounded_hours = round(hours * 2) / 2
    table = DRINK_PRICE_PER_PERSON_PER_HOUR.get(drink_id, {})
    return table.get(rounded_hours, 0.0)


def get_discount_tier(guests):
    match = DISCOUNT_TIERS[0]
    for tier in DISCOUNT_TIERS:
        if guests >= tier["min"]:
            match = tier
    return match


def get_food_price_per_person(guests):
    match = FOOD_TIERS[0]
    for tier in FOOD_TIERS:
        if guests >= tier["min"]:
            match = tier
    return match["pricePerPerson"]


def assign_room(guests):
    for room in ROOMS:
        if room["min"] <= guests <= room["max"]:
            return room
    return None


def parse_time_to_minutes(value):
    h, m = value.split(":")
    return int(h) * 60 + int(m)


def minutes_to_time(total_minutes):
    total_minutes = total_minutes % (24 * 60)
    h = total_minutes // 60
    m = total_minutes % 60
    return "%02d:%02d" % (h, m)


def compute_schedule(start_time, end_time, has_food):
    """Bouwt de PROGRAMMA-regels op basis van start-/eindtijd en of er food
    gekozen is. Spiegelt de regel uit het verzoek:
      - Ontvangst gasten = starttijd
      - Entertainment geopend = starttijd - eindtijd (hele duur)
      - (indien food) Food stands geopend = starttijd, 2,5 uur lang
      - (indien food) Late night snacken = 1 uur, tot 30 min voor vertrek
      - Vertrek gasten = eindtijd
    """
    start_min = parse_time_to_minutes(start_time)
    end_min = parse_time_to_minutes(end_time)
    duration_min = end_min - start_min
    if duration_min <= 0:
        duration_min += 24 * 60  # tijd loopt door middernacht

    rows = []
    rows.append(("Ontvangst gasten", minutes_to_time(start_min)))
    rows.append(("Entertainment geopend",
                  minutes_to_time(start_min) + " - " + minutes_to_time(start_min + duration_min)))

    if has_food:
        food_end = start_min + int(FOOD_HOURS * 60)
        rows.append(("Food stands geopend",
                      minutes_to_time(start_min) + " - " + minutes_to_time(food_end)))
        snack_end = start_min + duration_min - 30
        snack_start = snack_end - 60
        rows.append(("Late night snacken",
                      minutes_to_time(snack_start) + " - " + minutes_to_time(snack_end)))

    rows.append(("Vertrek gasten", minutes_to_time(start_min + duration_min)))
    return rows


def format_price(amount):
    """Formatteert als Nederlands bedrag zonder euroteken, bv. 1.234,56."""
    s = "{:,.2f}".format(amount)
    s = s.replace(",", "TMP").replace(".", ",").replace("TMP", ".")
    return s


DUTCH_MONTHS = [
    "januari", "februari", "maart", "april", "mei", "juni",
    "juli", "augustus", "september", "oktober", "november", "december",
]


def format_date_nl(iso_date):
    """'2026-12-13' -> '13 december 2026'."""
    if not iso_date:
        return ""
    y, m, d = iso_date.split("-")
    return "%d %s %s" % (int(d), DUTCH_MONTHS[int(m) - 1], y)


def parse_bool(value):
    """Robuuste boolean-check. Belangrijk omdat Zapier/formulieren een
    boolean soms als de TEKST 'false' doorgeven -- en bool('false') is in
    Python gewoon True (niet-lege string), dus dat los je hiermee op."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ("true", "1", "yes", "ja", "on")


def parse_list(value):
    """Maakt van een eventuele JSON-tekst (bv. '["a","b"]', zoals de
    funnel arrays nu doorstuurt naar Zapier) weer een echte Python-lijst.
    Werkt ook als er al een echte lijst binnenkomt."""
    if not value:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            import json
            parsed = json.loads(text)
            return parsed if isinstance(parsed, list) else [parsed]
        except (ValueError, TypeError):
            # Geen geldige JSON -- behandel als komma-gescheiden tekst
            return [v.strip() for v in text.split(",") if v.strip()]
    return [value]


def hours_between(start_time, end_time):
    """Berekent het aantal uren tussen starttijd en eindtijd (HH:MM), met
    ondersteuning voor evenementen die over middernacht heen lopen."""
    start_min = parse_time_to_minutes(start_time)
    end_min = parse_time_to_minutes(end_time)
    diff = end_min - start_min
    if diff <= 0:
        diff += 24 * 60
    return round(diff / 60.0, 2)


def compute_breakdown(lead):
    """Hoofdofunctie: neemt het lead-object (zoals nu naar Zapier gaat) en
    geeft een platte dict terug met alle waarden die de offerte-PDF nodig
    heeft."""

    guests = int(float(lead.get("guests") or 0))
    start_time = lead.get("startTime") or "18:00"
    end_time = lead.get("endTime") or "00:00"
    duration_hours = float(lead.get("durationHours") or 0) or hours_between(start_time, end_time)

    drink_id = lead.get("drink") or None
    package = lead.get("package") or None
    has_food = package == "foodbasis"
    drink_addons = parse_list(lead.get("drinkAddons"))
    addons = parse_list(lead.get("addons"))
    no_service = parse_bool(lead.get("noService"))

    room = assign_room(guests)
    room_price = room["price"] if room else 0.0
    room_pp = round2(room_price / guests) if guests else 0.0

    drink_pp = get_drink_price_per_person(drink_id, duration_hours)
    drink_original_total = round2(drink_pp * guests)
    tier = get_discount_tier(guests)
    discount_pct = tier["halenBar"] if no_service else tier["uitserveren"]
    drink_total = round2(drink_original_total * (1 - discount_pct / 100))
    drink_pp_discounted = round2(drink_pp * (1 - discount_pct / 100))

    food_pp = get_food_price_per_person(guests) if has_food else 0.0
    food_total = round2(food_pp * guests) if has_food else 0.0

    extras_total = 0.0
    extras_lines = []
    for extra_id in drink_addons:
        extra = DRINK_EXTRAS.get(extra_id)
        if not extra:
            continue
        is_pp = extra["type"] == "perPerson"
        amt = extra["price"] * guests if is_pp else extra["price"]
        extras_total += amt
        extras_lines.append({
            "name": extra["name"],
            "amount": round2(amt),
            "qty": guests if is_pp else 1,
            "pricePerPerson": extra["price"] if is_pp else None,
        })

    garderobe_pp = next(i["price"] for i in OTHER_COSTS_PER_PERSON if i["name"] == "Bemande garderobe")
    garderobe_total = round2(garderobe_pp * guests)

    event_manager_total = round2(65 * duration_hours + 195)
    fb_manager_total = round2(65 * duration_hours + 195)

    sanitair_included = guests >= SANITAIR_MIN_GUESTS
    sanitair_total = round2(SANITAIR_PRICE_PER_UUR * duration_hours) if sanitair_included else 0.0

    entertainment_rows = [ADDON_NAMES.get(a, a) for a in addons]

    eindschoonmaak = "Nader te bepalen"  # blijft altijd nacalculatie, niet automatisch in te vullen

    # ---- Totaal ----
    subtotal_low = food_total if has_food else 0.0
    subtotal_high = (
        room_price + garderobe_total + drink_total + extras_total
        + event_manager_total + fb_manager_total + sanitair_total
    )
    subtotal_excl_btw = round2(subtotal_low + subtotal_high)
    btw_laag = round2(subtotal_low * VAT_LOW_RATE)
    btw_hoog = round2(subtotal_high * VAT_HIGH_RATE)
    totaal_incl_btw = round2(subtotal_excl_btw + btw_laag + btw_hoog)

    schedule = compute_schedule(start_time, end_time, has_food)

    return {
        "opdrachtgever": (lead.get("firstName", "") + " " + lead.get("lastName", "")).strip(),
        "datum": format_date_nl(lead.get("date")),
        "tijd": "%s - %s" % (start_time, end_time),
        "aantal_gasten": guests,
        "schedule": schedule,

        "room_name": room["name"] if room else None,
        "room_price": room_price,
        "room_pp": room_pp,

        "garderobe_pp": garderobe_pp,
        "garderobe_total": garderobe_total,
        "eindschoonmaak": eindschoonmaak,

        "has_food": has_food,
        "food_pp": food_pp,
        "food_total": food_total,

        "drink_name": DRINK_NAMES.get(drink_id, ""),
        "drink_pp": drink_pp_discounted,
        "drink_total": drink_total,
        "discount_pct": discount_pct,
        "extras_lines": extras_lines,

        "event_manager_total": event_manager_total,
        "fb_manager_total": fb_manager_total,
        "sanitair_included": sanitair_included,
        "sanitair_total": sanitair_total,

        "entertainment_rows": entertainment_rows,

        "subtotal_excl_btw": subtotal_excl_btw,
        "btw_laag": btw_laag,
        "btw_hoog": btw_hoog,
        "totaal_incl_btw": totaal_incl_btw,
    }


if __name__ == "__main__":
    import json
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
    print(json.dumps(compute_breakdown(example_lead), indent=2, ensure_ascii=False))
