TRANSLATIONS = {
    'de': {
        'my_shelf': '📚 Mein Regal',
        'add_book': '➕ Buch hinzufügen',
        'edit_book': '📝 Buch bearbeiten',
        'save_in_shelf': 'Im Regal speichern',
        'save_changes': 'Änderungen speichern',
        'cancel': 'Abbrechen',
        'title': 'Buchtitel',
        'author': 'Autor(en)',
        'pages': 'Seiten',
        'status': 'Lesestatus',
        'rating': 'Meine Bewertung',
        'special': 'Special Edition',
        'series': 'Teil einer Buchreihe',
        'series_name': 'Name der Reihe',
        'series_num': 'Band Nummer',
        'start': 'Lesestart',
        'end': 'Leseende',
        'unread': 'Ungelesen',
        'reading': 'Wird gerade gelesen',
        'read': 'Abgeschlossen',
        'back_to_shelf': 'Zurück zum Regal',
        'not_found': 'Buch nicht gefunden!',
        'search': 'Suchen',
        'isbn_label': 'ISBN scannen / eingeben',
        'empty_shelf': 'Dein Regal ist noch leer.',
        'first_book': 'Erstes Buch erfassen',
        'none': 'Keine',
        'unknown_author': 'Unbekannter Autor',
        'stars': 'Sterne',
        'star': 'Stern',
        'delete': 'Löschen',
        'notify_deleted': 'wurde aus dem Regal genommen.',
        'notify_saved': 'Erfolgreich im Regal gespeichert!',
        'notify_isbn_warn': 'Bitte zuerst eine ISBN eingeben!',
        'notify_api_success': 'API-Daten erfolgreich geladen!',
        'notify_api_fail': 'Keine Spuren zu dieser ISBN gefunden.',
        'series_volume': 'Band',
        
        # NEUE KEYS FÜR DEINE ERWEITERUNG:
        'subtitle': 'Untertitel',
        'translator': 'Übersetzer',
        'narrator': 'Erzähler / Sprecher',
        'illustrator': 'Illustrator',
        'editor': 'Herausgeber / Editor',
        'publisher': 'Verlag',
        'published_date': 'Erscheinungsdatum',
        'language': 'Sprache des Buchs',
        'description': 'Beschreibung / Klappentext',
        'quantity': 'Menge',
        'location': 'Standort / Regal',
        'format': 'Format',
        'ownership': 'Besitzstatus',
        
        # Format-Optionen
        'PHYSICAL': '📖 Physisches Buch',
        'AUDIOBOOK': '🎧 Hörbuch',
        'EBOOK': '📱 E-Book',
        
        # Besitz-Optionen
        'OWNED': 'In Besitz',
        'BORROWED': 'Geliehen',
        'LENT': 'Verliehen'
    },
    'en': {
        'my_shelf': '📚 My Shelf',
        'add_book': '➕ Add Book',
        'edit_book': '📝 Edit Book',
        'save_in_shelf': 'Save in Shelf',
        'save_changes': 'Save Changes',
        'cancel': 'Cancel',
        'title': 'Book Title',
        'author': 'Author(s)',
        'pages': 'Pages',
        'status': 'Reading Status',
        'rating': 'My Rating',
        'special': 'Special Edition',
        'series': 'Part of a Series',
        'series_name': 'Series Name',
        'series_num': 'Volume',
        'start': 'Started Reading',
        'end': 'Finished Reading',
        'unread': 'Unread',
        'reading': 'Reading',
        'read': 'Completed',
        'back_to_shelf': 'Back to Shelf',
        'not_found': 'Book not found!',
        'search': 'Search',
        'isbn_label': 'Scan / Enter ISBN',
        'empty_shelf': 'Your shelf is empty.',
        'first_book': 'Add your first book',
        'none': 'None',
        'unknown_author': 'Unknown Author',
        'stars': 'Stars',
        'star': 'Star',
        'delete': 'Delete',
        'notify_deleted': 'was removed from your shelf.',
        'notify_saved': 'Successfully saved to shelf!',
        'notify_isbn_warn': 'Please enter an ISBN first!',
        'notify_api_success': 'API data loaded successfully!',
        'notify_api_fail': 'No traces found for this ISBN.',
        'series_volume': 'Volume',
        
        # NEUE KEYS FÜR DEINE ERWEITERUNG:
        'subtitle': 'Subtitle',
        'translator': 'Translator',
        'narrator': 'Narrator',
        'illustrator': 'Illustrator',
        'editor': 'Editor',
        'publisher': 'Publisher',
        'published_date': 'Publication Date',
        'language': 'Book Language',
        'description': 'Description / Synopsis',
        'quantity': 'Quantity',
        'location': 'Location / Shelf',
        'format': 'Format',
        'ownership': 'Ownership Status',
        
        # Format-Optionen
        'PHYSICAL': '📖 Physical Book',
        'AUDIOBOOK': '🎧 Audiobook',
        'EBOOK': '📱 E-Book',
        
        # Besitz-Optionen
        'OWNED': 'Owned',
        'BORROWED': 'Borrowed',
        'LENT': 'Lent'
    }
}

aktuelle_sprache = 'de'

def t(key: str) -> str:
    """Hilfsfunktion zum Holen des übersetzten Textes"""
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
        from datetime import datetime
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