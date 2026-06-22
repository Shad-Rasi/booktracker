from nicegui import ui
import database
from layout import basis_layout
import translations
from translations import t
from datetime import datetime
import asyncio
import book_api
from logger import ui_log_lang

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

    (
        book_id, title, author, isbn_13, pages, 
        status, rating, special, is_series, s_name, s_num, 
        start, end, subtitle, translator, narrator, illustrator, editor,
        isbn_10, publisher, published_date, language, description,
        format_type, ownership, quantity, location_id, location_name
    ) = buch

    status = status or 'UNREAD'
    rating = rating if rating is not None else 0
    format_type = format_type or 'PHYSICAL'
    ownership = ownership or 'OWNED'
    quantity = quantity if quantity is not None else 1
    gesamt_seiten = pages or 1
    
    seiten_status = {
        'aktueller_status': status,
        'rating': rating
    }
    
    author_id = None
    if author:
        author_id = database.hole_autoren_id_durch_name(layout.aktiver_user_id, author)

    buch_genres = database.lade_genres_eines_buches(b_id, layout.aktiver_user_id)

    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    is_dark = user_ui['dark_mode']
    dark_prop = 'dark popup-content-class="dark"' if is_dark else ''
    dialog_prop = 'dark' if is_dark else ''

    # TRICK: Registrierung für die Refresh-Funktionen, damit Python sie von oben nach unten kennt
    refresh_registry = {}

    def inline_speichern(neuer_status=None, neuer_rating_wert=None):
        """Speichert Status und Bewertung live und aktualisiert alle UI-Zonen."""
        nonlocal start, end  

        if neuer_status is not None:
            seiten_status['aktueller_status'] = neuer_status
        if neuer_rating_wert is not None:
            seiten_status['rating'] = neuer_rating_wert

        aktueller_typ = seiten_status['aktueller_status']
        heute_iso = datetime.now().strftime('%Y-%m-%d')

        if aktueller_typ == 'READ':
            if not end: end = heute_iso  
            if not start: start = heute_iso 
        elif aktueller_typ == 'READING':
            if not start: start = heute_iso 
            end = ""  
        elif aktueller_typ == 'UNREAD':
            start = ""
            end = ""

        aktuelle_book_data = {
            'title': title, 'subtitle': subtitle, 'author': author,
            'translator': translator, 'narrator': narrator, 'illustrator': illustrator, 'editor': editor,
            'isbn': isbn_13, 'isbn_10': isbn_10, 'publisher': publisher, 'published_date': published_date,
            'language': language, 'description': description, 'pages': pages, 'special': special,
            'is_series': is_series, 'series_name': s_name, 'series_number': s_num,
            'location_id': location_id
        }
        
        aktuelle_user_data = {
            'status': seiten_status['aktueller_status'],
            'rating': int(seiten_status['rating']),
            'format': format_type,
            'ownership': ownership,
            'quantity': quantity,
            'started_at': start or "",
            'finished_at': end or ""
        }
        
        database.speichere_buch_in_db(book_id, layout.aktiver_user_id, aktuelle_book_data, aktuelle_user_data)
        ui.notify(t('notify_saved'), type='positive', duration=1)
        
        if 'seite_neu_laden' in refresh_registry: 
            refresh_registry['seite_neu_laden']()
        
    with basis_layout(title):
        ui.button(
            t('back'), 
            icon='arrow_back', 
            on_click=lambda: ui.run_javascript('window.history.back()')
        ).props('flat dense').classes('text-slate-500 dark:text-slate-400 mb-4 ml-4 md:ml-0')
        
        # --- DIALOGE FÜR COVERSUCHE ---
        style_dialog_card = 'background-color: #1e293b; color: #f8fafc;' if is_dark else ''
        with ui.dialog() as search_dialog, ui.card().classes('p-6 w-full max-w-2xl flex flex-col gap-4').style(style_dialog_card):
            ui.label(t('book_search_cover_internet')).classes('text-lg font-bold text-slate-700 dark:text-slate-100')
            ui.label(t('book_choose_cover_live')).classes('text-xs text-slate-500 dark:text-slate-400 -mt-2')
            galerie_container = ui.element('div').classes('w-full')
            
            async def bild_waehlen(url):
                search_dialog.close()
                ui.notify(t('book_notify_saving_cover'), type='info')
                erfolg = await asyncio.to_thread(database.lade_und_speichere_cover, book_id, url)
                if erfolg:
                    ui.notify(t('book_notify_cover_updated'), type='positive')
                    ui_log_lang('log_cover_updated', title=title)
                    await asyncio.sleep(0.2)
                    ui.navigate.to(f'/book/{book_id}')
                else:
                    ui.notify(t('book_notify_cover_error'), type='negative')
                    ui_log_lang('log_cover_updated_error', title=title)

            async def suche_ausfuehren():
                with galerie_container: ui.spinner(size='lg').classes('mx-auto my-8 block')
                such_isbn = isbn_13 or isbn_10 or ""
                urls = []
                if isbn_13 and len(str(isbn_13).strip()) == 13:
                    urls.append(f"https://buch.isbn.de/gross/{str(isbn_13).strip()}.jpg")
                google_urls = await book_api.google_bildsuche_async(title, author, isbn=such_isbn)
                if google_urls: urls.extend(google_urls)
                galerie_container.clear()
                if not urls:
                    with galerie_container: ui.label(t('book_no_images_found')).classes('text-center text-slate-500 dark:text-slate-400 my-4')
                    return
                with galerie_container:
                    with ui.grid().classes('w-full grid grid-cols-2 sm:grid-cols-4 gap-4 justify-items-center max-h-96 overflow-y-auto p-1'):
                        for index, url in enumerate(urls):
                            is_isbn_de = (index == 0 and isbn_13 and url.startswith("https://buch.isbn.de"))
                            rahmen_css = 'border-2 border-emerald-500 shadow-md relative' if is_isbn_de else 'border border-slate-200 dark:border-slate-700'
                            with ui.element('div').classes(f'rounded p-1 hover:shadow-md hover:border-blue-500 cursor-pointer transition-all bg-white dark:bg-slate-900 w-full max-w-[120px] overflow-hidden {rahmen_css}'):
                                img = ui.image(url).classes('w-full aspect-[2/3] object-cover')
                                img.on('click', lambda e, u=url: bild_waehlen(u))
                                
            ui.button(t('cancel'), on_click=search_dialog.close).classes('bg-slate-400 dark:bg-slate-600 text-white w-full mt-2')

        with ui.dialog() as upload_dialog, ui.card().classes('p-6 w-96 flex flex-col gap-4').style(style_dialog_card):
            ui.label(t('book_upload_change_cover')).classes('text-lg font-bold text-slate-700 dark:text-slate-100')
            ui.upload(label=t('book_select_image_label'), auto_upload=True, on_upload=lambda e: cover_verarbeiten(e, upload_dialog)).props(f'accept=image/* max-files=1 {dialog_prop}').classes('w-full')
            ui.button(t('cancel'), on_click=upload_dialog.close).classes('bg-slate-400 dark:bg-slate-600 text-white w-full')

        async def cover_verarbeiten(e, dialog):
            import os
            os.makedirs(database.COVER_DIR, exist_ok=True)
            ziel = os.path.join(database.COVER_DIR, f"{book_id}.jpg")
            try:
                await e.file.save(ziel)
                ui.notify(t('book_notify_cover_updated'), type='positive')
                ui_log_lang('log_cover_updated', title=title)
                dialog.close()
                ui.navigate.to(f'/book/{book_id}')
            except Exception as ex:
                ui.notify(f"{t('book_notify_save_error')}: {str(ex)}", type='negative')
                ui_log_lang('log_cover_updated_error', title=title)

        # =========================================================================
        # THE FINAL MASTER ZONE: Grid mit CSS-Bündigkeit & perfekter Mobile-Abfolge
        # =========================================================================
        @ui.refreshable
        def seite_neu_laden_zone():
            with ui.element('div').classes('w-full max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-x-6 md:gap-x-8 gap-y-4 px-4 md:px-0 mb-16 items-start'):
                
                # --- 1. DER TITELBLOCK ---
                with ui.column().classes('w-full flex flex-col gap-1 md:col-start-2 md:col-span-2 md:row-start-1'):
                    with ui.row().classes('w-full justify-between items-start gap-2 flex-nowrap'):
                        with ui.column().classes('flex flex-col gap-0.5 flex-1 items-start'):
                            ui.label(title).classes('text-2xl md:text-3xl font-bold text-slate-800 dark:text-slate-100 leading-tight text-left')
                            if subtitle:
                                ui.label(subtitle).classes('text-base md:text-lg text-slate-500 dark:text-slate-400 font-medium text-left')
                        
                        with ui.row().classes('items-center gap-0.5 shrink-0 pt-1'):
                            if isbn_13 and (not description or not publisher or pages <= 1 or not s_name):
                                async def metadaten_blitz_update():
                                    ui.notify(t('book_notify_scrape_metadata'), type='info')
                                    # 1. User-ID direkt aus dem Layout-Modul ziehen (Absolut sicher!)
                                    aktive_id = layout.aktiver_user_id
                                    # 2. Wunsch-Reihenfolge aus der DB laden
                                    user_settings = database.lade_user_settings(aktive_id)
                                    provider_reihenfolge = user_settings.get('api_priority', 'isbn_de,google_books').split(',')
                                    # 3. Kaskadierenden Router füttern
                                    scraped_data = await book_api.hole_buch_details_kaskadierend(isbn_13, provider_reihenfolge)
                                    if scraped_data:
                                        database.aktualisiere_buch_metadaten(book_id, scraped_data)
                                        ui.notify(t('book_notify_metadata_saved'), type='positive')
                                        ui_log_lang('log_metadata_updated', title=title)
                                        await asyncio.sleep(0.5)
                                        ui.navigate.to(f'/book/{book_id}') 
                                    else:
                                        ui.notify(t('book_notify_metadata_not_found'), type='warning')
                                        ui_log_lang('log_metadata_update_error', title=title)

                                ui.button(icon='auto_fix_high', on_click=lambda: metadaten_blitz_update()) \
                                    .props('flat round dense').classes('text-emerald-600 dark:text-emerald-400') \
                                    .tooltip(t('book_tooltip_fetch_metadata'))
                            
                            ui.button(icon='edit', on_click=lambda: ui.navigate.to(f'/edit/{book_id}')) \
                                .props('flat round dense').classes('text-blue-600 dark:text-blue-400') \
                                .tooltip(t('edit_book'))
                            
                            def aktion_loeschen():
                                user_ui_delete = database.lade_user_settings(layout.aktiver_user_id)
                                is_dark_delete = user_ui_delete['dark_mode']
                                style_popup = 'background-color: #1e293b; color: #f8fafc;' if is_dark_delete else ''
                                with ui.dialog() as confirm_delete_dial, ui.card().classes('p-5 flex flex-col gap-4 w-full max-w-sm').style(style_popup):
                                    ui.label(t('book_confirm_delete_title')).classes('text-lg font-bold text-red-500')
                                    ui.label(f"{t('book_confirm_delete_text_1')} \"{title}\" {t('book_confirm_delete_text_2')}").classes('text-sm text-slate-600 dark:text-slate-300')
                                    with ui.row().classes('w-full justify-end gap-2 mt-2'):
                                        ui.button(t('cancel'), on_click=confirm_delete_dial.close).props('flat').classes('text-slate-500 dark:text-slate-400')
                                        async def definitiv_aus_db_werfen():
                                            confirm_delete_dial.close()
                                            database.loesche_buch_aus_db(book_id)
                                            ui.notify(f'"{title}" {t("notify_deleted")}', type='positive')
                                            ui_log_lang('log_book_deleted', title=title)
                                            ui.navigate.to('/')
                                        ui.button(t('delete'), on_click=definitiv_aus_db_werfen).classes('bg-red-500 text-white px-4')
                                confirm_delete_dial.open()

                            ui.button(icon='delete', on_click=aktion_loeschen) \
                                .props('flat round dense').classes('text-red-600 dark:text-red-400') \
                                .tooltip(t('delete'))

                    if author and author_id:
                        ui.label(author) \
                            .classes('text-lg md:text-xl text-slate-600 dark:text-slate-300 italic mt-0.5 cursor-pointer hover:text-blue-600 dark:hover:text-blue-400 hover:underline transition-colors inline-block text-left') \
                            .on('click', lambda: ui.navigate.to(f'/author/{author_id}')) \
                            .tooltip(t('book_tooltip_author_profile'))
                    else:
                        ui.label(author or t('unknown_author')).classes('text-lg md:text-xl text-slate-600 dark:text-slate-300 italic mt-0.5 inline-block text-left')
                    
                    with ui.row().classes('items-center gap-0.5 mt-1'):
                        for star_idx in range(1, 6):
                            is_active = star_idx <= seiten_status['rating']
                            star_icon = 'star' if is_active else 'star_border'
                            star_color = 'text-amber-500' if is_active else 'text-slate-400 dark:text-slate-600'
                            klick_wert = 0 if seiten_status['rating'] == star_idx else star_idx
                            ui.button(icon=star_icon, on_click=lambda _, val=klick_wert: inline_speichern(neuer_rating_wert=val)) \
                                .props('flat round dense size=sm').classes(f'{star_color} transition-colors')

                # --- 2. DIE MEDIASPALTE (Cover & Infokarte) ---
                with ui.column().classes('w-full md:col-span-1 flex flex-col gap-4 md:row-start-1 md:row-span-2 mt-2 md:mt-0'):
                    cover_pfad = database.hole_cover_url(book_id)
                    with ui.element('div').classes('w-full aspect-[2/3] rounded-lg shadow-md border border-slate-200 dark:border-slate-700 bg-slate-200 dark:bg-slate-800 flex items-center justify-center overflow-hidden'):
                        if cover_pfad != "/covers/placeholder.jpg":
                            ui.image(cover_pfad).classes('w-full h-full object-cover')
                        else:
                            with ui.column().classes('flex flex-col items-center gap-2 text-slate-400 dark:text-slate-500'):
                                ui.icon('book', size='xl')
                                ui.label(t('no_cover')).classes('text-xs font-medium')

                    with ui.row().classes('w-full justify-center gap-2 mt-1'):
                        ui.button(t('book_btn_change_cover'), icon='photo_camera', on_click=upload_dialog.open).props('flat dense').classes('text-blue-600 dark:text-blue-400 text-xs')
                        ui.button(t('book_btn_search_online'), icon='search', on_click=lambda: [search_dialog.open(), asyncio.create_task(suche_ausfuehren())]).props('flat dense').classes('text-emerald-600 dark:text-emerald-400 text-xs')

                    @ui.refreshable
                    def infokarte_links_refresh():
                        user_ui_links = database.lade_user_settings(layout.aktiver_user_id)
                        is_dark_links = user_ui_links['dark_mode']
                        bg_infokarte = 'bg-slate-800 border-slate-700 text-slate-200' if is_dark_links else 'bg-slate-50 border-slate-200 text-slate-700'
                        bg_zeit_box = 'bg-slate-900 border-slate-700 text-slate-300' if is_dark_links else 'bg-white border-slate-100 text-slate-500'
                        text_zeit_label = 'text-emerald-400' if is_dark_links else 'text-emerald-600'
                        text_zeit_read = 'text-blue-400' if is_dark_links else 'text-blue-600'

                        with ui.card().classes(f'w-full p-4 shadow-sm flex flex-col gap-2.5 text-sm {bg_infokarte}'):
                            with ui.row().classes('w-full justify-between items-center mb-1'):
                                ui.label(t('readingstatus')).classes('text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider')
                            status_opts = {'UNREAD': t('unread'), 'READING': t('reading'), 'READ': t('read')}
                            ui.select(options=status_opts, value=seiten_status['aktueller_status'], on_change=lambda e: inline_speichern(neuer_status=e.value)).classes('w-full px-2 py-1 rounded bg-slate-100 dark:bg-slate-900 border border-slate-200/60 dark:border-slate-700 text-xs mt-1').props(f'dense borderless {dark_prop}')
                            
                            with ui.row().classes('w-full justify-between items-center mb-1 mt-2'):
                                ui.label(t('details')).classes('text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider')
                            
                            ui.label(f"{t('format')}: {t(format_type)}")
                            ui.label(f"{t('ownership')}: {t(ownership)}")
                            ui.label(f"{t('quantity')}: {quantity}")
                            if location_name: ui.label(f"{t('location')}: {location_name}")
                            
                            real_start, real_end, cyc_status = database.hole_aktuelle_lesezeiten(layout.aktiver_user_id, book_id)
                            if real_start or real_end:
                                ui.separator().classes('my-1 dark:bg-slate-700')
                                with ui.element('div').classes(f'flex flex-col gap-1 text-xs p-2 rounded border shadow-inner {bg_zeit_box}'):
                                    if cyc_status == 'READING':
                                        ui.label(t('book_current_cycle')).classes(f'font-bold {text_zeit_label}')
                                        ui.label(f"{t('book_started_at')}: {translations.format_localized_date(real_start) or '--'}")
                                    elif cyc_status == 'READ':
                                        ui.label(t('book_last_read')).classes(f'font-bold {text_zeit_read}')
                                        ui.label(f"{t('book_from')}: {translations.format_localized_date(real_start) or '--'}")
                                        ui.label(f"{t('book_to')}: {translations.format_localized_date(real_end) or '--'}")

                    infokarte_links_refresh()
                    refresh_registry['infokarte_links'] = infokarte_links_refresh.refresh

                # --- 3. DIE DETAILSPALTE ---
                with ui.column().classes('w-full md:col-span-2 flex flex-col gap-4 md:row-start-2 md:col-start-2 md:-mt-3'):
                    beschreibung_container = ui.element('div').classes('w-full')
                    with beschreibung_container:
                        if description:
                            with ui.element('div').classes('bg-slate-50/50 dark:bg-slate-800 p-4 rounded-lg border border-slate-100 dark:border-slate-700 italic text-slate-700 dark:text-slate-300 leading-relaxed max-h-60 overflow-y-auto w-full'):
                                ui.markdown(description)
                            ui.separator().classes('my-2 dark:bg-slate-700')

                    if buch_genres:
                        with ui.row().classes('flex-wrap gap-1.5 mb-4 items-center'):
                            ui.icon('local_offer', size='xs').classes('text-slate-400 dark:text-slate-500 mr-0.5')
                            for genre_name in buch_genres:
                                ui.badge(genre_name, color='slate').classes('text-[10px] font-medium px-2 py-0.5 rounded-md dark:bg-slate-700 dark:text-slate-200')
                        ui.separator().classes('my-2 dark:bg-slate-700')

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
                        with ui.row().classes('w-full mt-2 p-3 bg-blue-50/50 dark:bg-slate-800 rounded border border-blue-100 dark:border-blue-900/50 items-center text-sm text-blue-800 dark:text-blue-300 font-medium no-wrap gap-1'):
                            ui.icon('layers').classes('text-blue-500 dark:text-blue-400 mr-1')
                            ui.label(f"{t('series_name')}:")
                            ui.label(s_name).classes('cursor-pointer text-blue-600 dark:text-blue-400 hover:underline transition-all font-bold').on('click', lambda name=s_name: ui.navigate.to(f'/series/{name}')).tooltip(t('view_series') if 'view_series' in translations.TRANSLATIONS[translations.aktuelle_sprache] else 'Reihe anzeigen')
                            ui.label(f"({t('series_volume')} {s_num or 0})").classes('text-slate-500 dark:text-slate-400 pl-1')

                    ui.separator().classes('my-4 dark:bg-slate-700')

                    @ui.refreshable
                    def tracking_zone_refresh():
                        current_status = seiten_status['aktueller_status']
                        user_ui_fresh = database.lade_user_settings(layout.aktiver_user_id)
                        is_dark_fresh = user_ui_fresh['dark_mode']
                        dark_prop_fresh = 'dark popup-content-class="dark"' if is_dark_fresh else ''
                        bg_card_fresh = 'bg-slate-800 border-slate-700 text-slate-100' if is_dark_fresh else 'bg-slate-50 border-slate-200 text-slate-700'
                        bg_input = 'bg-slate-900 text-slate-100' if is_dark_fresh else 'bg-white text-slate-800'
                        bg_log_row = 'bg-slate-900 border-slate-700 text-slate-200' if is_dark_fresh else 'bg-white border-slate-100 text-slate-700'
                        text_label = 'text-slate-200' if is_dark_fresh else 'text-slate-700'
                        text_sub_fresh = 'text-slate-400' if is_dark_fresh else 'text-slate-500'
                        
                        if current_status == 'READING':
                            c_id = database.hole_oder_erstelle_aktiven_zyklus(layout.aktiver_user_id, book_id)
                            letzte_seite = database.hole_letzte_seite_aus_logs(c_id)
                            logs = database.lade_logs_fuer_zyklus(c_id)
                            prozent = min(1.0, letzte_seite / gesamt_seiten)
                            
                            with ui.card().classes(f'w-full p-4 shadow-sm mb-4 {bg_card_fresh}'):
                                ui.label(t('book_track_progress_title')).classes(f'text-sm font-bold mb-1 {text_label}')
                                ui.linear_progress(value=prozent, color='emerald', show_value=False).classes('w-full my-2 h-2 rounded')
                                ui.label(f"{t('book_current_on_page')} {letzte_seite} {t('book_of_pages')} {gesamt_seiten} ({int(prozent*100)}%)").classes(f'text-xs mb-3 {text_sub_fresh}')
                                
                                with ui.row().classes('w-full items-center gap-3 no-wrap mb-4'):
                                    seiten_input = ui.number(label=t('book_input_new_page'), value=letzte_seite + 1, min=0, max=gesamt_seiten).props(f'dense outlined {dark_prop_fresh}').classes(f'w-32 {bg_input}')
                                    async def speichern_klick():
                                        if seiten_input.value is None: return
                                        neuer_stand = int(seiten_input.value)
                                        erfolg, meldung = database.trage_lese_log_ein(layout.aktiver_user_id, book_id, neuer_stand)
                                        if erfolg:
                                            ui.notify(f"{t('book_notify_log_saved')} +{meldung} {t('pages_short')}.", type='positive')
                                            ui_log_lang('log_progress_saved', pages=meldung, title=title)
                                            if neuer_stand >= gesamt_seiten:
                                                database.schliesse_aktiven_zyklus_ab(layout.aktiver_user_id, book_id)
                                                inline_speichern(neuer_status='READ')
                                            else:
                                                tracking_zone_refresh.refresh()
                                                if 'globales_logbuch' in refresh_registry: refresh_registry['globales_logbuch']()
                                        else:
                                            ui.notify(meldung, type='warning')
                                    ui.button(icon='check', on_click=speichern_klick).classes('bg-emerald-600 text-white p-2')

                                if logs:
                                    ui.separator().classes('my-2 dark:bg-slate-700')
                                    ui.label(t('book_logbook_current_cycle')).classes('text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-2')
                                    with ui.column().classes('w-full max-h-40 overflow-y-auto flex flex-col gap-1.5'):
                                        for l_date, p_page, p_read in logs:
                                            with ui.row().classes(f'w-full justify-between items-center text-xs p-2 rounded border shadow-sm no-wrap gap-2 {bg_log_row}'):
                                                with ui.row().classes('items-center gap-3'):
                                                    ui.label(translations.format_localized_date(l_date)).classes('font-medium text-slate-500 dark:text-slate-400 font-mono')
                                                    ui.label(f"{t('pages_short')}. {p_page} ({t('book_log_read_short')}: +{p_read})").classes('font-semibold')
                                                async def log_loeschen(d=l_date, cid=c_id, page=p_page):
                                                    if database.loesche_reading_log_aus_db(d, cid, page):
                                                        ui.notify(t('book_notify_log_removed'), type='info')
                                                        ui_log_lang('log_book_log_removed', title=title)
                                                        tracking_zone_refresh.refresh()
                                                        if 'globales_logbuch' in refresh_registry: refresh_registry['globales_logbuch']()
                                                ui.button(icon='close', on_click=log_loeschen).props('flat round dense size=sm').classes('text-red-400 hover:text-red-600 shrink-0')

                        elif current_status == 'READ':
                            card_read_bg = 'bg-slate-800 border-slate-700' if is_dark_fresh else 'bg-emerald-50/40 border-emerald-100'
                            with ui.card().classes(f'w-full p-4 border flex flex-col gap-2 items-center text-center mb-4 {card_read_bg}'):
                                ui.icon('auto_stories', size='md').classes('text-emerald-600 dark:text-emerald-400')
                                ui.label(t('book_already_read_title')).classes(f'text-sm font-bold {text_label}')
                                ui.label(t('book_already_read_subtitle')).classes(f'text-xs max-w-sm {text_sub_fresh}')
                                async def reread_starten():
                                    database.initialisiere_reread_status(layout.aktiver_user_id, book_id)
                                    ui.notify(t('book_notify_reread_started'), type='info')
                                    ui.navigate.to(f'/book/{book_id}')
                                ui.button(t('book_btn_reread'), icon='replay', on_click=reread_starten).classes('bg-emerald-600 text-white mt-1 px-4 text-xs font-semibold py-1.5 rounded shadow')
                        else:
                            with ui.element('div').classes(f'p-3 rounded border border-dashed text-center text-xs italic mb-4 {bg_card_fresh}'):
                                ui.label(t('book_hint_set_reading'))

                        beendete_zyklen = database.lade_beendete_zyklen(layout.aktiver_user_id, book_id)
                        if beendete_zyklen:
                            with ui.card().classes(f'w-full p-4 border shadow-sm {bg_card_fresh}'):
                                with ui.row().classes('items-center gap-2 mb-1'):
                                    ui.icon('history', size='sm').classes('text-blue-500 dark:text-blue-400')
                                    ui.label(t('book_past_cycles_title')).classes('text-xs font-bold text-slate-400 uppercase tracking-wider')
                                with ui.column().classes('w-full flex flex-col gap-2 mt-1'):
                                    for index, (cyc_id, s_at, f_at, r_cycle) in enumerate(beendete_zyklen, 1):
                                        with ui.row().classes(f'w-full justify-between items-center text-xs p-2.5 rounded border shadow-xs no-wrap gap-2 {bg_log_row}'):
                                            with ui.element('div').classes('flex flex-col gap-0.5'):
                                                ui.label(f"{index}. {t('book_label_cycle')}").classes('font-bold')
                                                ui.label(f"🗓️ {translations.format_localized_date(s_at) or '--'} {t('book_until')} {translations.format_localized_date(f_at) or '--'}").classes(f'font-mono text-[11px] {text_sub_fresh}')
                                            with ui.row().classes('items-center gap-3 shrink-0'):
                                                if r_cycle > 0:
                                                    with ui.row().classes('gap-0.5 text-amber-500 items-center'):
                                                        ui.icon('star', size='xs')
                                                        ui.label(str(r_cycle)).classes('font-bold')
                                                async def zyklus_loeschen(target_id=cyc_id):
                                                    with ui.dialog() as confirm_dial, ui.card().classes(f'p-4 {bg_card_fresh}').props(f'{dark_prop_fresh}'):
                                                        ui.label(t('book_confirm_cycle_delete')).classes('text-sm mb-4')
                                                        with ui.row().classes('w-full justify-end gap-2'):
                                                            ui.button(t('cancel'), on_click=confirm_dial.close).props('flat').classes('text-slate-500')
                                                            async def definitiv_loeschen():
                                                                confirm_dial.close()
                                                                if database.loesche_reading_cycle_aus_db(target_id):
                                                                    ui.notify(t('book_notify_cycle_removed'), type='info')
                                                                    ui_log_lang('log_book_cycle_removed', title=title, cycle=cyc_id)
                                                                    tracking_zone_refresh.refresh()
                                                                    if 'globales_logbuch' in refresh_registry: refresh_registry['globales_logbuch']()
                                                            ui.button(t('delete'), on_click=definitiv_loeschen).classes('bg-red-500 text-white')
                                                    confirm_dial.open()
                                                ui.button(icon='delete', on_click=zyklus_loeschen).props('flat round dense size=sm').classes('text-slate-400 hover:text-red-500')

                    tracking_zone_refresh()
                    refresh_registry['tracking_zone'] = tracking_zone_refresh.refresh

                    @ui.refreshable
                    def globales_logbuch_refresh():
                        user_ui_fresh = database.lade_user_settings(layout.aktiver_user_id)
                        is_dark_fresh = user_ui_fresh['dark_mode']
                        bg_log_row = 'bg-slate-900 border-slate-700 text-slate-200' if is_dark_fresh else 'bg-white border-slate-100 text-slate-700'
                        text_sub_fresh = 'text-slate-400' if is_dark_fresh else 'text-slate-500'
                        alle_logs = database.lade_globales_logbuch_fuer_buch(book_id, layout.aktiver_user_id)

                        with ui.expansion(t('book_view_logbook'), icon='auto_stories').classes('w-full border rounded-lg bg-slate-100/30 dark:bg-slate-900/10 dark:border-slate-700/50 mt-4'):
                            if not alle_logs:
                                ui.label(t('book_no_logs_recorded')).classes(f'text-xs italic p-4 text-center {text_sub_fresh}')
                            else:
                                with ui.column().classes('w-full p-3 gap-2 max-h-60 overflow-y-auto'):
                                    for l_date, p_page, p_read, cyc_status in alle_logs:
                                        with ui.row().classes(f'w-full justify-between items-center text-xs p-2 rounded border shadow-xs no-wrap {bg_log_row}'):
                                            with ui.row().classes('items-center gap-3'):
                                                ui.label(translations.format_localized_date(l_date)).classes('font-mono font-medium text-slate-500')
                                                ui.label(f"{t('book_log_until_page')} {p_page} (+{p_read} {t('pages_short')})").classes('font-bold')
                                            if cyc_status == 'READ':
                                                ui.badge(t('book_status_finished'), color='emerald').props('dense text-color=white').classes('text-[10px] px-1.5 py-0.5')
                                            else:
                                                ui.badge(t('book_status_active'), color='blue').props('dense text-color=white').classes('text-[10px] px-1.5 py-0.5')

                    globales_logbuch_refresh()
                    refresh_registry['globales_logbuch'] = globales_logbuch_refresh.refresh

        seite_neu_laden_zone()
        refresh_registry['seite_neu_laden'] = seite_neu_laden_zone.refresh