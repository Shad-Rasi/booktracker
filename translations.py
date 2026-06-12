from contextlib import contextmanager
from datetime import datetime

# =========================================================================
# 1. HAUPT-ÜBERSETZUNGS-DICTIONARY (Symmetrisch strukturiert)
# =========================================================================
TRANSLATIONS = {
    'de': {
        # --- Allgemein & Navigation ---
        'my_shelf': 'Dashboard',
        'back': 'Zurück',
        'back_to_shelf': 'Zurück zum Regal',
        'cancel': 'Abbrechen',
        'save': 'Speichern',
        'delete': 'Löschen',
        'ready': 'Fertig',
        'close': 'Schließen',
        'error': 'Fehler',
        'none': 'Keine',
        'active': 'Aktiv',
        'stars': 'Sterne',
        'star': 'Stern',
        'search': 'Suchen',
        'not_found': 'Buch nicht gefunden!',
        'empty_shelf': 'Dein Regal ist noch leer.',
        'no_search_results': 'Keine passenden Ergebnisse gefunden.',

        # --- Buch-Eintrag & Basisdetails ---
        'add_book': 'Buch hinzufügen',
        'edit_book': 'Buch bearbeiten',
        'save_in_shelf': 'Im Regal speichern',
        'save_changes': 'Änderungen speichern',
        'first_book': 'Erstes Buch erfassen',
        'title': 'Buchtitel',
        'subtitle': 'Untertitel',
        'author': 'Autor(en)',
        'unknown_author': 'Unbekannter Autor',
        'pages': 'Seiten',
        'pages_short': 'S.',
        'status': 'Lesestatus',
        'readingstatus': 'Lesestatus',
        'rating': 'Meine Bewertung',
        'special': 'Special Edition',
        'quantity': 'Menge',
        'location': 'Standort / Regal',
        'format': 'Format',
        'ownership': 'Besitzstatus',
        'details': 'Details',
        'section_book_info': 'Buchdetails',
        'section_personal_info': 'Persönliche Informationen',

        # --- Erweitere Metadaten & Beitragende ---
        'translator': 'Übersetzer',
        'narrator': 'Erzähler / Sprecher',
        'illustrator': 'Illustrator',
        'editor': 'Herausgeber / Editor',
        'publisher': 'Verlag',
        'published_date': 'Erscheinungsdatum',
        'language': 'Sprache des Buchs',
        'description': 'Beschreibung / Klappentext',
        'contributors': 'Beitragende',

        # --- Lesestatus (Aus der DB) ---
        'unread': 'Ungelesen',
        'reading': 'Wird gerade gelesen',
        'read': 'Abgeschlossen',

        # --- Format-Optionen ---
        'PHYSICAL': '📖 Physisches Buch',
        'AUDIOBOOK': '🎧 Hörbuch',
        'EBOOK': '📱 E-Book',
        'book': 'Buch',

        # --- Besitz-Optionen ---
        'OWNED': 'In Besitz',
        'BORROWED': 'Geliehen',
        'LENT': 'Verliehen',
        'GIVEN_AWAY': 'Weggegeben',
        'ownership_owned': 'In meinem Besitz',
        'ownership_lent': 'Verliehen',
        'ownership_given_away': 'Weggegeben',
        'given_away': 'Weggegeben',

        # --- Tracking, Zyklen & Progress ---
        'start': 'Lesestart',
        'end': 'Leseende',
        'book_current_cycle': '⚡ Aktueller Durchgang:',
        'book_started_at': 'Gestartet am',
        'book_last_read': '✅ Zuletzt gelesen:',
        'book_from': 'Vom',
        'book_to': 'Bis',
        'book_until': 'bis',
        'book_track_progress_title': 'Lese-Fortschritt tracken 📈',
        'book_current_on_page': 'Aktuell auf Seite',
        'book_of_pages': 'von',
        'book_input_new_page': 'Neue Seite',
        'book_logbook_current_cycle': 'Logbuch dieses Durchgangs:',
        'book_log_read_short': 'gelesen',
        'book_log_until_page': 'Bis S.',
        'book_view_logbook': 'Gesamtes Logbuch einsehen',
        'book_no_logs_recorded': 'Noch keine Log-Einträge für dieses Buch verzeichnet.',
        'book_status_finished': 'Abgeschlossen',
        'book_status_active': 'Aktiv',
        'book_already_read_title': 'Du hast dieses Buch bereits ausgelesen!',
        'book_already_read_subtitle': 'Möchtest du es noch einmal von vorne lesen und einen neuen Durchgang starten?',
        'book_btn_reread': 'Buch erneut lesen',
        'book_hint_set_reading': 'Stelle den Status auf "Am Lesen", um deinen Lesefortschritt zu dokumentieren.',
        'book_past_cycles_title': 'Vergangene Lesedurchgänge',
        'book_label_cycle': 'Lesedurchgang',
        'book_confirm_cycle_delete': 'Diesen Lesedurchgang wirklich löschen? Alle damit verknüpften täglichen Kalendereinträge gehen verloren!',

        # --- Cover-Management & API-Meldungen ---
        'isbn_label': 'ISBN scannen / eingeben',
        'no_cover': 'Kein Cover',
        'book_search_cover_internet': 'Cover im Internet suchen',
        'book_choose_cover_live': 'Wähle ein passendes Cover aus der Live-Suche aus:',
        'book_upload_change_cover': 'Cover hochladen / ändern',
        'book_select_image_label': 'Bild auswählen (JPG/PNG)',
        'book_btn_change_cover': 'Cover ändern',
        'book_btn_search_online': 'Online suchen',
        'book_no_images_found': 'Keine passenden Bilder gefunden.',
        'book_tooltip_author_profile': 'Zum Autorenprofil wechseln',
        'book_tooltip_fetch_metadata': 'Fehlende Metadaten online abrufen & dauerhaft einspeichern',
        'book_confirm_delete_title': 'Buch unwiderruflich löschen? 🚨',
        'book_confirm_delete_text_1': 'Möchtest du das Buch',
        'book_confirm_delete_text_2': 'wirklich aus deiner Bibliothek entfernen? Alle damit verknüpften Lesestände, Statistiken und Kalendereinträge werden permanent gelöscht.',
        
        # --- Benachrichtigungen (Notifies) ---
        'notify_deleted': 'wurde aus dem Regal genommen.',
        'notify_saved': 'Erfolgreich im Regal gespeichert!',
        'notify_isbn_warn': 'Bitte zuerst eine ISBN eingeben!',
        'notify_api_success': 'API-Daten erfolgreich geladen!',
        'notify_api_fail': 'Keine Spuren zu dieser ISBN gefunden.',
        'book_notify_saving_cover': 'Speichere ausgewähltes Cover...',
        'book_notify_cover_updated': 'Cover erfolgreich aktualisiert!',
        'book_notify_cover_error': 'Fehler beim Download des Covers.',
        'book_notify_save_error': 'Fehler beim Speichern',
        'book_notify_scrape_metadata': 'Scrape fehlende Buchdaten von isbn.de...',
        'book_notify_metadata_saved': 'Metadaten erfolgreich in DB gespeichert! 🎉',
        'book_notify_metadata_not_found': 'Keine Daten auf isbn.de gefunden.',
        'book_notify_log_saved': 'Eintrag gesichert!',
        'book_notify_log_removed': 'Lese-Eintrag entfernt.',
        'book_notify_reread_started': 'Neuer Lesedurchgang gestartet! Viel Spaß 📖',
        'book_notify_cycle_removed': 'Lesedurchgang inklusive Logs gelöscht.',

        # --- Sortierung (Main-Shelf) ---
        'sort_title': 'Titel (A-Z)',
        'sort_author': 'Autor (A-Z)',
        'sort_pages_desc': 'Meiste Seiten',
        'sort_pages_asc': 'Wenigste Seiten',
        'sort_rating': 'Beste Bewertung',

        # --- Sektion: Autoren (Authors) ---
        'authors': 'Autoren',
        'authors_title': 'Autoren & Schriftsteller',
        'authors_subtitle': 'Stöbere in deiner Bibliothek nach den Schöpfern deiner Bücher.',
        'no_authors_found': 'Noch keine Autoren in der Bibliothek erfasst.',
        'view_profile': 'Profil anzeigen →',
        'back_to_authors': 'Zurück zur Übersicht',
        'no_bio_available': 'Keine Biografie zu diesem Autoren hinterlegt.',
        'books_by_author': 'Bücher in deiner Sammlung:',
        'edit_author_title': 'Profil bearbeiten',
        'author_birth': 'Geburtsdatum / -ort (z.B. 1947 oder 21. September 1947)',
        'author_death': 'Sterbedatum (falls zutreffend)',
        'author_img_url': 'Link zu einem Autorenfoto (URL)',
        'author_bio': 'Biografie / Notizen',
        'notify_author_updated': 'Autorenprofil erfolgreich aktualisiert!',

        # --- Sektion: Buchreihen (Series) ---
        'series': 'Reihen',
        'series_title': 'Buchreihen',
        'series_subtitle': 'Hier findest du all deine gesammelten Buchreihen und Zyklen auf einen Blick.',
        'no_series_found': 'Keine Buchreihen in deiner Bibliothek gefunden.',
        'view_series': 'Reihe anzeigen',
        'back_to_series': 'Zurück zur Reihen-Übersicht',
        'books_in_series': 'Bücher in dieser Reihe:',
        'series_volume': 'Band',
        'series_name': 'Reihe',
        'series_num': 'Band',
        'volume': 'Band',
        'volume_unknown': 'Ohne Bandnr.',

        # --- Sektion: Genres ---
        'genres': 'Genre',
        'manage_genres': 'Genres verwalten',
        'genre_name': 'Neues Genre',
        'existing_genres': 'Eingerichtete Genres',
        'no_genres_hint': 'Noch keine Genres angelegt.',
        'notify_genre_added': 'als Genre hinzugefügt',
        'error_genre_exists': 'Dieses Genre existiert bereits!',
        'confirm_delete_genre_text': 'wirklich löschen? Zugeordnete Bücher werden auf "Kein Genre" zurückgesetzt.',
        'notify_genre_deleted': 'Genre gelöscht',
        'genre_subtitle':'Hier findest du alle deine angelegten Buchgenre.',

        # --- Sektion: Kalender (Calendar) ---
        'calendar': 'Lesekalender',
        'calendar_title': 'Mein Lese-Kalender',
        'calendar_subtitle': 'Hier siehst du deine täglichen Lese-Einheiten im Überblick.',
        'calendar_select_day': 'Wähle einen markierten Tag im Kalender aus, um deine Einheiten zu sehen.',
        'calendar_activities_at': 'Aktivitäten am',
        'calendar_no_logs': 'An diesem Tag hast du keine Lese-Etappe eingetragen.',
        'cal_mode_covers': '🖼️ Cover-Ansicht',
        'cal_mode_timeline': '📊 Zeitachse',
        'cal_no_timeline_data': 'Im diesem Monat wurden keine aktiven Zeiträume verzeichnet.',
        'cal_no_timeline_data_year': 'In diesem Jahr wurden keine aktiven Zeiträume verzeichnet.',
        'log_deleted': 'Eintrag erfolgreich gelöscht.',
        'log_delete_error': 'Fehler beim Löschen des Eintrags.',
        'cal_logs_for': 'Logs für',
        'no_logs_day': 'Keine Einträge an diesem Tag.',
        'month_1': 'Januar', 'month_2': 'Februar', 'month_3': 'März', 'month_4': 'April',
        'month_5': 'Mai', 'month_6': 'Juni', 'month_7': 'Juli', 'month_8': 'August',
        'month_9': 'September', 'month_10': 'Oktober', 'month_11': 'November', 'month_12': 'Dezember',
        'day_mo': 'Mo', 
        'day_di': 'Di', 
        'day_mi': 'Mi', 
        'day_do': 'Do', 
        'day_fr': 'Fr', 
        'day_sa': 'Sa', 
        'day_so': 'So',

        # --- Quick-Log Modal ---
        'quick_log_title': 'Lese-Etappe schnellbuchen ⚡',
        'quick_log_no_books': 'Du hast aktuell keine Bücher auf "Am Lesen" stehen!',
        'quick_log_warn_fields': 'Bitte wähle ein Buch aus und gib eine Seitenzahl ein!',
        'select_book': 'Buch auswählen',
        'pages_read_to': 'Gelesen bis Seite',
        'book_finished': 'Buch erfolgreich beendet!',

        # --- Sektion: Statistiken (Statistics) ---
        'stats': 'Statistik',
        'stats_sec_personal': '🧠 Persönliche Statistiken',
        'stats_sec_general': '📊 Allgemeine Tracker Statistiken',
        'stats_read_books_year': 'Ausgelesene Bücher',
        'stats_chart_monthly_pages': 'Gelesene Seiten im Verlauf',
        'stats_chart_formats': 'Verteilung der Buch-Formate',
        'stats_chart_ratings': 'Verteilung deiner Sterne-Bewertungen',
        'stats_chart_books_development': 'Gelesene Bücher im Verlauf',
        'stats_chart_status': 'Verteilung Lesestatus',
        'stats_chart_lengths': 'Buchlängen im Regal',
        'stats_chart_development': 'Deine Jahresentwicklung (Gelesene Bücher)',
        'books_count': 'Bücher',
        'export_report': 'Erstelle Bericht',
        'share_report_title': 'Bericht teilen',
        'share_report_desc': 'Wähle das Jahr für den PDF-Export:',
        'share_report_btn_export': 'PDF erstellen & Download',
        'share_report_error': 'Fehler beim PDF-Export',
        'generating_pdf': 'PDF wird generiert...',
        'all_years': 'Alle Jahre (Gesamt)',
        'stats_title': 'Bibliotheks-Statistiken',
        'stats_subtitle': 'Analysiere deine Lesegewohnheiten und Fortschritte.',
        'stats_total_pages_read': 'Gelesene Seiten gesamt',
        'stats_total_books': 'Bücher insgesamt',
        'chart_type_bar': 'Balken',
        'chart_type_line': 'Linie',
        'month_01': 'Januar', 'month_02': 'Februar', 'month_03': 'März', 'month_04': 'April',
        'month_05': 'Mai', 'month_06': 'Juni', 'month_07': 'Juli', 'month_08': 'August',
        'month_09': 'September', 'month_10': 'Oktober', 'month_11': 'November', 'month_12': 'Dezember',
        'stats_chart_genres': 'Verteilung der Genre',
        'stats_no_data_year': 'Du hast dieses Jahr noch kein Buch beendet.',

        # --- Sektion: Regale & Standorte ---
        'manage_locations': 'Regale & Standorte verwalten',
        'add_new_location': 'Neues Regal hinzufügen',
        'location_name': 'Name des Regals (z.B. Kellerregal)',
        'existing_locations': 'Eingerichtete Standorte:',
        'all_locations': 'Alle Regale anzeigen',
        'notify_location_added': 'wurde erfolgreich als Standort angelegt.',
        'error_empty_name': 'Bitte gib einen Namen für das Regal ein!',
        'error_location_exists': 'Dieses Regal existiert bereits!',
        'confirm_delete_location_text': 'wirklich löschen? Enthaltene Bücher werden nicht gelöscht, sondern verlieren nur ihre Regal-Zuweisung.',
        'notify_location_deleted': 'wurde gelöscht.',

        # --- Sektion: Einstellungen & System ---
        'settings': 'Einstellungen',
        'settings_title': 'System-Verwaltung',
        'settings_subtitle': 'Verwalte hier Benutzer, Bücherregale sowie den Daten-Im- und Export deiner Bibliothek.',
        'ui_design_title': 'Darstellung & Design',
        'ui_design_subtitle': 'Personalisierte Einstellungen für dein Lese-Erlebnis.',
        'shelf_view_mode': 'Kachel-Ansichtsmodus',
        'view_paginated': 'Seitenansicht (24 Bücher)',
        'view_infinite': 'Endlos-Scrollen',
        'activate_darkmode': 'Darkmode aktivieren 🌙',
        'user_management': 'Benutzer-Verwaltung',
        'new_username': 'Neuer Benutzername',
        'existing_users': 'Existierende Benutzer:',
        'user': 'Benutzer',
        'confirm_delete_user_text': 'Möchtest du den Benutzer wirklich löschen? Alle seine Lesestände und Statistiken werden unwiderruflich gelöscht! Permanent entfernen:',
        'notify_user_added': 'erfolgreich angelegt!',
        'notify_user_deleted': 'Nutzer gelöscht',
        'error_user_exists': 'Benutzer existiert bereits!',

        # --- Import / Export ---
        'import_export_title': 'Daten Import / Export',
        'import_export_subtitle': 'Verwalte deine Bibliothek durch Massen-Importe oder sichere deine Daten lokal.',
        'settings_importexport_title': 'Import/Export Bücher',
        'import_file_title': 'Datei-Import',
        'import_file_subtitle': 'Lade hier deinen Goodreads-Export (.csv) oder eine reine ISBN-Liste (.txt) hoch.',
        'import_select_file': 'Datei auswählen',
        'import_preparing': 'Bereite Import vor...',
        'import_live_protocol': 'Live-Protokoll:',
        'import_processing': 'Verarbeite',
        'import_notify_loaded': 'Bücher erfolgreich geladen.',
        'import_error_no_data': 'Keine gültigen Buchdaten oder ISBNs gefunden!',
        'import_error_read': 'Fehler beim Lesen der Datei',
        'import_log_start': 'STARTE IMPORT-VORGANG',
        'import_log_end': 'IMPORT BEENDET',
        'import_source_local': 'Lokale Datei',
        'import_log_skipped': 'Übersprungen (Bereits in DB)',
        'import_msg_success': 'importiert',
        'import_msg_duplicates': 'Duplikate',
        'import_msg_errors': 'Fehler',
        'export_file_title': 'Datei-Export',
        'export_file_subtitle': 'Sichere deine komplette Büchersammlung inklusive aller Lesestände, Rezensionen und Regaldaten in einer universellen CSV-Datei. Ideal für Excel oder Backups.',
        'export_btn_text': 'Bibliothek exportieren (.csv)',
        'export_empty_library': 'Deine Bibliothek ist noch leer. Es gibt nichts zu exportieren!',
        'export_success': 'Export erfolgreich generiert!',
        'export_failed': 'Fehler beim Exportieren',

        # --- Backup & Reset ---
        'settings_backup_title': 'Datensicherung & System',
        'settings_backup_subtitle': 'Backup (Datenbank & Medien)',
        'settings_backup_desc': 'Sichere deine komplette Datenbank sowie alle heruntergeladenen Buchcover und Autorenbilder in einer ZIP-Datei.',
        'settings_backup_download': 'Backup erstellen',
        'settings_backup_restore': 'Backup einspielen (.zip)',
        'settings_reset_title': 'Gefahrenzone',
        'settings_reset_desc': 'Hiermit werden ALLE Bücher, Autoren, Cover und Einstellungen unwiderruflich gelöscht. Die Anwendung wird auf den Werkszustand zurückgesetzt.',
        'settings_reset_confirm_title': '🔒 Wirklich alles unwiderruflich löschen?',
        'settings_reset_confirm_desc': 'Diese Aktion kann nicht rückgängig gemacht werden. Alle Daten gehen verloren, es sei denn, du hast vorher ein Backup heruntergeladen.',
        'settings_reset_execute': 'Ja, Werksreset durchführen',
        'settings_reset_btn': 'Anwendung zurücksetzen',

        # --- Dynamische Längen & Sprachen ---
        'pages_under_200': '< 200 Seiten',
        'pages_200_to_400': '200 - 400 Seiten',
        'pages_400_to_600': '400 - 600 Seiten',
        'pages_over_600': '> 600 Seiten',
        'pages_unknown': 'Unbekannte Länge',
        'lang_de': 'Deutsch',
        'lang_en': 'Englisch',

        # --- Spaßprojekt (Zufall-Auslosung) ---
        'book_suggestion_title': 'Was möchtest du lesen?',
        'book_suggestion_all': 'Egal (Aus allen Genres)',
        'book_suggestion_hint': 'Wie wäre es mit:',
        'book_suggestion_click_to_open': '(Klicke auf das Feld, um das Buch direkt zu öffnen)',
        'book_suggestion_empty': 'Keine passenden Bücher im Bestand gefunden!',
        'roll_book': 'Auslosen',
        'settings_suggestion_title': 'Zufällige Buch-Vorschläge',
        'settings_suggestion_desc': 'Aktiviert ein Würfel-Symbol in der Hauptnavigation, um dich per Zufall aus deinem Bestand inspirieren zu lassen.',
    },
    
    'en': {
        # --- Navigation & General ---
        'my_shelf': 'Dashboard',
        'back': 'Back',
        'back_to_shelf': 'Back to Shelf',
        'cancel': 'Cancel',
        'save': 'Save',
        'delete': 'Delete',
        'ready': 'Ready',
        'close': 'Close',
        'error': 'Error',
        'none': 'None',
        'active': 'Active',
        'stars': 'Stars',
        'star': 'Star',
        'search': 'Search',
        'not_found': 'Book not found!',
        'empty_shelf': 'Your shelf is empty.',
        'no_search_results': 'No matching results found.',

        # --- Book Entry & Core Details ---
        'add_book': 'Add Book',
        'edit_book': 'Edit Book',
        'save_in_shelf': 'Save in Shelf',
        'save_changes': 'Save Changes',
        'first_book': 'Add your first book',
        'title': 'Book Title',
        'subtitle': 'Subtitle',
        'author': 'Author(s)',
        'unknown_author': 'Unknown Author',
        'pages': 'Pages',
        'pages_short': 'p.',
        'status': 'Reading Status',
        'readingstatus': 'Reading State',
        'rating': 'My Rating',
        'special': 'Special Edition',
        'quantity': 'Quantity',
        'location': 'Location / Shelf',
        'format': 'Format',
        'ownership': 'Ownership Status',
        'details': 'Detailed Information',
        'section_book_info': 'Book Information',
        'section_personal_info': 'Personal Information',

        # --- Metadata & Contributors ---
        'translator': 'Translator',
        'narrator': 'Narrator',
        'illustrator': 'Illustrator',
        'editor': 'Editor',
        'publisher': 'Publisher',
        'published_date': 'Publication Date',
        'language': 'Book Language',
        'description': 'Description / Synopsis',
        'contributors': 'Contributors',

        # --- Reading States (From DB) ---
        'unread': 'Unread',
        'reading': 'Reading',
        'read': 'Read',

        # --- Format Options ---
        'PHYSICAL': '📖 Physical Book',
        'AUDIOBOOK': '🎧 Audiobook',
        'EBOOK': '📱 E-Book',

        # --- Ownership Options ---
        'OWNED': 'Owned',
        'BORROWED': 'Borrowed',
        'LENT': 'Lent',
        'GIVEN_AWAY': 'Given Away',
        'ownership_owned': 'Owned',
        'ownership_lent': 'Lent',
        'ownership_given_away': 'Given Away',

        # --- Progress & Cycle Tracking ---
        'start': 'Started Reading',
        'end': 'Finished Reading',
        'book_current_cycle': '⚡ Current Cycle:',
        'book_started_at': 'Started on',
        'book_last_read': '✅ Last Read:',
        'book_from': 'From',
        'book_to': 'To',
        'book_until': 'until',
        'book_track_progress_title': 'Track Reading Progress 📈',
        'book_current_on_page': 'Currently on page',
        'book_of_pages': 'of',
        'book_input_new_page': 'New Page',
        'book_logbook_current_cycle': 'Logbook of this cycle:',
        'book_log_read_short': 'read',
        'book_log_until_page': 'Up to p.',
        'book_view_logbook': 'View Full Logbook',
        'book_no_logs_recorded': 'No log entries recorded for this book yet.',
        'book_status_finished': 'Completed',
        'book_status_active': 'Active',
        'book_already_read_title': 'You have already finished this book!',
        'book_already_read_subtitle': 'Would you like to read it again from the beginning and start a new cycle?',
        'book_btn_reread': 'Reread book',
        'book_hint_set_reading': 'Set status to "Reading" to document your progress.',
        'book_past_cycles_title': 'Past Reading Cycles',
        'book_label_cycle': 'Reading Cycle',
        'book_confirm_cycle_delete': 'Really delete this reading cycle? All linked daily calendar entries will be lost!',

        # --- Cover Management & API Responses ---
        'isbn_label': 'Scan / Enter ISBN',
        'no_cover': 'No Cover',
        'book_search_cover_internet': 'Search cover online',
        'book_choose_cover_live': 'Select a matching cover from the live search:',
        'book_upload_change_cover': 'Upload / change cover',
        'book_select_image_label': 'Select image (JPG/PNG)',
        'book_btn_change_cover': 'Change Cover',
        'book_btn_search_online': 'Search online',
        'book_no_images_found': 'No matching images found.',
        'book_confirm_delete_title': 'Permanently delete book? 🚨',
        'book_confirm_delete_text_1': 'Do you really want to remove',
        'book_confirm_delete_text_2': 'from your library? All linked reading progress, stats, and calendar entries will be permanently deleted.',

        # --- Notifications (Notifies) ---
        'notify_deleted': 'was removed from your shelf.',
        'notify_saved': 'Successfully saved to shelf!',
        'notify_isbn_warn': 'Please enter an ISBN first!',
        'notify_api_success': 'API data loaded successfully!',
        'notify_api_fail': 'No traces found for this ISBN.',
        'book_notify_saving_cover': 'Saving selected cover...',
        'book_notify_cover_updated': 'Cover updated successfully!',
        'book_notify_cover_error': 'Error downloading the cover.',
        'book_notify_save_error': 'Error saving',
        'book_notify_scrape_metadata': 'Scraping missing metadata from isbn.de...',
        'book_notify_metadata_saved': 'Metadata successfully stored in database! 🎉',
        'book_notify_metadata_not_found': 'No data found on isbn.de.',
        'book_notify_log_saved': 'Progress saved!',
        'book_notify_log_removed': 'Reading entry removed.',
        'book_notify_reread_started': 'New reading cycle started! Enjoy 📖',
        'book_notify_cycle_removed': 'Reading cycle and logs deleted.',

        # --- Sorting (Main-Shelf) ---
        'sort_title': 'Title (A-Z)',
        'sort_author': 'Author (A-Z)',
        'sort_pages_desc': 'Most Pages',
        'sort_pages_asc': 'Fewest Pages',
        'sort_rating': 'Highest Rating',

        # --- Section: Authors ---
        'authors': 'Authors',
        'authors_title': 'Authors & Writers',
        'authors_subtitle': 'Browse your library by the creators of your books.',
        'no_authors_found': 'No authors found in your library yet.',
        'view_profile': 'View Profile →',
        'back_to_authors': 'Back to Overview',
        'no_bio_available': 'No biography available for this author.',
        'books_by_author': 'Books in your collection:',
        'edit_author_title': 'Edit Profile',
        'author_birth': 'Date / Place of Birth',
        'author_death': 'Date of Death (if applicable)',
        'author_img_url': 'Link to Author Photo (URL)',
        'author_bio': 'Biography / Notes',
        'notify_author_updated': 'Author profile successfully updated!',

        # --- Section: Series ---
        'series': 'Series',
        'series_title': 'Book Series',
        'series_subtitle': 'Find all your collected book series and sagas at a glance.',
        'no_series_found': 'No book series found in your library.',
        'view_series': 'View Series',
        'back_to_series': 'Back to Series',
        'books_in_series': 'Books in this series:',
        'series_volume': 'Volume',
        'volume': 'Volume',
        'volume_unknown': 'No Vol. No.',
        'series_name': 'Series Name',
        'series_num': 'Volume',

        # --- Section: Genres ---
        'genres': 'Genre',
        'manage_genres': 'Manage Genres',
        'genre_name': 'New Genre',
        'existing_genres': 'Configured Genres',
        'no_genres_hint': 'No genres created yet.',
        'notify_genre_added': 'added as genre',
        'error_genre_exists': 'This genre already exists!',
        'confirm_delete_genre_text': 'really delete? Linked books will be reset to "No Genre".',
        'notify_genre_deleted': 'Genre deleted',
        'genre_subtitle':'Find all your book genres at a glance.',

        # --- Section: Calendar ---
        'calendar': 'Reading Calendar',
        'calendar_title': 'My Reading Calendar',
        'calendar_subtitle': 'See an overview of your daily reading sessions here.',
        'calendar_select_day': 'Select a highlighted day in the calendar to view your sessions.',
        'calendar_activities_at': 'Activities on',
        'calendar_no_logs': 'No reading sessions logged on this day.',
        'cal_mode_covers': '🖼️ Cover View',
        'cal_mode_timeline': '📊 Timeline',
        'cal_no_timeline_data': 'No active reading periods recorded in this month.',
        'cal_no_timeline_data_year': 'No active reading periods recorded in this year.',
        'log_deleted': 'Entry successfully deleted.',
        'log_delete_error': 'Error deleting the entry.',
        'cal_logs_for': 'Logs for',
        'no_logs_day': 'No entries for this day.',
        'month_1': 'January', 'month_2': 'February', 'month_3': 'March', 'month_4': 'April',
        'month_5': 'May', 'month_6': 'June', 'month_7': 'July', 'month_8': 'August',
        'month_9': 'September', 'month_10': 'October', 'month_11': 'November', 'month_12': 'December',
        'day_mo': 'Mon', 
        'day_di': 'Tue', 
        'day_mi': 'Wed', 
        'day_do': 'Thu', 
        'day_fr': 'Fri', 
        'day_sa': 'Sat', 
        'day_so': 'Sun',

        # --- Quick-Log Modal ---
        'quick_log_title': 'Quick-Log Reading Session ⚡',
        'quick_log_no_books': 'You currently have no books marked as "Reading"!',
        'quick_log_warn_fields': 'Please select a book and enter a page number!',
        'select_book': 'Select Book',
        'pages_read_to': 'Read up to page',
        'book_finished': 'Book completed successfully!',

        # --- Section: Statistics ---
        'stats': 'Statistics',
        'stats_sec_personal': '🧠 Personal Statistics',
        'stats_sec_general': '📊 General Tracker Statistics',
        'stats_read_books_year': 'Books Read',
        'stats_chart_monthly_pages': 'Pages Read over Time',
        'stats_chart_formats': 'Book Format Distribution',
        'stats_chart_ratings': 'Star Rating Distribution',
        'stats_chart_books_development': 'Books Read over Time',
        'stats_chart_status': 'Reading Status Distribution',
        'stats_chart_lengths': 'Book Length Distribution',
        'stats_chart_development': 'Your Yearly Development (Books Read)',
        'books_count': 'Books',
        'export_report': 'Create Report',
        'share_report_title': 'Share Report',
        'share_report_desc': 'Select the year for the PDF export:',
        'share_report_btn_export': 'Create PDF & Download',
        'share_report_error': 'Error during PDF export',
        'generating_pdf': 'Generating PDF...',
        'all_years': 'All Years (Total)',
        'stats_title': 'Library Statistics',
        'stats_subtitle': 'Analyze your reading habits and progress.',
        'stats_total_pages_read': 'Total Pages Read',
        'stats_total_books': 'Total Books',
        'chart_type_bar': 'Bar',
        'chart_type_line': 'Line',
        'month_01': 'January', 'month_02': 'February', 'month_03': 'March', 'month_04': 'April',
        'month_05': 'May', 'month_06': 'June', 'month_07': 'July', 'month_08': 'August',
        'month_09': 'September', 'month_10': 'October', 'month_11': 'November', 'month_12': 'December',
        'stats_chart_genres': 'Genre overview',
        'stats_no_data_year': 'You did not finish a book this year.',

        # --- Section: Shelves & Locations ---
        'manage_locations': 'Manage Shelves & Locations',
        'add_new_location': 'Add New Shelf',
        'location_name': 'Shelf Name (e.g., Basement)',
        'existing_locations': 'Configured Locations:',
        'all_locations': 'Show All Shelves',
        'notify_location_added': 'has been successfully created.',
        'error_empty_name': 'Please enter a name for the shelf!',
        'error_location_exists': 'This shelf already exists!',
        'confirm_delete_location_text': 'really delete this shelf? Contained books will not be deleted, they will just lose their shelf assignment.',
        'notify_location_deleted': 'has been deleted.',

        # --- Section: Settings & System ---
        'settings': 'Settings',
        'settings_title': 'System Management',
        'settings_subtitle': 'Manage users, bookshelves, and data import/export for your library here.',
        'ui_design_title': 'Appearance & Design',
        'ui_design_subtitle': 'Personalized settings for your reading experience.',
        'shelf_view_mode': 'Grid View Mode',
        'view_paginated': 'Paginated View (24 books)',
        'view_infinite': 'Infinite Scrolling',
        'activate_darkmode': 'Activate Darkmode 🌙',
        'user_management': 'User Management',
        'new_username': 'New Username',
        'existing_users': 'Existing Users:',
        'user': 'User',
        'confirm_delete_user_text': 'Are you sure you want to delete this user? All of their reading history and stats will be permanently lost! Permanently remove:',
        'notify_user_added': 'successfully created!',
        'notify_user_deleted': 'User deleted',
        'error_user_exists': 'User already exists!',

        # --- Import / Export ---
        'import_export_title': 'Data Import / Export',
        'import_export_subtitle': 'Manage your library through bulk imports or back up your data locally.',
        'settings_importexport_title': 'Import/Export Books',
        'import_file_title': 'File Import',
        'import_file_subtitle': 'Upload your Goodreads export (.csv) or a plain ISBN list (.txt) here.',
        'import_select_file': 'Select File',
        'import_preparing': 'Preparing import...',
        'import_live_protocol': 'Live Protocol:',
        'import_processing': 'Processing',
        'import_notify_loaded': 'books successfully loaded.',
        'import_error_no_data': 'No valid book data or ISBNs found!',
        'import_error_read': 'Error reading file',
        'import_log_start': 'STARTING IMPORT PROCESS',
        'import_log_end': 'IMPORT FINISHED',
        'import_source_local': 'Local file',
        'import_log_skipped': 'Skipped (Already in DB)',
        'import_msg_success': 'imported',
        'import_msg_duplicates': 'duplicates',
        'import_msg_errors': 'errors',
        'export_file_title': 'File Export',
        'export_file_subtitle': 'Secure your entire book collection including all reading progress, reviews, and shelf data in a universal CSV file. Ideal for Excel or backups.',
        'export_btn_text': 'Export Library (.csv)',
        'export_empty_library': 'Your library is empty. There is nothing to export!',
        'export_success': 'Export successfully generated!',
        'export_failed': 'Error exporting data',

        # --- Backup & Reset ---
        'settings_backup_title': 'Data Backup & System',
        'settings_backup_subtitle': 'Backup (Database & Media)',
        'settings_backup_desc': 'Secure your complete database as well as all downloaded book covers and author images in a single ZIP file.',
        'settings_backup_download': 'Create Backup',
        'settings_backup_restore': 'Restore Backup (.zip)',
        'settings_reset_title': 'Danger Zone',
        'settings_reset_desc': 'This will irrevocably delete ALL books, authors, covers, and settings. The application will be reset to its factory state.',
        'settings_reset_confirm_title': '🔒 Really delete everything permanently?',
        'settings_reset_confirm_desc': 'This action cannot be undone. All data will be lost unless you have downloaded a backup beforehand.',
        'settings_reset_execute': 'Yes, perform factory reset',
        'settings_reset_btn': 'Reset Application',

        # --- Dynamic Lengths & Languages ---
        'pages_under_200': '< 200 pages',
        'pages_200_to_400': '200 - 400 pages',
        'pages_400_to_600': '400 - 600 pages',
        'pages_over_600': '> 600 pages',
        'pages_unknown': 'Unknown Length',
        'lang_de': 'German',
        'lang_en': 'English',

        # --- Fun Project (Suggestions) ---
        'book_suggestion_title': 'What do you want to read?',
        'book_suggestion_all': 'Any (From all genres)',
        'book_suggestion_hint': 'How about:',
        'book_suggestion_click_to_open': '(Click on the card to open the book directly)',
        'book_suggestion_empty': 'No matching books found in your library!',
        'roll_book': 'Roll Book',
        'settings_suggestion_title': 'Random Book Suggestions',
        'settings_suggestion_desc': 'Activates a dice icon in the main navigation to get random reading inspiration from your library.',
    }
}

