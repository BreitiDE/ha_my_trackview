/* My TrackView – Übersetzungen / translations */
window.I18N = {
de: {
  nav_trips: "Reisen", nav_unassigned: "Nicht zugeordnet", nav_trash: "Papierkorb",
  nav_settings: "Einstellungen", nav_log: "Log", nav_help: "Anleitung",
  st_auto: "Auto-Import aktiv", st_manual: "Nur manueller Import", st_importing: "Import läuft …",
  st_offline: "Karten offline (Cache)", st_error: "Letzter Import fehlgeschlagen",
  btn_import_now: "Jetzt einlesen", btn_reimport: "Neu einlesen & abgleichen",
  btn_show_selection: "Auswahl anzeigen", gps_file: "GPS-Datei", change: "ändern",
  s_trips: "Reisen", s_trips_sub: "letzte {date}", s_trips_none: "noch keine",
  s_running: "Unterwegs", s_running_yes: "Ja", s_running_no: "Nein", s_running_since: "seit {date}",
  s_home: "zu Hause", s_distance: "Strecke gesamt", s_avg: "Ø {v} pro Reise",
  s_driving: "Fahrzeit gesamt", s_stages: "{n} Etappen", s_unassigned: "Nicht zugeordnet",
  s_unassigned_sub: "zur Bearbeitung", s_unassigned_none: "alles zugeordnet", s_last_import: "Letzter Import",
  s_never: "noch nie", s_new: "{n} neu", s_failed: "fehlgeschlagen",
  trips_title: "Reisen", trips_sub: "Abfahrt und Rückkehr am Heimstandort",
  per_page: "Pro Seite", all: "Alle",
  col_date: "Datum", col_start: "Start", col_end: "Ende", col_duration: "Dauer", col_driving: "Fahrzeit",
  col_distance: "Kilometer", col_distance_mi: "Meilen", col_stages: "Etappen", col_actions: "Aktionen", col_reason: "Grund",
  col_deleted: "Gelöscht am", col_status: "Status",
  running: "unterwegs", page_info: "{a}–{b} von {n}", page_info_empty: "0 Einträge",
  sel_count: "{n} ausgewählt", sel_show: "Auf Karte anzeigen", sel_pdf: "PDF", sel_merge: "Zusammenführen",
  sel_delete: "Löschen", sel_clear: "Auswahl aufheben", sel_restore: "Wiederherstellen", sel_purge: "Endgültig löschen",
  sel_assign: "Als Reise übernehmen",
  empty_trips: "Noch keine Reisen erkannt.", empty_trips_hint: "Prüfe Heimstandort und GPS-Datei unter Einstellungen und klicke dann auf „Jetzt einlesen“.",
  empty_unassigned: "Keine offenen Einträge – alles ist zugeordnet.", empty_trash: "Der Papierkorb ist leer.",
  un_title: "Nicht zugeordnet", un_sub: "Abschnitte ohne eindeutige Abfahrt oder Rückkehr",
  un_intro: "Hier landen Fahrten, die nicht sauber am Heimstandort beginnen oder enden – etwa weil die Logdatei unterwegs beginnt oder Daten fehlen. Übernimm sie als Reise, führe sie mit der vorherigen bzw. nächsten Fahrt zusammen, teile sie an einer Etappengrenze oder lösche sie.",
  reason_start_outside: "Beginn außerhalb", reason_gap: "Datenlücke", reason_manual: "bearbeitet",
  act_view: "Auf Karte anzeigen", act_pdf: "PDF-Export", act_delete: "In den Papierkorb", act_assign: "Als Reise übernehmen",
  act_merge_prev: "Mit vorheriger zusammenführen", act_merge_next: "Mit nächster zusammenführen", act_split: "Teilen",
  act_restore: "Wiederherstellen", act_purge: "Endgültig löschen",
  trash_title: "Papierkorb", trash_sub: "gelöschte Einträge", trash_empty_btn: "Papierkorb leeren",
  trash_intro: "Gelöschte Reisen bleiben hier, bis du sie endgültig löschst. Endgültig gelöschte Reisen können über „Neu einlesen & abgleichen“ wieder aus der GPS-Datei hergestellt werden.",
  v_trip: "Reise", v_trips: "{n} Reisen", v_color: "Farbe", v_stages: "Etappen einfärben", v_pdf: "PDF exportieren",
  v_close: "Schließen", v_name: "Name (optional)", v_stage: "Etappe", v_legend: "Reisen", v_total: "Gesamt",
  v_prev: "Vorherige Reise", v_next: "Nächste Reise", v_side: "Details",
  confirm_delete: "{n} Eintrag/Einträge in den Papierkorb verschieben?", confirm_purge: "{n} Eintrag/Einträge endgültig löschen? Das kann nicht rückgängig gemacht werden.",
  confirm_purge_all: "Papierkorb vollständig leeren? Das kann nicht rückgängig gemacht werden.",
  confirm_merge: "{n} Einträge zu einem zusammenführen?", merge_none: "Kein benachbarter Eintrag vorhanden.",
  split_title: "Eintrag teilen", split_text: "Teilen vor Etappe:", split_btn: "Teilen",
  cancel: "Abbrechen", ok: "OK", start: "Starten", save: "Speichern", yes: "Ja", no: "Nein",
  ri_title: "Neu einlesen & abgleichen",
  ri_reconcile: "Abgleichen", ri_reconcile_d: "Die komplette GPS-Datei wird gelesen. Fehlende Reisen werden ergänzt, vorhandene bleiben mit Farbe und Namen erhalten.",
  ri_restore: "Gelöschte Reisen aus dem Papierkorb wiederherstellen",
  ri_rebuild: "Komplett neu aufbauen", ri_rebuild_d: "Alle Einträge werden gelöscht und neu erkannt – nötig nach geänderten Erkennungs-Einstellungen oder einer ausgetauschten GPS-Datei. Farben, Namen und Bearbeitungen gehen verloren; vorher wird automatisch ein Datenbank-Backup erstellt.",
  imp_started: "Import gestartet …", imp_done: "Import fertig: {ins} neu, {upd} aktualisiert", imp_overlap: "{n} überlappende Einträge übersprungen – evtl. „Komplett neu aufbauen“.",
  imp_running: "Es läuft bereits ein Import.", imp_err: "Import fehlgeschlagen: {e}",
  err_no_home: "Heimstandort ist noch nicht eingestellt.", err_file_missing: "GPS-Datei nicht gefunden: {d}",
  err_generic: "Fehler: {e}", saved: "Gespeichert", done: "Erledigt",
  n_setup: "Bitte zuerst unter Einstellungen den Heimstandort (Breitengrad, Längengrad, Radius) eintragen.",
  n_setup_btn: "Zu den Einstellungen", n_file: "Die GPS-Datei {p} wurde nicht gefunden.",
  n_params: "Die Erkennungs-Einstellungen wurden seit dem letzten Aufbau geändert. Für ein konsistentes Ergebnis „Komplett neu aufbauen“ ausführen.",
  n_params_btn: "Neu aufbauen …",
  set_title: "Einstellungen", set_file: "GPS-Datei", set_path: "Pfad zur Logdatei", set_path_h: "Format je Zeile: Datum,Breitengrad,Längengrad,Höhe,Geschwindigkeit. Der /config-Ordner von Home Assistant ist eingebunden (nur lesend).",
  set_check: "Prüfen", set_tz: "Zeitstempel in der Datei", set_tz_utc: "UTC", set_tz_local: "Lokalzeit von Home Assistant",
  set_tz_h: "Zeitstempel ohne Zeitzonen-Angabe (z. B. 2026-10-18T15:02:01) werden so interpretiert.",
  set_interval: "Automatisch einlesen alle", set_interval_h: "Minuten. 0 = nur manuell.",
  set_home: "Heimstandort", set_lat: "Breitengrad (Latitude)", set_lon: "Längengrad (Longitude)", set_radius: "Radius",
  set_radius_h: "Meter. Verlassen und Wiederkommen werden an diesem Kreis erkannt.", set_from_ha: "Position aus Home Assistant übernehmen",
  set_map_h: "Tipp: Klicke in die Karte oder ziehe die Markierung, um den Standort zu setzen.",
  set_detect: "Erkennung", set_leave: "Punkte zum Bestätigen der Abfahrt", set_leave_h: "So viele Punkte in Folge müssen außerhalb des Radius liegen (filtert GPS-Rauschen).",
  set_gap: "Neue Etappe nach Pause ab", set_gap_h: "Minuten ohne Logeintrag (das GPS loggt im Stand nicht).",
  set_min: "Mindeststrecke einer Reise", set_min_h: "km. Kürzere Fahrten werden ignoriert.",
  set_vmax: "Ausreißer-Filter", set_vmax_h: "km/h. Punkte, die eine höhere Geschwindigkeit ergeben würden, werden verworfen.",
  set_jump: "Sprung = fehlende Daten ab", set_jump_h: "km. Springt die Position nach einer Pause weiter, gilt der Abschnitt als „nicht zugeordnet“.",
  set_view: "Darstellung", set_lang: "Sprache", set_lang_auto: "Automatisch (Home Assistant)", set_unit: "Entfernungen",
  set_color: "Standard-Trackfarbe", set_pagesize: "Einträge pro Seite (Standard)",
  set_tiles: "Karte & Cache", set_tile_url: "Kachel-Server", set_tile_url_h: "Vorlage mit {z}, {x}, {y}. Standard: OpenStreetMap.",
  set_cache_days: "Kacheln aktualisieren nach", set_cache_days_h: "Tagen. Ältere Kacheln werden beim Server neu angefragt; ohne Internet wird der Cache genutzt.",
  set_cache_mb: "Maximale Cache-Größe", set_cache_mb_h: "MB. Selten genutzte Kacheln werden zuerst entfernt.",
  set_cache_info: "Belegt: {s} · {n} Kacheln", set_cache_clear: "Cache leeren",
  set_db: "Datenbank", set_backup: "Backup jetzt erstellen", set_backup_h: "Backups liegen im App-Datenordner (/data/backups), die letzten 5 werden behalten. Die App-Daten sind auch in Home-Assistant-Backups enthalten.",
  set_rebuild: "Komplett neu aufbauen …", set_unsaved: "Ungespeicherte Änderungen", set_invalid: "Bitte markierte Felder prüfen.",
  set_rebuild_q: "Erkennungs-Einstellungen geändert. Sollen alle Reisen jetzt neu aufgebaut werden? (Farben und Bearbeitungen gehen verloren, vorher wird ein Backup erstellt.)",
  chk_ok: "Datei gefunden: {s}, {ok} von {n} Probezeilen gültig.", chk_missing: "Datei nicht gefunden.", chk_dir: "(Ordner existiert)",
  backup_done: "Backup erstellt: {p}",
  log_title: "Log", log_sub: "Meldungen dieser Sitzung", log_level: "Mindest-Level", log_auto: "Automatisch aktualisieren",
  col_time: "Zeit", col_level: "Level", col_source: "Quelle", col_msg: "Meldung", log_empty: "Keine Meldungen.",
  help_title: "Anleitung",
  foot: "Kartendaten © OpenStreetMap-Mitwirkende",
  unit_h: "h", unit_min: "min", unit_d: "T",
},
en: {
  nav_trips: "Trips", nav_unassigned: "Unassigned", nav_trash: "Trash",
  nav_settings: "Settings", nav_log: "Log", nav_help: "Help",
  st_auto: "Auto import active", st_manual: "Manual import only", st_importing: "Importing …",
  st_offline: "Maps offline (cache)", st_error: "Last import failed",
  btn_import_now: "Import now", btn_reimport: "Re-read & reconcile",
  btn_show_selection: "Show selection", gps_file: "GPS file", change: "change",
  s_trips: "Trips", s_trips_sub: "last {date}", s_trips_none: "none yet",
  s_running: "On the road", s_running_yes: "Yes", s_running_no: "No", s_running_since: "since {date}",
  s_home: "at home", s_distance: "Total distance", s_avg: "avg {v} per trip",
  s_driving: "Total driving time", s_stages: "{n} stages", s_unassigned: "Unassigned",
  s_unassigned_sub: "need review", s_unassigned_none: "all assigned", s_last_import: "Last import",
  s_never: "never", s_new: "{n} new", s_failed: "failed",
  trips_title: "Trips", trips_sub: "departure from and return to home",
  per_page: "Per page", all: "All",
  col_date: "Date", col_start: "Start", col_end: "End", col_duration: "Duration", col_driving: "Driving",
  col_distance: "Kilometres", col_distance_mi: "Miles", col_stages: "Stages", col_actions: "Actions", col_reason: "Reason",
  col_deleted: "Deleted", col_status: "Status",
  running: "on the road", page_info: "{a}–{b} of {n}", page_info_empty: "0 entries",
  sel_count: "{n} selected", sel_show: "Show on map", sel_pdf: "PDF", sel_merge: "Merge",
  sel_delete: "Delete", sel_clear: "Clear selection", sel_restore: "Restore", sel_purge: "Delete permanently",
  sel_assign: "Accept as trip",
  empty_trips: "No trips detected yet.", empty_trips_hint: "Check home location and GPS file in Settings, then click “Import now”.",
  empty_unassigned: "Nothing to review – everything is assigned.", empty_trash: "The trash is empty.",
  un_title: "Unassigned", un_sub: "sections without a clear departure or return",
  un_intro: "Drives that do not cleanly start or end at home show up here – for example when the log file starts on the road or data is missing. Accept them as a trip, merge them with the previous or next drive, split them at a stage boundary or delete them.",
  reason_start_outside: "Starts away", reason_gap: "Data gap", reason_manual: "edited",
  act_view: "Show on map", act_pdf: "PDF export", act_delete: "Move to trash", act_assign: "Accept as trip",
  act_merge_prev: "Merge with previous", act_merge_next: "Merge with next", act_split: "Split",
  act_restore: "Restore", act_purge: "Delete permanently",
  trash_title: "Trash", trash_sub: "deleted entries", trash_empty_btn: "Empty trash",
  trash_intro: "Deleted trips stay here until you delete them permanently. Permanently deleted trips can be recovered from the GPS file with “Re-read & reconcile”.",
  v_trip: "Trip", v_trips: "{n} trips", v_color: "Colour", v_stages: "Colour stages", v_pdf: "Export PDF",
  v_close: "Close", v_name: "Name (optional)", v_stage: "Stage", v_legend: "Trips", v_total: "Total",
  v_prev: "Previous trip", v_next: "Next trip", v_side: "Details",
  confirm_delete: "Move {n} entry/entries to the trash?", confirm_purge: "Permanently delete {n} entry/entries? This cannot be undone.",
  confirm_purge_all: "Empty the trash completely? This cannot be undone.",
  confirm_merge: "Merge {n} entries into one?", merge_none: "There is no neighbouring entry.",
  split_title: "Split entry", split_text: "Split before stage:", split_btn: "Split",
  cancel: "Cancel", ok: "OK", start: "Start", save: "Save", yes: "Yes", no: "No",
  ri_title: "Re-read & reconcile",
  ri_reconcile: "Reconcile", ri_reconcile_d: "The complete GPS file is read. Missing trips are added; existing ones keep their colour and name.",
  ri_restore: "Restore deleted trips from the trash",
  ri_rebuild: "Rebuild from scratch", ri_rebuild_d: "All entries are deleted and detected again – needed after changing detection settings or replacing the GPS file. Colours, names and edits are lost; a database backup is created first.",
  imp_started: "Import started …", imp_done: "Import finished: {ins} new, {upd} updated", imp_overlap: "{n} overlapping entries skipped – consider “Rebuild from scratch”.",
  imp_running: "An import is already running.", imp_err: "Import failed: {e}",
  err_no_home: "Home location is not configured yet.", err_file_missing: "GPS file not found: {d}",
  err_generic: "Error: {e}", saved: "Saved", done: "Done",
  n_setup: "Please enter the home location (latitude, longitude, radius) in Settings first.",
  n_setup_btn: "Open settings", n_file: "The GPS file {p} was not found.",
  n_params: "Detection settings changed since the last rebuild. Run “Rebuild from scratch” for consistent results.",
  n_params_btn: "Rebuild …",
  set_title: "Settings", set_file: "GPS file", set_path: "Path to log file", set_path_h: "Format per line: date,latitude,longitude,altitude,speed. Home Assistant's /config folder is mounted (read-only).",
  set_check: "Check", set_tz: "Timestamps in the file", set_tz_utc: "UTC", set_tz_local: "Home Assistant local time",
  set_tz_h: "Timestamps without a time zone (e.g. 2026-10-18T15:02:01) are interpreted this way.",
  set_interval: "Import automatically every", set_interval_h: "minutes. 0 = manual only.",
  set_home: "Home location", set_lat: "Latitude", set_lon: "Longitude", set_radius: "Radius",
  set_radius_h: "Metres. Leaving and returning are detected at this circle.", set_from_ha: "Use Home Assistant location",
  set_map_h: "Tip: click the map or drag the marker to set the location.",
  set_detect: "Detection", set_leave: "Points to confirm departure", set_leave_h: "This many consecutive points must be outside the radius (filters GPS noise).",
  set_gap: "New stage after a pause of", set_gap_h: "minutes without log entries (the GPS does not log while parked).",
  set_min: "Minimum trip distance", set_min_h: "km. Shorter drives are ignored.",
  set_vmax: "Outlier filter", set_vmax_h: "km/h. Points implying a higher speed are discarded.",
  set_jump: "Jump = missing data from", set_jump_h: "km. If the position jumps further after a pause, the section is marked “unassigned”.",
  set_view: "Display", set_lang: "Language", set_lang_auto: "Automatic (Home Assistant)", set_unit: "Distances",
  set_color: "Default track colour", set_pagesize: "Entries per page (default)",
  set_tiles: "Map & cache", set_tile_url: "Tile server", set_tile_url_h: "Template with {z}, {x}, {y}. Default: OpenStreetMap.",
  set_cache_days: "Refresh tiles after", set_cache_days_h: "days. Older tiles are requested again; without internet the cache is used.",
  set_cache_mb: "Maximum cache size", set_cache_mb_h: "MB. Least recently used tiles are removed first.",
  set_cache_info: "Used: {s} · {n} tiles", set_cache_clear: "Clear cache",
  set_db: "Database", set_backup: "Create backup now", set_backup_h: "Backups are stored in the app data folder (/data/backups); the last 5 are kept. App data is also part of Home Assistant backups.",
  set_rebuild: "Rebuild from scratch …", set_unsaved: "Unsaved changes", set_invalid: "Please check the highlighted fields.",
  set_rebuild_q: "Detection settings changed. Rebuild all trips now? (Colours and edits are lost; a backup is created first.)",
  chk_ok: "File found: {s}, {ok} of {n} sample lines valid.", chk_missing: "File not found.", chk_dir: "(folder exists)",
  backup_done: "Backup created: {p}",
  log_title: "Log", log_sub: "messages of this session", log_level: "Minimum level", log_auto: "Auto refresh",
  col_time: "Time", col_level: "Level", col_source: "Source", col_msg: "Message", log_empty: "No messages.",
  help_title: "Help",
  foot: "Map data © OpenStreetMap contributors",
  unit_h: "h", unit_min: "min", unit_d: "d",
}};

