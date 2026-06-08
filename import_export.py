import csv
import io
import asyncio
from nicegui import ui, context
import database
import layout
from layout import basis_layout
from translations import t
import book_api

def status_uebersetzen(goodreads_shelf):
    mapping = {
        'read': 'READ',
        'currently-reading': 'READING',
        'to-read': 'UNREAD'
    }
    return mapping.get(goodreads_shelf.lower().strip(), 'UNREAD')

def isbn_bereinigen(isbn_raw):
    if not isbn_raw:
        return None
    cleaned = isbn_raw.replace('=', '').replace('"', '').strip()
    return cleaned if cleaned.isdigit() else None

async def import_queue_verarbeiten(buecher_liste, fortschritt_label, fortschritt_balken, aktueller_client):
    """Arbeitet die Liste ab, überspringt bereits vorhandene ISBNs anhand der DB-Einträge."""
    gesamtzahl = len(buecher_liste)
    erfolgreich = 0
    uebersprungen = 0
    
    alle_user_buecher = database.lade_buecher_aus_db(layout.aktiver_user_id)
    existierende_isbns = set()
    for buch in alle_user_buecher:
        if buch[3]:  
            existierende_isbns.add(str(buch[3]).strip())
    
    for index, import_buch in enumerate(buecher_liste):
        isbn = import_buch['isbn']
        aktuelle_nummer = index + 1
        prozent = int((aktuelle_nummer / gesamtzahl) * 100)
        
        if isbn and str(isbn).strip() in existierende_isbns:
            uebersprungen += 1
            fortschritt_label.set_text(f'Überspringe Duplikat {aktuelle_nummer} von {gesamtzahl} ({prozent}%) | ISBN: {isbn}')
            fortschritt_balken.set_value(aktuelle_nummer / gesamtzahl)
            fortschritt_label.update()
            fortschritt_balken.update()
            continue
            
        fortschritt_label.set_text(f'Verarbeite Buch {aktuelle_nummer} von {gesamtzahl} ({prozent}%) | ISBN: {isbn}')
        fortschritt_balken.set_value(aktuelle_nummer / gesamtzahl)
        fortschritt_label.update()
        fortschritt_balken.update()
        
        book_data = {
            'title': import_buch['title'], 'subtitle': '', 'author': import_buch['author'],
            'translator': '', 'narrator': '', 'illustrator': '', 'editor': '',
            'isbn': isbn if isbn else '', 'isbn_10': '', 'publisher': '', 'published_date': '',
            'language': 'de', 'description': '', 'pages': 0,
            'special': False, 'is_series': False, 'series_name': '', 'series_number': 0, 'location_id': None
        }
        
        user_data = {
            'status': import_buch['status'], 'rating': import_buch['rating'],
            'format': 'PHYSICAL', 'ownership': 'OWNED', 'quantity': 1, 'started_at': '', 'finished_at': ''
        }
        
        if isbn:
            api_daten = await book_api.isbn_suche_async(isbn)
            if api_daten:
                book_data['title'] = api_daten['title']
                book_data['subtitle'] = api_daten['subtitle']
                book_data['author'] = api_daten['author']
                book_data['publisher'] = api_daten['publisher']
                book_data['published_date'] = api_daten['published_date']
                book_data['language'] = api_daten['language']
                book_data['description'] = api_daten['description']
                book_data['pages'] = api_daten['pages']
                import_buch['cover_url'] = api_daten['cover_url']

        try:
            neue_id = database.speichere_buch_in_db(None, layout.aktiver_user_id, book_data, user_data)
            if neue_id and import_buch.get('cover_url'):
                database.lade_und_speichere_cover(neue_id, import_buch['cover_url'])
            erfolgreich += 1
        except Exception as db_ex:
            print(f"Datenbankfehler bei Import von ISBN {isbn}: {str(db_ex)}")
            
        await asyncio.sleep(1.5)
        
    meldung = f'Fertig! {erfolgreich} neu importiert.'
    if uebersprungen > 0:
        meldung += f' ({uebersprungen} Duplikate übersprungen).'
        
    fortschritt_label.set_text(meldung)
    fortschritt_label.update()
    
    with aktueller_client:
        ui.notify(meldung, type='positive' if erfolgreich > 0 else 'info')
        await asyncio.sleep(3)
        ui.navigate.to('/')

