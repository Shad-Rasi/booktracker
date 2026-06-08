import os
import httpx
import requests
import sqlite3
from datetime import datetime
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

        # 5. TABELLE: Autoren
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS authors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                bio TEXT,
                birth_date TEXT,
                death_date TEXT,
                image_url TEXT,
                local_image_path TEXT
            )
        """)

        # 1. Der Lesedurchgang (Erlaubt unbegrenztes Wiederholen)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reading_cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'READING', -- READING, READ, ABANDONED
            started_at TEXT,                        -- YYYY-MM-DD
            finished_at TEXT,                       -- YYYY-MM-DD
            rating INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(book_id) REFERENCES books(id)
        )
        """)

        # 2. Das tägliche Leseprotokoll (Für den Kalender und Seiten-Statistiken)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reading_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id INTEGER NOT NULL,              -- Verknüpft mit dem aktuellen Durchgang
            log_date TEXT NOT NULL,                 -- YYYY-MM-DD (Wann wurde gelesen?)
            progress_page INTEGER NOT NULL,         -- Bis zu welcher Seite wurde gelesen?
            pages_read INTEGER NOT NULL,            -- Wie viele Seiten wurden in DIESER Session gelesen?
            FOREIGN KEY(cycle_id) REFERENCES reading_cycles(id) ON DELETE CASCADE
        )
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
            ORDER BY LOWER(b.title) ASC
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

        return book_id

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

def speichere_regal_in_db(name, description=""):
    """Fügt ein neues Bücherregal/Standort in die Datenbank ein."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO locations (name, description) VALUES (?, ?)", (name, description))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False # Name existiert schon (UNIQUE)

def loesche_regal_aus_db(location_id):
    """Setzt die location_id bei betroffenen Büchern auf NULL und löscht das Regal."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            # 1. Bücher in diesem Regal wieder freistellen
            cursor.execute("UPDATE books SET location_id = NULL WHERE location_id = ?", (location_id,))
            # 2. Das Regal selbst löschen
            cursor.execute("DELETE FROM locations WHERE id = ?", (location_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Fehler beim Löschen des Regals: {e}")
            return False

def lade_alle_autoren_aus_db(user_id):
    """
    Holt alle einzigartigen Autorennamen aus den Büchern des Users
    und gleicht sie mit der authors-Tabelle ab.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        # Wir holen erst alle Autoren, die der User überhaupt in seiner Bibliothek hat
        cursor.execute("""
            SELECT DISTINCT b.author 
            FROM books b
            JOIN user_books ub ON b.id = ub.book_id
            WHERE ub.user_id = ? AND b.author IS NOT NULL AND b.author != ''
            ORDER BY b.author ASC
        """, (user_id,))
        vorhandene_autoren = [row[0] for row in cursor.fetchall()]
        
        # Wir stellen sicher, dass diese Autoren alle in der 'authors'-Tabelle existieren
        for autoren_name in vorhandene_autoren:
            try:
                cursor.execute("INSERT OR IGNORE INTO authors (name) VALUES (?)", (autoren_name.strip(),))
            except:
                pass
        conn.commit()
        
        # Jetzt holen wir die vollständigen Datensätze aus der authors-Tabelle
        # Trick: Nur die Autoren, von denen der User auch wirklich Bücher hat!
        platzhalter = ",".join(["?"] * len(vorhandene_autoren))
        if not vorhandene_autoren:
            return []
            
        cursor.execute(f"""
            SELECT id, name, bio, image_url, local_image_path 
            FROM authors 
            WHERE name IN ({platzhalter})
            ORDER BY name ASC
        """, vorhandene_autoren)
        return cursor.fetchall()

def lade_autor_details(autor_id):
    """Holt die Metadaten eines einzelnen Autors."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, bio, birth_date, death_date, image_url, local_image_path FROM authors WHERE id = ?", (autor_id,))
        return cursor.fetchone()

def lade_buecher_von_autor(user_id, autoren_name):
    """Holt alle Bücher eines spezifischen Autors für den aktuellen User."""
    with get_connection() as conn:
        cursor = conn.cursor()
        # Hier nutzen wir deine bestehende Spaltenstruktur aus lade_buecher_aus_db
        # b[0]=id, b[1]=title, b[2]=author, b[3]=isbn_13, b[4]=pages, b[5]=status...
        cursor.execute("""
            SELECT b.id, b.title, b.author, b.isbn_13, b.pages, ub.status, ub.rating
            FROM books b
            JOIN user_books ub ON b.id = ub.book_id
            WHERE ub.user_id = ? AND b.author = ?
        """, (user_id, autoren_name))
        return cursor.fetchall()

def aktualisiere_autor_in_db(autor_id, bio, birth, death, image_url=None):
    """Speichert die Metadaten und lädt das Profilbild lokal herunter."""
    local_path = None
    
    if image_url:
        # Ordner für Autorenfotos sicherstellen
        storage_dir = os.path.join('data', 'authors')
        os.makedirs(storage_dir, exist_ok=True)
        
        filename = f"author_{autor_id}.jpg"
        target_path = os.path.join(storage_dir, filename)
        
        try:
            # Bild synchron herunterladen
            with httpx.Client() as client:
                res = client.get(image_url, timeout=10.0)
                if res.status_code == 200 and len(res.content) > 1000:
                    with open(target_path, 'wb') as f:
                        f.write(res.content)
                    # Der Pfad, den NiceGUI über statische Routen ausliest
                    local_path = f"/authors/{filename}"
        except Exception as e:
            print(f"Fehler beim Download des Autorenfotos: {e}")

    with get_connection() as conn:
        cursor = conn.cursor()
        if local_path:
            cursor.execute("""
                UPDATE authors 
                SET bio = ?, birth_date = ?, death_date = ?, image_url = ?, local_image_path = ? 
                WHERE id = ?
            """, (bio, birth, death, image_url, local_path, autor_id))
        else:
            cursor.execute("""
                UPDATE authors 
                SET bio = ?, birth_date = ?, death_date = ?, image_url = ? 
                WHERE id = ?
            """, (bio, birth, death, image_url, autor_id))
        conn.commit()

def lade_aktuelle_buecher(user_id):
    """Holt alle Bücher, die der User aktuell auf dem Status 'READING' hat."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT b.id, b.title 
            FROM books b
            JOIN user_books ub ON b.id = ub.book_id
            WHERE ub.user_id = ? AND ub.status = 'READING'
            ORDER BY b.title ASC
        """, (user_id,))
        return cursor.fetchall()

