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
    
    if not aktuelles_buch:
        with basis_layout('edit_book'):
            ui.label('Buch wird geladen...').classes('italic text-slate-400')
            ui.navigate.to('/') 
        return
        
    formular_rendern(edit_id=book_id, daten=aktuelles_buch)


def formular_rendern(edit_id=None, daten=None):
    ist_edit = edit_id is not None
    regale = database.lade_alle_regale()
    
    globale_genres = database.lade_alle_genres(layout.aktiver_user_id)
    genre_liste_auswahl = [g[1] for g in globale_genres]
    bereits_zugeordnete_genres = database.lade_genres_eines_buches(edit_id, layout.aktiver_user_id) if ist_edit else []
    
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    is_dark = user_ui['dark_mode']
    
    dark_prop = 'dark' if is_dark else ''
    select_prop = 'dark popup-content-class="dark"' if is_dark else ''
    
    bg_card = 'bg-slate-800 border-slate-700' if is_dark else 'bg-slate-50 border-slate-200'
    bg_sub_section = 'bg-slate-900/40 border-slate-700/50' if is_dark else 'bg-white border-slate-200/60'
    text_main = 'text-slate-100' if is_dark else 'text-slate-800'
    text_sub = 'text-slate-400' if is_dark else 'text-slate-500'
    text_switch = 'text-slate-200' if is_dark else 'text-slate-700'
    
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
    
    db_format = daten[23] if daten and daten[23] else "PHYSICAL"
    db_ownership = daten[24] if daten and daten[24] else "OWNED"
    db_quantity = daten[25] if daten and daten[25] is not None else 1
    db_location_id = daten[26] if daten else None

    genre_checkboxes = {}

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
        
        user_data = {
            'status': status_input.value if status_input.value else 'UNREAD', 
            'rating': int(rating_input.value) if rating_input.value is not None else 0, 
            'format': format_input.value if format_input.value else 'PHYSICAL',
            'ownership': ownership_input.value if ownership_input.value else 'OWNED', 
            'quantity': int(quantity_input.value) if quantity_input.value is not None else 1,
            'started_at': start_date_input.value if start_date_input.value else "", 
            'finished_at': end_date_input.value if end_date_input.value else ""
        }
        
        ziel_id = database.speichere_buch_in_db(edit_id, layout.aktiver_user_id, book_data, user_data)
        aktive_book_id = edit_id if ist_edit else ziel_id
        ausgewaehlte_genres = [name for name, cb in genre_checkboxes.items() if cb.value]
        database.aktualisiere_buch_genres(aktive_book_id, ausgewaehlte_genres, layout.aktiver_user_id)

        ui.notify(t('notify_saved'), type='positive')
        ui.navigate.to(f'/book/{aktive_book_id}')

    titel_key = 'edit_book' if ist_edit else 'add_book'
    
    with basis_layout(titel_key):
        # OPTIMIERT: px-4 auf Mobile verhindert, dass die Cards an den Displayrand klatschen
        with ui.element('div').classes('w-full max-w-4xl mx-auto mb-20 px-4 flex flex-col gap-6 content-safe'):
            ui.label(t(titel_key)).classes(f'text-2xl font-bold {text_main}')
            
            # =========================================================================
            # BLOCK 1: HARTE BUCHFAKTEN & INFORMATIONEN
            # =========================================================================
            with ui.card().classes(f'w-full p-4 sm:p-6 border shadow-xs flex flex-col gap-4 {bg_card}'):
                ui.label(t('section_book_info')).classes(f'text-sm font-bold uppercase tracking-wider {text_sub} mb-1')
                
                # ISBN-Suche (Optimiert: Flex-col auf Mobile, Button w-full)
                with ui.row().classes('w-full items-center gap-2 flex-col sm:flex-row flex-nowrap'):
                    if not ist_edit:
                        isbn_input = ui.input(label=t('isbn_label'), value=db_isbn).classes('w-full sm:w-64 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                        search_btn = ui.button(t('search')).classes('w-full sm:w-auto bg-blue-600 hover:bg-blue-500 text-white px-4 h-[40px] rounded')
                    else:
                        isbn_input = ui.input(label='ISBN 13', value=db_isbn).classes('w-full sm:w-64 dark:bg-slate-900').props(f'outlined dense readonly {dark_prop}')

                # Titel & Untertitel (Optimiert: flex-col auf Mobile)
                with ui.row().classes('w-full gap-4 flex-col md:flex-row md:flex-nowrap'):
                    titel_input = ui.input(label=t('title'), value=db_titel).classes('w-full md:flex-1 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                    subtitle_input = ui.input(label=t('subtitle'), value=db_subtitle).classes('w-full md:flex-1 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                
                # Autor & Verlag (Optimiert: flex-col auf Mobile)
                with ui.row().classes('w-full gap-4 flex-col md:flex-row md:flex-nowrap'):
                    autor_input = ui.input(label=t('author'), value=db_autor).classes('w-full md:flex-1 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                    publisher_input = ui.input(label=t('publisher'), value=db_publisher).classes('w-full md:flex-1 dark:bg-slate-900').props(f'outlined dense {dark_prop}')

                # Kennzahlen (Optimiert: flex-row mit flex-wrap, Boxen nutzen mobilen Platz besser aus)
                with ui.row().classes('w-full items-center gap-3 mt-1 flex-wrap'):
                    seiten_input = ui.number(label=t('pages'), value=db_seiten, format='%d').classes('flex-1 min-w-[80px] sm:w-24 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                    isbn_10_input = ui.input(label='ISBN 10', value=db_isbn_10).classes('flex-1 min-w-[130px] sm:w-36 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                    pub_date_input = ui.input(label=t('published_date'), value=db_published_date).classes('flex-1 min-w-[130px] sm:w-36 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                    
                    sprach_optionen = {'de': t('lang_de'), 'en': t('lang_en'), 'fr': 'Français', 'es': 'Español', 'it': 'Italiano'}
                    lang_input = ui.select(options=sprach_optionen, value=db_language, label=t('language')).classes('flex-1 min-w-[130px] sm:w-36 dark:bg-slate-900').props(f'outlined dense {select_prop}')
                    
                    # Genres (Wechselt mobil auf 1 Spalte, Tablet 2, Desktop 3)
                    with ui.expansion(t('manage_genres'), icon='local_offer').classes('w-full border rounded-lg bg-slate-100/50 dark:bg-slate-900/30 dark:border-slate-700/50'):
                        with ui.element('div').classes('p-4 w-full'):
                            with ui.grid().classes('w-full grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3'):
                                genre_checkboxes = {}
                                for g_name in genre_liste_auswahl:
                                    ist_gehakt = g_name in bereits_zugeordnete_genres
                                    cb = ui.checkbox(g_name, value=ist_gehakt).classes('text-sm font-medium')
                                    genre_checkboxes[g_name] = cb
                    
                    special_checkbox = ui.checkbox(t('special'), value=db_special).classes(f'w-full sm:w-auto ml-2 {text_switch}')

                # Format, Besitzstatus, Menge & Lagerort (Optimiert: flex-wrap für mobile Bildschirme)
                with ui.row().classes('w-full items-center gap-3 flex-wrap mt-1'):
                    format_options = {'PHYSICAL': t('PHYSICAL'), 'AUDIOBOOK': t('AUDIOBOOK'), 'EBOOK': t('EBOOK')}
                    format_input = ui.select(options=format_options, value=db_format, label=t('format')).classes('flex-1 min-w-[140px] sm:w-40 dark:bg-slate-900').props(f'outlined dense {select_prop}')
                    
                    ownership_options = {'OWNED': t('OWNED'), 'BORROWED': t('BORROWED'), 'LENT': t('LENT'), 'GIVEN_AWAY': t('ownership_given_away')}
                    ownership_input = ui.select(options=ownership_options, value=db_ownership, label=t('ownership')).classes('flex-1 min-w-[140px] sm:w-36 dark:bg-slate-900').props(f'outlined dense {select_prop}')
                    
                    quantity_input = ui.number(label=t('quantity'), value=db_quantity, format='%d').classes('w-20 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                    
                    regale_options = {r[0]: r[1] for r in regale}
                    location_input = ui.select(options=regale_options, value=db_location_id, label=t('location')).classes('flex-1 min-w-[200px] sm:w-56 dark:bg-slate-900').props(f'outlined dense {select_prop}')

                # Mitwirkende Expandable (Optimiert: Zeilenstruktur flex-col)
                with ui.row().classes('w-full'):
                    with ui.expansion(t('contributors'), icon='people').classes(f'w-full border rounded-lg bg-slate-100/50 dark:bg-slate-900/30 dark:border-slate-700/50'):
                        with ui.column().classes('w-full p-4 gap-4'):
                            with ui.row().classes('w-full gap-4 flex-col sm:flex-row sm:flex-nowrap'):
                                translator_input = ui.input(label=t('translator'), value=db_translator).classes('w-full sm:flex-1 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                                narrator_input = ui.input(label=t('narrator'), value=db_narrator).classes('w-full sm:flex-1 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                            with ui.row().classes('w-full gap-4 flex-col sm:flex-row sm:flex-nowrap'):
                                illustrator_input = ui.input(label=t('illustrator'), value=db_illustrator).classes('w-full sm:flex-1 dark:bg-slate-900').props(f'outlined dense {dark_prop}')
                                editor_input = ui.input(label=t('editor'), value=db_editor).classes('w-full sm:flex-1 dark:bg-slate-900').props(f'outlined dense {dark_prop}')

                # Buchreihe (Optimiert: Eingabefelder flex-wrap)
                with ui.row().classes(f'w-full items-center gap-3 mt-1 p-3 rounded-lg border flex-wrap {bg_sub_section}'):
                    series_checkbox = ui.checkbox(t('series'), value=db_is_series).classes(f'w-full sm:w-auto {text_switch}')
                    
                    existierende_reihen = sorted(list({b[9].strip() for b in database.lade_buecher_aus_db(layout.aktiver_user_id) if b[8] and b[9] and b[9].strip()}))
                    # 1. Das Eingabefeld definieren
                    reihenname_input = ui.select(
                        options=existierende_reihen, 
                        value=db_s_name.strip() if db_s_name else None, 
                        label=t('series_name')
                    ).classes('flex-1 min-w-[200px] sm:w-72 dark:bg-slate-900') \
                    .props(f'outlined dense use-input hide-selected fill-input input-debounce="0" new-value-mode="add" {select_prop}') \
                    .bind_visibility_from(series_checkbox, 'value')

                    # 2. Die Filter-Funktion (Nutzt e.args[0] für die Live-Suche)
                    def filter_reihen(e):
                        val = e.args[0].lower() if (e.args and e.args[0]) else ""
                        reihenname_input.options = [r for r in existierende_reihen if val in r.lower()]
                        
                        # TRICK: Wenn der Nutzer tippt, schreiben wir den aktuellen Text parallel 
                        # in das .value-Attribut, damit es beim Speichern nicht verloren geht!
                        if val and not any(r.lower() == val for r in reihenname_input.options):
                            reihenname_input.value = e.args[0]

                    reihenname_input.on('filter', filter_reihen)                                              
                    band_input = ui.number(label=t('series_num'), value=db_s_num, format='%d').classes('w-24 dark:bg-slate-900').props(f'outlined dense {dark_prop}').bind_visibility_from(series_checkbox, 'value')

                # Beschreibung
                desc_input = ui.textarea(label=t('description'), value=db_description).classes('w-full dark:bg-slate-900').props(f'outlined rows=4 {dark_prop}')
            
            # =========================================================================
            # BLOCK 2: PERSÖNLICHE NUTZER-STEUERUNG
            # =========================================================================
            with ui.card().classes(f'w-full p-4 sm:p-6 border shadow-xs flex flex-col gap-4 {bg_card}'):
                ui.label(t('section_personal_info')).classes(f'text-sm font-bold uppercase tracking-wider {text_sub} mb-1')

                # Status, Rating, Daten (Optimiert: Flex-wrap + Mindestbreiten für sauberes Wrapping auf Mobile)
                with ui.row().classes('w-full items-center gap-3 flex-wrap'):
                    status_options = {'UNREAD': t('unread'), 'READING': t('reading'), 'READ': t('read')}
                    status_input = ui.select(options=status_options, value=db_status, label=t('status')).classes('flex-1 min-w-[140px] sm:w-44 dark:bg-slate-900').props(f'outlined dense {select_prop}')
                    
                    rating_options = {i: (t('none') if i == 0 else f'{i} {t("stars" if i > 1 else "star")}') for i in range(6)}
                    rating_input = ui.select(options=rating_options, value=db_rating, label=t('rating')).classes('flex-1 min-w-[140px] sm:w-40 dark:bg-slate-900').props(f'outlined dense {select_prop}')
                    
                    start_date_input = ui.input(label=t('start'), value=db_start).classes('flex-1 min-w-[140px] sm:w-44 dark:bg-slate-900').props(f'type=date outlined dense {dark_prop}')
                    end_date_input = ui.input(label=t('end'), value=db_end).classes('flex-1 min-w-[140px] sm:w-44 dark:bg-slate-900').props(f'type=date outlined dense {dark_prop}')

            # --- FOOTER BUTTONS (Optimiert: flex-col-reverse auf Mobile -> Speichern oben, Abbrechen unten) ---
            with ui.row().classes('w-full gap-3 mt-2 flex-col-reverse sm:flex-row sm:justify-end pb-12 sm:pb-0'):
                abbruch_ziel = f'/book/{edit_id}' if ist_edit else '/'
                ui.button(t('cancel'), on_click=lambda: ui.navigate.to(abbruch_ziel)).classes('w-full sm:w-auto bg-slate-400 hover:bg-slate-500 text-white px-4 py-2.5 rounded')
                
                btn_color = 'bg-orange-600 hover:bg-orange-500' if ist_edit else 'bg-green-600 hover:bg-green-500'
                btn_text = t('save_changes') if ist_edit else t('save_in_shelf')
                ui.button(btn_text, on_click=speichern).classes(f'w-full sm:w-auto {btn_color} text-white px-6 py-2.5 rounded shadow text-base font-semibold')

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