# =========================================================================
# 2. RUNTIME SYSTEM VARIABLEN & HILFSFUNKTIONEN
# =========================================================================
aktuelle_sprache = 'de'


def t(key: str) -> str:
    """Hilfsfunktion zum Holen des übersetzten Textes."""
    return TRANSLATIONS[aktuelle_sprache].get(key, key)


# Zentrale Sprachübersetzungen für Buchsprachen
LANGUAGES = {
    'de': {
        'de': 'Deutsch', 'en': 'Englisch', 'fr': 'Französisch', 
        'es': 'Spanisch', 'it': 'Italienisch', 'ja': 'Japanisch'
    },
    'en': {
        'de': 'German', 'en': 'English', 'fr': 'French', 
        'es': 'Spanish', 'it': 'Italian', 'ja': 'Japanese'
    }
}

# Monatsnamen für die Datumsformatierung
MONTHS = {
    'de': {
        1: 'Januar', 2: 'Februar', 3: 'März', 4: 'April', 5: 'Mai', 6: 'Juni',
        7: 'Juli', 8: 'August', 9: 'September', 10: 'Oktober', 11: 'November', 12: 'Dezember'
    },
    'en': {
        1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
        7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'
    }
}


def format_book_language(lang_code: str) -> str:
    """Übersetzt ein Sprachkürzel passend zur aktuellen App-Sprache."""
    if not lang_code:
        return ""
    code_lower = lang_code.lower()
    return LANGUAGES[aktuelle_sprache].get(code_lower, lang_code.upper())


