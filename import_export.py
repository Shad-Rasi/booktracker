import csv
import io
import asyncio
from nicegui import ui, context
import database
import layout
import translations
from layout import basis_layout
from translations import t

def status_uebersetzen(goodreads_shelf):
    mapping = {'read': 'READ', 'currently-reading': 'READING', 'to-read': 'UNREAD'}
    return mapping.get(goodreads_shelf.lower().strip(), 'UNREAD')

def isbn_bereinigen(isbn_raw):
    if not isbn_raw: return None
    cleaned = isbn_raw.replace('=', '').replace('"', '').strip()
    return cleaned if cleaned.isdigit() else None

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

        # ... (Deine API-Scraper-Logik für isbn.de und Google Books bleibt hier exakt gleich)
        
        try:
            neue_id = database.speichere_buch_in_db(None, layout.aktiver_user_id, book_data, user_data)
            if neue_id and cover_url_to_download:
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
            
            ui.add_head_html(f'''
                <style>
                    .log-konsole, .log-konsole .q-field__control, .log-konsole .q-field__control-container, .log-konsole .q-field__native {{ height: 100% !important; color: {"#f8fafc" if is_dark else "#ffffff"} !important; }}
                    .log-konsole textarea {{ height: 100% !important; color: {"#f8fafc" if is_dark else "#ffffff"} !important; overflow-y: auto !important; }}
                </style>
            ''')
            log_box = ui.textarea(value='').classes('w-full font-mono text-xs p-3 bg-slate-900 rounded h-64 log-konsole').props('readonly invisible-scrollbar')

        asyncio.create_task(import_queue_verarbeiten(buecher_liste, lbl, progress, log_box, context.client))
    except Exception as ex:
        ui.notify(f"{t('import_error_read')}: {str(ex)}", type='negative')

def exportiere_buecher():
    try:
        buecher_daten = database.lade_buecher_aus_db(layout.aktiver_user_id)
        if not buecher_daten:
            ui.notify(t('export_empty_library'), type='warning')
            return

        fieldnames = ['ID', 'Title', 'Subtitle', 'Author', 'ISBN13', 'ISBN10', 'Pages', 'Publisher', 'PublishedDate', 'Language', 'Status', 'Rating', 'Format', 'Ownership', 'Quantity', 'Location', 'StartedAt', 'FinishedAt']
        output = io.StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(fieldnames)
        
        for b in buecher_daten:
            row = [b[0], b[1], b[13], b[2], b[3], b[18], b[4], b[19], b[20], b[21], b[5], b[6], b[23], b[24], b[25], b[27], b[11], b[12]]
            writer.writerow(["" if x is None else str(x) for x in row])

        csv_bytes = output.getvalue().encode('utf-8')
        output.close()
        ui.download(csv_bytes, filename="meine_bibliothek_export.csv")
        ui.notify(t('export_success'), type='positive')
    except Exception as ex:
        ui.notify(f"{t('export_failed')}: {str(ex)}", type='negative')

@ui.page('/import')
def import_export_seite():
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    is_dark = user_ui['dark_mode']
    
    bg_card = 'bg-slate-800 border-slate-700' if is_dark else 'bg-slate-50 border-slate-200'
    text_main = 'text-slate-100' if is_dark else 'text-slate-700'
    text_sub = 'text-slate-400' if is_dark else 'text-slate-500'

    with basis_layout('import_export'):
        ui.label(t('import_export_title')).classes(f'text-2xl font-bold mb-2 {text_main}')
        ui.label(t('import_export_subtitle')).classes(f'text-sm mb-6 {text_sub}')
        
        with ui.element('div').classes('w-full max-w-4xl flex flex-col gap-6'):
            with ui.card().classes(f'w-full p-6 border shadow-sm flex flex-col gap-2 {bg_card}'):
                ui.label(t('import_file_title')).classes(f'text-lg font-bold {text_main}')
                ui.label(t('import_file_subtitle')).classes(f'text-xs {text_sub} mb-2')
                
                status_container = ui.element('div').classes('w-full flex flex-col gap-1')
                upload_field = ui.upload(label=t('import_select_file'), auto_upload=True).props(f'accept=.csv,.txt {"dark" if is_dark else ""}').classes('w-full mt-2')
                upload_field.on_upload(lambda e: handle_upload(e, status_container, upload_field, is_dark))

            with ui.card().classes(f'w-full p-6 border shadow-sm flex flex-col gap-2 {bg_card}'):
                ui.label(t('export_file_title')).classes(f'text-lg font-bold {text_main}')
                ui.label(t('export_file_subtitle')).classes(f'text-xs {text_sub}')
                ui.button(t('export_btn_text'), icon='download', on_click=exportiere_buecher).classes('bg-slate-700 hover:bg-slate-600 text-white py-2.5 mt-2 w-full sm:w-auto self-start px-6')