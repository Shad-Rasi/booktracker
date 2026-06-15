import os
import httpx
import requests
import sqlite3
import random
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/database.db")
DB_PATH.parent.mkdir(exist_ok=True)

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")  # Aktiviert Verknüpfungsschutz für relationale DBs
    return conn

def init_db():
    """Initialisiert die erweiterten Tabellenstrukturen in der exakt richtigen Reihenfolge."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Benutzer (Basis-Tabelle, hat keine Fremdschlüssel)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
        """)
        
        # 2. Standorte (Basis-Tabelle, hat keine Fremdschlüssel)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT
            );
        """)
        
        # 3. Genres (WICHTIG: Muss VOR book_genres kommen, da user_id genutzt wird)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS genres (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                UNIQUE(user_id, name),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );
        """)

        # 4. Globale Buchdaten (Nutzt locations)
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
                ownership TEXT DEFAULT 'OWNED',
                format TEXT DEFAULT 'PHYSICAL',
                quantity INTEGER DEFAULT 1,
                FOREIGN KEY (location_id) REFERENCES locations(id)
            );
        """)

        # 5. Buch-Genres Koppel-Tabelle (Nutzt books UND genres -> MUSS dahinter stehen!)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS book_genres (
                book_id INTEGER NOT NULL,
                genre_id INTEGER NOT NULL,
                PRIMARY KEY (book_id, genre_id),
                FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
                FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE
            );
        """)
        
        # 6. Benutzer-Buch-Verknüpfung (Nutzt users UND books)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_books (
                user_id INTEGER,
                book_id INTEGER,
                status TEXT DEFAULT 'UNREAD',
                rating INTEGER DEFAULT 0,
                started_at TEXT,
                finished_at TEXT,
                PRIMARY KEY (user_id, book_id),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE
            );
        """)

        # 7. Autoren
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS authors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                bio TEXT,
                birth_date TEXT,
                death_date TEXT,
                image_url TEXT,
                local_image_path TEXT
            );
        """)

        # 8. Benutzer-Einstellungen
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            view_mode TEXT DEFAULT 'PAGINATED',
            dark_mode BOOLEAN DEFAULT 0,
            buch_vorschlag_aktiv BOOLEAN DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        # 9. Lesezyklus
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reading_cycles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'READING',
            started_at TEXT,
            finished_at TEXT,
            rating INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE
        )
        """)

        # 10. Leseprotokoll
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reading_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cycle_id INTEGER NOT NULL,
            log_date TEXT NOT NULL,
            progress_page INTEGER NOT NULL,
            pages_read INTEGER NOT NULL,
            FOREIGN KEY(cycle_id) REFERENCES reading_cycles(id) ON DELETE CASCADE
        )
        """)
        
        # Standard-User anlegen
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO users (name) VALUES (?)", ("Booktracker User",))
            
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
        