def hole_oder_erstelle_aktiven_zyklus(user_id, book_id, wunsch_datum=None):
    """Holt den aktiven Zyklus oder erstellt einen neuen mit dem passenden Startdatum."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM reading_cycles 
            WHERE user_id = ? AND book_id = ? AND status = 'READING'
        """, (user_id, book_id))
        row = cursor.fetchone()
        
        if row:
            return row[0]
            
        # Wenn kein Wunschdatum übergeben wurde (z.B. normaler Klick), nimm heute
        if not wunsch_datum:
            wunsch_datum = datetime.now().strftime('%Y-%m-%d')
            
        cursor.execute("""
            INSERT INTO reading_cycles (user_id, book_id, status, started_at) 
            VALUES (?, ?, 'READING', ?)
        """, (user_id, book_id, wunsch_datum))
        conn.commit()
        return cursor.lastrowid

def hole_letzte_seite_aus_logs(cycle_id):
    """Ermittelt den letzten bekannten Seitenstand dieses Durchgangs."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT progress_page FROM reading_logs 
            WHERE cycle_id = ? 
            ORDER BY log_date DESC, id DESC LIMIT 1
        """, (cycle_id,))
        row = cursor.fetchone()
        return row[0] if row else 0

def hole_aktuelle_lesezeiten(user_id, book_id):
    """Holt die Lesezeiten. Nutzt primär Zyklen, fällt bei alten Daten auf user_books zurück."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Globalen Buchstatus und alte Datumsfelder als Backup holen
        cursor.execute("""
            SELECT status, started_at, finished_at 
            FROM user_books 
            WHERE user_id = ? AND book_id = ?
        """, (user_id, book_id))
        status_row = cursor.fetchone()
        
        if not status_row:
            return None, None, None
            
        aktueller_buch_status, alt_start, alt_end = status_row
        
        # 2. Passenden modernen Zyklus suchen
        if aktueller_buch_status == 'READ':
            cursor.execute("""
                SELECT started_at, finished_at, status FROM reading_cycles 
                WHERE user_id = ? AND book_id = ? AND status = 'READ'
                ORDER BY id DESC LIMIT 1
            """, (user_id, book_id))
        else:
            cursor.execute("""
                SELECT started_at, finished_at, status FROM reading_cycles 
                WHERE user_id = ? AND book_id = ? AND status = 'READING'
                ORDER BY id DESC LIMIT 1
            """, (user_id, book_id))
            
        row = cursor.fetchone()
        
        if row:
            return row[0], row[1], row[2]
            
        # --- FALLBACK: Wenn kein moderner Zyklus existiert, alte Daten nutzen ---
        if aktueller_buch_status == 'READ' and (alt_start or alt_end):
            return alt_start, alt_end, 'READ'
        elif aktueller_buch_status == 'READING' and alt_start:
            return alt_start, None, 'READING'
            
        return None, None, None

def schliesse_aktiven_zyklus_ab(user_id, book_id, end_datum=None):
    """Setzt den aktiven Lesezyklus auf 'READ' und trägt das gewählte Enddatum ein."""
    if not end_datum:
        end_datum = datetime.now().strftime('%Y-%m-%d')
        
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE reading_cycles 
            SET status = 'READ', finished_at = ? 
            WHERE user_id = ? AND book_id = ? AND status = 'READING'
        """, (end_datum, user_id, book_id))
        conn.commit()

