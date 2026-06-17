import csv
import io
import asyncio
import os
import shutil
import zipfile
from io import BytesIO
from nicegui import ui, context
import database
import layout
import book_api
import translations
from layout import basis_layout
from translations import t

# Helper-Funktionen (bleiben funktional exakt gleich)
def status_uebersetzen(goodreads_shelf):
    mapping = {'read': 'READ', 'currently-reading': 'READING', 'to-read': 'UNREAD'}
    return mapping.get(goodreads_shelf.lower().strip(), 'UNREAD')

def isbn_bereinigen(isbn_raw):
    if not isbn_raw: 
        return None
    cleaned = (isbn_raw.replace('=', '')
                       .replace('"', '')
                       .replace('-', '')
                       .replace('.', '')
                       .replace(' ', '')
                       .strip())
    if cleaned.isdigit() and len(cleaned) in [10, 13]:
        return cleaned
    if len(cleaned) == 10 and cleaned[:9].isdigit() and cleaned[9].upper() == 'X':
        return cleaned.upper()
    return None

async def import_queue_verarbeiten(buecher_liste, fortschritt_label, fortschritt_balken, log_view, aktueller_client):
    gesamtzahl = len(buecher_liste)
    erfolgreich, uebersprungen, fehler = 0, 0, 0
    
    alle_user_buecher = database.lade_buecher_aus_db(layout.aktiver_user_id)
    existierende_isbns = {str(b[3]).strip() for b in alle_user_buecher if b[3]}
    
    with aktueller_client:
        log_view.value = f"🚀 === {t('import_log_start')} ===\n\n"
    
    for index, import_buch in enumerate(buecher_liste):
        isbn = import_buch['isbn']
        aktuelle_nummer = index + 1
        prozent = int((aktuelle_nummer / gesamtzahl) * 100)
        
        with aktueller_client:
            fortschritt_balken.set_value(aktuelle_nummer / gesamtzahl)
            fortschritt_balken.update()
        
        if isbn and str(isbn).strip() in existierende_isbns:
            uebersprungen += 1
            with aktueller_client:
                fortschritt_label.set_text(f"{t('import_processing')} {aktuelle_nummer}/{gesamtzahl} ({prozent}%)")
                log_view.value = f"🔵 [{aktuelle_nummer}/{gesamtzahl}] ISBN {isbn}: {t('import_log_skipped')}\n" + log_view.value
            continue
            
        with aktueller_client:
            fortschritt_label.set_text(f"{t('import_processing')} {aktuelle_nummer}/{gesamtzahl} ({prozent}%)")
        
        book_data = {
            'title': import_buch['title'], 'subtitle': '', 'author': import_buch['author'],
            'translator': '', 'narrator': '', 'illustrator': '', 'editor': '',
            'isbn': isbn if isbn else '', 'isbn_10': '', 'publisher': '', 'published_date': '',
            'language': translations.aktuelle_sprache, 'description': '', 'pages': 0,
            'special': False, 'is_series': False, 'series_name': '', 'series_number': 0, 'location_id': None
        }
        
        user_data = {
            'status': import_buch['status'], 'rating': import_buch['rating'],
            'format': 'PHYSICAL', 'ownership': 'OWNED', 'quantity': 1, 'started_at': '', 'finished_at': ''
        }
        
        cover_url_to_download = None
        quelle = t('import_source_local')

        if isbn:
            try:
                scraped_daten = await book_api.scrape_buch_details_isbn_de_async(isbn)
                if scraped_daten:
                    if (book_data['title'].startswith("ISBN:") or not book_data['title']) and scraped_daten.get('title'):
                        book_data['title'] = scraped_daten['title']
                    if (book_data['author'] == t('unknown_author') or not book_data['author']) and scraped_daten.get('author'):
                        book_data['author'] = scraped_daten['author']
                    if scraped_daten.get('description'): book_data['description'] = scraped_daten['description']
                    if scraped_daten.get('publisher'): book_data['publisher'] = scraped_daten['publisher']
                    if scraped_daten.get('published_date'): book_data['published_date'] = scraped_daten['published_date']
                    if scraped_daten.get('pages') and scraped_daten['pages'] > 1: book_data['pages'] = scraped_daten['pages']
                    if scraped_daten.get('series_name'):
                        book_data['is_series'] = True
                        book_data['series_name'] = scraped_daten['series_name']
                        book_data['series_number'] = int(scraped_daten.get('series_number', 0))
                    cover_url_to_download = f"https://buch.isbn.de/gross/{isbn}.jpg" if len(isbn) == 13 else None
                    quelle = "isbn.de"

                if not book_data['title'] or book_data['title'].startswith("ISBN:"):
                    google_daten = await book_api.isbn_suche_async(isbn)
                    if google_daten:
                        book_data['title'] = google_daten.get('title') or book_data['title']
                        if book_data['author'] == t('unknown_author') or not book_data['author']:
                            book_data['author'] = google_daten.get('author') or book_data['author']
                        if not book_data['description']: book_data['description'] = google_daten.get('description', '')
                        if not book_data['publisher']: book_data['publisher'] = google_daten.get('publisher', '')
                        if not book_data['pages']: book_data['pages'] = int(google_daten.get('pages', 0))
                        if not book_data['published_date']: book_data['published_date'] = google_daten.get('published_date', '')
                        if not cover_url_to_download: cover_url_to_download = google_daten.get('cover_url')
                        quelle = "Google Books (Fallback)"
            except Exception as api_err:
                print(f"Fehler beim Import für ISBN {isbn}: {str(api_err)}")

        try:
            neue_id = database.speichere_buch_in_db(None, layout.aktiver_user_id, book_data, user_data)
            if neue_id and cover_url_to_download:
                db_path_obj = getattr(database, 'DB_PATH', None)
                if hasattr(database, 'lade_und_speichere_cover'):
                    database.lade_und_speichere_cover(neue_id, cover_url_to_download)
                else:
                    database.lade_and_speichere_cover(neue_id, cover_url_to_download)
            erfolgreich += 1
            with aktueller_client:
                log_view.value = f"🟢 [{aktuelle_nummer}/{gesamtzahl}] {book_data['title'][:50]}... ({quelle})\n" + log_view.value
        except Exception as db_ex:
            fehler += 1
            with aktueller_client:
                log_view.value = f"🔴 [{aktuelle_nummer}/{gesamtzahl}] {t('error')}: {str(db_ex)}\n" + log_view.value
        await asyncio.sleep(1.5)
        
    with aktueller_client:
        meldung = f"{t('ready')}! {erfolgreich} {t('import_msg_success')}, {uebersprungen} {t('import_msg_duplicates')}, {fehler} {t('import_msg_errors')}."
        fortschritt_label.set_text(meldung)
        log_view.value = f"🏁 === {t('import_log_end')} ===\n{meldung}\n\n" + log_view.value
        ui.notify(meldung, type='positive' if erfolgreich > 0 else 'info')

