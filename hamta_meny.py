#!/usr/bin/env python3
"""
Hämtar veckans skolmatsmeny från Mateo-menyns API och bygger, per plats:
  1) en RSS-feed med hela veckans meny (för en rullande ticker-widget)
  2) en RSS-feed med bara dagens meny (för en statisk/icke-rullande widget)

Vilka platser som ska hämtas styrs av platser.json i samma mapp – lägg till
eller ta bort platser där, ingen ändring i själva scriptet behövs.

Bakomliggande API (hittat i sidans JS-bundle, kräver ingen inloggning):
https://meny-api.mateo.se/api/v1/days/{unit_id}?from=YYYY-MM-DD&to=YYYY-MM-DD
Samma endpoint funkar även för en enskild dag (from och to satta till samma
datum) – men här hämtas hela veckan i ett anrop och dagens post plockas ut
ur samma svar, så vi slår bara i API:et en gång per plats.
"""

import datetime
import json
from email.utils import format_datetime
from xml.sax.saxutils import escape

import requests

# ---- Konfiguration ------------------------------------------------------
PLATSER_FIL = "platser.json"
API_BAS = "https://meny-api.mateo.se/api/v1"
DOCS_MAPP = "docs"
VECKODAGAR = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
# --------------------------------------------------------------------------


def las_platser():
    """Läser listan över skolor/platser från platser.json."""
    with open(PLATSER_FIL, "r", encoding="utf-8") as f:
        return json.load(f)


def hamta_veckans_dagar(unit_id):
    """Hämtar menyn för aktuell vecka (måndag till söndag) för en plats."""
    idag = datetime.date.today()
    mandag = idag - datetime.timedelta(days=idag.weekday())
    sondag = mandag + datetime.timedelta(days=6)

    url = f"{API_BAS}/days/{unit_id}"
    params = {"from": mandag.isoformat(), "to": sondag.isoformat()}
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def formatera_dag(dag):
    """Bygger en läsbar textbeskrivning av en dags måltider."""
    datum = datetime.date.fromisoformat(dag["date"][:10])
    veckodag = VECKODAGAR[datum.weekday()]

    maltider = dag.get("meals") or []
    if not maltider:
        rader = ["Ingen meny inlagd."]
    else:
        rader = [f"{m.get('type', 'Lunch')}: {m.get('name', '').strip()}" for m in maltider]

    titel = f"{veckodag} {datum.strftime('%d/%m')}"
    beskrivning = " | ".join(rader)
    return datum, titel, beskrivning


def rss_item(kalla_url, dag):
    datum, titel, beskrivning = formatera_dag(dag)
    pub_date = datetime.datetime.combine(
        datum, datetime.time(6, 0), tzinfo=datetime.timezone.utc
    )
    guid = f"{kalla_url}#{datum.isoformat()}"
    return f"""    <item>
      <title>{escape(titel)}</title>
      <description>{escape(beskrivning)}</description>
      <link>{escape(kalla_url)}</link>
      <guid isPermaLink="false">{escape(guid)}</guid>
      <pubDate>{format_datetime(pub_date)}</pubDate>
    </item>"""


def bygg_rss(kanaltitel, kalla_url, beskrivning_kanal, dagar):
    nu = datetime.datetime.now(datetime.timezone.utc)
    items_xml = [rss_item(kalla_url, dag) for dag in sorted(dagar, key=lambda d: d["date"])]

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{escape(kanaltitel)}</title>
    <link>{escape(kalla_url)}</link>
    <description>{escape(beskrivning_kanal)}</description>
    <language>sv-se</language>
    <lastBuildDate>{format_datetime(nu)}</lastBuildDate>
{chr(10).join(items_xml)}
  </channel>
</rss>
"""


def plocka_ut_dagens_post(dagar):
    """Plockar ut dagens post ur veckans data. Om ingen post finns för
    dagens datum (t.ex. inte inlagd än) skapas en tom platshållarpost."""
    idag = datetime.date.today().isoformat()
    for dag in dagar:
        if dag["date"][:10] == idag:
            return dag
    return {"date": f"{idag}T00:00:00.000Z", "meals": []}


def bygg_index(platser):
    """Bygger en enkel index.html med länkar till alla feeds, till hjälp
    när man ska hitta rätt url att peka en skärm på."""
    rader = "\n".join(
        f'    <li>{escape(p["namn"])}: '
        f'<a href="{escape(p["fil"])}">Veckomeny</a> · '
        f'<a href="{escape(p["fil_dag"])}">Dagens meny</a></li>'
        for p in platser
    )
    return f"""<!DOCTYPE html>
<html lang="sv">
<head><meta charset="utf-8"><title>Meny-feeds</title></head>
<body>
  <h1>Tillgängliga meny-feeds</h1>
  <ul>
{rader}
  </ul>
</body>
</html>
"""


def main():
    platser = las_platser()

    for plats in platser:
        unit_id = plats["unit_id"]
        namn = plats["namn"]
        kalla_url = plats["kalla_url"]
        fil_vecka = plats["fil"]
        fil_dag = plats["fil_dag"]

        try:
            veckans_dagar = hamta_veckans_dagar(unit_id)
        except requests.RequestException as e:
            print(f"FEL: kunde inte hämta menyn för '{namn}' (unit_id={unit_id}): {e}")
            continue

        # 1) Veckans meny – hela listan, för en rullande ticker.
        vecka_xml = bygg_rss(
            f"Veckans meny – {namn}",
            kalla_url,
            f"Automatiskt hämtad veckomeny för {namn}",
            veckans_dagar,
        )
        with open(f"{DOCS_MAPP}/{fil_vecka}", "w", encoding="utf-8") as f:
            f.write(vecka_xml)

        # 2) Dagens meny – en enda post, för en statisk widget.
        dagens_post = plocka_ut_dagens_post(veckans_dagar)
        dag_xml = bygg_rss(
            f"Dagens meny – {namn}",
            kalla_url,
            f"Automatiskt hämtad dagsmeny för {namn}",
            [dagens_post],
        )
        with open(f"{DOCS_MAPP}/{fil_dag}", "w", encoding="utf-8") as f:
            f.write(dag_xml)

        print(
            f"'{namn}': skrev {len(veckans_dagar)} dagar till {DOCS_MAPP}/{fil_vecka} "
            f"och dagens meny till {DOCS_MAPP}/{fil_dag}"
        )

    with open(f"{DOCS_MAPP}/index.html", "w", encoding="utf-8") as f:
        f.write(bygg_index(platser))


if __name__ == "__main__":
    main()
