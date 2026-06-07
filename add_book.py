from nicegui import ui
import database
import requests
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
    # Dynamische User-ID statt hartcodierter 1!
    all_books = database.lade_buecher_aus_db(layout.aktiver_user_id)
    aktuelles_buch = next((b for b in all_books if b[0] == book_id), None)
    formular_rendern(edit_id=book_id, daten=aktuelles_buch)


def formular_rendern(edit_id=None, daten=None):
    ist_edit = edit_id is not None
    regale = database.lade_alle_regale()
    
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
    
    # NEUE FELDER AUS DER DB ENTGEGENNEHMEN
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

    def isbn_suchen():
        isbn_wert = isbn_input.value.strip().replace("-", "")
        if not isbn_wert:
            ui.notify(t('notify_isbn_warn'), type='warning')
            return
        try:
            url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn_wert}&key={GOOGLE_API_KEY}"
            response = requests.get(url, timeout=5)
            res_data = response.json()
            if "items" not in res_data:
                url = f"https://www.googleapis.com/books/v1/volumes?q={isbn_wert}&key={GOOGLE_API_KEY}"
                response = requests.get(url, timeout=5)
                res_data = response.json()
                
            if "items" in res_data:
                volume_info = res_data["items"][0]["volumeInfo"]
                titel_input.value = volume_info.get("title", "")
                subtitle_input.value = volume_info.get("subtitle", "")
                
                autoren = volume_info.get("authors", [])
                autor_input.value = ", ".join(autoren)
                seiten_input.value = volume_info.get("pageCount", 0)
                
                # Erweiterte automatische API-Befüllung
                publisher_input.value = volume_info.get("publisher", "")
                pub_date_input.value = volume_info.get("publishedDate", "")
                lang_input.value = volume_info.get("language", "de")
                desc_input.value = volume_info.get("description", "")
                
                ui.notify(t('notify_api_success'), type='positive')
            else:
                ui.notify(t('notify_api_fail'), type='negative')
        except Exception as e:
            ui.notify(f'Fehler: {str(e)}', type='negative')

    def speichern():
        title = titel_input.value.strip()
        if not title:
            ui.notify('Titel fehlt!' if translations.aktuelle_sprache == 'de' else 'Title is missing!', type='warning')
            return

        book_data = {
            'title': title,
            'subtitle': subtitle_input.value.strip(),
            'author': autor_input.value.strip(),
            'translator': translator_input.value.strip(),
            'narrator': narrator_input.value.strip(),
            'illustrator': illustrator_input.value.strip(),
            'editor': editor_input.value.strip(),
            'isbn': isbn_input.value.strip().replace("-", ""),
            'isbn_10': isbn_10_input.value.strip(),
            'publisher': publisher_input.value.strip(),
            'published_date': pub_date_input.value.strip(),
            'language': lang_input.value.strip(),
            'description': desc_input.value.strip(),
            'pages': int(seiten_input.value or 0),
            'special': special_checkbox.value,
            'is_series': series_checkbox.value,
            'series_name': reihenname_input.value.strip() if series_checkbox.value else "",
            'series_number': int(band_input.value or 0) if series_checkbox.value else 0,
            'location_id': location_input.value
        }
        
        user_data = {
            'status': status_input.value,
            'rating': int(rating_input.value),
            'format': format_input.value,
            'ownership': ownership_input.value,
            'quantity': int(quantity_input.value or 1),
            'started_at': start_date_input.value,
            'finished_at': end_date_input.value
        }
        
        # Dynamische ID des aktuell wirkenden Nutzers nutzen!
        database.speichere_buch_in_db(edit_id, layout.aktiver_user_id, book_data, user_data)
        ui.notify(t('notify_saved'), type='positive')
        ui.navigate.to('/')

    titel_key = 'edit_book' if ist_edit else 'add_book'
    
    with basis_layout(titel_key):
        with ui.element('div').classes('w-full max-w-4xl mx-auto mb-12'):
            ui.label(t(titel_key)).classes('text-2xl font-bold text-slate-700 mb-6')
            
            with ui.card().classes('w-full p-6 bg-slate-50 shadow-sm flex flex-col gap-4'):
                
                # --- ISBN & SUCHE ---
                if not ist_edit:
                    with ui.row().classes('w-full items-center gap-4'):
                        isbn_input = ui.input(label=t('isbn_label'), value=db_isbn).classes('w-64')
                        ui.button(t('search'), on_click=isbn_suchen).classes('bg-blue-600 text-white')
                    ui.separator()
                else:
                    isbn_input = ui.input(label='ISBN 13', value=db_isbn).classes('w-64').props('readonly')

                # --- TITEL & METADATEN ---
                with ui.row().classes('w-full gap-4'):
                    titel_input = ui.input(label=t('title'), value=db_titel).classes('flex-1')
                    subtitle_input = ui.input(label=t('subtitle'), value=db_subtitle).classes('flex-1')
                
                with ui.row().classes('w-full gap-4'):
                    autor_input = ui.input(label=t('author'), value=db_autor).classes('flex-1')
                    publisher_input = ui.input(label=t('publisher'), value=db_publisher).classes('flex-1')

                # --- ERWEITERTE MITWIRKENDE ---
                with ui.row().classes('w-full gap-4'):
                    translator_input = ui.input(label=t('translator'), value=db_translator).classes('flex-1')
                    narrator_input = ui.input(label=t('narrator'), value=db_narrator).classes('flex-1')
                
                with ui.row().classes('w-full gap-4'):
                    illustrator_input = ui.input(label=t('illustrator'), value=db_illustrator).classes('flex-1')
                    editor_input = ui.input(label=t('editor'), value=db_editor).classes('flex-1')

                # --- BUCHSPEZIFISCHE INFORMATIONEN ---
                with ui.row().classes('w-full items-center gap-4 mt-2'):
                    seiten_input = ui.number(label=t('pages'), value=db_seiten, format='%d').classes('w-24')
                    isbn_10_input = ui.input(label='ISBN 10', value=db_isbn_10).classes('w-36')
                    pub_date_input = ui.input(label=t('published_date'), value=db_published_date).classes('w-36')
                    lang_input = ui.input(label=t('language'), value=db_language).classes('w-28')
                    special_checkbox = ui.checkbox(t('special'), value=db_special).classes('ml-2')

                # --- PHYSISCHER LAGERORT (GLOBAL) ---
                with ui.row().classes('w-full items-center gap-6 mt-2 p-3 bg-amber-50/40 rounded border border-amber-100'):
                    regal_options = {r[0]: r[1] for r in regale}
                    location_input = ui.select(options=regal_options, value=db_location_id, label=t('location')).classes('w-64 bg-white px-2 rounded')

                # --- PERSÖNLICHE NUTZER-STEUERUNG (STATUS, FORMAT, MENGE) ---
                with ui.row().classes('w-full items-center gap-4 mt-2 p-3 bg-slate-100 rounded border'):
                    status_options = {'UNREAD': t('unread'), 'READING': t('reading'), 'READ': t('read')}
                    status_input = ui.select(options=status_options, value=db_status, label=t('status')).classes('w-44 bg-white px-2 rounded')
                    
                    rating_options = {i: (t('none') if i == 0 else f'{i} {t("stars" if i > 1 else "star")}') for i in range(6)}
                    rating_input = ui.select(options=rating_options, value=db_rating, label=t('rating')).classes('w-36 bg-white px-2 rounded')
                    
                    format_options = {'PHYSICAL': t('PHYSICAL'), 'AUDIOBOOK': t('AUDIOBOOK'), 'EBOOK': t('EBOOK')}
                    format_input = ui.select(options=format_options, value=db_format, label=t('format')).classes('w-44 bg-white px-2 rounded')
                    
                    ownership_options = {'OWNED': t('OWNED'), 'BORROWED': t('BORROWED'), 'LENT': t('LENT')}
                    ownership_input = ui.select(options=ownership_options, value=db_ownership, label=t('ownership')).classes('w-36 bg-white px-2 rounded')
                    
                    quantity_input = ui.number(label=t('quantity'), value=db_quantity, format='%d').classes('w-20 bg-white px-2 rounded')

                # --- REIHEN-DETAILS ---
                with ui.row().classes('w-full items-center gap-6 mt-2 p-3 bg-blue-50/40 rounded border border-blue-100'):
                    series_checkbox = ui.checkbox(t('series'), value=db_is_series)
                    reihenname_input = ui.input(label=t('series_name'), value=db_s_name).classes('w-80').bind_visibility_from(series_checkbox, 'value')
                    band_input = ui.number(label=t('series_num'), value=db_s_num, format='%d').classes('w-28').bind_visibility_from(series_checkbox, 'value')

                # --- LESEZEITEN ---
                with ui.row().classes('w-full items-center gap-6 mt-2 p-3 bg-emerald-50/40 rounded border border-emerald-100'):
                    start_date_input = ui.input(label=t('start'), value=db_start).classes('w-48').props('type=date')
                    end_date_input = ui.input(label=t('end'), value=db_end).classes('w-48').props('type=date')

                # --- TEXTBESCHREIBUNG ---
                desc_input = ui.textarea(label=t('description'), value=db_description).classes('w-full h-24')

                # --- FOOTER BUTTONS ---
                with ui.row().classes('w-full justify-end gap-3 mt-4'):
                    ui.button(t('cancel'), on_click=lambda: ui.navigate.to('/')).classes('bg-slate-400 text-white')
                    
                    btn_color = 'bg-orange-600' if ist_edit else 'bg-green-600'
                    btn_text = t('save_changes') if ist_edit else t('save_in_shelf')
                    ui.button(btn_text, on_click=speichern).classes(f'{btn_color} text-white px-6')