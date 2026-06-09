from nicegui import ui
import database
from layout import basis_layout
import translations
from translations import t
from datetime import datetime
import asyncio
import book_api

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
    gesamt_seiten = pages or 1
    
    author_id = None
    if author:
        author_id = database.hole_autoren_id_durch_name(layout.aktiver_user_id, author)

    # --- 1. DARKMODE-ZUSTAND FÜR PROPS ERMITTLEN ---
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    is_dark = user_ui['dark_mode']
    dark_prop = 'dark popup-content-class="dark"' if is_dark else ''
    dialog_prop = 'dark' if is_dark else ''

    # --- LIVE SPEICHERFUNKTION (STATUS & RATING) ---
    def inline_speichern():
        """Speichert Status und Bewertung live und aktualisiert alle UI-Zonen."""
        aktuelle_book_data = {
            'title': title, 'subtitle': subtitle, 'author': author,
            'translator': translator, 'narrator': narrator, 'illustrator': illustrator, 'editor': editor,
            'isbn': isbn_13, 'isbn_10': isbn_10, 'publisher': publisher, 'published_date': published_date,
            'language': language, 'description': description, 'pages': pages, 'special': special,
            'is_series': is_series, 'series_name': s_name, 'series_number': s_num,
            'location_id': location_id
        }
        
        aktuelle_user_data = {
            'status': status_select.value,
            'rating': int(rating_select.value),
            'format': format_type,
            'ownership': ownership,
            'quantity': quantity,
            'started_at': start or "",
            'finished_at': end or ""
        }
        
        database.speichere_buch_in_db(book_id, layout.aktiver_user_id, aktuelle_book_data, aktuelle_user_data)
        ui.notify(t('notify_saved'), type='positive', duration=1)
        
        infokarte_links_refresh.refresh()
        tracking_zone_refresh.refresh()

    with basis_layout(title):
        ui.button(
                t('back'), 
                icon='arrow_back', 
                on_click=lambda: ui.run_javascript('window.history.back()')
            ).props('flat dense').classes('text-slate-500 dark:text-slate-400 mb-4')
        
        with ui.element('div').classes('w-full max-w-4xl mx-auto flex flex-col md:flex-row gap-8 items-start'):
            
            # --- LINKE SPALTE: COVER & REINE TEXT-INFOS ---
            with ui.element('div').classes('w-full md:w-1/3 flex flex-col gap-4'):
                
                cover_pfad = database.hole_cover_url(book_id)
                
                with ui.element('div').classes('relative w-full aspect-[2/3] rounded-lg shadow-md border border-slate-200 dark:border-slate-700 bg-slate-200 dark:bg-slate-800 flex items-center justify-center overflow-hidden') as cover_container:
                    if cover_pfad != "/covers/placeholder.jpg":
                        ui.image(cover_pfad).classes('w-full h-full object-cover')
                    else:
                        with ui.element('div').classes('flex flex-col items-center gap-2 text-slate-400 dark:text-slate-500'):
                            ui.icon('book', size='xl')
                            ui.label(t('no_cover') if 'no_cover' in translations.LANGUAGES[translations.aktuelle_sprache] else 'Kein Cover').classes('text-xs font-medium')

                # --- DIALOG FÜR DIE ONLINE-BILDER-SUCHE ---
                style_dialog_card = 'background-color: #1e293b; color: #f8fafc;' if is_dark else ''
                
                with ui.dialog() as search_dialog, ui.card().classes('p-6 w-full max-w-2xl flex flex-col gap-4').style(style_dialog_card):
                    ui.label('Cover im Internet suchen').classes('text-lg font-bold text-slate-700 dark:text-slate-100')
                    ui.label('Wähle ein passendes Cover aus der Live-Suche aus:').classes('text-xs text-slate-500 dark:text-slate-400 -mt-2')
                    
                    galerie_container = ui.element('div').classes('w-full')
                    
                    async def bild_waehlen(url):
                        search_dialog.close()
                        ui.notify('Speichere ausgewähltes Cover...', type='info')
                        
                        erfolg = database.lade_und_speichere_cover(book_id, url)
                        if erfolg:
                            ui.notify('Cover erfolgreich aktualisiert!', type='positive')
                            await asyncio.sleep(0.5)
                            ui.navigate.to(f'/book/{book_id}')
                        else:
                            ui.notify('Fehler beim Download des Covers.', type='negative')

                    async def suche_ausfuehren():
                        with galerie_container:
                            ui.spinner(size='lg').classes('mx-auto my-8 block')
                        
                        such_isbn = isbn_13 or isbn_10 or ""
                        urls = []
                        
                        if isbn_13 and len(str(isbn_13).strip()) == 13:
                            isbn_clean = str(isbn_13).strip()
                            isbnde_url = f"https://buch.isbn.de/gross/{isbn_clean}.jpg"
                            urls.append(isbnde_url)

                        google_urls = await book_api.google_bildsuche_async(title, author, isbn=such_isbn)
                        if google_urls:
                            urls.extend(google_urls)
                        
                        galerie_container.clear()
                        
                        if not urls:
                            with galerie_container:
                                ui.label('Keine passenden Bilder gefunden.').classes('text-center text-slate-500 dark:text-slate-400 my-4')
                            return
                            
                        with galerie_container:
                            with ui.grid(columns=4).classes('gap-4 w-full justify-items-center max-h-96 overflow-y-auto p-1'):
                                for index, url in enumerate(urls):
                                    is_isbn_de = (index == 0 and isbn_13 and url.startswith("https://buch.isbn.de"))
                                    rahmen_css = 'border-2 border-emerald-500 shadow-md relative' if is_isbn_de else 'border border-slate-200 dark:border-slate-700'
                                    
                                    with ui.element('div').classes(f'rounded p-1 hover:shadow-md hover:border-blue-500 cursor-pointer transition-all bg-white dark:bg-slate-900 {rahmen_css}'):
                                        img = ui.image(url).classes('w-24 h-36 object-cover')
                                        img.on('click', lambda e, u=url: bild_waehlen(u))
                                        
                                        if is_isbn_de:
                                            with ui.element('div').classes('absolute top-0 left-0 bg-emerald-600 text-white text-[9px] font-bold px-1 py-0.5 rounded-br shadow'):
                                                ui.label('ISBN.de')

                    ui.button(t('cancel'), on_click=search_dialog.close).classes('bg-slate-400 dark:bg-slate-600 text-white w-full mt-2')

                # --- DIALOG FÜR MANUELLEN UPLOAD ---
                # --- DIALOG FÜR MANUELLEN UPLOAD (BACKGROUND FIXED) ---
                with ui.dialog() as upload_dialog, ui.card().classes('p-6 w-96 flex flex-col gap-4').style(style_dialog_card):
                    ui.label('Cover hochladen / ändern').classes('text-lg font-bold text-slate-700 dark:text-slate-100')
                    
                    ui.upload(
                        label='Bild auswählen (JPG/PNG)',
                        auto_upload=True,
                        on_upload=lambda e: cover_verarbeiten(e, upload_dialog, cover_container)
                    ).props(f'accept=image/* max-files=1 {dialog_prop}').classes('w-full')
                    
                    ui.button(t('cancel'), on_click=upload_dialog.close).classes('bg-slate-400 dark:bg-slate-600 text-white w-full')

                async def cover_verarbeiten(e, dialog, container):
                    import os
                    os.makedirs(database.COVER_DIR, exist_ok=True)
                    ziel = os.path.join(database.COVER_DIR, f"{book_id}.jpg")
                    try:
                        await e.file.save(ziel)
                        ui.notify('Cover erfolgreich aktualisiert!', type='positive')
                        dialog.close()
                        ui.navigate.to(f'/book/{book_id}')
                    except Exception as ex:
                        ui.notify(f'Fehler beim Speichern: {str(ex)}', type='negative')

                # --- CONTROL BUTTONS UNTER DEM COVER ---
                with ui.row().classes('w-full justify-center gap-2'):
                    ui.button('Cover ändern', icon='photo_camera', on_click=upload_dialog.open) \
                        .props('flat dense').classes('text-blue-600 dark:text-blue-400 text-xs')
                    
                    ui.button('Online suchen', icon='search', on_click=lambda: [search_dialog.open(), asyncio.create_task(suche_ausfuehren())]) \
                        .props('flat dense').classes('text-emerald-600 dark:text-emerald-400 text-xs')

                @ui.refreshable
                @ui.refreshable
                def infokarte_links_refresh():
                    # REPARIERT: Darkmode-Zustand direkt für die linke Karte auslesen
                    user_ui_links = database.lade_user_settings(layout.aktiver_user_id)
                    is_dark_links = user_ui_links['dark_mode']
                    
                    # Farb-Definitionen für die linke Infokarte
                    bg_infokarte = 'bg-slate-800 border-slate-700 text-slate-200' if is_dark_links else 'bg-slate-50 border-slate-200 text-slate-700'
                    bg_zeit_box = 'bg-slate-900 border-slate-700 text-slate-300' if is_dark_links else 'bg-white border-slate-100 text-slate-500'
                    text_zeit_label = 'text-emerald-400' if is_dark_links else 'text-emerald-600'
                    text_zeit_read = 'text-blue-400' if is_dark_links else 'text-blue-600'
                    text_location = 'text-blue-400' if is_dark_links else 'text-blue-600'

                    with ui.card().classes(f'w-full p-4 shadow-sm flex flex-col gap-2.5 text-sm {bg_infokarte}'):
                        
                        with ui.row().classes('w-full justify-between items-center mb-1'):
                            ui.label('Details').classes('text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider')
                        
                        ui.label(f"{t('format')}: {t(format_type)}")
                        ui.label(f"{t('ownership')}: {t(ownership)}")
                        ui.label(f"{t('quantity')}: {quantity}")
                        
                        real_start, real_end, cyc_status = database.hole_aktuelle_lesezeiten(layout.aktiver_user_id, book_id)
                        
                        if real_start or real_end:
                            ui.separator().classes('my-1 dark:bg-slate-700')
                            # REPARIERT: bg_zeit_box zwingt die kleine innere Box in den Darkmode-Hintergrund
                            with ui.element('div').classes(f'flex flex-col gap-1 text-xs p-2 rounded border shadow-inner {bg_zeit_box}'):
                                if cyc_status == 'READING':
                                    ui.label('⚡ Aktueller Durchgang:').classes(f'font-bold {text_zeit_label in locals() and text_zeit_label or text_zeit_label}')
                                    ui.label(f"Gestartet am: {translations.format_localized_date(real_start) or '--'}")
                                elif cyc_status == 'READ':
                                    ui.label('✅ Zuletzt gelesen:').classes(f'font-bold {text_zeit_read}')
                                    ui.label(f"Vom: {translations.format_localized_date(real_start) or '--'}")
                                    ui.label(f"Bis: {translations.format_localized_date(real_end) or '--'}")

                        if location_name:
                            ui.separator().classes('my-1 dark:bg-slate-700')
                            ui.label(f"📍 {t('location')}: {location_name}").classes(f'font-semibold {text_location}')
                infokarte_links_refresh()

            # --- RECHTE SPALTE: TITELZEILE & METADATEN ---
            with ui.element('div').classes('flex-1 flex flex-col gap-4 w-full'):
                
                with ui.row().classes('w-full justify-between items-start no-wrap gap-4'):
                    with ui.element('div').classes('flex flex-col gap-1 flex-1'):
                        ui.label(title).classes('text-3xl font-bold text-slate-800 dark:text-slate-100 leading-tight')
                        if subtitle:
                            ui.label(subtitle).classes('text-lg text-slate-500 dark:text-slate-400 font-medium')
                        if author and author_id:
                            ui.label(author) \
                                .classes('text-xl text-slate-600 dark:text-slate-300 italic mt-1 cursor-pointer hover:text-blue-600 dark:hover:text-blue-400 hover:underline transition-colors') \
                                .on('click', lambda: ui.navigate.to(f'/author/{author_id}')) \
                                .tooltip('Zum Autorenprofil wechseln')
                        else:
                            ui.label(author or t('unknown_author')).classes('text-xl text-slate-600 dark:text-slate-300 italic mt-1')
                    
                    with ui.row().classes('items-center gap-1 shrink-0'):
                        if isbn_13 and (not description or not publisher or pages <= 1 or not s_name):
                            async def metadaten_blitz_update():
                                ui.notify('Scrape fehlende Buchdaten von isbn.de...', type='info')
                                scraped_data = await book_api.scrape_buch_details_isbn_de_async(isbn_13)
                                
                                if scraped_data:
                                    database.aktualisiere_buch_metadaten(book_id, scraped_data)
                                    ui.notify('Metadaten erfolgreich in DB gespeichert! 🎉', type='positive')
                                    await asyncio.sleep(0.5)
                                    ui.navigate.to(f'/book/{book_id}') 
                                else:
                                    ui.notify('Keine Daten auf isbn.de gefunden.', type='warning')

                            ui.button(icon='auto_fix_high', on_click=lambda: metadaten_blitz_update()) \
                                .props('flat round dense').classes('text-emerald-600 dark:text-emerald-400') \
                                .tooltip('Fehlende Metadaten online abrufen & dauerhaft einspeichern')
                        
                        ui.button(icon='edit', on_click=lambda: ui.navigate.to(f'/edit/{book_id}')) \
                            .props('flat round dense text-color=blue-600').classes('text-blue-600 dark:text-blue-400') \
                            .tooltip(t('edit_book'))
                        
                        # --- BÜCHER-LÖSCHEN MIT ERZWUNGENEM POPUP-DESIGN ---
                        def aktion_loeschen():
                            # Wir holen uns den exakten Darkmode-Status des Users
                            user_ui_delete = database.lade_user_settings(layout.aktiver_user_id)
                            is_dark_delete = user_ui_delete['dark_mode']
                            
                            # Stil-Erzwingung für das Popup-Fenster
                            style_popup = 'background-color: #1e293b; color: #f8fafc;' if is_dark_delete else ''
                            
                            with ui.dialog() as confirm_delete_dial, ui.card().classes('p-5 flex flex-col gap-4 w-full max-w-sm').style(style_popup):
                                ui.label('Buch unwiderruflich löschen? 🚨').classes('text-lg font-bold text-red-500')
                                ui.label(f'Möchtest du das Buch "{title}" wirklich aus deiner Bibliothek entfernen? Alle damit verknüpften Lesestände, Statistiken und Kalendereinträge werden permanent gelöscht.').classes('text-sm text-slate-600 dark:text-slate-300')
                                
                                with ui.row().classes('w-full justify-end gap-2 mt-2'):
                                    ui.button(t('cancel'), on_click=confirm_delete_dial.close).props('flat').classes('text-slate-500 dark:text-slate-400')
                                    
                                    async def definitiv_aus_db_werfen():
                                        confirm_delete_dial.close()
                                        database.loesche_buch_aus_db(book_id)
                                        ui.notify(f'"{title}" {t("notify_deleted")}', type='positive')
                                        ui.navigate.to('/')
                                        
                                    ui.button(t('delete'), on_click=definitiv_aus_db_werfen).classes('bg-red-500 text-white px-4')
                                    
                            confirm_delete_dial.open()

                        ui.button(icon='delete', on_click=aktion_loeschen) \
                            .props('flat round dense text-color=red-600').classes('text-red-600 dark:text-red-400') \
                            .tooltip(t('delete'))

                # --- INTERAKTIVE LIVE-ZONE (STATUS & RATINGS) ---
                with ui.row().classes('items-center gap-4 mt-2 w-full bg-slate-100/60 dark:bg-slate-800 p-3 rounded-lg border border-slate-200/60 dark:border-slate-700'):
                    status_opts = {'UNREAD': t('unread'), 'READING': t('reading'), 'READ': t('read')}
                    status_select = ui.select(options=status_opts, value=status, on_change=inline_speichern)\
                        .classes('w-44 px-2 rounded dark:bg-slate-900').props(f'dense borderless {dark_prop}')
                    
                    rating_opts = {i: (t('none') if i == 0 else f'{i} {t("stars" if i > 1 else "star")}') for i in range(6)}
                    rating_select = ui.select(options=rating_opts, value=rating, on_change=inline_speichern)\
                        .classes('w-36 px-2 rounded dark:bg-slate-900').props(f'dense borderless {dark_prop}')

                ui.separator().classes('my-2 dark:bg-slate-700')

                # --- KLAPPENTEXT / BESCHREIBUNG ---
                beschreibung_container = ui.element('div').classes('w-full')
                
                with beschreibung_container:
                    if description:
                        with ui.element('div').classes('bg-slate-50/50 dark:bg-slate-800 p-4 rounded-lg border border-slate-100 dark:border-slate-700 italic text-slate-700 dark:text-slate-300 leading-relaxed max-h-60 overflow-y-auto w-full'):
                            ui.markdown(description)
                        ui.separator().classes('my-2 dark:bg-slate-700')

                # --- METADATEN-BLOCK ---
                formatiertes_datum = translations.format_localized_date(published_date)
                ausgeschriebene_sprache = translations.format_book_language(language)

                with ui.element('div').classes('grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm text-slate-600 dark:text-slate-400'):
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

                if is_series and s_name:
                    with ui.row().classes('w-full mt-2 p-3 bg-blue-50/50 dark:bg-slate-800 rounded border border-blue-100 dark:border-blue-900/50 items-center text-sm text-blue-800 dark:text-blue-300 font-medium'):
                        ui.icon('layers').classes('text-blue-500 dark:text-blue-400')
                        ui.label(f"{t('series_name')}: {s_name} ({t('series_volume')} {s_num or 0})")

                ui.separator().classes('my-4 dark:bg-slate-700')

                # --- TRACKING-ZONE ---
                @ui.refreshable
                # --- TRACKING-ZONE (ERZWUNGENER DESIGN-WECHSEL) ---
                @ui.refreshable
                def tracking_zone_refresh():
                    current_status = status_select.value
                    
                    # Hier holen wir uns den Zustand frisch in den Refresh-Scope
                    user_ui_fresh = database.lade_user_settings(layout.aktiver_user_id)
                    is_dark_fresh = user_ui_fresh['dark_mode']
                    dark_prop_fresh = 'dark popup-content-class="dark"' if is_dark_fresh else ''
                    
                    # Dynamische Farb-Variablen für Python-gesteuertes CSS
                    bg_card = 'bg-slate-800 border-slate-700 text-slate-100' if is_dark_fresh else 'bg-slate-50 border-slate-200 text-slate-700'
                    bg_input = 'bg-slate-900 text-slate-100' if is_dark_fresh else 'bg-white text-slate-800'
                    bg_log_row = 'bg-slate-900 border-slate-700 text-slate-200' if is_dark_fresh else 'bg-white border-slate-100 text-slate-700'
                    text_label = 'text-slate-200' if is_dark_fresh else 'text-slate-700'
                    text_sub = 'text-slate-400' if is_dark_fresh else 'text-slate-500'
                    
                    if current_status == 'READING':
                        c_id = database.hole_oder_erstelle_aktiven_zyklus(layout.aktiver_user_id, book_id)
                        letzte_seite = database.hole_letzte_seite_aus_logs(c_id)
                        logs = database.lade_logs_fuer_zyklus(c_id)
                        
                        prozent = min(1.0, letzte_seite / gesamt_seiten)
                        
                        with ui.card().classes(f'w-full p-4 shadow-sm mb-4 {bg_card}'):
                            ui.label('Lese-Fortschritt tracken 📈').classes(f'text-sm font-bold mb-1 {text_label}')
                            
                            ui.linear_progress(value=prozent, color='emerald', show_value=False).classes('w-full my-2 h-2 rounded')
                            ui.label(f"Aktuell auf Seite {letzte_seite} von {gesamt_seiten} ({int(prozent*100)}%)").classes(f'text-xs mb-3 {text_sub}')
                            
                            with ui.row().classes('w-full items-center gap-3 no-wrap mb-4'):
                                # REPARIERT: bg_input erzwingt die Hintergrundfarbe direkt auf dem Element
                                seiten_input = ui.number(label='Neue Seite', value=letzte_seite + 1, min=0, max=gesamt_seiten) \
                                    .props(f'dense outlined {dark_prop_fresh}').classes(f'w-32 {bg_input}')
                                
                                async def speichern_klick():
                                    if seiten_input.value is None: return
                                    neuer_stand = int(seiten_input.value)
                                    
                                    erfolg, meldung = database.trage_lese_log_ein(layout.aktiver_user_id, book_id, neuer_stand)
                                    if erfolg:
                                        ui.notify(f"Eintrag gesichert! +{meldung} Seiten.", type='positive')
                                        if neuer_stand >= gesamt_seiten:
                                            database.schliesse_aktiven_zyklus_ab(layout.aktiver_user_id, book_id)
                                            status_select.value = 'READ'
                                            inline_speichern()
                                        tracking_zone_refresh.refresh()
                                    else:
                                        ui.notify(meldung, type='warning')
                                        
                                ui.button(icon='check', on_click=speichern_klick).classes('bg-emerald-600 text-white p-2')

                            if logs:
                                ui.separator().classes('my-2 dark:bg-slate-700')
                                ui.label('Logbuch dieses Durchgangs:').classes('text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2')
                                with ui.element('div').classes('w-full max-h-40 overflow-y-auto flex flex-col gap-1.5'):
                                    for l_date, p_page, p_read in logs:
                                        # REPARIERT: bg_log_row tauscht das komplette CSS-Paket für die Log-Zeile aus
                                        with ui.row().classes(f'w-full justify-between items-center text-xs p-2 rounded border shadow-sm no-wrap gap-2 {bg_log_row}'):
                                            with ui.row().classes('items-center gap-3'):
                                                ui.label(translations.format_localized_date(l_date)).classes('font-medium text-slate-500 dark:text-slate-400 font-mono')
                                                ui.label(f"S. {p_page} (gelesen: +{p_read})").classes('font-semibold')
                                            
                                            async def log_loeschen(d=l_date, cid=c_id, page=p_page):
                                                if database.loesche_reading_log_aus_db(d, cid, page):
                                                    ui.notify('Lese-Eintrag entfernt.', type='info')
                                                    tracking_zone_refresh.refresh()
                                            
                                            ui.button(icon='close', on_click=log_loeschen).props('flat round dense size=sm').classes('text-red-400 hover:text-red-600 shrink-0')

                    elif current_status == 'READ':
                        card_read_bg = 'bg-slate-800 border-slate-700' if is_dark_fresh else 'bg-emerald-50/40 border-emerald-100'
                        with ui.card().classes(f'w-full p-4 border flex flex-col gap-2 items-center text-center mb-4 {card_read_bg}'):
                            ui.icon('auto_stories', size='md').classes('text-emerald-600 dark:text-emerald-400')
                            ui.label('Du hast dieses Buch bereits ausgelesen!').classes(f'text-sm font-bold {text_label}')
                            ui.label('Möchtest du es noch einmal von vorne lesen und einen neuen Durchgang starten?').classes(f'text-xs max-w-sm {text_sub}')
                            
                            async def reread_starten():
                                with database.get_connection() as conn:
                                    cursor = conn.cursor()
                                    heute = datetime.now().strftime('%Y-%m-%d')
                                    cursor.execute("""
                                        UPDATE reading_cycles 
                                        SET status = 'READ', finished_at = ? 
                                        WHERE user_id = ? AND book_id = ? AND status = 'READING'
                                    """, (heute, layout.aktiver_user_id, book_id))
                                    conn.commit()
                                
                                status_select.value = 'READING'
                                inline_speichern()
                                ui.notify('Neuer Lesedurchgang gestartet! Viel Spaß 📖', type='info')

                            ui.button('Buch erneut lesen', icon='replay', on_click=reread_starten) \
                                .classes('bg-emerald-600 text-white mt-1 px-4 text-xs font-semibold py-1.5 rounded shadow')
                    else:
                        with ui.element('div').classes(f'p-3 rounded border border-dashed text-center text-xs italic mb-4 {bg_card}'):
                            ui.label('Stelle den Status auf "Am Lesen", um deinen Lesefortschritt zu dokumentieren.')

                    beendete_zyklen = database.lade_beendete_zyklen(layout.aktiver_user_id, book_id)
                    if beendete_zyklen:
                        with ui.card().classes(f'w-full p-4 border shadow-sm {bg_card}'):
                            with ui.row().classes('items-center gap-2 mb-1'):
                                ui.icon('history', size='sm').classes('text-blue-500 dark:text-blue-400')
                                ui.label('Vergangene Lesedurchgänge').classes('text-xs font-bold text-slate-400 uppercase tracking-wider')
                            
                            with ui.element('div').classes('w-full flex flex-col gap-2 mt-1'):
                                for index, (cyc_id, s_at, f_at, r_cycle) in enumerate(beendete_zyklen, 1):
                                    with ui.row().classes(f'w-full justify-between items-center text-xs p-2.5 rounded border shadow-xs no-wrap gap-2 {bg_log_row}'):
                                        with ui.element('div').classes('flex flex-col gap-0.5'):
                                            ui.label(f"{index}. Lesedurchgang").classes('font-bold')
                                            ui.label(f"🗓️ {translations.format_localized_date(s_at) or '--'} bis {translations.format_localized_date(f_at) or '--'}").classes(f'font-mono text-[11px] {text_sub}')
                                        
                                        with ui.row().classes('items-center gap-3 shrink-0'):
                                            if r_cycle > 0:
                                                with ui.row().classes('gap-0.5 text-amber-500 items-center'):
                                                    ui.icon('star', size='xs')
                                                    ui.label(str(r_cycle)).classes('font-bold')
                                            
                                            async def zyklus_loeschen(target_id=cyc_id):
                                                with ui.dialog() as confirm_dial, ui.card().classes(f'p-4 {bg_card}').props(f'{dark_prop_fresh}'):
                                                    ui.label('Diesen Lesedurchgang wirklich löschen? Alle damit verknüpften täglichen Kalendereinträge gehen verloren!').classes('text-sm mb-4')
                                                    
                                                    with ui.row().classes('w-full justify-end gap-2'):
                                                        ui.button(t('cancel'), on_click=confirm_dial.close).props('flat').classes('text-slate-500')
                                                        
                                                        async def definitiv_loeschen():
                                                            confirm_dial.close()
                                                            if database.loesche_reading_cycle_aus_db(target_id):
                                                                ui.notify('Lesedurchgang inklusive Logs gelöscht.', type='info')
                                                                tracking_zone_refresh.refresh()
                                                        
                                                        ui.button(t('delete'), on_click=definitiv_loeschen).classes('bg-red-500 text-white')
                                                confirm_dial.open()

                                            ui.button(icon='delete', on_click=zyklus_loeschen).props('flat round dense size=sm').classes('text-slate-400 hover:text-red-500')
                tracking_zone_refresh()