from nicegui import ui
import database
import asyncio
import book_api
import os
import layout
from layout import basis_layout
import translations
from translations import t

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

@ui.page('/add')
def buch_hinzufuegen():
    formular_rendern()

@ui.page('/edit/{book_id}')
def buch_bearbeiten(book_id: int):
    all_books = database.lade_buecher_aus_db(layout.aktiver_user_id)
    aktuelles_buch = next((b for b in all_books if b[0] == book_id), None)
    formular_rendern(edit_id=book_id, daten=aktuelles_buch)


def formular_rendern(edit_id=None, daten=None):
    ist_edit = edit_id is not None
    regale = database.lade_alle_regale()
    
    # 1. DARKMODE-ZUSTAND ERMITTLEN & PROPS VORBEREITEN
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    is_dark = user_ui['dark_mode']
    
    dark_prop = 'dark' if is_dark else ''
    select_prop = 'dark popup-content-class="dark"' if is_dark else ''
    
    # Adaptive CSS-Klassen für Container und Texte
    bg_card = 'bg-slate-800 border-slate-700' if is_dark else 'bg-slate-50 border-slate-200'
    bg_row_location = 'bg-slate-900 border-amber-900/40' if is_dark else 'bg-amber-50/40 border-amber-100'
    bg_row_personal = 'bg-slate-900 border-slate-700' if is_dark else 'bg-slate-100 border border-slate-200'
    bg_row_series = 'bg-slate-900 border-blue-900/40' if is_dark else 'bg-blue-50/40 border-blue-100'
    bg_row_dates = 'bg-slate-900 border-emerald-900/40' if is_dark else 'bg-emerald-50/40 border-emerald-100'
    
    text_main = 'text-slate-100' if is_dark else 'text-slate-700'
    text_switch = 'text-slate-200' if is_dark else 'text-slate-700'
    
    # Datenbankfelder strukturiert entpacken falls vorhanden
    db_titel = daten[1] if daten else ""
    db_autor = daten[2] if daten else ""
    db_isbn = daten[3] if daten else ""
    db_seiten = daten[4] if daten else 0
    db_status = daten[5] if daten else "UNREAD"
    db_rating = daten[6] if daten else 0
    db_special = bool(daten[7]) if daten else False
    db_is_series = bool(daten[8]) if daten else False
    db_s_name = daten[9] if daten else ""
    db_s_num = daten[10] if daten else 0
    db_start = daten[11] if daten else ""
    db_end = daten[12] if daten else ""
    
    db_subtitle = daten[13] if daten else ""
    db_translator = daten[14] if daten else ""
    db_narrator = daten[15] if daten else ""
    db_illustrator = daten[16] if daten else ""
    db_editor = daten[17] if daten else ""
    db_isbn_10 = daten[18] if daten else ""
    db_publisher = daten[19] if daten else ""
    db_published_date = daten[20] if daten else ""
    db_language = daten[21] if daten else ""
    db_description = daten[22] if daten else ""
    db_format = daten[23] if daten else "PHYSICAL"
    db_ownership = daten[24] if daten else "OWNED"
    db_quantity = daten[25] if daten else 1
    db_location_id = daten[26] if daten else (regale[0][0] if regale else None)

    async def isbn_suchen():
        isbn_wert = isbn_input.value.strip().replace("-", "")
        if not isbn_wert:
            ui.notify(t('notify_isbn_warn'), type='warning')
            return
            
        ui.notify('Frage Daten von isbn.de ab...', type='info')
        scraped_daten = await book_api.scrape_buch_details_isbn_de_async(isbn_wert)
        
        if not scraped_daten:
            scraped_daten = {}
            
        ui.notify('Prüfe Google Books auf fehlende Details...', type='info')
        google_daten = await book_api.isbn_suche_async(isbn_wert)
        
        vereinte_daten = {}
        if google_daten:
            vereinte_daten.update(google_daten)
            
        if scraped_daten:
            if scraped_daten.get('description'): vereinte_daten['description'] = scraped_daten['description']
            if scraped_daten.get('publisher'): vereinte_daten['publisher'] = scraped_daten['publisher']
            if scraped_daten.get('published_date'): vereinte_daten['published_date'] = scraped_daten['published_date']
            if scraped_daten.get('pages') and scraped_daten['pages'] > 1: vereinte_daten['pages'] = scraped_daten['pages']
            
            if scraped_daten.get('series_name'):
                vereinte_daten['is_series'] = True
                vereinte_daten['series_name'] = scraped_daten['series_name']
                vereinte_daten['series_number'] = scraped_daten['series_number']

        if vereinte_daten and (vereinte_daten.get('title') or scraped_daten.get('series_name')):
            titel_input.value = vereinte_daten.get('title') or "Unbekannter Titel (Bitte ergänzen)"
            autor_input.value = vereinte_daten.get('author') or "Unbekannter Autor"
            subtitle_input.value = vereinte_daten.get('subtitle', '')
            publisher_input.value = vereinte_daten.get('publisher', '')
            pub_date_input.value = vereinte_daten.get('published_date', '')
            lang_input.value = vereinte_daten.get('language', 'de')
            desc_input.value = vereinte_daten.get('description', '')
            seiten_input.value = int(vereinte_daten.get('pages', 0))
            
            if vereinte_daten.get('is_series'):
                series_checkbox.value = True
                reihenname_input.value = vereinte_daten.get('series_name', '')
                band_input.value = vereinte_daten.get('series_number', 0)
            
            if len(isbn_wert) == 13:
                formular_rendern.temporaere_cover_url = f"https://buch.isbn.de/gross/{isbn_wert}.jpg"
            else:
                formular_rendern.temporaere_cover_url = vereinte_daten.get('cover_url', '')
                
            ui.notify(t('notify_api_success'), type='positive')
        else:
            ui.notify(t('notify_api_fail'), type='negative')
            
    def speichern():
        title = titel_input.value.strip()
        if not title:
            ui.notify(t('title_missing') if 'title_missing' in translations.TRANSLATIONS[translations.aktuelle_sprache] else 'Titel fehlt!', type='warning')
            return

        book_data = {
            'title': title, 'subtitle': subtitle_input.value.strip(), 'author': autor_input.value.strip(),
            'translator': translator_input.value.strip(), 'narrator': narrator_input.value.strip(),
            'illustrator': illustrator_input.value.strip(), 'editor': editor_input.value.strip(),
            'isbn': isbn_input.value.strip().replace("-", ""), 'isbn_10': isbn_10_input.value.strip(),
            'publisher': publisher_input.value.strip(), 'published_date': pub_date_input.value.strip(),
            'language': lang_input.value.strip(), 'description': desc_input.value.strip(),
            'pages': int(seiten_input.value or 0), 'special': special_checkbox.value, 'is_series': series_checkbox.value,
            'series_name': reihenname_input.value.strip() if series_checkbox.value else "",
            'series_number': int(band_input.value or 0) if series_checkbox.value else 0, 'location_id': location_input.value
        }
        
        user_data = {
            'status': status_input.value, 'rating': int(rating_input.value), 'format': format_input.value,
            'ownership': ownership_input.value, 'quantity': int(quantity_input.value or 1),
            'started_at': start_date_input.value, 'finished_at': end_date_input.value
        }
        
        neue_id = database.speichere_buch_in_db(edit_id, layout.aktiver_user_id, book_data, user_data)
        
        if not ist_edit and neue_id:
            cover_url = getattr(formular_rendern, 'temporaere_cover_url', None)
            if cover_url:
                database.lade_und_speichere_cover(neue_id, cover_url)
                formular_rendern.temporaere_cover_url = None

        ui.notify(t('notify_saved'), type='positive')
        ui.navigate.to('/')

    titel_key = 'edit_book' if ist_edit else 'add_book'
    
    with basis_layout(titel_key):
        with ui.element('div').classes('w-full max-w-4xl mx-auto mb-12'):
            ui.label(t(titel_key)).classes(f'text-2xl font-bold mb-6 {text_main}')
            
            with ui.card().classes(f'w-full p-6 border shadow-sm flex flex-col gap-4 {bg_card}'):
                
                # --- ISBN & SUCHE ---
                if not ist_edit:
                    with ui.row().classes('w-full items-center gap-4'):
                        isbn_input = ui.input(label=t('isbn_label'), value=db_isbn).classes('w-64 dark:bg-slate-900').props(f'outlined {dark_prop}')
                        ui.button(t('search'), on_click=isbn_suchen).classes('bg-blue-600 hover:bg-blue-500 text-white py-2 px-4 rounded')
                    ui.separator().classes('dark:bg-slate-700')
                else:
                    isbn_input = ui.input(label='ISBN 13', value=db_isbn).classes('w-64 dark:bg-slate-900').props(f'outlined readonly {dark_prop}')

                # --- TITEL & METADATEN ---
                with ui.row().classes('w-full gap-4'):
                    titel_input = ui.input(label=t('title'), value=db_titel).classes('flex-1 dark:bg-slate-900').props(f'outlined {dark_prop}')
                    subtitle_input = ui.input(label=t('subtitle'), value=db_subtitle).classes('flex-1 dark:bg-slate-900').props(f'outlined {dark_prop}')
                
                with ui.row().classes('w-full gap-4'):
                    autor_input = ui.input(label=t('author'), value=db_autor).classes('flex-1 dark:bg-slate-900').props(f'outlined {dark_prop}')
                    publisher_input = ui.input(label=t('publisher'), value=db_publisher).classes('flex-1 dark:bg-slate-900').props(f'outlined {dark_prop}')

                # --- ERWEITERTE MITWIRKENDE ---
                with ui.row().classes('w-full gap-4'):
                    translator_input = ui.input(label=t('translator'), value=db_translator).classes('flex-1 dark:bg-slate-900').props(f'outlined {dark_prop}')
                    narrator_input = ui.input(label=t('narrator'), value=db_narrator).classes('flex-1 dark:bg-slate-900').props(f'outlined {dark_prop}')
                
                with ui.row().classes('w-full gap-4'):
                    illustrator_input = ui.input(label=t('illustrator'), value=db_illustrator).classes('flex-1 dark:bg-slate-900').props(f'outlined {dark_prop}')
                    editor_input = ui.input(label=t('editor'), value=db_editor).classes('flex-1 dark:bg-slate-900').props(f'outlined {dark_prop}')

                # --- BUCHSPEZIFISCHE INFORMATIONEN ---
                with ui.row().classes('w-full items-center gap-4 mt-2 flex-wrap sm:flex-nowrap'):
                    seiten_input = ui.number(label=t('pages'), value=db_seiten, format='%d').classes('w-24 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                    isbn_10_input = ui.input(label='ISBN 10', value=db_isbn_10).classes('w-36 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                    pub_date_input = ui.input(label=t('published_date'), value=db_published_date).classes('w-36 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                    lang_input = ui.input(label=t('language'), value=db_language).classes('w-28 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                    special_checkbox = ui.checkbox(t('special'), value=db_special).classes(f'ml-2 {text_switch}')

                # --- PHYSISCHER LAGERORT ---
                with ui.row().classes(f'w-full items-center gap-6 mt-2 p-3 rounded border {bg_row_location}'):
                    regal_options = {r[0]: r[1] for r in regale}
                    location_input = ui.select(options=regal_options, value=db_location_id, label=t('location')).classes('w-64 dark:bg-slate-900 px-2 rounded').props(f'outlined dense {select_prop}')

                # --- PERSÖNLICHE NUTZER-STEUERUNG (STATUS, FORMAT, MENGE) ---
                with ui.row().classes(f'w-full items-center gap-4 mt-2 p-3 rounded flex-wrap {bg_row_personal}'):
                    status_options = {'UNREAD': t('unread'), 'READING': t('reading'), 'READ': t('read')}
                    status_input = ui.select(options=status_options, value=db_status, label=t('status')).classes('w-44 dark:bg-slate-900 px-2 rounded').props(f'outlined dense {select_prop}')
                    
                    rating_options = {i: (t('none') if i == 0 else f'{i} {t("stars" if i > 1 else "star")}') for i in range(6)}
                    rating_input = ui.select(options=rating_options, value=db_rating, label=t('rating')).classes('w-36 dark:bg-slate-900 px-2 rounded').props(f'outlined dense {select_prop}')
                    
                    format_options = {'PHYSICAL': t('PHYSICAL'), 'AUDIOBOOK': t('AUDIOBOOK'), 'EBOOK': t('EBOOK')}
                    format_input = ui.select(options=format_options, value=db_format, label=t('format')).classes('w-44 dark:bg-slate-900 px-2 rounded').props(f'outlined dense {select_prop}')
                    
                    ownership_options = {'OWNED': t('OWNED'), 'BORROWED': t('BORROWED'), 'LENT': t('LENT')}
                    ownership_input = ui.select(options=ownership_options, value=db_ownership, label=t('ownership')).classes('w-36 dark:bg-slate-900 px-2 rounded').props(f'outlined dense {select_prop}')
                    
                    quantity_input = ui.number(label=t('quantity'), value=db_quantity, format='%d').classes('w-20 dark:bg-slate-900 px-2 rounded').props(f'outlined dense {dark_prop}')

                # --- REIHEN-DETAILS (JETZT MIT AUTOCOMPLETION-SUCHFUNKTION) ---
                with ui.row().classes(f'w-full items-center gap-6 mt-2 p-3 rounded border {bg_row_series}'):
                    series_checkbox = ui.checkbox(t('series'), value=db_is_series).classes(text_switch)
                    
                    # 1. Alle aktuell existierenden Reihennamen aus der DB für die Autocomplete-Vorschläge laden
                    existierende_reihen = sorted(list({
                        b[9].strip() for b in database.lade_buecher_aus_db(layout.aktiver_user_id) 
                        if b[8] and b[9] and b[9].strip()
                    }))
                    
                    # 2. Das ui.input wird durch ein ui.select mit Eingabefunktion ersetzt
                    # new-value-mode="add" erlaubt es dir, völlig neue Reihennamen einzutippen, die noch nicht in der Liste sind!
                    reihenname_input = ui.select(
                        options=existierende_reihen,
                        value=db_s_name.strip() if db_s_name else None,
                        label=t('series_name')
                    ).classes('w-80 dark:bg-slate-900 px-2 rounded') \
                     .props(f'outlined use-input hide-selected fill-input input-debounce="0" new-value-mode="add" {select_prop}') \
                     .bind_visibility_from(series_checkbox, 'value')
                    
                    # Filter-Logik: Filtert die Vorschläge live, während du tippst
                    def filter_reihen(e):
                        val = e.value.lower()
                        reihenname_input.options = [r for r in existierende_reihen if val in r.lower()]
                    reihenname_input.on('filter', filter_reihen)

                    band_input = ui.number(label=t('series_num'), value=db_s_num, format='%d').classes('w-28 dark:bg-slate-900').props(f'outlined {dark_prop}').bind_visibility_from(series_checkbox, 'value')
                # --- LESEZEITEN ---
                with ui.row().classes(f'w-full items-center gap-6 mt-2 p-3 rounded border {bg_row_dates}'):
                    start_date_input = ui.input(label=t('start'), value=db_start).classes('w-48 dark:bg-slate-900').props(f'type=date outlined {dark_prop}')
                    end_date_input = ui.input(label=t('end'), value=db_end).classes('w-48 dark:bg-slate-900').props(f'type=date outlined {dark_prop}')

                # --- TEXTBESCHREIBUNG ---
                desc_input = ui.textarea(label=t('description'), value=db_description).classes('w-full h-24 dark:bg-slate-900').props(f'outlined {dark_prop}')

                # --- FOOTER BUTTONS ---
                with ui.row().classes('w-full justify-end gap-3 mt-4'):
                    ui.button(t('cancel'), on_click=lambda: ui.navigate.to('/')).classes('bg-slate-400 hover:bg-slate-500 text-white')
                    
                    btn_color = 'bg-orange-600 hover:bg-orange-500' if ist_edit else 'bg-green-600 hover:bg-green-500'
                    btn_text = t('save_changes') if ist_edit else t('save_in_shelf')
                    ui.button(btn_text, on_click=speichern).classes(f'{btn_color} text-white px-6 py-2 rounded shadow')