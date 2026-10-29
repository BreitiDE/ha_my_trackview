# My TrackView – Home Assistant App

![My TrackView](ha_my_trackview/logo.png)

[🇩🇪 Deutsch](#deutsch) · [🇬🇧 English](#english)

---

## Deutsch

**My TrackView** liest die GPS-Logdatei deines Wohnmobils und zeigt jede Reise als Track auf einer
OpenStreetMap-Karte – direkt in der Seitenleiste von Home Assistant.

- Erkennt Reisen automatisch: **Abfahrt** aus dem Heimradius → Aufenthalte/Weiterfahrt → **Rückkehr**
- Teilt Reisen anhand von Pausen in **Etappen** (das GPS loggt im Stand nicht)
- Liste mit Datum, Start, Ende, Dauer, Fahrzeit und Kilometern; sortierbar, 10/25/50/100/Alle pro Seite
- Mini-Karte je Reise, Kartenansicht mit Farbwahl und Etappen-Einfärbung, **PDF-Export**
- Mehrere Reisen auswählen und gemeinsam auf einer Karte anzeigen
- Bearbeitungsliste für **nicht zuordenbare** Abschnitte (übernehmen, zusammenführen, teilen, löschen)
- **Papierkorb**, Neu einlesen & Abgleichen, kompletter Neuaufbau mit automatischem Backup
- Inkrementeller Import: nur neue Daten der Datei werden gelesen
- Kartenkacheln mit Cache für unterwegs (LTE / Funkloch), regelmäßige Aktualisierung
- SQLite-Datenbank, Oberfläche auf Deutsch und Englisch

### Installation

1. In Home Assistant **Einstellungen → Apps → App Store** öffnen.
2. Oben rechts **⋮ → Repositories** wählen und hinzufügen:
   ```
   https://github.com/BreitiDE/ha_my_trackview
   ```
3. **My TrackView** suchen, installieren und starten. „In Seitenleiste anzeigen“ aktivieren.
4. In der App unter **Einstellungen** GPS-Datei und Heimstandort eintragen, speichern, **Jetzt einlesen**.

Details: siehe [Dokumentation](ha_my_trackview/DOCS.md).

### GPS-Dateiformat

CSV, eine Zeile pro Messpunkt, optional mit Kopfzeile:

```
date,latitude,longitude,altitude,speed
2026-10-18T15:02:01,51.47258759,6.60797644,24,39
```

Geschwindigkeit in km/h. Zeitstempel ISO 8601 (mit oder ohne Zeitzone) oder Unix-Zeit.

---

## English

**My TrackView** reads your motorhome's GPS log file and shows every trip as a track on an
OpenStreetMap map – right in the Home Assistant sidebar.

- Detects trips automatically: **departure** from the home radius → stays/onward travel → **return**
- Splits trips into **stages** at pauses (the GPS does not log while parked)
- List with date, start, end, duration, driving time and distance; sortable, 10/25/50/100/all per page
- Mini map per trip, map view with colour picker and stage colouring, **PDF export**
- Select several trips and show them together on one map
- Review list for **unassigned** sections (accept, merge, split, delete)
- **Trash**, re-read & reconcile, full rebuild with automatic backup
- Incremental import: only new data in the file is read
- Map tiles cached for life on the road (LTE / no signal), refreshed regularly
- SQLite database, user interface in German and English

### Installation

1. In Home Assistant open **Settings → Apps → App store**.
2. Click **⋮ → Repositories** (top right) and add:
   ```
   https://github.com/BreitiDE/ha_my_trackview
   ```
3. Find **My TrackView**, install and start it. Enable “Show in sidebar”.
4. In the app's **Settings**, enter the GPS file and home location, save, then **Import now**.

Details: see the [documentation](ha_my_trackview/DOCS.md).

### GPS file format

CSV, one line per fix, header optional:

```
date,latitude,longitude,altitude,speed
2026-10-18T15:02:01,51.47258759,6.60797644,24,39
```

Speed in km/h. Timestamps ISO 8601 (with or without time zone) or Unix time.

---

Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright). License: MIT.
