# Verkehrsanordnungen Basel-Stadt

Übersicht der Verkehrsanordnungen und der verkehrsrelevanten Baupublikationen aus dem Kantonsblatt Basel-Stadt, nach Datum, Strasse und Massnahme. Gestaltet nach dem CI des Gewerbeverbands Basel-Stadt.

- `build.py` holt die Meldungen der letzten drei Monate über die Schnittstelle des Kantonsblatts und baut `docs/index.html`.
- `.github/workflows/update.yml` startet das jeden Mittwoch und Samstag automatisch (manuell: Actions → «Kantonsblatt aktualisieren» → Run workflow).
- Die Seite wird über GitHub Pages aus dem Ordner `docs` veröffentlicht.

Quelle: Kantonsblatt Basel-Stadt. Rechtsverbindlich ist allein die Publikation im Kantonsblatt.
