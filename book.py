from nicegui import ui
import database
from layout import basis_layout
import translations
from translations import t
from datetime import datetime

@ui.page('/book/{b_id}')
def detailseite(b_id: int):
    import layout
    
    buecher = database.lade_buecher_aus_db(layout.aktiver_user_id)
    buch = next((b for b in buecher if b[0] == b_id), None)
    
    if not buch:
        with basis_layout('not_found'):
            ui.label(t('not_found')).classes('text-xl text-red-500 font-bold')
            ui.button(t('back_to_shelf'), on_click=lambda: ui.navigate.to('/')).classes('mt-4 bg-slate-600 text-white')
        return

    # Alle Felder entpacken
    (
        book_id, title, author, isbn_13, pages, 
        status, rating, special, is_series, s_name, s_num, 
        start, end, subtitle, translator, narrator, illustrator, editor,
        isbn_10, publisher, published_date, language, description,
        format_type, ownership, quantity, location_id, location_name
    ) = buch

    # Absicherung für leere Benutzerdaten
    status = status or 'UNREAD'
    rating = rating if rating is not None else 0
    format_type = format_type or 'PHYSICAL'
    ownership = ownership or 'OWNED'
    quantity = quantity if quantity is not None else 1

    # --- LIVE SPEICHERFUNKTION (NUR NOCH FÜR STATUS & RATING) ---
    def inline_speichern():
        """Speichert Status und Bewertung des aktuellen Nutzers live bei Änderung."""
        aktuelle_book_data = {
            'title': title, 'subtitle': subtitle, 'author': author,
            'translator': translator, 'narrator': narrator, 'illustrator': illustrator, 'editor': editor,
            'isbn': isbn_13, 'isbn_10': isbn_10, 'publisher': publisher, 'published_date': published_date,
            'language': language, 'description': description, 'pages': pages, 'special': special,
            'is_series': is_series, 'series_name': s_name, 'series_number': s_num,
            'location_id': location_id  # Bleibt unverändert via Text
        }
        
        aktuelle_user_data = {
            'status': status_select.value,
            'rating': int(rating_select.value),
            'format': format_type,    # Bleibt unverändert via Text
            'ownership': ownership,  # Bleibt unverändert via Text
            'quantity': quantity,    # Bleibt unverändert via Text
            'started_at': start or "",
            'finished_at': end or ""
        }
        
        database.speichere_buch_in_db(book_id, layout.aktiver_user_id, aktuelle_book_data, aktuelle_user_data)
        ui.notify(t('notify_saved'), type='positive', duration=1)

    with basis_layout(title):
        with ui.element('div').classes('w-full max-w-4xl mx-auto flex flex-col md:flex-row gap-8 items-start'):
            
            # --- LINKE SPALTE: COVER & REINE TEXT-INFOS ---
            with ui.element('div').classes('w-full md:w-1/3 flex flex-col gap-4'):
                ui.image(f'https://picsum.photos/seed/{book_id}/400/600').classes('w-full rounded-lg shadow-md border')
                
                # Statische Infokarte (Änderungen bequem über den Edit-Stift oben rechts)
                with ui.card().classes('w-full p-4 bg-slate-50 border border-slate-200 shadow-sm flex flex-col gap-2.5 text-sm text-slate-700'):
                    ui.label('Details').classes('text-xs font-bold text-slate-400 uppercase tracking-wider mb-1')
                    
                    ui.label(f"{t('format')}: {t(format_type)}")
                    ui.label(f"{t('ownership')}: {t(ownership)}")
                    ui.label(f"{t('quantity')}: {quantity}")
                    
                    if location_name:
                        ui.separator().classes('my-1')
                        ui.label(f"📍 {t('location')}: {location_name}").classes('font-semibold text-blue-600')

            # --- RECHTE SPALTE: TITELZEILE & METADATEN ---
            with ui.element('div').classes('flex-1 flex flex-col gap-4 w-full'):
                
                # Titel-Zeile mit Stift- und Lösch-Icon oben rechts
                with ui.row().classes('w-full justify-between items-start no-wrap gap-4'):
                    with ui.element('div').classes('flex flex-col gap-1 flex-1'):
                        ui.label(title).classes('text-3xl font-bold text-slate-800 leading-tight')
                        if subtitle:
                            ui.label(subtitle).classes('text-lg text-slate-500 font-medium')
                        ui.label(author or t('unknown_author')).classes('text-xl text-slate-600 italic mt-1')
                    
                    with ui.row().classes('items-center gap-1 shrink-0'):
                        ui.button(icon='edit', on_click=lambda: ui.navigate.to(f'/edit/{book_id}')) \
                            .props('flat round dense text-color=blue-600').classes('text-blue-600') \
                            .tooltip(t('edit_book'))
                        
                        def aktion_loeschen():
                            database.loesche_buch_aus_db(book_id)
                            ui.notify(f'"{title}" {t("notify_deleted")}', type='positive')
                            ui.navigate.to('/')

                        ui.button(icon='delete', on_click=aktion_loeschen) \
                            .props('flat round dense text-color=red-600').classes('text-red-600') \
                            .tooltip(t('delete'))

                # --- INTERAKTIVE LIVE-ZONE (NUR STATUS & RATINGS) ---
                with ui.row().classes('items-center gap-4 mt-2 w-full bg-slate-100/60 p-3 rounded-lg border border-slate-200/60'):
                    status_opts = {'UNREAD': t('unread'), 'READING': t('reading'), 'READ': t('read')}
                    status_select = ui.select(options=status_opts, value=status, on_change=inline_speichern)\
                        .classes('w-44 bg-white px-2 rounded shadow-sm').props('dense borderless')
                    
                    rating_opts = {i: (t('none') if i == 0 else f'{i} {t("stars" if i > 1 else "star")}') for i in range(6)}
                    rating_select = ui.select(options=rating_opts, value=rating, on_change=inline_speichern)\
                        .classes('w-36 bg-white px-2 rounded shadow-sm').props('dense borderless')

                ui.separator().classes('my-2')

                # Klappentext / Beschreibung
                if description:
                    with ui.element('div').classes('bg-slate-50/50 p-4 rounded-lg border border-slate-100 italic text-slate-700 leading-relaxed max-h-60 overflow-y-auto'):
                        ui.markdown(description)
                    ui.separator().classes('my-2')

                # --- DYNAMISCHE FORMATIERUNG ÜBER TRANSLATIONS.PY ---
                formatiertes_datum = translations.format_localized_date(published_date)
                ausgeschriebene_sprache = translations.format_book_language(language)

                # --- METADATEN-BLOCK (ANZEIGE) ---
                with ui.element('div').classes('grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm text-slate-600'):
                    ui.label(f"{t('pages')}: {pages or 0}")
                    if publisher: ui.label(f"{t('publisher')}: {publisher}")
                    if formatiertes_datum: ui.label(f"{t('published_date')}: {formatiertes_datum}")
                    if ausgeschriebene_sprache: ui.label(f"{t('language')}: {ausgeschriebene_sprache}")
                    if isbn_13: ui.label(f"ISBN-13: {isbn_13}")
                    if isbn_10: ui.label(f"ISBN-10: {isbn_10}")
                    
                    if translator: ui.label(f"{t('translator')}: {translator}")
                    if narrator: ui.label(f"{t('narrator')}: {narrator}")
                    if illustrator: ui.label(f"{t('illustrator')}: {illustrator}")
                    if editor: ui.label(f"{t('editor')}: {editor}")

                # Buchreihe-Informationen
                if is_series and s_name:
                    with ui.row().classes('w-full mt-2 p-3 bg-blue-50/50 rounded border border-blue-100 items-center text-sm text-blue-800 font-medium'):
                        ui.icon('layers').classes('text-blue-500')
                        ui.label(f"{t('series_name')}: {s_name} ({t('series_volume')} {s_num or 0})")

                # Lese-Zeitraum
                if start or end:
                    with ui.row().classes('w-full mt-2 p-3 bg-emerald-50/50 rounded border border-emerald-100 text-sm text-emerald-800'):
                        ui.icon('event').classes('text-emerald-500')
                        ui.label(f"{t('start')}: {start or '--'}   |   {t('end')}: {end or '--'}")