window.HELP = {
de: `
<h3>Was macht My TrackView?</h3>
<p>Die App liest die GPS-Logdatei deines Wohnmobils und erkennt daraus Reisen: Eine Reise beginnt, wenn das Fahrzeug den Heimstandort verlässt, und endet, wenn es wieder dort ankommt. Pausen (das GPS loggt im Stand nicht) teilen eine Reise in <b>Etappen</b>.</p>
<h3>Erste Schritte</h3>
<ol>
<li>Unter <b>Einstellungen</b> den Pfad zur GPS-Datei eintragen (z. B. <code>/config/skdata/skwomo-gps-log.csv</code>) und auf <b>Prüfen</b> klicken.</li>
<li>Den <b>Heimstandort</b> setzen – per Klick in die Karte, über „Position aus Home Assistant übernehmen“ oder mit Breiten-/Längengrad. Der <b>Radius</b> (Standard 200 m) sollte Einfahrt und Stellplatz umfassen.</li>
<li>Prüfen, ob die Zeitstempel der Datei <b>UTC</b> oder <b>Lokalzeit</b> sind. Stimmen die Uhrzeiten nach dem Import nicht, die Einstellung ändern und „Komplett neu aufbauen“ ausführen.</li>
<li>Speichern und auf <b>Jetzt einlesen</b> klicken. Danach liest die App automatisch neue Daten nach (Standard alle 5 Minuten) – nur der neue Teil der Datei wird gelesen.</li>
</ol>
<h3>Reisen-Liste</h3>
<ul>
<li>Ein Klick auf die Mini-Karte öffnet die Reise in der Kartenansicht – gezoomt auf den Track, mit Farbwahl, Etappen-Einfärbung und PDF-Export.</li>
<li>Nach <b>Datum, Dauer, Fahrzeit</b> und <b>Kilometern</b> sortieren: auf den Spaltenkopf klicken.</li>
<li>Mit den Auswahlkästchen mehrere Reisen markieren, dann <b>Auf Karte anzeigen</b> – alle erscheinen gemeinsam, jede in eigener Farbe. Auch ein gemeinsamer PDF-Export ist möglich.</li>
<li><b>Dauer</b> ist die Gesamtzeit von Abfahrt bis Rückkehr, <b>Fahrzeit</b> die Summe der Etappen.</li>
</ul>
<h3>Nicht zugeordnet</h3>
<p>Abschnitte, die nicht am Heimstandort beginnen oder bei denen Daten fehlen (Positionssprung nach einer Pause), landen hier. Du kannst sie als Reise übernehmen, mit der vorherigen/nächsten Fahrt zusammenführen, an einer Etappengrenze teilen oder löschen. Zusammenführen geht auch in der Reisen-Liste: mehrere markieren → „Zusammenführen“.</p>
<h3>Löschen & Wiederherstellen</h3>
<p>Gelöschte Reisen wandern in den <b>Papierkorb</b> und werden in der Liste ausgeblendet. Von dort lassen sie sich wiederherstellen oder endgültig löschen. Über <b>Neu einlesen & abgleichen</b> wird die komplette GPS-Datei erneut gelesen: fehlende Reisen werden ergänzt, optional auch gelöschte zurückgeholt. Hast du die GPS-Datei ausgetauscht oder Erkennungs-Einstellungen geändert, nimm <b>Komplett neu aufbauen</b> (vorher wird automatisch ein Backup erstellt).</p>
<h3>Karten & Offline-Betrieb</h3>
<p>Kartenkacheln werden über die App geladen und zwischengespeichert. Nach der eingestellten Zeit (Standard 7 Tage) werden sie beim Server neu angefragt, damit die Karte aktuell bleibt; ohne Internet nutzt die App den Cache. Bitte beachte die Nutzungsbedingungen von OpenStreetMap – für den privaten Gebrauch ist das unproblematisch.</p>
<h3>Daten</h3>
<p>Alle Reisen liegen in einer SQLite-Datenbank im Datenordner der App und sind in Home-Assistant-Backups enthalten (ohne den Kachel-Cache). Die GPS-Datei wird nur gelesen, nie verändert.</p>`,
en: `
<h3>What does My TrackView do?</h3>
<p>The app reads your motorhome's GPS log file and detects trips: a trip starts when the vehicle leaves home and ends when it arrives there again. Pauses (the GPS does not log while parked) split a trip into <b>stages</b>.</p>
<h3>Getting started</h3>
<ol>
<li>In <b>Settings</b>, enter the path of the GPS file (e.g. <code>/config/skdata/skwomo-gps-log.csv</code>) and click <b>Check</b>.</li>
<li>Set the <b>home location</b> – by clicking the map, with “Use Home Assistant location”, or by latitude/longitude. The <b>radius</b> (default 200 m) should cover your driveway and parking spot.</li>
<li>Check whether the file's timestamps are <b>UTC</b> or <b>local time</b>. If times look wrong after importing, change the setting and run “Rebuild from scratch”.</li>
<li>Save and click <b>Import now</b>. Afterwards the app picks up new data automatically (every 5 minutes by default) – only the new part of the file is read.</li>
</ol>
<h3>Trip list</h3>
<ul>
<li>Click the mini map to open the trip in the map view – zoomed to the track, with colour picker, stage colouring and PDF export.</li>
<li>Sort by <b>date, duration, driving time</b> and <b>distance</b> by clicking the column header.</li>
<li>Tick several trips and click <b>Show on map</b> – they are shown together, each in its own colour. A combined PDF export is possible as well.</li>
<li><b>Duration</b> is the total time from departure to return, <b>driving</b> the sum of all stages.</li>
</ul>
<h3>Unassigned</h3>
<p>Sections that do not start at home or where data is missing (position jump after a pause) end up here. You can accept them as a trip, merge them with the previous/next drive, split them at a stage boundary or delete them. Merging also works in the trip list: tick several → “Merge”.</p>
<h3>Delete & restore</h3>
<p>Deleted trips go to the <b>trash</b> and are hidden from the list. From there they can be restored or deleted permanently. <b>Re-read & reconcile</b> reads the whole GPS file again: missing trips are added and, optionally, deleted ones are brought back. If you replaced the GPS file or changed detection settings, use <b>Rebuild from scratch</b> (a backup is created automatically first).</p>
<h3>Maps & offline use</h3>
<p>Map tiles are loaded through the app and cached. After the configured time (default 7 days) they are requested again so the map stays current; without internet the cache is used. Please respect the OpenStreetMap tile usage policy – private use is fine.</p>
<h3>Data</h3>
<p>All trips are stored in an SQLite database in the app's data folder and are included in Home Assistant backups (without the tile cache). The GPS file is only read, never modified.</p>`
};
