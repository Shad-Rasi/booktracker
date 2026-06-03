import os
import sqlite3
from pathlib import Path
import requests
from nicegui import ui

# 1. HARDWARE-INITIALISIERUNG (Datenbank einrichten)
DB_PATH = Path("data/regal.db")
DB_PATH.parent.mkdir(exist_ok=True) 

# HIER DEINEN KOPIERTEN GOOGLE-API-KEY EINTRAGEN:
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT,
            isbn_13 TEXT,
            isbn_10 TEXT,       
            pages INTEGER,
            rating INTEGER DEFAULT 0,
            status TEXT DEFAULT 'UNREAD',
            special BOOLEAN DEFAULT FALSE
        )
    ''')
    conn.commit()
    conn.close()

init_db()


# 2. LOGIKBAUSTEINE / FUNKTIONEN

def daten_laden():
    """Liest alle Bücher aus der DB für die HMI-Tabelle."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, author, isbn_13, pages, rating, special FROM books ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    return [{
        'id': r[0],
        'title': r[1],
        'author': r[2],
        'isbn_13': r[3],
        'pages': r[4],
        'rating': f"{r[5]} ⭐" if r[5] > 0 else "Keine",
        'special': "Ja" if r[6] else "Nein"
    } for r in rows]


def isbn_suchen():
    """Fragt die Google Books API ab – jetzt sicher mit API-Schlüssel auth."""
    isbn_wert = isbn_input.value.strip().replace("-", "")
    
    if not isbn_wert:
        ui.notify('Bitte zuerst eine ISBN eingeben!', type='warning')
        return
        
    ui.notify(f'Suche nach ISBN {isbn_wert} (mit API-Key)...', type='info')
    
    try:
        # Wir hängen den &key= Parameter an die URL an
        url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn_wert}&key={GOOGLE_API_KEY}"
        response = requests.get(url, timeout=5)
        daten = response.json()
        
        # Fallback: Freitext-Suche mit Key
        if "items" not in daten and "error" not in daten:
            url = f"https://www.googleapis.com/books/v1/volumes?q={isbn_wert}&key={GOOGLE_API_KEY}"
            response = requests.get(url, timeout=5)
            daten = response.json()
            
        # Debug-Anzeige im Terminal lassen wir zur Sicherheit noch kurz drin
        print("--- API ANTWORT ---")
        print(daten)
        
        if "error" in daten:
            ui.notify(f'Google meldet Fehler: {daten["error"]["message"]}', type='negative')
            return

        if "items" not in daten:
            ui.notify('Kein Buch unter dieser ISBN gefunden!', type='negative')
            return
            
        volume_info = daten["items"][0]["volumeInfo"]
        
        titel_input.value = volume_info.get("title", "Unbekannter Titel")
        
        autoren_liste = volume_info.get("authors", ["Unbekannter Autor"])
        autor_input.value = ", ".join(autoren_liste)
        
        # Die heiß ersehnte Seitenzahl!
        seiten_input.value = volume_info.get("pageCount", 0)
        
        ui.notify('Buchdaten erfolgreich geladen!', type='positive')
        
    except Exception as e:
        ui.notify(f'Fehler bei der API-Abfrage: {str(e)}', type='negative')

def buch_speichern():
    """Schreibt die Daten aus den Eingabefeldern fix in die SQLite-DB."""
    title = titel_input.value.strip()
    author = autor_input.value.strip()
    isbn = isbn_input.value.strip().replace("-", "")
    pages = int(seiten_input.value or 0) # Falls Feld leer ist, nimm 0
    rating = int(rating_input.value)
    special_edition = special_checkbox.value
    
    if not title:
        ui.notify('Titel darf nicht leer sein!', type='warning')
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO books (title, author, isbn_13, pages, rating, special) VALUES (?, ?, ?, ?, ?, ?)",
        (title, author, isbn, pages, rating, special_edition)
    )
    conn.commit()
    conn.close()
    
    ui.notify(f'"{title}" wurde im Regal archiviert!', type='positive')
    
    # Eingabemaske sauber zurücksetzen (0 statt "" für das Zahlenfeld!)
    titel_input.value = ""
    autor_input.value = ""
    isbn_input.value = ""
    seiten_input.value = 0
    rating_input.value = 0
    special_checkbox.value = False
    
    # Tabelle live aktualisieren
    tabelle.rows = daten_laden()

# 3. VISUALISIERUNG / HMI (NiceGUI Oberfläche)
with ui.header().classes('background bg-slate-800 text-white p-4'):
    ui.label('📚 Booktracker').classes('text-2xl font-bold')

with ui.element('div').classes('w-full p-6 max-w-7xl mx-auto'):
    
    # --- EINGABEMASKE (BEDIENPANEL) ---
    ui.label('Neues Buch erfassen').classes('text-xl font-bold text-slate-700 mb-2')
    
    with ui.card().classes('w-full p-4 bg-slate-50 mb-6 shadow-sm'):
        with ui.row().classes('w-full items-center gap-4'):
            # Das primäre Suchfeld
            isbn_input = ui.input(label='ISBN scannen / eingeben').classes('w-64')
            ui.button('Suchen', on_click=isbn_suchen).classes('bg-blue-600 text-white')
            
        ui.separator().classes('my-4')
        
        # Automatisch befüllte oder manuell anpassbare Felder
        with ui.row().classes('w-full gap-4'):
            titel_input = ui.input(label='Buchtitel').classes('flex-1')
            autor_input = ui.input(label='Autor(en)').classes('flex-1')
            
        with ui.row().classes('w-full items-center gap-6 mt-2'):
            seiten_input = ui.number(label='Seitenzahl', value=0, format='%d').classes('w-32')
            
            # DEIN STERNE-RATING (Nativ, simpel von 0 bis 5)
            rating_input = ui.select(
                options={0: 'Keine Bewertung', 1: '1 Stern', 2: '2 Sterne', 3: '3 Sterne', 4: '4 Sterne', 5: '5 Sterne'}, 
                value=0, 
                label='Meine Bewertung'
            ).classes('w-48')
            
            # DEIN SPECIAL-EDITION BIT
            special_checkbox = ui.checkbox('Special Edition / Sammlerstück')
            
            # Speicher-Button
            ui.button('Im Regal speichern', on_click=buch_speichern).classes('bg-green-600 text-white ml-auto px-6')

    ui.separator().classes('my-6')

    # --- DIE BÜCHERTABELLE ---
    ui.label('Mein Regalbestand').classes('text-xl font-bold text-slate-700 mb-2')
    
    columns = [
        {'name': 'title', 'label': 'Titel', 'field': 'title', 'required': True, 'align': 'left'},
        {'name': 'author', 'label': 'Autor', 'field': 'author', 'align': 'left'},
        {'name': 'isbn_13', 'label': 'ISBN', 'field': 'isbn_13', 'align': 'left'},
        {'name': 'pages', 'label': 'Seiten', 'field': 'pages', 'sortable': True},
        {'name': 'rating', 'label': 'Bewertung', 'field': 'rating', 'sortable': True},
        {'name': 'special', 'label': 'Special', 'field': 'special'},
    ]

    tabelle = ui.table(columns=columns, rows=daten_laden(), row_key='id').classes('w-full shadow-md')


# App starten
ui.run(port=8080, title="Booktracker", reload=True)