async def handle_upload(e, status_container, upload_element):
    try:
        upload_datei = e.file
        bytes_inhalt = await upload_datei.read()
        content = bytes_inhalt.decode('utf-8')
        buecher_liste = []
        
        if 'ISBN13' in content or 'Title' in content:
            csv_file = io.StringIO(content)
            reader = csv.DictReader(csv_file)
            for row in reader:
                title = row.get('Title')
                author = row.get('Author')
                isbn13 = isbn_bereinigen(row.get('ISBN13'))
                shelf = row.get('Exclusive Shelf')
                rating = row.get('My Rating')
                
                if not title and not isbn13:
                    continue
                    
                buecher_liste.append({
                    'title': title if title else f"ISBN: {isbn13}",
                    'author': author if author else t('unknown_author'),
                    'isbn': isbn13,
                    'status': status_uebersetzen(shelf) if shelf else 'UNREAD',
                    'rating': int(rating) if rating and rating.isdigit() else 0
                })
        else:
            zeilen = content.splitlines()
            for zeile in zeilen:
                isbn_rein = isbn_bereinigen(zeile)
                if isbn_rein:
                    buecher_liste.append({
                        'title': f"ISBN: {isbn_rein}",
                        'author': t('unknown_author'),
                        'isbn': isbn_rein,
                        'status': 'UNREAD',
                        'rating': 0
                    })
            
        if not buecher_liste:
            ui.notify('Keine gültigen Buchdaten oder ISBNs gefunden!', type='warning')
            return
            
        ui.notify(f'{len(buecher_liste)} Bücher eingelesen. Starte API-Abruf...', type='info')
        upload_element.set_visibility(False)
        
        with status_container:
            lbl = ui.label('Bereite Import vor...').classes('text-sm text-slate-600 mt-2')
            progress = ui.linear_progress(value=0.0, show_value=False, color='blue').classes('w-full mt-1')

        aktueller_client = context.client
        asyncio.create_task(import_queue_verarbeiten(buecher_liste, lbl, progress, aktueller_client))
        
    except Exception as ex:
        ui.notify(f'Fehler beim Lesen der Datei: {str(ex)}', type='negative')

# --- NEU: DYNAMISCHER CSV-EXPORT ---
def exportiere_buecher():
    """Lädt alle Bücher des Nutzers aus der DB und generiert einen CSV-Download im Arbeitsspeicher."""
    try:
        buecher_daten = database.lade_buecher_aus_db(layout.aktiver_user_id)
        
        if not buecher_daten:
            ui.notify('Deine Bibliothek ist noch leer. Es gibt nichts zu exportieren!', type='warning')
            return

        # Wir definieren die Spaltenüberschriften für das CSV-Backup
        fieldnames = [
            'ID', 'Title', 'Subtitle', 'Author', 'ISBN13', 'ISBN10', 'Pages', 
            'Publisher', 'PublishedDate', 'Language', 'Status', 'Rating', 
            'Format', 'Ownership', 'Quantity', 'Location', 'StartedAt', 'FinishedAt'
        ]

        # String-Buffer im Speicher erzeugen (verhindert temporäre Dateien auf dem Server)
        output = io.StringIO()
        # Dialekt 'excel' sorgt für Standard-Komma-Trennung und saubere Quotes bei Texten mit Kommas
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        
        # Header schreiben
        writer.writerow(fieldnames)
        
        # Datensätze transformieren und schreiben
        for b in buecher_daten:
            # Hier entpacken wir exakt nach deiner Struktur aus lade_buecher_aus_db:
            # b[0]=id, b[1]=title, b[2]=author, b[3]=isbn_13, b[4]=pages, b[5]=status, b[6]=rating...
            row = [
                b[0],   # ID
                b[1],   # Title
                b[13],  # Subtitle
                b[2],   # Author
                b[3],   # ISBN13
                b[18],  # ISBN10
                b[4],   # Pages
                b[19],  # Publisher
                b[20],  # PublishedDate
                b[21],  # Language
                b[5],   # Status
                b[6],   # Rating
                b[23],  # Format
                b[24],  # Ownership
                b[25],  # Quantity
                b[27],  # Location_Name (Regal)
                b[11],  # StartedAt
                b[12]   # FinishedAt
            ]
            # Eventuelle None-Werte durch leere Strings ersetzen, damit die CSV sauber bleibt
            row = ["" if x is None else str(x) for x in row]
            writer.writerow(row)

        # Den Inhalt des Buffers als Bytes konvertieren
        csv_bytes = output.getvalue().encode('utf-8')
        output.close()

        # NiceGUI Trigger für den Browser-Download
        # Der Dateiname bekommt einen dynamischen Suffix (könnte man noch mit Datum verfeinern)
        ui.download(csv_bytes, filename="meine_bibliothek_export.csv")
        ui.notify('Export erfolgreich generiert!', type='positive')

    except Exception as ex:
        ui.notify(f'Fehler beim Exportieren: {str(ex)}', type='negative')


