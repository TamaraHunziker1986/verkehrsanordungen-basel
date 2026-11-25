# Verkehrsanordnungen Basel-Stadt

Übersicht der Verkehrsanordnungen und der verkehrsrelevanten Bau- und Allmendgesuche aus dem Kantonsblatt Basel-Stadt, nach Datum, Strasse und Massnahme. Gestaltet nach dem CI des Gewerbeverbands Basel-Stadt.

## Was drin ist

- Alle Verkehrsanordnungen ab dem 1. Januar 2026 (Rubrik VE-BS40).
- Strassenbau-Publikationen (VE-BS10).
- Alle Bau- und Nutzungsgesuche auf Allmend (BP-BS20), ausser Boulevard-Gastronomie.
- Baupublikationen (BP-BS10), wenn es um Baumfällungen der öffentlichen Hand, Parkplätze, Garagen, Einstellhallen, Ladestationen, Strassenlinien oder Strassenraum geht.
- Die Rubrik «Weitere verkehrspolizeiliche Bekanntmachung» (VE-BS50) wird abgefragt. Verwertungsverfügungen für abgestellte Fahrzeuge werden bewusst weggelassen, weil sie Personendaten enthalten und den Verkehr nicht betreffen. Bis November 2026 enthielt die Rubrik nur solche Verfügungen.

## Bekannte Lücken

- 11. Juni bis 7. August 2026: keine Verkehrsanordnungen. Das Kantonsblatt hat in dieser Zeit keine veröffentlicht; das Open-Data-Archiv data.bs.ch (Datensatz 100352) zeigt ebenfalls keine.
- Baupublikationen und Allmendgesuche vor August 2026: Das Kantonsblatt nimmt sie nach Ablauf der Einsprachefrist vom Netz, sie sind über die Schnittstelle nicht mehr abrufbar.

## Wie es läuft

- `build.py` holt die Meldungen über die Schnittstelle des Kantonsblatts und baut `docs/index.html` und `docs/data.json`. Einträge, die das Kantonsblatt vom Netz nimmt, werden aus `docs/data.json` übernommen und bleiben erhalten.
- `.github/workflows/update.yml` startet das jeden Mittwoch und Samstag um 07:17 und 11:17 Uhr (Schweizer Winterzeit). Jeder Lauf schreibt `docs/letzter-lauf.txt`, damit GitHub den Zeitplan nicht wegen Inaktivität abschaltet. Schlägt ein Lauf fehl, schickt GitHub eine E-Mail an die Kontoinhaberin.
- Manuell starten: Actions, «Kantonsblatt aktualisieren», «Run workflow».
- Die Seite wird über GitHub Pages aus dem Ordner `docs` veröffentlicht.

Quelle: Kantonsblatt Basel-Stadt. Rechtsverbindlich ist allein die Publikation im Kantonsblatt.
