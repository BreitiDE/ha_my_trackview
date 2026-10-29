# My TrackView

[🇩🇪 Deutsch](#deutsch) · [🇬🇧 English](#english)

## Deutsch

### Einrichtung

Nach dem Start erscheint **My TrackView** in der Seitenleiste. Alle Einstellungen werden in der App
unter **Einstellungen** vorgenommen; in der App-Konfiguration von Home Assistant gibt es nur den Log-Level.

| Einstellung | Standard | Bedeutung |
|---|---|---|
| Pfad zur Logdatei | `/config/gpsdata.log` | CSV-Datei mit `date,latitude,longitude,altitude,speed`. Der Home-Assistant-Ordner `/config` ist nur lesend eingebunden. |
| Zeitstempel in der Datei | UTC | Gilt für Zeitstempel ohne Zeitzone. Stimmen die Uhrzeiten nicht, auf „Lokalzeit“ stellen und neu aufbauen. |
| Automatisch einlesen alle | 5 min | 0 = nur manuell über „Jetzt einlesen“. |
| Breitengrad / Längengrad / Radius | – / – / 200 m | Heimstandort. Abfahrt und Rückkehr werden an diesem Kreis erkannt. |
| Punkte zum Bestätigen der Abfahrt | 5 | Punkte in Folge außerhalb des Radius, bevor eine Abfahrt zählt. |
| Neue Etappe nach Pause ab | 30 min | Lücke im Log, ab der eine neue Etappe beginnt. |
| Mindeststrecke einer Reise | 1 km | Kürzere Fahrten werden ignoriert. |
| Ausreißer-Filter | 250 km/h | Punkte mit unplausiblem Sprung werden verworfen. |
| Sprung = fehlende Daten ab | 5 km | Springt die Position nach einer Pause weiter, wird der Abschnitt „nicht zugeordnet“. |
| Kachel-Server | OpenStreetMap | URL-Vorlage mit `{z}`, `{x}`, `{y}`. |
| Kacheln aktualisieren nach | 7 Tagen | Danach wird jede Kachel beim Server neu geprüft (ETag), ohne Internet dient der Cache. |
| Maximale Cache-Größe | 500 MB | Selten genutzte Kacheln werden zuerst gelöscht. |

### Wie Reisen erkannt werden

1. Liegt das Fahrzeug im Heimradius, ist es **zu Hause**.
2. Liegen mehrere Punkte in Folge außerhalb, beginnt eine **Reise** (der letzte Punkt zu Hause wird als Startpunkt übernommen).
3. Lücken im Log (das GPS loggt im Stand nicht) trennen **Etappen**.
4. Der erste Punkt wieder im Heimradius beendet die Reise.
5. Ist das Fahrzeug noch unterwegs, erscheint die Reise als **unterwegs** und wird bei jedem Import fortgeschrieben.

**Nicht zugeordnet** werden Abschnitte, die außerhalb des Heimradius beginnen (z. B. Logdatei startet unterwegs)
oder bei denen nach einer Pause die Position springt (Daten fehlen). Diese können übernommen, zusammengeführt,
geteilt oder gelöscht werden.

### Import, Abgleich, Neuaufbau

- **Jetzt einlesen** liest nur den neuen Teil der Datei (ab der letzten erkannten Reise). Eine unvollständige letzte Zeile wird beim nächsten Mal gelesen.
- **Neu einlesen & abgleichen** liest die ganze Datei: fehlende Reisen werden ergänzt, vorhandene behalten Farbe und Namen. Optional werden gelöschte Reisen wiederhergestellt.
- **Komplett neu aufbauen** löscht alle Einträge und erkennt sie neu – nötig nach geänderten Erkennungs-Einstellungen oder einer ausgetauschten Datei. Vorher wird automatisch ein Backup unter `/data/backups` angelegt (die letzten 5 bleiben erhalten).

Wird die GPS-Datei ersetzt oder rotiert, erkennt die App das und setzt anhand des Zeitstempels fort.

### Daten & Datenschutz

- Datenbank: `/data/trackview.db` (SQLite) – ist in Home-Assistant-Backups enthalten.
- Kachel-Cache und Miniaturen sind von Backups ausgenommen.
- Die App ist nur über Home Assistant (Ingress) erreichbar und liest die GPS-Datei ausschließlich.
- Kartenkacheln werden mit eigenem User-Agent beim Kachel-Server abgerufen. Bitte die
  [Nutzungsbedingungen von OpenStreetMap](https://operations.osmfoundation.org/policies/tiles/) beachten.

## English

### Setup

After starting, **My TrackView** shows up in the sidebar. All settings live in the app's **Settings**
page; the Home Assistant app configuration only contains the log level.

| Setting | Default | Meaning |
|---|---|---|
| Path to log file | `/config/gpsdata.log` | CSV file with `date,latitude,longitude,altitude,speed`. Home Assistant's `/config` folder is mounted read-only. |
| Timestamps in the file | UTC | Applies to timestamps without a time zone. If times look wrong, switch to “local time” and rebuild. |
| Import automatically every | 5 min | 0 = manual only via “Import now”. |
| Latitude / longitude / radius | – / – / 200 m | Home location. Departure and return are detected at this circle. |
| Points to confirm departure | 5 | Consecutive points outside the radius before a departure counts. |
| New stage after a pause of | 30 min | Gap in the log that starts a new stage. |
| Minimum trip distance | 1 km | Shorter drives are ignored. |
| Outlier filter | 250 km/h | Points implying an implausible jump are discarded. |
| Jump = missing data from | 5 km | If the position jumps further after a pause, the section becomes “unassigned”. |
| Tile server | OpenStreetMap | URL template with `{z}`, `{x}`, `{y}`. |
| Refresh tiles after | 7 days | After that each tile is revalidated with the server (ETag); offline the cache is used. |
| Maximum cache size | 500 MB | Least recently used tiles are removed first. |

### How trips are detected

1. Inside the home radius the vehicle is **at home**.
2. Several consecutive points outside start a **trip** (the last point at home becomes the starting point).
3. Gaps in the log (the GPS does not log while parked) separate **stages**.
4. The first point back inside the home radius ends the trip.
5. While still on the road, the trip is shown as **on the road** and extended on every import.

Sections that start outside the home radius (e.g. the log file starts on the road) or where the position jumps
after a pause (missing data) become **unassigned**. They can be accepted, merged, split or deleted.

### Import, reconcile, rebuild

- **Import now** reads only the new part of the file (from the last detected trip). An incomplete last line is read next time.
- **Re-read & reconcile** reads the whole file: missing trips are added, existing ones keep colour and name. Optionally deleted trips are restored.
- **Rebuild from scratch** deletes all entries and detects them again – needed after changing detection settings or replacing the file. A backup is created first in `/data/backups` (the last 5 are kept).

If the GPS file is replaced or rotated, the app notices and continues based on the timestamp.

### Data & privacy

- Database: `/data/trackview.db` (SQLite) – included in Home Assistant backups.
- Tile cache and thumbnails are excluded from backups.
- The app is only reachable through Home Assistant (ingress) and only reads the GPS file.
- Map tiles are requested with a dedicated user agent. Please respect the
  [OpenStreetMap tile usage policy](https://operations.osmfoundation.org/policies/tiles/).