def trage_lese_log_ein(user_id, book_id, neue_seite, datum_str=None):
    """Trägt eine Lese-Etappe ein und reicht das korrekte Datum an den Zyklus weiter."""
    if not datum_str:
        datum_str = datetime.now().strftime('%Y-%m-%d')
        
    # --- FIX: Hier übergeben wir das datum_str an die Zyklus-Erstellung! ---
    cycle_id = hole_oder_erstelle_aktiven_zyklus(user_id, book_id, wunsch_datum=datum_str)
    alte_seite = hole_letzte_seite_aus_logs(cycle_id)
    
    # Check, ob der User das Startdatum des Zyklus manuell unterbieten will (Sicherheitsnetz)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT started_at FROM reading_cycles WHERE id = ?", (cycle_id,))
        cycle_row = cursor.fetchone()
        if cycle_row and cycle_row[0] > datum_str:
            # Falls ein älteres Log nachgetragen wird, korrigieren wir das Startdatum des Zyklus nach vorne!
            cursor.execute("UPDATE reading_cycles SET started_at = ? WHERE id = ?", (datum_str, cycle_id))
            conn.commit()
    
    gelesene_seiten = neue_seite - alte_seite
    if gelesene_seiten <= 0:
        return False, "Die Seitenzahl muss höher sein als der letzte Stand!"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO reading_logs (cycle_id, log_date, progress_page, pages_read) 
            VALUES (?, ?, ?, ?)
        """, (cycle_id, datum_str, neue_seite, gelesene_seiten))
        conn.commit()
        return True, gelesene_seiten

def hole_kalender_daten_fuer_user(user_id):
    """Holt alle Tage, an denen der User gelesen hat, inklusive Buch-Details und ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT rl.log_date, b.title, rl.pages_read, b.id -- <-- HIER b.id ERGÄNZT!
            FROM reading_logs rl
            JOIN reading_cycles rc ON rl.cycle_id = rc.id
            JOIN books b ON rc.book_id = b.id
            WHERE rc.user_id = ?
            ORDER BY rl.log_date DESC
        """, (user_id,))
        return cursor.fetchall()

def lade_logs_fuer_zyklus(cycle_id):
    """Holt alle Lese-Einträge eines spezifischen Lesezyklus, neueste zuerst."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT log_date, progress_page, pages_read 
            FROM reading_logs 
            WHERE cycle_id = ? 
            ORDER BY log_date DESC, id DESC
        """, (cycle_id,))
        return cursor.fetchall()

def loesche_reading_log_aus_db(log_date, cycle_id, progress_page):
    """Löscht einen spezifischen Lese-Eintrag aus den Logs."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                DELETE FROM reading_logs 
                WHERE log_date = ? AND cycle_id = ? AND progress_page = ?
            """, (log_date, cycle_id, progress_page))
            conn.commit()
            return True
        except Exception as e:
            print(f"Fehler beim Löschen des Logs: {e}")
            return False

def lade_beendete_zyklen(user_id, book_id):
    """Holt alle historisch abgeschlossenen Lesezyklen eines Buches – chronologisch aufsteigend."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, started_at, finished_at, rating 
            FROM reading_cycles 
            WHERE user_id = ? AND book_id = ? AND status = 'READ'
            ORDER BY id ASC -- <-- FIX: Älteste zuerst, damit die ID-Nummerierung stabil bleibt
        """, (user_id, book_id))
        return cursor.fetchall()

def loesche_reading_cycle_aus_db(cycle_id):
    """Löscht einen kompletten Lesezyklus. (Kaskadiert automatisch zu den Logs)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            # Löscht den Zyklus. Gekoppelte Logs fliegen dank FOREIGN KEY automatisch raus.
            cursor.execute("DELETE FROM reading_cycles WHERE id = ?", (cycle_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Fehler beim Löschen des Lesezyklus: {e}")
            return False

def lade_alle_user():
    """Holt alle registrierten Benutzer aus der Datenbank für das Auswahlmenü."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM users ORDER BY id ASC;")
        return cursor.fetchall()
    
COVER_DIR = os.path.join('data', 'covers')

def lade_und_speichere_cover(book_id: int, url: str) -> bool:
    """Lädt ein Bild von einer URL und speichert es lokal als {book_id}.jpg ab."""
    if not url:
        return False
    try:
        response = requests.get(url, timeout=10, stream=True)
        if response.status_code == 200:
            ziel_pfad = os.path.join(COVER_DIR, f"{book_id}.jpg")
            with open(ziel_pfad, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            return True
    except Exception as e:
        print(f"Fehler beim Cover-Download für Buch {book_id}: {e}")
    return False

def hole_cover_url(book_id: int) -> str:
    """Gibt den URL-Pfad für das Cover zurück. Falls nicht existent, ein Platzhalter."""
    lokaler_pfad = os.path.join(COVER_DIR, f"{book_id}.jpg")
    if os.path.exists(lokaler_pfad):
        return f"/covers/{book_id}.jpg"
    # Wenn kein Cover da ist, nutzen wir ein Standard-Bild oder steuern das in der UI aus
    return "/covers/placeholder.jpg"