def speichere_user_in_db(name):
    """Legt einen neuen User an und verknüpft ihn automatisch mit allen vorhandenen Büchern."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Prüfen, ob der User bereits existiert
            cursor.execute("SELECT id FROM users WHERE name = ?", (name,))
            if cursor.fetchone():
                return False
                
            # 2. Den neuen User in die Tabelle schreiben
            cursor.execute("INSERT INTO users (name) VALUES (?)", (name,))
            neue_user_id = cursor.lastrowid # Die gerade erzeugte ID abgreifen
            
            # 3. AUTOMATISIERUNG: Alle globalen Bücher ermitteln
            cursor.execute("SELECT id FROM books")
            alle_buch_ids = [row[0] for row in cursor.fetchall()]
            
            # 4. Jedes Buch mit dem Status 'UNREAD' für den neuen User verknüpfen
            for b_id in alle_buch_ids:
                cursor.execute("""
                    INSERT OR IGNORE INTO user_books (user_id, book_id, status) 
                    VALUES (?, ?, 'UNREAD')
                """, (neue_user_id, b_id))
                
            conn.commit()
            return True
    except Exception as e:
        print(f"Fehler beim Erstellen des Users und Verknüpfen der Bücher: {str(e)}")
        return False

def loesche_user_aus_db(user_id):
    """Löscht einen Benutzer und kaskadiert alle seine Daten (Logs, Zyklen, Verknüpfungen)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            # Da sqlite foreign keys aktiv sind (PRAGMA), müssen wir verknüpfte Logs, 
            # Zyklen und user_books manuell oder über Kaskade löschen. 
            # Sicherer Weg zu Fuß, falls ON DELETE CASCADE nicht überall definiert war:
            
            # 1. Alle cycle_ids dieses Users holen
            cursor.execute("SELECT id FROM reading_cycles WHERE user_id = ?", (user_id,))
            cycle_ids = [row[0] for row in cursor.fetchall()]
            
            if cycle_ids:
                platzhalter = ",".join(["?"] * len(cycle_ids))
                # Logs löschen
                cursor.execute(f"DELETE FROM reading_logs WHERE cycle_id IN ({platzhalter})", cycle_ids)
            
            # Zyklen löschen
            cursor.execute("DELETE FROM reading_cycles WHERE user_id = ?", (user_id,))
            # User-Buchverknüpfungen löschen
            cursor.execute("DELETE FROM user_books WHERE user_id = ?", (user_id,))
            # Den User selbst löschen
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Fehler beim Löschen des Benutzers: {e}")
            return False


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
                b.format, b.ownership, b.quantity, b.location_id, l.name
            FROM books b
            LEFT JOIN user_books ub ON b.id = ub.book_id AND ub.user_id = ?
            LEFT JOIN locations l ON b.location_id = l.id
            ORDER BY LOWER(b.title) ASC
        '''
        cursor.execute(query, (user_id,))
        return cursor.fetchall()

def speichere_buch_in_db(active_id, user_id, book_data, user_data):
    """Fügt ein Buch mit allen erweiterten Metadaten hinzu oder aktualisiert es.
    
    Format, Besitzstatus und Menge sind jetzt global beim Buch gespeichert!
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        if active_id is None:
            # 1. NEU: ownership, format und quantity direkt hier beim Erstellen mitgeben
            cursor.execute(
                """INSERT OR IGNORE INTO books 
                   (title, subtitle, author, translator, narrator, illustrator, editor,
                    isbn_13, isbn_10, publisher, published_date, language, description,
                    pages, special, is_series, series_name, series_number, location_id,
                    ownership, format, quantity) -- HIERHER VERSCHOBEN
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (book_data['title'], book_data.get('subtitle'), book_data['author'],
                 book_data.get('translator'), book_data.get('narrator'), book_data.get('illustrator'), book_data.get('editor'),
                 book_data['isbn'], book_data.get('isbn_10'), book_data.get('publisher'),
                 book_data.get('published_date'), book_data.get('language'), book_data.get('description'),
                 book_data['pages'], book_data['special'], book_data['is_series'], 
                 book_data['series_name'], book_data['series_number'], book_data.get('location_id'),
                 user_data.get('ownership', 'OWNED'), user_data.get('format', 'PHYSICAL'), user_data.get('quantity', 1))
            )
            # ID des Buches holen
            cursor.execute("SELECT id FROM books WHERE isbn_13 = ?", (book_data['isbn'],))
            book_id = cursor.fetchone()[0]
        else:
            book_id = active_id
            # 2. NEU: Auch beim Update die Werte in der 'books' Tabelle aktualisieren
            cursor.execute(
                """UPDATE books SET 
                   title = ?, subtitle = ?, author = ?, translator = ?, narrator = ?, illustrator = ?, editor = ?,
                   isbn_13 = ?, isbn_10 = ?, publisher = ?, published_date = ?, language = ?, description = ?,
                   pages = ?, special = ?, is_series = ?, series_name = ?, series_number = ?, location_id = ?,
                   ownership = ?, format = ?, quantity = ? -- HIERHER VERSCHOBEN
                   WHERE id = ?""",
                (book_data['title'], book_data.get('subtitle'), book_data['author'],
                 book_data.get('translator'), book_data.get('narrator'), book_data.get('illustrator'), book_data.get('editor'),
                 book_data['isbn'], book_data.get('isbn_10'), book_data.get('publisher'),
                 book_data.get('published_date'), book_data.get('language'), book_data.get('description'),
                 book_data['pages'], book_data['special'], book_data['is_series'], 
                 book_data['series_name'], book_data['series_number'], book_data.get('location_id'),
                 user_data.get('ownership', 'OWNED'), user_data.get('format', 'PHYSICAL'), user_data.get('quantity', 1), book_id)
            )
        
        # 3. BEREINIGT: user_books enthält jetzt NUR noch die echten User-Zustände
        cursor.execute(
            """INSERT OR REPLACE INTO user_books 
               (user_id, book_id, status, rating, started_at, finished_at) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, book_id, user_data['status'], user_data['rating'], 
             user_data['started_at'], user_data['finished_at'])
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

def hole_autoren_id_durch_name(user_id, autor_name):
    """
    Sucht die ID eines Autors anhand seines exakten Namens.
    Stellt sicher, dass der Autor in der 'authors'-Tabelle existiert, 
    wenn er in den Büchern des Benutzers vorkommt.
    """
    if not autor_name:
        return None
        
    sauberer_name = autor_name.strip()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Versuch: Schauen, ob der Autor bereits existiert
        cursor.execute("SELECT id FROM authors WHERE name = ?", (sauberer_name,))
        row = cursor.fetchone()
        if row:
            return row[0]
            
        # 2. Sicherheitsnetz: Falls die authors-Tabelle verzögert gefüllt wird, 
        # legen wir den Eintrag schnell an (wird durch lade_alle_autoren_aus_db ohnehin synchronisiert)
        try:
            cursor.execute("INSERT OR IGNORE INTO authors (name) VALUES (?)", (sauberer_name,))
            conn.commit()
            
            # ID des neu erzeugten Autors zurückliefern
            cursor.execute("SELECT id FROM authors WHERE name = ?", (sauberer_name,))
            row = cursor.fetchone()
            return row[0] if row else None
        except sqlite3.Error:
            return None

def lade_buecher_von_autor(user_id, autoren_name):
    """Holt alle Bücher eines spezifischen Autors für den aktuellen User inklusive Erscheinungsdatum."""
    with get_connection() as conn:
        cursor = conn.cursor()
        # Wir fügen b.published_date als 8. Feld (Index 7) hinzu
        cursor.execute("""
            SELECT b.id, b.title, b.author, b.isbn_13, b.pages, ub.status, ub.rating, b.published_date, b.ownership
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
        
        # 1. Deinen bestehenden Zyklus updaten
        cursor.execute("""
            UPDATE reading_cycles 
            SET status = 'READ', finished_at = ? 
            WHERE user_id = ? AND book_id = ? AND status = 'READING'
        """, (end_datum, user_id, book_id))
        
        # 2. NEU: Jetzt auch die Haupttabelle für die Statistiken füttern
        cursor.execute("""
            UPDATE user_books 
            SET status = 'READ', finished_at = ? 
            WHERE user_id = ? AND book_id = ?
        """, (end_datum, user_id, book_id))
        
        conn.commit()

def initialisiere_reread_status(user_id, book_id):
    """Beendet offene Zyklen, setzt das Startdatum auf heute und löscht das alte Enddatum."""
    heute = datetime.now().strftime('%Y-%m-%d')
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Alten Zyklus in reading_cycles ordnungsgemäß schließen, falls noch offen
        cursor.execute("""
            UPDATE reading_cycles 
            SET status = 'READ', finished_at = ? 
            WHERE user_id = ? AND book_id = ? AND status = 'READING'
        """, (heute, user_id, book_id))
        
        # 2. In user_books den Status auf READING setzen, started_at eintragen und finished_at LEEREN
        cursor.execute("""
            UPDATE user_books 
            SET status = 'READING', started_at = ?, finished_at = NULL 
            WHERE user_id = ? AND book_id = ?
        """, (heute, user_id, book_id))
        
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
    """Holt alle Tage, an denen der User gelesen hat, inklusive Buch-Details und IDs."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT rl.log_date, b.title, rl.pages_read, b.id, rc.id, rl.progress_page -- <-- HIER progress_page ERGÄNZT
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

def lade_globales_logbuch_fuer_buch(book_id, user_id):
    """Holt alle Leseprotokolle eines Buchs für das globale Logbuch."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT rl.log_date, rl.progress_page, rl.pages_read, rc.status
            FROM reading_logs rl
            JOIN reading_cycles rc ON rl.cycle_id = rc.id
            WHERE rc.book_id = ? AND rc.user_id = ?
            ORDER BY rl.log_date DESC, rl.progress_page DESC
        """, (book_id, user_id))
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

def aktualisiere_buch_metadaten(book_id, metadaten):
    """
    Aktualisiert gezielt die Metadaten eines bereits existierenden Buches,
    inklusive der Reiheninformationen, wenn diese noch leer sind.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE books
            SET description = COALESCE(NULLIF(description, ''), ?),
                publisher = COALESCE(NULLIF(publisher, ''), ?),
                published_date = COALESCE(NULLIF(published_date, ''), ?),
                pages = CASE WHEN pages IS NULL OR pages <= 1 THEN ? ELSE pages END,
                is_series = CASE WHEN (series_name IS NULL OR series_name = '') AND ? != '' THEN 1 ELSE is_series END,
                series_name = COALESCE(NULLIF(series_name, ''), ?),
                series_number = CASE WHEN series_number IS NULL OR series_number = 0 THEN ? ELSE series_number END
            WHERE id = ?
        """, (
            metadaten.get('description', ''),
            metadaten.get('publisher', ''),
            metadaten.get('published_date', ''),
            metadaten.get('pages', 1),
            metadaten.get('series_name', ''), # Für die Aktivierung des 'is_series' Flags
            metadaten.get('series_name', ''),
            metadaten.get('series_number', 0),
            book_id
        ))
        conn.commit()

def lade_user_settings(user_id):
    """Lädt die UI-Einstellungen des Benutzers und sichert sie gegen ungültige IDs ab."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # CRITICAL REPAIR: Prüfen, ob der User überhaupt in der Haupttabelle existiert
            cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
            user_existiert = cursor.fetchone()
            
            # Falls nicht (z.B. nach Löschung oder bei leerem RAM-Startwert 1),
            # legen wir keine fälschlichen Settings an, sondern fangen das ab.
            if not user_existiert:
                # Wir holen uns stattdessen die erste echte ID, die existiert
                cursor.execute("SELECT id FROM users LIMIT 1")
                erster_user = cursor.fetchone()
                if erster_user:
                    user_id = erster_user[0]
                else:
                    # Totale Absicherung: Wenn die DB komplett leer ist, geben wir Standard-Dummy-Settings zurück
                    return {'dark_mode': False, 'view_mode': 'PAGINATED', 'buch_vorschlag_aktiv': False}

            # Jetzt erst führen wir das Insert aus – absolut Foreign-Key-sicher!
            cursor.execute("INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)", (user_id,))
            conn.commit()
            
            # Die eigentlichen Settings auslesen (Erweitert um buch_vorschlag_aktiv)
            cursor.execute("SELECT dark_mode, view_mode, buch_vorschlag_aktiv FROM user_settings WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            
            # Mapping für die Rückgabe
            return {
                'dark_mode': bool(row[0]) if row else False,
                'view_mode': row[1] if row and row[1] else 'PAGINATED',
                'buch_vorschlag_aktiv': bool(row[2]) if row and row[2] else False  # NEU
            }
    except Exception as e:
        print(f"Fehler in lade_user_settings für User {user_id}: {str(e)}")
        return {'dark_mode': False, 'view_mode': 'PAGINATED', 'buch_vorschlag_aktiv': False}

def speichere_user_settings(user_id, view_mode, dark_mode, vorschlag_aktiv):
    """Speichert die UI-Einstellungen und den Spaßprojekt-Status dauerhaft ab."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO user_settings (user_id, view_mode, dark_mode, buch_vorschlag_aktiv)
            VALUES (?, ?, ?, ?)
        """, (user_id, view_mode, int(dark_mode), int(vorschlag_aktiv)))
        conn.commit()

def datenbank_strukturen_leeren():
    """Löscht den Inhalt aller Tabellen, falls die Datei zur Laufzeit gesperrt ist."""
    import sqlite3
    # Nutzt direkt dein Path-Objekt und macht einen String daraus
    db_pfad = str(DB_PATH) if 'DB_PATH' in globals() else os.path.join('data', 'db2.db')
    if not os.path.exists(db_pfad):
        return
        
    conn = sqlite3.connect(db_pfad)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tabellen = cursor.fetchall()
        for tabelle in tabellen:
            tabelle_name = tabelle[0]
            if tabelle_name != 'sqlite_sequence':
                cursor.execute(f"DROP TABLE IF EXISTS {tabelle_name};")
        conn.commit()
    except Exception as e:
        print(f"Fehler beim SQL-Leeren: {e}")
    finally:
        conn.close()

def lade_alle_genres(user_id):
    """Holt alle für den User definierten Genres sortiert aus der DB (für Einstellungen & Dropdowns)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM genres WHERE user_id = ? ORDER BY name ASC", (user_id,))
        return cursor.fetchall()

def speichere_genre_in_db(user_id, name):
    """Speichert ein neues Genre global in der Liste, wenn es nicht doppelt ist."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO genres (user_id, name) VALUES (?, ?)", (user_id, name))
            conn.commit()
            return True
        except:
            return False  # Doppelter Eintrag (Unique-Constraint) abgefangen

def loesche_genre_aus_db(genre_id):
    """Löscht ein Genre vollständig aus der globalen Liste. 
    
    Durch ON DELETE CASCADE in der Koppeltabelle 'book_genres' werden alle 
    Verbindungen zu den Büchern automatisch und sauber von SQLite mitgelöscht.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM genres WHERE id = ?", (genre_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Fehler beim Löschen des Genres: {e}")
            return False

def lade_genres_eines_buches(book_id):
    """Holt alle zugeordneten Genres für ein bestimmtes Buch (gibt eine Liste von Strings zurück)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT g.name 
            FROM genres g
            JOIN book_genres bg ON g.id = bg.genre_id
            WHERE bg.book_id = ?
            ORDER BY g.name ASC
        """, (book_id,))
        return [row[0] for row in cursor.fetchall()]

def lade_andere_user_mit_genres(aktuelle_user_id):
    """Holt alle User, die nicht der aktuelle User sind und Genres besitzen."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT u.id, u.name 
            FROM users u
            JOIN genres g ON u.id = g.user_id
            WHERE u.id != ?
        """, (aktuelle_user_id,))
        return cursor.fetchall()

def kopiere_genres_von_user(von_user_id, zu_user_id):
    """Kopiert die Genres eines Users zu einem anderen User, falls sie nicht existieren."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Hole alle Genre-Namen des Quell-Users
        cursor.execute("SELECT name FROM genres WHERE user_id = ?", (von_user_id,))
        genres_quell_user = cursor.fetchall()
        
        # 2. Füge sie beim Ziel-User ein (UNIQUE Constraint verhindert Duplikate)
        for (g_name,) in genres_quell_user:
            cursor.execute("""
                INSERT OR IGNORE INTO genres (user_id, name) 
                VALUES (?, ?)
            """, (zu_user_id, g_name))
            
        conn.commit()

def aktualisiere_buch_genres(book_id, genre_namen_liste, user_id):
    """Löscht alle alten Zuordnungen des Buches und setzt die neuen Genres aus der Auswahl."""
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            # 1. Alle alten Verbindungen für dieses Buch kappen
            cursor.execute("DELETE FROM book_genres WHERE book_id = ?", (book_id,))
            
            # 2. Die IDs der ausgewählten Genres holen und neu verknüpfen
            for g_name in genre_namen_liste:
                cursor.execute("SELECT id FROM genres WHERE user_id = ? AND name = ?", (user_id, g_name))
                row = cursor.fetchone()
                if row:
                    genre_id = row[0]
                    cursor.execute("INSERT OR IGNORE INTO book_genres (book_id, genre_id) VALUES (?, ?)", (book_id, genre_id))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Fehler beim Zuordnen der Genres: {e}")
            return False
        
def hole_genre_verteilung_stats(user_id):
    """Holt die Anzahl der Bücher pro Genre für die Statistik-Charts."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT g.name, COUNT(bg.book_id) as anzahl
            FROM genres g
            JOIN book_genres bg ON g.id = bg.genre_id
            JOIN user_books ub ON bg.book_id = ub.book_id
            WHERE g.user_id = ? AND ub.user_id = ?
            GROUP BY g.id
            ORDER BY anzahl DESC
        """, (user_id, user_id))
        return cursor.fetchall()
        
def hole_zufaelliges_buch_vorschlag(user_id, genre_name=None):
    """
    Holt ein zufälliges Buch (OWNED oder BORROWED) des Benutzers, das noch NICHT gelesen wurde.
    Falls das gezogene Buch Teil einer Reihe ist, wird automatisch das ERSTE 
    noch nicht gelesene Buch ('status' != 'READ') dieser Reihe zurückgegeben.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # 1. BASIS-QUERY: Wir holen nur UNGELESENE/ANGELESENE Bücher
        query = """
            SELECT b.id, b.title, b.is_series, b.series_name
            FROM books b
            JOIN user_books ub ON b.id = ub.book_id
        """
        params = [user_id]
        
        # Falls ein spezifisches Genre gefiltert werden soll
        if genre_name and genre_name != 'ALL':
            query += """
                JOIN book_genres bg ON b.id = bg.book_id
                JOIN genres g ON bg.genre_id = g.id
                WHERE ub.user_id = ? 
                  AND ub.status != 'READ' -- NEU: Bereits gelesene direkt ausschließen!
                  AND b.ownership IN ('OWNED', 'BORROWED') -- REPARIERT: b.ownership statt ub.ownership
                  AND g.name = ?
            """
            params.append(genre_name)
        else:
            query += """
                WHERE ub.user_id = ? 
                  AND ub.status != 'READ' -- NEU: Bereits gelesene direkt ausschließen!
                  AND b.ownership IN ('OWNED', 'BORROWED')
            """
            
        cursor.execute(query, params)
        alle_buecher = cursor.fetchall()
        
        if not alle_buecher:
            return None
            
        # 2. ZUFALLS-POOL: Ein garantiert ungelesenes Buch blind ziehen
        zufalls_buch = random.choice(alle_buecher)
        b_id, b_title, is_series, series_name = zufalls_buch
        
        # 3. REIHEN-LOGIK: Wenn das Buch zu einer Reihe gehört, prüfen wir die Reihenfolge
        if is_series and series_name:
            cursor.execute("""
                SELECT b.id, b.title, b.series_number, ub.status
                FROM books b
                JOIN user_books ub ON b.id = ub.book_id
                WHERE ub.user_id = ? AND b.series_name = ?
                ORDER BY CAST(b.series_number AS REAL) ASC, b.series_number ASC
            """, (user_id, series_name))
            reihen_buecher = cursor.fetchall()
            
            for rb in reihen_buecher:
                rb_id, rb_title, _, rb_status = rb
                if rb_status != 'READ':
                    return {
                        'id': rb_id, 
                        'title': rb_title, 
                        'is_series': True, 
                        'series_name': series_name,
                        'genres': lade_genres_eines_buches(rb_id)
                    }
                    
        # Wenn es keine Reihe ist, bleibt es beim gezogenen, ungelesenen Buch.
        return {
            'id': b_id, 
            'title': b_title, 
            'is_series': False, 
            'series_name': None,
            'genres': lade_genres_eines_buches(b_id)
        }