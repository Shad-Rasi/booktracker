import os
import sqlite3
from pathlib import Path
from datetime import datetime  # Neu für die Zeitstempel
import requests
from nicegui import ui

# 1. HARDWARE-INITIALISIERUNG & CONFIG
DB_PATH = Path("data/medien.db") # Erneut umbenannt, um Cache-Probleme zu vermeiden
DB_PATH.parent.mkdir(exist_ok=True) 

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
AKTIVE_BUCH_ID = None  

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT,
            isbn_13 TEXT UNIQUE,
            pages INTEGER,
            special BOOLEAN DEFAULT FALSE,
            is_series BOOLEAN DEFAULT FALSE,
            series_name TEXT,
            series_number INTEGER
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    
    # NEU: started_at und finished_at in die User-Tabelle eingefügt
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_books (
            user_id INTEGER,
            book_id INTEGER,
            status TEXT DEFAULT 'UNREAD',
            rating INTEGER DEFAULT 0,
            started_at TEXT,    -- NEU (Format: YYYY-MM-DD)
            finished_at TEXT,   -- NEU (Format: YYYY-MM-DD)
            PRIMARY KEY (user_id, book_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(book_id) REFERENCES books(id)
        )
    ''')
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (name) VALUES (?)", ("Ich",))
        cursor.execute("INSERT INTO users (name) VALUES (?)", ("Meine Frau",))
    conn.commit()
    conn.close()

init_db()


def get_current_user_id():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE name = ?", (user_select.value,))
    user_id = cursor.fetchone()[0]
    conn.close()
    return user_id


# 2. LOGIKBAUSTEINE / FUNKTIONEN

def daten_laden():
    if not user_select.value:
        return []
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Zeitstempel aus user_books in die Abfrage aufnehmen
    query = '''
        SELECT b.id, b.title, b.author, b.isbn_13, b.pages, ub.status, ub.rating, b.special,
               b.is_series, b.series_name, b.series_number, ub.started_at, ub.finished_at
        FROM books b
        LEFT JOIN user_books ub ON b.id = ub.book_id AND ub.user_id = ?
        ORDER BY b.id DESC
    '''
    cursor.execute(query, (get_current_user_id(),))
    rows = cursor.fetchall()
    conn.close()
    
    # Datum für die Anzeige formatieren (aus 2026-06-04 wird 04.06.2026)
    def fmt_date(iso_str):
        if not iso_str: return "-"
        try:
            return datetime.strptime(iso_str, "%Y-%m-%d").strftime("%d.%m.%Y")
        except:
            return iso_str

    return [{
        'id': r[0],
        'title': r[1],
        'author': r[2],
        'isbn_13': r[3],
        'pages': r[4],
        'status': r[5] if r[5] else 'UNREAD',
        'rating': f"{r[6]} ⭐" if (r[6] and r[6] > 0) else "Keine",
        'special': "Ja" if r[7] else "Nein",
        'reihe_anzeige': f"{r[9]} (Band {r[10]})" if r[8] and r[9] else "Nein",
        'started_at': r[11] if r[11] else "",   # Rohes ISO-Format für Bearbeitungsmaske
        'finished_at': r[12] if r[12] else "", # Rohes ISO-Format für Bearbeitungsmaske
        'lesedauer_anzeige': f"Start: {fmt_date(r[11])} | Ende: {fmt_date(r[12])}" # Für die Tabelle
    } for r in rows]


def user_wechsel():
    tabelle.rows = daten_laden()
    ui.notify(f"Ansicht gewechselt zu: {user_select.value}", type='info')


def isbn_suchen():
    isbn_wert = isbn_input.value.strip().replace("-", "")
    if not isbn_wert:
        ui.notify('Bitte zuerst eine ISBN eingeben!', type='warning')
        return
    ui.notify(f'Suche nach ISBN {isbn_wert}...', type='info')
    try:
        url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn_wert}&key={GOOGLE_API_KEY}"
        response = requests.get(url, timeout=5)
        daten = response.json()
        if "items" not in daten and "error" not in daten:
            url = f"https://www.googleapis.com/books/v1/volumes?q={isbn_wert}&key={GOOGLE_API_KEY}"
            response = requests.get(url, timeout=5)
            daten = response.json()
            
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
        seiten_input.value = volume_info.get("pageCount", 0)
        
        series_info = daten["items"][0].get("seriesInfo", {})
        if series_info:
            series_checkbox.value = True
            reihenname_input.value = series_info.get("bookDisplayNumber", "")
        else:
            series_checkbox.value = False
            reihenname_input.value = ""
            band_input.value = 0
            
        ui.notify('Buchdaten erfolgreich geladen!', type='positive')
    except Exception as e:
        ui.notify(f'Fehler bei der API-Abfrage: {str(e)}', type='negative')


def buch_speichern():
    global AKTIVE_BUCH_ID
    
    title = titel_input.value.strip()
    author = autor_input.value.strip()
    isbn = isbn_input.value.strip().replace("-", "")
    pages = int(seiten_input.value or 0)
    status = status_input.value
    rating = int(rating_input.value)
    special_edition = special_checkbox.value
    is_series = series_checkbox.value
    series_name = reihenname_input.value.strip() if is_series else ""
    series_number = int(band_input.value or 0) if is_series else 0
    
    # Datumsfelder aus dem HMI auslesen
    start_datum = start_date_input.value
    ende_datum = end_date_input.value
    
    # AUTOMATIK-LOGIK: Wenn Felder leer sind, stempeln wir das aktuelle Datum anhand des Status
    heute = datetime.now().strftime("%Y-%m-%d")
    if status == 'READING' and not start_datum:
        start_datum = heute
    elif status == 'READ':
        if not start_datum:
            start_datum = heute  # Falls direkt als gelesen markiert
        if not ende_datum:
            ende_datum = heute

    if not title:
        ui.notify('Titel darf nicht leer sein!', type='warning')
        return
        
    current_user_id = get_current_user_id()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        if AKTIVE_BUCH_ID is None:
            cursor.execute(
                """INSERT OR IGNORE INTO books 
                   (title, author, isbn_13, pages, special, is_series, series_name, series_number) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (title, author, isbn, pages, special_edition, is_series, series_name, series_number)
            )
            cursor.execute("SELECT id FROM books WHERE isbn_13 = ?", (isbn,))
            book_id = cursor.fetchone()[0]
        else:
            book_id = AKTIVE_BUCH_ID
            cursor.execute(
                """UPDATE books SET 
                   title = ?, author = ?, isbn_13 = ?, pages = ?, special = ?, 
                   is_series = ?, series_name = ?, series_number = ? 
                   WHERE id = ?""",
                (title, author, isbn, pages, special_edition, is_series, series_name, series_number, book_id)
            )
        
        # Zeitstempel mit in user_books wegspeichern
        cursor.execute(
            """INSERT OR REPLACE INTO user_books (user_id, book_id, status, rating, started_at, finished_at) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (current_user_id, book_id, status, rating, start_datum, ende_datum)
        )
        conn.commit()
        ui.notify(f'"{title}" erfolgreich gespeichert!', type='positive')
        
    except Exception as e:
        ui.notify(f'Fehler beim Speichern: {str(e)}', type='negative')
    finally:
        conn.close()
    
    # Maske zurücksetzen
    AKTIVE_BUCH_ID = None
    titel_input.value = ""
    autor_input.value = ""
    isbn_input.value = ""
    seiten_input.value = 0
    status_input.value = 'UNREAD'
    rating_input.value = 0
    special_checkbox.value = False
    series_checkbox.value = False
    reihenname_input.value = ""
    band_input.value = 0
    start_date_input.value = ""
    end_date_input.value = ""
    
    speicher_button.set_text('Im Regal speichern')
    speicher_button.classes('bg-green-600', remove='bg-orange-600')
    tabelle.rows = daten_laden()


def buch_loeschen(book_id, title):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM user_books WHERE book_id = ?", (book_id,))
        cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
        ui.notify(f'"{title}" komplett gelöscht!', type='warning')
    except Exception as e:
        ui.notify(f'Fehler beim Löschen: {str(e)}', type='negative')
    finally:
        conn.close()
    tabelle.rows = daten_laden()


def buch_bearbeiten(row):
    global AKTIVE_BUCH_ID
    AKTIVE_BUCH_ID = row['id']
    
    isbn_input.value = row['isbn_13']
    titel_input.value = row['title']
    autor_input.value = row['author']
    seiten_input.value = row['pages']
    status_input.value = row['status']
    
    if "⭐" in row['rating']:
        rating_input.value = int(row['rating'].split()[0])
    else:
        rating_input.value = 0
        
    special_checkbox.value = True if row['special'] == "Ja" else False
    
    if row['reihe_anzeige'] != "Nein":
        series_checkbox.value = True
        parts = row['reihe_anzeige'].split(" (Band ")
        reihenname_input.value = parts[0]
        band_input.value = int(parts[1].replace(")", ""))
    else:
        series_checkbox.value = False
        reihenname_input.value = ""
        band_input.value = 0
        
    # Zeitstempel zurück in die Maske laden (für manuelle Korrekturen)
    start_date_input.value = row['started_at']
    end_date_input.value = row['finished_at']
    
    speicher_button.set_text('Änderungen speichern')
    speicher_button.classes('bg-orange-600')
    ui.notify(f'"{row["title"]}" wird jetzt bearbeitet.', type='info')


# 3. VISUALISIERUNG / HMI (NiceGUI Oberfläche)
with ui.header().classes('background bg-slate-800 text-white p-4 flex justify-between items-center'):
    ui.label('📚 Booktracker').classes('text-2xl font-bold')
    user_select = ui.select(options=['Ich', 'Meine Frau'], value='Ich', on_change=user_wechsel).classes('w-48 bg-white rounded px-2 text-black')

with ui.element('div').classes('w-full p-6 max-w-7xl mx-auto'):
    
    ui.label('Buch erfassen / bearbeiten').classes('text-xl font-bold text-slate-700 mb-2')
    
    with ui.card().classes('w-full p-4 bg-slate-50 mb-6 shadow-sm'):
        with ui.row().classes('w-full items-center gap-4'):
            isbn_input = ui.input(label='ISBN scannen / eingeben').classes('w-64')
            ui.button('Suchen', on_click=isbn_suchen).classes('bg-blue-600 text-white')
            
        ui.separator().classes('my-4')
        
        with ui.row().classes('w-full gap-4'):
            titel_input = ui.input(label='Buchtitel').classes('flex-1')
            autor_input = ui.input(label='Autor(en)').classes('flex-1')
            
        with ui.row().classes('w-full items-center gap-6 mt-2'):
            seiten_input = ui.number(label='Seitenzahl', value=0, format='%d').classes('w-32')
            
            status_input = ui.select(
                options={'UNREAD': 'Ungelesen', 'READING': 'Wird gerade gelesen', 'READ': 'Abgeschlossen'},
                value='UNREAD', label='Lesestatus'
            ).classes('w-48')
            
            rating_input = ui.select(
                options={0: 'Keine Bewertung', 1: '1 Stern', 2: '2 Sterne', 3: '3 Sterne', 4: '4 Sterne', 5: '5 Sterne'}, 
                value=0, label='Meine Bewertung'
            ).classes('w-48')
            
            special_checkbox = ui.checkbox('Special Edition')

        # REIHE FÜR DIE REIHEN-LOGIK
        with ui.row().classes('w-full items-center gap-6 mt-2 p-2 bg-blue-50/30 rounded border border-blue-100'):
            series_checkbox = ui.checkbox('Teil einer Buchreihe')
            reihenname_input = ui.input(label='Name der Reihe').classes('w-80').bind_visibility_from(series_checkbox, 'value')
            band_input = ui.number(label='Band Nummer', value=0, format='%d').classes('w-28').bind_visibility_from(series_checkbox, 'value')

        # --- NEUE REIHE FÜR DIE ZEITSTEMPEL (HMI) ---
        with ui.row().classes('w-full items-center gap-6 mt-4 p-2 bg-emerald-50/30 rounded border border-emerald-100'):
            ui.label('📅 Zeitstempel (optional / Automatik):').classes('text-sm font-bold text-emerald-800')
            
            # NiceGUI HTML5-Datums-Eingabefelder (tippen oder über Kalender-Icon auswählen)
            start_date_input = ui.input(label='Lesestart (JJJJ-MM-TT)').classes('w-48').props('type=date')
            end_date_input = ui.input(label='Leseende (JJJJ-MM-TT)').classes('w-48').props('type=date')
            
            speicher_button = ui.button('Im Regal speichern', on_click=buch_speichern).classes('bg-green-600 text-white ml-auto px-6')

    ui.separator().classes('my-6')

    ui.label('Mein Regalbestand').classes('text-xl font-bold text-slate-700 mb-2')
    
    columns = [
        {'name': 'title', 'label': 'Titel', 'field': 'title', 'required': True, 'align': 'left'},
        {'name': 'author', 'label': 'Autor', 'field': 'author', 'align': 'left'},
        {'name': 'isbn_13', 'label': 'ISBN', 'field': 'isbn_13', 'align': 'left'},
        {'name': 'pages', 'label': 'Seiten', 'field': 'pages', 'sortable': True},
        {'name': 'reihe', 'label': 'Buchreihe', 'field': 'reihe_anzeige', 'sortable': True, 'align': 'left'},
        {'name': 'status', 'label': 'Status', 'field': 'status', 'sortable': True},
        {'name': 'lesedauer', 'label': 'Lesezeitraum', 'field': 'lesedauer_anzeige', 'align': 'left'}, # NEU IN TABELLE
        {'name': 'rating', 'label': 'Bewertung', 'field': 'rating', 'sortable': True},
        {'name': 'special', 'label': 'Special', 'field': 'special'},
        {'name': 'actions', 'label': 'Aktionen', 'field': 'actions', 'align': 'center'},
    ]

    tabelle = ui.table(columns=columns, rows=daten_laden(), row_key='id').classes('w-full shadow-md')
    
    tabelle.add_slot('body-cell-actions', '''
        <q-td :props="props">
            <q-btn flat round dense icon="edit" color="blue" @click="$parent.$emit('edit_row', props.row)"></q-btn>
            <q-btn flat round dense icon="delete" color="red" @click="$parent.$emit('delete_row', props.row)"></q-btn>
        </q-td>
    ''')
    
    tabelle.on('edit_row', lambda msg: buch_bearbeiten(msg.args))
    tabelle.on('delete_row', lambda msg: buch_loeschen(msg.args['id'], msg.args['title']))

ui.run(port=8080, title="Booktracker", reload=True)