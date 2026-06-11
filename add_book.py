import os
import asyncio
from datetime import datetime
from nicegui import ui
import database
import book_api
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
    
    # Sicherheitsgurt: Falls durch den Hot-Reload der User-Kontext kurz verwirrt ist
    if not aktuelles_buch:
        with basis_layout('edit_book'):
            ui.label('Buch wird geladen...').classes('italic text-slate-400')
            # Erzwingt den Sprung zur Hauptseite, um das Layout-Gedächtnis zu füttern
            ui.navigate.to('/') 
        return
        
    formular_rendern(edit_id=book_id, daten=aktuelles_buch)


def formular_rendern(edit_id=None, daten=None):
    ist_edit = edit_id is not None
    regale = database.lade_alle_regale()
    
    # 1. DARKMODE-ZUSTAND ERMITTLEN & PROPS VORBEREITEN
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    is_dark = user_ui['dark_mode']
    
    dark_prop = 'dark' if is_dark else ''
    select_prop = 'dark popup-content-class="dark"' if is_dark else ''
    
    bg_card = 'bg-slate-800 border-slate-700' if is_dark else 'bg-slate-50 border-slate-200'
    bg_sub_section = 'bg-slate-900/40 border-slate-700/50' if is_dark else 'bg-white border-slate-200/60'
    text_main = 'text-slate-100' if is_dark else 'text-slate-800'
    text_sub = 'text-slate-400' if is_dark else 'text-slate-500'
    text_switch = 'text-slate-200' if is_dark else 'text-slate-700'
    
    # KORRIGIERT & ABSTURZSICHER: Daten aus dem DB-Tuple entpacken mit festen Fallbacks
    db_titel = daten[1] if daten else ""
    db_autor = daten[2] if daten else ""
    db_isbn = daten[3] if daten else ""
    db_seiten = daten[4] if daten and daten[4] is not None else 0
    db_status = daten[5] if daten and daten[5] else "UNREAD"
    db_rating = daten[6] if daten and daten[6] is not None else 0
    db_special = bool(daten[7]) if daten else False
    db_is_series = bool(daten[8]) if daten else False
    db_s_name = daten[9] if daten else ""
    db_s_num = daten[10] if daten and daten[10] is not None else 0
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
    db_language = daten[21] if daten else "de"
    db_description = daten[22] if daten else ""
    
    # REPARIERT: Abgleich mit den exakten Indizes aus deiner books.py (23=Format, 24=Ownership, 25=Quantity)
    db_format = daten[23] if daten and daten[23] else "PHYSICAL"
    db_ownership = daten[24] if daten and daten[24] else "OWNED"
    db_quantity = daten[25] if daten and daten[25] is not None else 1
    db_location_id = daten[26] if daten else None

    def formatiere_erscheinungsdatum(datum_str, sprache):
        if not datum_str:
            return ""
        try:
            dt = datetime.strptime(datum_str[:10], '%Y-%m-%d')
            if sprache == 'de':
                return dt.strftime('%d.%m.%Y')
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            return datum_str

    def speichern():
        title = titel_input.value.strip() if titel_input.value else ""
        if not title:
            ui.notify(t('title_missing') if 'title_missing' in translations.TRANSLATIONS[translations.aktuelle_sprache] else 'Titel fehlt!', type='warning')
            return

        book_data = {
            'title': title, 
            'subtitle': subtitle_input.value.strip() if subtitle_input.value else "", 
            'author': autor_input.value.strip() if autor_input.value else "",
            'translator': translator_input.value.strip() if translator_input.value else "", 
            'narrator': narrator_input.value.strip() if narrator_input.value else "",
            'illustrator': illustrator_input.value.strip() if illustrator_input.value else "", 
            'editor': editor_input.value.strip() if editor_input.value else "",
            'isbn': isbn_input.value.strip().replace("-", "") if isbn_input.value else "", 
            'isbn_10': isbn_10_input.value.strip() if isbn_10_input.value else "",
            'publisher': publisher_input.value.strip() if publisher_input.value else "", 
            'published_date': pub_date_input.value.strip() if pub_date_input.value else "",
            'language': lang_input.value, 
            'description': desc_input.value.strip() if desc_input.value else "",
            'pages': int(seiten_input.value) if seiten_input.value is not None else 0, 
            'special': bool(special_checkbox.value), 
            'is_series': bool(series_checkbox.value),
            'series_name': reihenname_input.value.strip() if (series_checkbox.value and reihenname_input.value) else "",
            'series_number': int(band_input.value) if (series_checkbox.value and band_input.value) else 0, 
            'location_id': location_input.value
        }
        
        # REPARIERT: Alle int()-Konvertierungen haben jetzt felsenfeste Fallbacks gegen NoneTypes!
        user_data = {
            'status': status_input.value if status_input.value else 'UNREAD', 
            'rating': int(rating_input.value) if rating_input.value is not None else 0, 
            'format': format_input.value if format_input.value else 'PHYSICAL',
            'ownership': ownership_input.value if ownership_input.value else 'OWNED', 
            'quantity': int(quantity_input.value) if quantity_input.value is not None else 1,
            'started_at': start_date_input.value if start_date_input.value else "", 
            'finished_at': end_date_input.value if end_date_input.value else ""
        }
        
        neue_id = database.speichere_buch_in_db(edit_id, layout.aktiver_user_id, book_data, user_data)

        ui.notify(t('notify_saved'), type='positive')
        
        if ist_edit:
            ui.navigate.to(f'/book/{edit_id}')
        else:
            ui.navigate.to(f'/book/{neue_id}')

    titel_key = 'edit_book' if ist_edit else 'add_book'
    
    with basis_layout(titel_key):
        with ui.element('div').classes('w-full max-w-4xl mx-auto mb-12 flex flex-col gap-6'):
            ui.label(t(titel_key)).classes(f'text-2xl font-bold {text_main}')
            
            # =========================================================================
            # BLOCK 1: HARTE BUCHFAKTEN & INFORMATIONEN (OBEN)
            # =========================================================================
            with ui.card().classes(f'w-full p-6 border shadow-xs flex flex-col gap-4 {bg_card}'):
                ui.label(t('section_book_info')).classes(f'text-sm font-bold uppercase tracking-wider {text_sub} mb-2')
                
                # ISBN-Suche
                with ui.row().classes('w-full items-center gap-4'):
                    if not ist_edit:
                        isbn_input = ui.input(label=t('isbn_label'), value=db_isbn).classes('w-64 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                        search_btn = ui.button(t('search')).classes('bg-blue-600 hover:bg-blue-500 text-white px-4 h-[40px] rounded')
                    else:
                        isbn_input = ui.input(label='ISBN 13', value=db_isbn).classes('w-64 dark:bg-slate-900').props(f'outlined dense readonly {dark_prop}')

                # Titel & Untertitel
                with ui.row().classes('w-full gap-4 no-wrap flex-wrap sm:flex-nowrap'):
                    titel_input = ui.input(label=t('title'), value=db_titel).classes('flex-1 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                    subtitle_input = ui.input(label=t('subtitle'), value=db_subtitle).classes('flex-1 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                
                # Autor & Verlag
                with ui.row().classes('w-full gap-4 no-wrap flex-wrap sm:flex-nowrap'):
                    autor_input = ui.input(label=t('author'), value=db_autor).classes('flex-1 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                    publisher_input = ui.input(label=t('publisher'), value=db_publisher).classes('flex-1 dark:bg-slate-900').props(f'outlined dense {dark_prop}')

                # Kennzahlen (Seiten, ISBN10, Jahr, Sprache)
                with ui.row().classes('w-full items-center gap-4 mt-1 flex-wrap'):
                    seiten_input = ui.number(label=t('pages'), value=db_seiten, format='%d').classes('w-24 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                    isbn_10_input = ui.input(label='ISBN 10', value=db_isbn_10).classes('w-36 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                    pub_date_input = ui.input(label=t('published_date'), value=db_published_date).classes('w-36 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                    
                    sprach_optionen = {
                        'de': t('lang_de'), 
                        'en': t('lang_en'), 
                        'fr': 'Français', 'es': 'Español', 'it': 'Italiano'
                    }
                    lang_input = ui.select(options=sprach_optionen, value=db_language, label=t('language')).classes('w-36 dark:bg-slate-900').props(f'outlined dense {select_prop}')
                    
                    special_checkbox = ui.checkbox(t('special'), value=db_special).classes(f'ml-2 {text_switch}')

                # Format, Besitzstatus, Menge & Lagerort
                with ui.row().classes('w-full items-center gap-4 flex-wrap mt-1'):
                    format_options = {'PHYSICAL': t('PHYSICAL'), 'AUDIOBOOK': t('AUDIOBOOK'), 'EBOOK': t('EBOOK')}
                    format_input = ui.select(options=format_options, value=db_format, label=t('format')).classes('w-40 dark:bg-slate-900').props(f'outlined dense {select_prop}')
                    
                    ownership_options = {'OWNED': t('OWNED'), 'BORROWED': t('BORROWED'), 'LENT': t('LENT'), 'GIVEN_AWAY': t('ownership_given_away')}
                    ownership_input = ui.select(options=ownership_options, value=db_ownership, label=t('ownership')).classes('w-36 dark:bg-slate-900').props(f'outlined dense {select_prop}')
                    
                    quantity_input = ui.number(label=t('quantity'), value=db_quantity, format='%d').classes('w-20 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                    
                    regale_options = {r[0]: r[1] for r in regale}
                    location_input = ui.select(options=regale_options, value=db_location_id, label=t('location')).classes('w-56 dark:bg-slate-900').props(f'outlined dense {select_prop}')

                # --- COLLAPSIBLE FÜR MITWIRKENDE ---
                with ui.expansion(t('contributors')).classes(f'w-full border rounded-lg bg-slate-100/50 dark:bg-slate-900/30 dark:border-slate-700/50'):
                    with ui.column().classes('w-full p-4 gap-4'):
                        with ui.row().classes('w-full gap-4 no-wrap flex-wrap sm:flex-nowrap'):
                            translator_input = ui.input(label=t('translator'), value=db_translator).classes('flex-1 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                            narrator_input = ui.input(label=t('narrator'), value=db_narrator).classes('flex-1 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                        with ui.row().classes('w-full gap-4 no-wrap flex-wrap sm:flex-nowrap'):
                            illustrator_input = ui.input(label=t('illustrator'), value=db_illustrator).classes('flex-1 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                            editor_input = ui.input(label=t('editor'), value=db_editor).classes('flex-1 dark:bg-slate-900').props(f'outlined dense {dark_prop}')

                # Buchreihe
                with ui.row().classes(f'w-full items-center gap-4 mt-1 p-3 rounded-lg border {bg_sub_section}'):
                    series_checkbox = ui.checkbox(t('series'), value=db_is_series).classes(text_switch)
                    
                    existierende_reihen = sorted(list({b[9].strip() for b in database.lade_buecher_aus_db(layout.aktiver_user_id) if b[8] and b[9] and b[9].strip()}))
                    reihenname_input = ui.select(options=existierende_reihen, value=db_s_name.strip() if db_s_name else None, label=t('series_name')).classes('w-72 dark:bg-slate-900') \
                        .props(f'outlined dense use-input hide-selected fill-input input-debounce="0" new-value-mode="add" {select_prop}') \
                        .bind_visibility_from(series_checkbox, 'value')
                    
                    def filter_reihen(e):
                        val = e.value.lower() if e.value else ""
                        reihenname_input.options = [r for r in existierende_reihen if val in r.lower()]
                    reihenname_input.on('filter', filter_reihen)
                    band_input = ui.number(label=t('series_num'), value=db_s_num, format='%d').classes('w-24 dark:bg-slate-900').props(f'outlined dense {dark_prop}').bind_visibility_from(series_checkbox, 'value')

                # Beschreibung
                desc_input = ui.textarea(label=t('description'), value=db_description).classes('w-full dark:bg-slate-900').props(f'outlined rows=4 {dark_prop}')
            
            # =========================================================================
            # BLOCK 2: PERSÖNLICHE NUTZER-STEUERUNG (UNTEN)
            # =========================================================================
            with ui.card().classes(f'w-full p-6 border shadow-xs flex flex-col gap-4 {bg_card}'):
                ui.label(t('section_personal_info')).classes(f'text-sm font-bold uppercase tracking-wider {text_sub} mb-2')

                with ui.row().classes('w-full items-center gap-4 flex-wrap'):
                    status_options = {'UNREAD': t('unread'), 'READING': t('reading'), 'READ': t('read')}
                    status_input = ui.select(options=status_options, value=db_status, label=t('status')).classes('w-44 dark:bg-slate-900').props(f'outlined dense {select_prop}')
                    
                    rating_options = {i: (t('none') if i == 0 else f'{i} {t("stars" if i > 1 else "star")}') for i in range(6)}
                    rating_input = ui.select(options=rating_options, value=db_rating, label=t('rating')).classes('w-40 dark:bg-slate-900').props(f'outlined dense {select_prop}')
                    
                    start_date_input = ui.input(label=t('start'), value=db_start).classes('w-44 dark:bg-slate-900').props(f'type=date outlined dense {dark_prop}')
                    end_date_input = ui.input(label=t('end'), value=db_end).classes('w-44 dark:bg-slate-900').props(f'type=date outlined dense {dark_prop}')

            # --- FOOTER BUTTONS ---
            with ui.row().classes('w-full justify-end gap-3 mt-2'):
                abbruch_ziel = f'/book/{edit_id}' if ist_edit else '/'
                ui.button(t('cancel'), on_click=lambda: ui.navigate.to(abbruch_ziel)).classes('bg-slate-400 hover:bg-slate-500 text-white px-4 py-2 rounded')
                
                btn_color = 'bg-orange-600 hover:bg-orange-500' if ist_edit else 'bg-green-600 hover:bg-green-500'
                btn_text = t('save_changes') if ist_edit else t('save_in_shelf')
                ui.button(btn_text, on_click=speichern).classes(f'{btn_color} text-white px-6 py-2 rounded shadow')

    async def isbn_suchen():
        isbn_wert = isbn_input.value.strip().replace("-", "") if isbn_input.value else ""
        if not isbn_wert:
            ui.notify(t('notify_isbn_warn'), type='warning')
            return
            
        ui.notify('Frage Daten von isbn.de ab...', type='info')
        scraped_daten = await book_api.scrape_buch_details_isbn_de_async(isbn_wert)
        
        if not scraped_daten:
            scraped_daten = {}
            
        ui.notify('Prüfe Google Books auf missing Details...', type='info')
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
            desc_input.value = vereinte_daten.get('description', '')
            seiten_input.value = int(vereinte_daten.get('pages', 0))
            lang_input.value = vereinte_daten.get('language', 'de')
            
            rohes_datum = vereinte_daten.get('published_date', '')
            pub_date_input.value = formatiere_erscheinungsdatum(rohes_datum, translations.aktuelle_sprache)
            
            if vereinte_daten.get('is_series'):
                series_checkbox.value = True
                reihenname_input.value = vereinte_daten.get('series_name', '')
                band_input.value = vereinte_daten.get('series_number', 0)
            
            formular_rendern.temporaere_cover_url = f"https://buch.isbn.de/gross/{isbn_wert}.jpg" if len(isbn_wert) == 13 else vereinte_daten.get('cover_url', '')
                
            ui.notify(t('notify_api_success'), type='positive')
        else:
            ui.notify(t('notify_api_fail'), type='negative')

    if not ist_edit:
        search_btn.on('click', isbn_suchen)