def format_localized_date(date_str: str) -> str:
    """Wandelt YYYY-MM-DD in ein ausgeschriebenes, lokalisiertes Datum um."""
    if not date_str:
        return ""
    try:
        # Komplettes Datum: YYYY-MM-DD
        if len(date_str) == 10:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            monat_name = MONTHS[aktuelle_sprache][dt.month]
            if aktuelle_sprache == 'de':
                return f"{dt.day}. {monat_name} {dt.year}"  # 21. März 1999
            else:
                return f"{monat_name} {dt.day}, {dt.year}"  # March 21, 1999
        
        # Nur Jahr und Monat: YYYY-MM
        elif len(date_str) == 7:
            dt = datetime.strptime(date_str, '%Y-%m')
            monat_name = MONTHS[aktuelle_sprache][dt.month]
            return f"{monat_name} {dt.year}"
            
    except Exception:
        pass
    return date_str  # Fallback auf Rohdaten bei Fehlern


# Locales für das Quasar UI Framework (NiceGUI Basis)
QUASAR_LOCALES = {
    'de': {
        'days': ['Sonntag', 'Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag'],
        'daysShort': ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'],
        'months': ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'],
        'monthsShort': ['Jan', 'Feb', 'Mrz', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
    },
    'en': {
        'days': ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
        'daysShort': ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
        'months': ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
        'monthsShort': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    }
}


def hole_kalender_locale(lang_code='de'):
    """Liefert das passende Quasar-Locale-Objekt für den Kalender."""
    return QUASAR_LOCALES.get(lang_code, QUASAR_LOCALES['de'])