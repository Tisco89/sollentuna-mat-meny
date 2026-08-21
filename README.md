# Meny-RSS för skärm (flera skolor/platser)

Hämtar automatiskt skolmatsmenyn för en eller flera skolor från
meny.mateo.se och publicerar, per skola, två RSS-feeds som en skärm utan
webbläsare kan läsa:

- `docs/feed-<id>.xml` — hela veckans meny, tänkt för en rullande
  ticker-widget.
- `docs/feed-<id>-idag.xml` — bara dagens meny (en enda post), tänkt för en
  statisk/icke-rullande widget på resten av skärmen.

## Så funkar det

`hamta_meny.py` läser listan över skolor från `platser.json`, och för varje
skola anropar den det bakomliggande API:et
(`https://meny-api.mateo.se/api/v1/days/{unit_id}?from=...&to=...`) som
webbsidan meny.mateo.se själv använder. Den hämtar hela veckan i ett enda
anrop, bygger veckofeeden av den, och plockar sedan ut dagens post ur samma
svar till dagsfeeden (så det görs bara ett API-anrop per skola, inte två).
Den skriver också en `docs/index.html` med länkar till samtliga feeds
(både vecko- och dagsvarianten), så det är enkelt att hitta rätt url.

GitHub Actions-workflowen `.github/workflows/meny.yml` körs varje
vardagsmorgon, kör scriptet för samtliga skolor i listan, och
committar/pushar de uppdaterade filerna till repot.

## Lägga till eller ta bort en skola

Öppna `platser.json` och lägg till en rad per skola, t.ex.:

```json
[
  {
    "unit_id": 936,
    "namn": "Sollentuna – Skola A",
    "kalla_url": "https://meny.mateo.se/sollentuna/936",
    "fil": "feed-936.xml",
    "fil_dag": "feed-936-idag.xml"
  },
  {
    "unit_id": 1042,
    "namn": "Sollentuna – Skola B",
    "kalla_url": "https://meny.mateo.se/sollentuna/1042",
    "fil": "feed-1042.xml",
    "fil_dag": "feed-1042-idag.xml"
  }
]
```

- **unit_id** = id:et i slutet av skolans url på meny.mateo.se
  (t.ex. `.../sollentuna/1042` → `1042`).
- **namn** = fritt visningsnamn, används i feedens titel.
- **kalla_url** = länken till skolans egen menysida (visas som `<link>` i
  RSS-posterna).
- **fil** = filnamnet för veckofeeden i `docs/`-mappen (ticker-widgeten).
- **fil_dag** = filnamnet för dagsfeeden i `docs/`-mappen (den statiska
  widgeten).

Ingen kodändring behövs – nästa gång workflown körs (eller om du kör den
manuellt) genereras/uppdateras feeden för den nya skolan automatiskt.

## Uppsättning

1. Skapa ett nytt (eller använd ett befintligt) repo på GitHub och lägg in
   alla filer i det här paketet.
2. Gå till repots **Settings → Pages** och sätt "Source" till
   **Deploy from a branch**, branch `main`, mapp **`/docs`**. Spara.
3. Efter några minuter är sidan tillgänglig på:
   `https://<ditt-github-konto>.github.io/<repo-namn>/`
   och respektive skolas feeds på
   `https://<ditt-github-konto>.github.io/<repo-namn>/feed-<id>.xml` (vecka)
   och
   `https://<ditt-github-konto>.github.io/<repo-namn>/feed-<id>-idag.xml` (dag)
   (öppna gärna rot-url:en först – där listas alla feeds med länkar).
4. Peka skärmens ticker-widget (rullande, längst ner) på veckofeeden, och
   den statiska widgeten (resten av skärmen) på dagsfeeden – ställ in den
   sistnämnda som "statisk"/icke-rullande i skärmens egna inställningar.
5. (Valfritt) Gå till fliken **Actions** i repot och kör workflowen manuellt
   en gång ("Run workflow") för att generera feederna direkt, istället för
   att vänta till nästa schemalagda körning.

## Att justera

- **Skolor** — se avsnittet ovan, styrs helt av `platser.json`.
- **cron-tiden** i `meny.yml` — GitHub Actions cron är alltid UTC. Standard är
  satt till 05:00 svensk sommartid (03:00 UTC). Justera vid vintertid eller
  om ni vill ha en annan tid.
- **Innehåll per dag** — just nu listas alla måltider (Lunch 1, Lunch 2 osv)
  separerade med " | ". Ändra `formatera_dag()` i `hamta_meny.py` om ni vill
  ha ett annat format.

## Att tänka på

- Länkarna är helt publika (ingen inloggning eller repo-access krävs för att
  läsa dem) – precis som vilken annan hemsida som helst. Lägg inte in något
  känsligt i `platser.json` eller feederna.
- Om ett API-anrop för en skola misslyckas (t.ex. fel unit_id) hoppar
  scriptet bara över den skolan och fortsätter med resten – kolla
  Actions-loggen om en feed slutar uppdateras.
- Om repot inte har någon annan aktivitet stänger GitHub av schemalagda
  workflows efter 60 dagars inaktivitet. Eftersom workflowen själv committar
  ändringar varje vardag räknas det som aktivitet, så detta ska normalt inte
  bli ett problem.
- "Dagens meny" avgörs av vilket datum det är enligt GitHub Actions-maskinens
  klocka (UTC) när scriptet körs. Med standardschemat (03:00 UTC = 05:00
  svensk sommartid) är det inget problem. Om du kör workflowen manuellt sent
  på kvällen svensk tid (efter kl 02 på natten UTC, dvs sent svenskt
  kvällspass) skulle "dagens meny" i teorin kunna hämta fel dag — i praktiken
  ett icke-problem så länge den bara körs på morgonen.