async def handle_upload(e, status_container, upload_element, is_dark):
    try:
        content = (await e.file.read()).decode('utf-8')
        buecher_liste = []
        if 'ISBN13' in content or 'Title' in content:
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                title, author, isbn13, shelf, rating = row.get('Title'), row.get('Author'), isbn_bereinigen(row.get('ISBN13')), row.get('Exclusive Shelf'), row.get('My Rating')
                if not title and not isbn13: continue
                buecher_liste.append({
                    'title': title if title else f"ISBN: {isbn13}", 'author': author if author else t('unknown_author'),
                    'isbn': isbn13, 'status': status_uebersetzen(shelf) if shelf else 'UNREAD', 'rating': int(rating) if rating and rating.isdigit() else 0
                })
        else:
            for zeile in content.splitlines():
                isbn_rein = isbn_bereinigen(zeile)
                if isbn_rein: buecher_liste.append({'title': f"ISBN: {isbn_rein}", 'author': t('unknown_author'), 'isbn': isbn_rein, 'status': 'UNREAD', 'rating': 0})
            
        if not buecher_liste:
            ui.notify(t('import_error_no_data'), type='warning')
            return
            
        ui.notify(f"{len(buecher_liste)} {t('import_notify_loaded')}", type='info')
        upload_element.set_visibility(False)
        
        with status_container:
            lbl = ui.label(t('import_preparing')).classes('text-sm text-slate-600 dark:text-slate-300 mt-2')
            progress = ui.linear_progress(value=0.0, show_value=False, color='blue').classes('w-full mt-1')
            ui.label(t('import_live_protocol')).classes('text-xs font-bold mt-4 text-slate-500 dark:text-slate-400')
            with ui.scroll_area().classes('w-full h-64 p-3 bg-slate-950 dark:bg-black rounded-lg border border-slate-700/50 mt-1') as scroll:
                log_box = ui.label('').classes('font-mono text-[11px] text-emerald-400 whitespace-pre-line leading-relaxed')
            def set_value(neuer_text):
                log_box.text = neuer_text
                scroll.scroll_to(percent=0, duration=0.1)
            log_box.value = ""
            type(log_box).value = property(lambda self: self.text, lambda self, val: set_value(val))

        asyncio.create_task(import_queue_verarbeiten(buecher_liste, lbl, progress, log_box, context.client))
    except Exception as ex:
        ui.notify(f"{t('import_error_read')}: {str(ex)}", type='negative')


