# Changelog

## 1.1.0 – 2026-10-29

- Kartenansicht: Reise, Status und Bedienelemente stehen oben, die Kennzahlen-Zeile darunter direkt über der Karte
- Details-Knopf blendet Name und Etappenliste jetzt auf allen Bildschirmgrößen ein/aus (Einstellung wird gemerkt)
- Ausgewählte Etappe (Klick in Liste oder Karte) liegt oben, wird hervorgehoben, die übrigen abgeblendet; gleiches für Reisen in der Mehrfachansicht
- Log-Seite: „Log leeren“
- PayPal-Spendenknopf neben der GPS-Datei-Anzeige
- Startwarnung behoben: `bashio::app.version` statt `bashio::addon.version`

## 1.0.0 – 2026-10-29

Erste Version / first release.

- Reiseerkennung mit Heimstandort, Radius und Abfahrts-Hysterese; Etappen anhand von Pausen
- Inkrementeller Import mit Wiederaufnahme an der letzten Reise; erkennt ersetzte/rotierte Dateien
- Reisen-Liste mit Mini-Karte, Sortierung (Datum, Dauer, Fahrzeit, Kilometer), Seitengröße und Seitennavigation
- Kartenansicht: auf Track gezoomt, Farbwahl, Etappen einfärben, Name, Etappenliste, PDF-Export
- Mehrfachauswahl: gemeinsame Kartenansicht, gemeinsamer PDF-Export, Zusammenführen, Löschen
- „Nicht zugeordnet“: übernehmen, mit vorheriger/nächster zusammenführen, teilen, löschen
- Papierkorb mit Wiederherstellen und endgültigem Löschen
- Neu einlesen & abgleichen, Komplett neu aufbauen mit automatischem DB-Backup
- OSM-Kachel-Proxy mit Cache, Aktualisierung per ETag, Offline-Betrieb
- Einstellungsseite mit Karte für den Heimstandort und Dateiprüfung
- Log-Seite, Anleitung, Oberfläche Deutsch/Englisch, helles und dunkles Design