@ui.page('/import')
def import_export_seite():
    with basis_layout('import_export'):
        ui.label('Daten Import / Export').classes('text-2xl font-bold text-slate-700 mb-2')
        ui.label('Verwalte deine Bibliothek durch Massen-Importe oder sichere deine Daten lokal.').classes('text-sm text-slate-500 mb-6')
        
        # Layout-Raster für zwei Karten nebeneinander (Import und Export)
        with ui.element('div').classes('w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-6'):
            
            # LINKER KASTEN: IMPORT (Dein bestehender Code)
            with ui.card().classes('p-6 bg-slate-50 border border-slate-200 shadow-sm flex flex-col justify-between'):
                with ui.element('div'):
                    ui.label('Datei-Import').classes('text-lg font-bold text-slate-700 mb-2')
                    ui.label('Lade hier deinen Goodreads-Export (.csv) oder eine reine ISBN-Liste (.txt) hoch.').classes('text-xs text-slate-500 mb-4')
                    status_container = ui.element('div').classes('w-full')
                
                upload_field = ui.upload(
                    label='Datei auswählen',
                    auto_upload=True
                ).props('accept=.csv,.txt').classes('w-full mt-2')
                
                upload_field.on_upload(lambda e: handle_upload(e, status_container, upload_field))

            # RECHTER KASTEN: EXPORT (Neu hinzugefügt)
            with ui.card().classes('p-6 bg-slate-50 border border-slate-200 shadow-sm flex flex-col justify-between'):
                with ui.element('div'):
                    ui.label('Datei-Export').classes('text-lg font-bold text-slate-700 mb-2')
                    ui.label('Sichere deine komplette Büchersammlung inklusive aller Lesestände, Rezensionen und Regaldaten in einer universellen CSV-Datei. Ideal für Excel oder Backups.').classes('text-xs text-slate-500 mb-6')
                
                # Der Button ruft die Export-Logik auf
                ui.button(
                    'Bibliothek exportieren (.csv)', 
                    icon='download', 
                    on_click=exportiere_buecher
                ).classes('w-full bg-slate-700 text-white py-2 mt-4')

    # --- NEU: REGAL / STANDORT VERWALTUNG ---
        ui.separator().classes('my-6')
        ui.label(t('manage_locations')).classes('text-2xl font-bold text-slate-700 mb-2')
        
        with ui.card().classes('w-full max-w-4xl p-6 bg-slate-50 border border-slate-200 shadow-sm'):
            ui.label(t('add_new_location')).classes('text-lg font-bold text-slate-700 mb-2')
            
            # Eingabezeile für neues Regal
            with ui.row().classes('w-full items-center gap-4 no-wrap'):
                neues_regal_input = ui.input(label=t('location_name')).classes('flex-1 bg-white px-2 rounded shadow-sm')
                
                async def regal_speichern():
                    name = neues_regal_input.value.strip()
                    if not name:
                        ui.notify(t('error_empty_name'), type='warning')
                        return
                    
                    # Abstecher in die DB
                    erfolg = database.speichere_regal_in_db(name)
                    if erfolg:
                        ui.notify(f'"{name}" {t("notify_location_added")}', type='positive')
                        neues_regal_input.value = ''
                        # Aktualisiert die Liste der Regale im UI
                        regal_liste_refresh.refresh()
                    else:
                        ui.notify(t('error_location_exists'), type='negative')
                
                ui.button(icon='add', on_click=regal_speichern).classes('bg-slate-700 text-white p-3 rounded')

            ui.separator().classes('my-4')
            ui.label(t('existing_locations')).classes('text-sm font-bold text-slate-500 mb-2')
            
            # Eine dynamische Liste, die sich bei jedem neuen Regal aktualisiert
            @ui.refreshable
            def regal_liste_refresh():
                regale = database.lade_alle_regale()
                
                with ui.element('div').classes('flex flex-wrap gap-2'):
                    for r_id, r_name in regale:
                        # Ein schicker Container für Name + Löschbutton
                        with ui.element('div').classes('flex items-center bg-slate-200 rounded-full pl-3 pr-1 py-1 gap-2 shadow-sm'):
                            ui.label(r_name).classes('text-sm font-medium text-slate-700')
                            
                            # Die Lösch-Logik mit Sicherheitsabfrage
                            async def regal_loeschen_klick(id_zu_loeschen=r_id, name_zu_loeschen=r_name):
                                with ui.dialog() as dialog, ui.card().classes('p-4'):
                                    ui.label(f'"{name_zu_loeschen}" {t("confirm_delete_location_text")}').classes('text-sm text-slate-600 mb-4')
                                    with ui.row().classes('w-full justify-end gap-2'):
                                        ui.button(t('cancel'), on_click=dialog.close).classes('text-slate-500').props('flat')
                                        
                                        async def definitiv_loeschen():
                                            if database.loesche_regal_aus_db(id_zu_loeschen):
                                                ui.notify(f'"{name_zu_loeschen}" {t("notify_location_deleted")}', type='info')
                                                regal_liste_refresh.refresh()
                                            dialog.close()
                                            
                                        ui.button(t('delete'), on_click=definitiv_loeschen).classes('bg-red-500 text-white')
                                dialog.open()

                            # Der kleine rote X-Button am Ende des Badges
                            ui.button(icon='close', on_click=regal_loeschen_klick).props('round dense flat size=sm').classes('text-red-500 hover:bg-red-100')
            
            regal_liste_refresh()       