def exportiere_buecher():
    try:
        buecher_daten = database.lade_buecher_aus_db(layout.aktiver_user_id)
        if not buecher_daten:
            ui.notify(t('export_empty_library'), type='warning')
            return
        goodreads_fields = [
            'Book Id', 'Title', 'Author', 'Author l-f', 'Additional Authors', 
            'ISBN', 'ISBN13', 'My Rating', 'Average Rating', 'Publisher', 
            'Binding', 'Number of Pages', 'Year Published', 'Original Publication Year', 
            'Date Read', 'Date Added', 'Bookshelves', 'Bookshelves with positions', 
            'Exclusive Shelf', 'My Review', 'Spoiler', 'Private Notes', 
            'Read Count', 'Owned Copies', 'Owned Status', 'Owned Date', 
            'Owned Notes', 'Condition', 'Condition Description', 'BCID', 'Year Read'
        ]
        output = io.StringIO()
        writer = csv.writer(output, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(goodreads_fields)
        from datetime import datetime
        heute_slash = datetime.now().strftime('%Y/%m/%d')
        
        for b in buecher_daten:
            db_start, db_end = b[11] if b[11] else "", b[12] if b[12] else ""
            date_started, date_read = db_start.replace('-', '/') if db_start else "", db_end.replace('-', '/') if db_end else ""
            status_db = b[5] or 'UNREAD'
            status_mapping = {'READ': 'read', 'READING': 'currently-reading', 'UNREAD': 'to-read'}
            exclusive_shelf = status_mapping.get(status_db, 'to-read')
            fmt_db = b[23] or 'PHYSICAL'
            fmt_mapping = {'PHYSICAL': 'Paperback', 'EBOOK': 'ebook', 'AUDIOBOOK': 'Audiobook'}
            binding = fmt_mapping.get(fmt_db, 'Paperback')
            isbn13_raw = str(b[3]).strip() if b[3] else ""
            isbn13_formatted = f'="{isbn13_raw}"' if isbn13_raw else ""

            ownership_db = b[24] if len(b) > 24 else 'OWNED'
            
            owned_status = "0" if ownership_db == 'GIVEN_AWAY' else "1"
            owned_notes = "Weggegeben" if ownership_db == 'GIVEN_AWAY' else ""
            
            if ownership_db == 'LENT':
                owned_notes = "Verliehen"

            row = [
                b[0], b[1], b[2] if b[2] else "Unbekannt", "", "", b[18] if b[18] else "", isbn13_formatted,
                b[6] if b[6] is not None else 0, "0.0", b[19] if b[19] else "", binding, b[4] if b[4] else 0,
                b[20][:4] if b[20] else "", b[20][:4] if b[20] else "", date_read, heute_slash, "", "", exclusive_shelf,
                b[22] if b[22] else "", "", "", "1" if status_db == 'READ' else "0", 
                b[25] if b[25] is not None else 1,
                owned_status,
                "", 
                owned_notes,
                "", "", "", date_read[:4] if date_read else ""
            ]
            writer.writerow(["" if x is None else str(x) for x in row])

        csv_bytes = output.getvalue().encode('utf-8')
        output.close()
        ui.download(csv_bytes, filename="goodreads_library_export.csv")
        ui.notify(t('export_success'), type='positive')
    except Exception as ex:
        ui.notify(f"{t('export_failed')}: {str(ex)}", type='negative')

def backup_erstellen():
    try:
        db_path_obj = getattr(database, 'DB_PATH', None)
        db_datei = str(db_path_obj) if db_path_obj else os.path.join('data', 'db2.db')
        covers_dir, autoren_dir = os.path.join('data', 'covers'), os.path.join('data', 'authors')
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            if os.path.exists(db_datei):
                zip_file.write(db_datei, arcname=os.path.basename(db_datei))
            if os.path.exists(covers_dir):
                for root, _, files in os.walk(covers_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, start='data')
                        zip_file.write(file_path, arcname=os.path.join('media', arcname))
            if os.path.exists(autoren_dir):
                for root, _, files in os.walk(autoren_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, start='data')
                        zip_file.write(file_path, arcname=os.path.join('media', arcname))
        zip_buffer.seek(0)
        ui.download(zip_buffer.getvalue(), filename="buecherregal_backup.zip")
        ui.notify("Backup erfolgreich erstellt und heruntergeladen!", type='positive')
    except Exception as e:
        ui.notify(f"Fehler beim Backup erstellen: {str(e)}", type='negative')

async def backup_einspielen(e):
    try:
        if hasattr(e, 'file') and e.file:
            zip_content = await e.file.read()
        else:
            raise AttributeError("NiceGUI 'e.file' nicht gefunden.")
        zip_buffer = BytesIO(zip_content)
        db_path_obj = getattr(database, 'DB_PATH', None)
        db_datei = str(db_path_obj) if db_path_obj else os.path.join('data', 'db2.db')
        data_dir = 'data'
        with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
            dateien_im_zip = zip_file.namelist()
            if not any(f.endswith('.db') for f in dateien_im_zip):
                ui.notify("Ungültiges Backup: Keine Datenbank-Datei (.db) im ZIP gefunden!", type='negative')
                return
            for ordner in ['covers', 'authors']:
                pfad = os.path.join(data_dir, ordner)
                if os.path.exists(pfad): shutil.rmtree(pfad)
                os.makedirs(pfad, exist_ok=True)
            for member in zip_file.infolist():
                if member.filename.endswith('.db'):
                    with open(db_datei, 'wb') as f: f.write(zip_file.read(member.filename))
                elif member.filename.startswith('media/'):
                    rel_path = member.filename.replace('media/', '', 1)
                    target_path = os.path.join(data_dir, rel_path)
                    if member.is_dir(): os.makedirs(target_path, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        with open(target_path, 'wb') as f: f.write(zip_file.read(member.filename))
        ui.notify("🎉 Backup erfolgreich eingespielt! Bitte lade die Seite neu.", type='positive', duration=5)
    except Exception as ex:
        ui.notify(f"Fehler beim Einspielen des Backups: {str(ex)}", type='negative')

def werksreset_ausfuehren():
    try:
        db_path_obj = getattr(database, 'DB_PATH', None)
        db_datei = str(db_path_obj) if db_path_obj else os.path.join('data', 'db2.db')
        covers_dir, autoren_dir = os.path.join('data', 'covers'), os.path.join('data', 'authors')
        if os.path.exists(db_datei):
            try: os.remove(db_datei)
            except PermissionError: database.datenbank_strukturen_leeren()
        for ordner_pfad in [covers_dir, autoren_dir]:
            if os.path.exists(ordner_pfad): shutil.rmtree(ordner_pfad)
            os.makedirs(ordner_pfad, exist_ok=True)
        if hasattr(database, 'init_db'): database.init_db()
        elif hasattr(database, 'create_tables'): database.create_tables()
        ui.notify("💥 Werksreset erfolgreich! Alle Daten wurden gelöscht.", type='warning', duration=5)
    except Exception as e:
        ui.notify(f"Fehler beim Werksreset: {str(e)}", type='negative')


@ui.page('/settings')
def einstellungen_seite():
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    is_dark = user_ui['dark_mode']
    
    dark_prop = 'dark' if is_dark else ''
    select_prop = 'dark popup-content-class="dark"' if is_dark else ''
    style_modal = 'background-color: #1e293b; color: #f8fafc;' if is_dark else ''
    
    bg_card = 'bg-slate-800 border-slate-700 text-slate-100' if is_dark else 'bg-slate-50 border-slate-200 text-slate-700'
    bg_pill = 'bg-slate-900 text-slate-200' if is_dark else 'bg-slate-200 text-slate-700'
    text_main = 'text-slate-100' if is_dark else 'text-slate-700'
    text_sub = 'text-slate-400' if is_dark else 'text-slate-500'

    with basis_layout('settings'):
        ui.label(t('settings_title')).classes(f'text-2xl font-bold mb-2 {text_main}')
        ui.label(t('settings_subtitle')).classes(f'text-sm mb-6 {text_sub}')
        
        # Das umschließende Master-Grid (Zweispaltig auf Desktops)
        with ui.element('div').classes('w-full max-w-7xl grid grid-cols-1 md:grid-cols-2 gap-6 items-start'):
            
            # ==========================================
            # SEKTION 1: UI & DARSTELLUNGS-EINSTELLUNGEN
            # ==========================================
            with ui.card().classes(f'w-full p-6 border shadow-sm col-span-full {bg_card}'):
                ui.label(t('ui_design_title')).classes(f'text-lg font-bold {text_main} mb-2')
                ui.label(t('ui_design_subtitle')).classes(f'text-xs {text_sub} -mt-2 mb-4')
                
                current_settings = database.lade_user_settings(layout.aktiver_user_id)
                
                # REPARIERT: Nimmt den vorschlag_switch.value Zustand jetzt sicher mit auf
                async def ui_einstellungen_speichern():
                    database.speichere_user_settings(
                        layout.aktiver_user_id, 
                        ansicht_select.value, 
                        dark_switch.value,
                        vorschlag_switch.value
                    )
                    if dark_switch.value:
                        ui.dark_mode().enable()
                    else:
                        ui.dark_mode().disable()
                    ui.notify(t('notify_saved'), type='positive', duration=1)
                    await asyncio.sleep(0.2)
                    ui.navigate.to('/settings')

                with ui.row().classes('w-full items-center justify-between gap-4 flex-wrap mb-4'):
                    view_opts = {
                        'PAGINATED': f"📄 {t('view_paginated')}", 
                        'INFINITE': f"📜 {t('view_infinite')}"
                    }
                    ansicht_select = ui.select(
                        options=view_opts, 
                        value=current_settings['view_mode'],
                        label=t('shelf_view_mode'),
                        on_change=ui_einstellungen_speichern
                    ).classes('w-64 px-1').props(f'outlined dense {select_prop}')
                    
                    dark_switch = ui.switch(
                        t('activate_darkmode'), 
                        value=current_settings['dark_mode'],
                        on_change=ui_einstellungen_speichern
                    ).classes(f'font-medium {text_main}')

                ui.separator().classes('my-3 dark:bg-slate-700')

                # NEU: Der dedizierte Zeilen-Switch für dein Lese-Auslos-Spaßprojekt
                with ui.row().classes('w-full items-center justify-between gap-4 flex-wrap mt-2'):
                    with ui.column().classes('gap-0 flex-1 pr-4'):
                        ui.label(t('settings_suggestion_title')).classes('font-bold text-sm text-slate-800 dark:text-slate-100')
                        ui.label(t('settings_suggestion_desc')).classes('text-xs text-slate-400 leading-tight mt-0.5')
                    
                    vorschlag_switch = ui.switch(
                        value=current_settings.get('buch_vorschlag_aktiv', False),
                        on_change=ui_einstellungen_speichern
                    ).props('color="blue"')

            # ==========================================
            # SEKTION 2: BENUTZERVERWALTUNG
            # ==========================================
            with ui.card().classes(f'w-full p-6 border shadow-sm min-h-[300px] {bg_card}'):
                ui.label(t('user_management')).classes(f'text-lg font-bold {text_main} mb-2')
                
                with ui.row().classes('w-full items-center gap-3 no-wrap mb-4'):
                    neuer_user_input = ui.input(label=t('new_username')).classes('flex-1 px-1').props(f'outlined dense {dark_prop}')
                    async def user_speichern():
                        name = neuer_user_input.value.strip()
                        if not name:
                            ui.notify(t('error_empty_name'), type='warning')
                            return
                        if database.speichere_user_in_db(name):
                            ui.notify(f'{t("user")} "{name}" {t("notify_user_added")}', type='positive')
                            neuer_user_input.value = ''
                            user_liste_refresh.refresh()
                        else:
                            ui.notify(t('error_user_exists'), type='negative')
                    ui.button(icon='person_add', on_click=user_speichern).classes('bg-slate-700 text-white p-2.5 rounded shadow-sm')
                
                ui.separator().classes('my-4 dark:bg-slate-700')
                ui.label(t('existing_users')).classes(f'text-sm font-bold mb-2 {text_sub}')
                
                @ui.refreshable
                def user_liste_refresh():
                    user_liste = database.lade_alle_user()
                    with ui.element('div').classes('flex flex-wrap gap-2'):
                        for u_id, u_name in user_liste:
                            with ui.element('div').classes(f'flex items-center rounded-full pl-3 pr-1 py-1 gap-2 shadow-sm {bg_pill}'):
                                ui.label(u_name).classes('text-sm font-medium')
                                if u_id == layout.aktiver_user_id:
                                    ui.badge(t('active'), color='blue').classes('text-[10px]')
                                else:
                                    async def user_loeschen_klick(id_zu_loeschen=u_id, name_zu_loeschen=u_name):
                                        with ui.dialog() as dialog, ui.card().classes('p-4 w-full max-w-sm flex flex-col gap-4').style(style_modal):
                                            ui.label(f'{t("confirm_delete_user_text")} "{name_zu_loeschen}"?').classes('text-sm mb-4')
                                            with ui.row().classes('w-full justify-end gap-3'):
                                                ui.button(t('cancel'), on_click=dialog.close).classes('text-slate-500').props('flat')
                                                async def definitiv_loeschen():
                                                    if database.loesche_user_aus_db(id_zu_loeschen):
                                                        ui.notify(f'"{name_zu_loeschen}" {t("notify_user_deleted")}', type='info')
                                                        user_liste_refresh.refresh()
                                                    dialog.close()
                                                ui.button(t('delete'), on_click=definitiv_loeschen).classes('bg-red-500 text-white')
                                        dialog.open()
                                    ui.button(icon='close', on_click=user_loeschen_klick).props('round dense flat size=sm').classes('text-red-500 hover:bg-red-900/30')
                user_liste_refresh()

            # ==========================================
            # SEKTION 3: REGAL- / STANDORTVERWALTUNG
            # ==========================================
            with ui.card().classes(f'w-full p-6 border shadow-sm min-h-[300px] {bg_card}'):
                ui.label(t('manage_locations')).classes(f'text-lg font-bold {text_main} mb-2')
                
                with ui.row().classes('w-full items-center gap-3 no-wrap mb-4'):
                    neues_regal_input = ui.input(label=t('location_name')).classes('flex-1 px-1').props(f'outlined dense {dark_prop}')
                    async def regal_speichern():
                        name = neues_regal_input.value.strip()
                        if not name:
                            ui.notify(t('error_empty_name'), type='warning')
                            return
                        if database.speichere_regal_in_db(name):
                            ui.notify(f'"{name}" {t("notify_location_added")}', type='positive')
                            neues_regal_input.value = ''
                            regal_liste_refresh.refresh()
                        else:
                            ui.notify(t('error_location_exists'), type='negative')
                    ui.button(icon='add', on_click=regal_speichern).classes('bg-slate-700 text-white p-2.5 rounded shadow-sm')

                ui.separator().classes('my-4 dark:bg-slate-700')
                ui.label(t('existing_locations')).classes(f'text-sm font-bold mb-2 {text_sub}')
                
                @ui.refreshable
                def regal_liste_refresh():
                    regale = database.lade_alle_regale()
                    with ui.element('div').classes('flex flex-wrap gap-2'):
                        for r_id, r_name in regale:
                            with ui.element('div').classes(f'flex items-center rounded-full pl-3 pr-1 py-1 gap-2 shadow-sm {bg_pill}'):
                                ui.label(r_name).classes('text-sm font-medium')
                                async def regal_loeschen_klick(id_zu_loeschen=r_id, name_zu_loeschen=r_name):
                                    with ui.dialog() as dialog, ui.card().classes('p-4 w-full max-w-sm flex flex-col gap-4').style(style_modal):
                                        ui.label(f'"{name_zu_loeschen}" {t("confirm_delete_location_text")}').classes('text-sm mb-4')
                                        with ui.row().classes('w-full justify-end gap-2'):
                                            ui.button(t('cancel'), on_click=dialog.close).classes('text-slate-500').props('flat')
                                            async def definitiv_loeschen():
                                                if database.loesche_regal_aus_db(id_zu_loeschen):
                                                    ui.notify(f'"{name_zu_loeschen}" {t("notify_location_deleted")}', type='info')
                                                    regal_liste_refresh.refresh()
                                                dialog.close()
                                            ui.button(t('delete'), on_click=definitiv_loeschen).classes('bg-red-500 text-white')
                                    dialog.open()
                                ui.button(icon='close', on_click=regal_loeschen_klick).props('round dense flat size=sm').classes('text-red-500 hover:bg-red-900/30')
                regal_liste_refresh()

            # ==========================================
            # SEKTION 3b: GENRE-VERWALTUNG
            # ==========================================
            with ui.card().classes(f'w-full p-6 border shadow-sm min-h-[300px] {bg_card}'):
                ui.label(t('manage_genres')).classes(f'text-lg font-bold {text_main} mb-2')
                
                # --- Eigenes Genre hinzufügen ---
                with ui.row().classes('w-full items-center gap-3 no-wrap mb-4'):
                    neues_genre_input = ui.input(label=t('genre_name')).classes('flex-1 px-1').props(f'outlined dense {dark_prop}')
                    async def genre_speichern():
                        name = neues_genre_input.value.strip()
                        if not name:
                            ui.notify(t('error_empty_name'), type='warning')
                            return
                        if database.speichere_genre_in_db(layout.aktiver_user_id, name):
                            ui.notify(f'"{name}" {t("notify_genre_added")}', type='positive')
                            neues_genre_input.value = ''
                            genre_liste_refresh.refresh()
                        else:
                            ui.notify(t('error_genre_exists'), type='negative')
                    ui.button(icon='add', on_click=genre_speichern).classes('bg-slate-700 text-white p-2.5 rounded shadow-sm')

                # --- NEU: INTEGRATION GENRE-IMPORT (Auswahl anderer Nutzer) ---
                andere_user = database.lade_andere_user_mit_genres(layout.aktiver_user_id)
                if andere_user:
                    with ui.element('div').classes('w-full p-3 rounded border border-dashed border-slate-300 dark:border-slate-700 mb-4 bg-slate-50/50 dark:bg-slate-900/50 flex flex-col gap-2'):
                        ui.label(t('profile_copy:')).classes(f'text-xs font-bold uppercase tracking-wider {text_sub}')
                        
                        with ui.row().classes('w-full items-center gap-3 no-wrap'):
                            user_opts = {u_id: u_name for u_id, u_name in andere_user}
                            user_auswahl = ui.select(
                                options=user_opts, 
                                label=t('choose_user')
                            ).classes('flex-1 max-w-xs px-1').props(f'outlined dense {dark_prop}')
                            
                            async def import_starten():
                                if not user_auswahl.value:
                                    ui.notify(t('choose_user_first'), type='warning')
                                    return
                                database.kopiere_genres_von_user(user_auswahl.value, layout.aktiver_user_id)
                                ui.notify(t('genre_copy_successful'), type='positive')
                                user_auswahl.value = None
                                genre_liste_refresh.refresh()  # Aktualisiert sofort die Pill-Anzeige darunter!
                            
                            ui.button(icon='download', on_click=import_starten).classes('bg-blue-600 text-white p-2.5 rounded shadow-sm').tooltip(t('import_genre'))

                ui.separator().classes('my-4 dark:bg-slate-700')
                ui.label(t('existing_genres')).classes(f'text-sm font-bold mb-2 {text_sub}')
                
                # --- Bestehende Genres (Pills) ---
                @ui.refreshable
                def genre_liste_refresh():
                    genres = database.lade_alle_genres(layout.aktiver_user_id)
                    with ui.element('div').classes('flex flex-wrap gap-2'):
                        if not genres:
                            ui.label(t('no_genres_hint')).classes('text-xs italic text-slate-400')
                        for g_id, g_name in genres:
                            with ui.element('div').classes(f'flex items-center rounded-full pl-3 pr-1 py-1 gap-2 shadow-sm {bg_pill}'):
                                ui.label(g_name).classes('text-sm font-medium')
                                async def genre_loeschen_klick(id_zu_loeschen=g_id, name_zu_loeschen=g_name):
                                    with ui.dialog() as dialog, ui.card().classes('p-4 w-full max-w-sm flex flex-col gap-4').style(style_modal):
                                        ui.label(f'"{name_zu_loeschen}" {t("confirm_delete_genre_text")}').classes('text-sm mb-4')
                                        with ui.row().classes('w-full justify-end gap-2'):
                                            ui.button(t('cancel'), on_click=dialog.close).classes('text-slate-500').props('flat')
                                            async def definitiv_loeschen():
                                                if database.loesche_genre_aus_db(id_zu_loeschen):
                                                    ui.notify(f'"{name_zu_loeschen}" {t("notify_genre_deleted")}', type='info')
                                                    genre_liste_refresh.refresh()
                                                dialog.close()
                                            ui.button(t('delete'), on_click=definitiv_loeschen).classes('bg-red-500 text-white')
                                    dialog.open()
                                ui.button(icon='close', on_click=genre_loeschen_klick).props('round dense flat size=sm').classes('text-red-500 hover:bg-red-900/30')
                
                genre_liste_refresh()

            # ==========================================
            # SEKTION 4: DATEI-IMPORT
            # ==========================================
            ui.label(t('settings_importexport_title')).classes(f'text-lg font-bold col-span-full {text_main} uppercase tracking-wide mt-4 -mb-2')

            with ui.card().classes(f'w-full p-6 border shadow-sm min-h-[250px] flex flex-col justify-between {bg_card}'):
                with ui.element('div'):
                    ui.label(t('import_file_title')).classes(f'text-lg font-bold {text_main}')
                    ui.label(t('import_file_subtitle')).classes(f'text-xs {text_sub} mb-4')
                
                status_container = ui.element('div').classes('w-full flex flex-col gap-1')
                
                upload_field = ui.upload(auto_upload=True).props(
                    f'accept=.csv,.txt label="{t("import_select_file")}" hide-upload-btn label-slot outlined dense {dark_prop}'
                ).classes('w-full h-[40px]')
                upload_field.on_upload(lambda e: handle_upload(e, status_container, upload_field, is_dark))

            # ==========================================
            # SEKTION 5: DATEI-EXPORT
            # ==========================================
            with ui.card().classes(f'w-full p-6 border shadow-sm min-h-[250px] flex flex-col justify-between {bg_card}'):
                with ui.element('div'):
                    ui.label(t('export_file_title')).classes(f'text-lg font-bold {text_main}')
                    ui.label(t('export_file_subtitle')).classes(f'text-xs {text_sub} mb-4')
                
                ui.button(t('export_btn_text'), icon='download', on_click=exportiere_buecher).classes('bg-slate-700 hover:bg-slate-600 text-white h-[40px] w-full shadow-sm rounded text-sm py-0')

            # ==========================================
            # SEKTION 6: DATENSICHERUNG & SYSTEM
            # ==========================================
            ui.label(t('settings_backup_title')).classes(f'text-lg font-bold col-span-full {text_main} uppercase tracking-wide mt-4 -mb-2')

            with ui.card().classes(f'w-full p-6 border shadow-sm min-h-[250px] flex flex-col justify-between {bg_card}'):
                with ui.element('div'):
                    ui.label(t('settings_backup_subtitle')).classes(f'text-md font-bold {text_main} mb-1')
                    ui.label(t('settings_backup_desc')).classes(f'text-xs {text_sub} mb-4')
                
                with ui.row().classes('w-full items-stretch gap-3 no-wrap mt-2'):
                    ui.button(
                        t('settings_backup_download'), 
                        icon='download', 
                        on_click=lambda: backup_erstellen()
                    ).classes('flex-1 bg-slate-700 hover:bg-slate-600 text-white rounded shadow-sm text-sm py-0')
                    
                    ui.upload(auto_upload=True, max_files=1).props(
                        f'accept=.zip label="{t("settings_backup_restore")}" hide-upload-btn label-slot outlined dense {dark_prop}'
                    ).classes('flex-1 h-[40px]') \
                     .on_upload(lambda e: backup_einspielen(e))

            # ==========================================
            # SEKTION 7: GEFAHRENZONE (WERKSRESET)
            # ==========================================
            with ui.card().classes(f'w-full p-6 border border-red-300 dark:border-red-900/40 bg-red-50/50 dark:bg-red-950/10 min-h-[250px] flex flex-col justify-between shadow-sm'):
                with ui.element('div'):
                    ui.label(t('settings_reset_title')).classes('text-md font-bold text-red-700 dark:text-red-400 mb-1')
                    ui.label(t('settings_reset_desc')).classes('text-xs text-red-900/80 dark:text-red-300/80 mb-4')
                
                with ui.dialog() as reset_dialog, ui.card().classes('p-6 w-full max-w-md flex flex-col gap-4').style(style_modal):
                    ui.label(t('settings_reset_confirm_title')).classes('text-lg font-bold text-red-600 dark:text-red-400')
                    ui.label(t('settings_reset_confirm_desc')).classes(f'text-sm {text_sub}')
                    with ui.row().classes('w-full justify-end gap-3 mt-2'):
                        ui.button(t('cancel'), on_click=reset_dialog.close).classes('text-slate-500').props('flat')
                        ui.button(t('settings_reset_execute'), on_click=lambda: [reset_dialog.close(), werksreset_ausfuehren()]).classes('bg-red-600 text-white')

                ui.button(t('settings_reset_btn'), icon='delete_forever', on_click=reset_dialog.open).classes('bg-red-600 hover:bg-red-700 text-white h-[40px] w-full rounded shadow-sm text-sm py-0')

    # ==========================================
    # FOOTER (VERSION & ENTWICKLER)
    # ==========================================
    with ui.element('div').classes('col-span-full w-full flex flex-col items-center justify-center gap-1 mt-12 mb-4 text-[11px] font-mono tracking-wide text-slate-400 dark:text-slate-500'):
        ui.separator().classes('w-16 mb-2 opacity-50 dark:opacity-30')
        with ui.row().classes('items-center gap-1.5'):
            ui.icon('code', size='xs')
            ui.label('Booktracker v0.6.3')
        with ui.row().classes('items-center gap-1.5'):
            ui.icon('copyright', size='xs')
            ui.label('Developed by Shad-Rasi')