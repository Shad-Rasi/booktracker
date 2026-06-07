import sqlite3
from pathlib import Path

DB_PATH = Path("data/db2.db")
DB_PATH.parent.mkdir(exist_ok=True)

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")  # Aktiviert Verknüpfungsschutz für relationale DBs
    return conn

def init_db():
    """Initialisiert die erweiterten Tabellenstrukturen und legt Standorte sowie Standard-User an."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. TABELLE: Benutzer
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
        """)
        
        # 2. TABELLE: Standorte / Bücherregale (Global im Haus)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT
            );
        """)
        
        # 3. TABELLE: Globale Buchdaten (Erweitert um all deine neuen Wunschfelder!)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                subtitle TEXT,
                author TEXT,
                translator TEXT,
                narrator TEXT,
                illustrator TEXT,
                editor TEXT,
                isbn_13 TEXT UNIQUE,
                isbn_10 TEXT,
                publisher TEXT,
                published_date TEXT,
                language TEXT,
                description TEXT,
                pages INTEGER DEFAULT 0,
                special BOOLEAN DEFAULT FALSE,
                is_series BOOLEAN DEFAULT FALSE,
                series_name TEXT,
                series_number INTEGER DEFAULT 0,
                location_id INTEGER,
                FOREIGN KEY (location_id) REFERENCES locations(id) -- ON SET NULL entfernt
            );
        """)
        
        # 4. TABELLE: Benutzer-Buch-Verknüpfung (Format, Besitzstatus, Menge)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_books (
                user_id INTEGER,
                book_id INTEGER,
                status TEXT DEFAULT 'UNREAD', -- UNREAD, READING, READ
                rating INTEGER DEFAULT 0,
                format TEXT DEFAULT 'PHYSICAL', -- PHYSICAL, AUDIOBOOK, EBOOK
                ownership TEXT DEFAULT 'OWNED', -- OWNED, BORROWED, LENT
                quantity INTEGER DEFAULT 1,
                started_at TEXT,
                finished_at TEXT,
                PRIMARY KEY (user_id, book_id),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE
            );
        """)
        
        # Standard-User anlegen
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO users (name) VALUES (?)", ("Robin",))
            cursor.execute("INSERT INTO users (name) VALUES (?)", ("Stella",))
            
        # Standard-Regale anlegen
        cursor.execute("SELECT COUNT(*) FROM locations")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO locations (name) VALUES (?)", ("Wohnzimmer Hauptregal",))
            cursor.execute("INSERT INTO locations (name) VALUES (?)", ("Nachttisch",))
            cursor.execute("INSERT INTO locations (name) VALUES (?)", ("Arbeitszimmer",))
            
        conn.commit()

def get_user_id_by_name(username):
    """Holt die ID des ausgewählten Benutzers aus der Datenbank."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE name = ?", (username,))
        row = cursor.fetchone()
        return row[0] if row else None

def lade_buecher_aus_db(user_id):
    """Holt die Liste aller Bücher inklusive der neuen globalen Details und User-Stati."""
    with get_connection() as conn:
        cursor = conn.cursor()
        query = '''
            SELECT 
                b.id, b.title, b.author, b.isbn_13, b.pages, 
                ub.status, ub.rating, b.special,
                b.is_series, b.series_name, b.series_number, 
                ub.started_at, ub.finished_at,
                b.subtitle, b.translator, b.narrator, b.illustrator, b.editor,
                b.isbn_10, b.publisher, b.published_date, b.language, b.description,
                ub.format, ub.ownership, ub.quantity, b.location_id, l.name
            FROM books b
            LEFT JOIN user_books ub ON b.id = ub.book_id AND ub.user_id = ?
            LEFT JOIN locations l ON b.location_id = l.id
            ORDER BY b.id DESC
        '''
        cursor.execute(query, (user_id,))
        return cursor.fetchall()

def speichere_buch_in_db(active_id, user_id, book_data, user_data):
    """Fügt ein Buch mit allen erweiterten Metadaten hinzu oder aktualisiert es."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if active_id is None:
            # Neues Buch in die globale Tabelle einfügen
            cursor.execute(
                """INSERT OR IGNORE INTO books 
                   (title, subtitle, author, translator, narrator, illustrator, editor,
                    isbn_13, isbn_10, publisher, published_date, language, description,
                    pages, special, is_series, series_name, series_number, location_id) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (book_data['title'], book_data.get('subtitle'), book_data['author'],
                 book_data.get('translator'), book_data.get('narrator'), book_data.get('illustrator'), book_data.get('editor'),
                 book_data['isbn'], book_data.get('isbn_10'), book_data.get('publisher'),
                 book_data.get('published_date'), book_data.get('language'), book_data.get('description'),
                 book_data['pages'], book_data['special'], book_data['is_series'], 
                 book_data['series_name'], book_data['series_number'], book_data.get('location_id'))
            )
            # ID des (entweder neu angelegten oder ignorierten) Buches holen
            cursor.execute("SELECT id FROM books WHERE isbn_13 = ?", (book_data['isbn'],))
            book_id = cursor.fetchone()[0]
        else:
            book_id = active_id
            # Bestehendes Buch aktualisieren
            cursor.execute(
                """UPDATE books SET 
                   title = ?, subtitle = ?, author = ?, translator = ?, narrator = ?, illustrator = ?, editor = ?,
                   isbn_13 = ?, isbn_10 = ?, publisher = ?, published_date = ?, language = ?, description = ?,
                   pages = ?, special = ?, is_series = ?, series_name = ?, series_number = ?, location_id = ?
                   WHERE id = ?""",
                (book_data['title'], book_data.get('subtitle'), book_data['author'],
                 book_data.get('translator'), book_data.get('narrator'), book_data.get('illustrator'), book_data.get('editor'),
                 book_data['isbn'], book_data.get('isbn_10'), book_data.get('publisher'),
                 book_data.get('published_date'), book_data.get('language'), book_data.get('description'),
                 book_data['pages'], book_data['special'], book_data['is_series'], 
                 book_data['series_name'], book_data['series_number'], book_data.get('location_id'), book_id)
            )
        
        # Benutzer-spezifische Daten (inklusive Format, Besitz, Menge) wegspeichern
        cursor.execute(
            """INSERT OR REPLACE INTO user_books 
               (user_id, book_id, status, rating, format, ownership, quantity, started_at, finished_at) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, book_id, user_data['status'], user_data['rating'], 
             user_data.get('format', 'PHYSICAL'), user_data.get('ownership', 'OWNED'),
             user_data.get('quantity', 1), user_data['started_at'], user_data['finished_at'])
        )
        conn.commit()

def loesche_buch_aus_db(book_id):
    """Entfernt das Buch und die Verknüpfungen komplett über Kaskadierung."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_books WHERE book_id = ?", (book_id,))
        cursor.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()

def lade_alle_regale():
    """Lädt alle verfügbaren Regale für Formular-Dropdowns."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM locations ORDER BY name ASC;")
        return cursor.fetchall()
    
def lade_alle_user():
    """Holt alle registrierten Benutzer aus der Datenbank für das Auswahlmenü."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM users ORDER BY id ASC;")
        return cursor.fetchall()