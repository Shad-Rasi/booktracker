import os
import asyncio
from datetime import datetime
from nicegui import ui
import database
import layout
from layout import basis_layout
import translations
from translations import t
import book_api

@ui.page('/authors')
def autoren_uebersicht():
    # 1. Darkmode-Zustand für den statischen Teil ermitteln
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    is_dark = user_ui['dark_mode']
    
    with basis_layout('authors'):
        ui.label(t('authors_title')).classes('text-2xl font-bold text-slate-700 dark:text-slate-100 mb-2')
        ui.label(t('authors_subtitle')).classes('text-sm text-slate-500 dark:text-slate-400 mb-6')
        
        alle_autoren = database.lade_alle_autoren_aus_db(layout.aktiver_user_id)
        
        if not alle_autoren:
            with ui.card().classes('w-full p-6 text-center bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700'):
                ui.icon('people', size='lg').classes('mx-auto mb-2')
                ui.label(t('no_authors_found'))
            return

        # --- SUCHLEISTE (ERZWUNGENER DARKMODE-RAHMEN) ---
        with ui.card().classes('w-full p-4 bg-slate-100 dark:bg-slate-800 shadow-sm border border-slate-200 dark:border-slate-700 mb-6 flex flex-col gap-3'):
            with ui.row().classes('w-full items-center gap-4'):
                suchfeld = ui.input(
                    placeholder=t('search'), 
                    on_change=lambda: autoren_raster_refresh.refresh()
                ).classes('flex-1 px-3 text-slate-800 dark:text-slate-100') \
                 .props(f'clearable icon=search outlined {"dark" if is_dark else ""}')

        # --- DYNAMISCHER KACHEL-CONTAINER ---
        @ui.refreshable
        def autoren_raster_refresh():
            user_ui_fresh = database.lade_user_settings(layout.aktiver_user_id)
            is_dark_fresh = user_ui_fresh['dark_mode']
            
            bg_card = 'bg-slate-800 border-slate-700 text-slate-100' if is_dark_fresh else 'bg-slate-50 border-slate-200 text-slate-700'
            text_author = 'text-slate-100' if is_dark_fresh else 'text-slate-700'
            
            suchbegriff = suchfeld.value.strip().lower() if suchfeld.value else ""
            gefilterte_autoren = [a for a in alle_autoren if suchbegriff in a[1].lower()]
            
            if not gefilterte_autoren:
                with ui.element('div').classes('w-full p-8 text-center text-slate-400 dark:text-slate-500 italic'):
                    ui.label(t('no_search_results') if 'no_search_results' in translations.TRANSLATIONS[translations.aktuelle_sprache] else 'Keine passenden Autoren gefunden')
                return

            with ui.element('div').classes('w-full grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6'):
                for a_id, a_name, a_bio, a_img, a_local_img in gefilterte_autoren:
                    with ui.card().classes(f'p-4 cursor-pointer hover:shadow-md transition-shadow items-center text-center h-full flex flex-col justify-between border {bg_card}') \
                            .on('click', lambda _, current_id=a_id: ui.navigate.to(f'/author/{current_id}')):
                        
                        with ui.element('div').classes('flex flex-col items-center w-full'):
                            if a_local_img:
                                ui.image(a_local_img).classes('w-20 h-20 rounded-full object-cover shadow-sm mb-3')
                            else:
                                with ui.element('div').classes('w-20 h-20 rounded-full bg-slate-300 dark:bg-slate-700 text-slate-600 dark:text-slate-300 flex items-center justify-center text-2xl font-bold mb-3 shadow-inner'):
                                    ui.label(a_name[0] if a_name else '?')
                            
                            ui.label(a_name).classes(f'font-bold text-sm md:text-base line-clamp-2 leading-snug {text_author}')
                        
                        ui.label(t('view_profile')).classes('text-[11px] text-blue-500 dark:text-blue-400 mt-3 uppercase tracking-wider font-semibold block')

        autoren_raster_refresh()


@ui.page('/author/{author_id}')
def autor_detailseite(author_id: int):
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    is_dark = user_ui['dark_mode']
    
    with basis_layout('authors'):
        
        ui.button(t('back_to_authors'), icon='arrow_back', on_click=lambda: ui.navigate.to('/authors')) \
            .props('flat dense').classes('text-slate-500 dark:text-slate-400 mb-4')

        autor_details = database.lade_autor_details(author_id)
        autor_name_fuer_buecher = autor_details[1] if autor_details else ""
        
        # REPARIERT: Holt das Array jetzt direkt mit der ownership-Spalte aus der DB
        buecher = database.lade_buecher_von_autor(layout.aktiver_user_id, autor_name_fuer_buecher)
        autoren_isbns = [b[3] for b in buecher if b[3] and str(b[3]).strip()]

        def formatiere_lebensdatum(datum_str, sprache):
            if not datum_str:
                return ""
            try:
                dt = datetime.strptime(datum_str.strip()[:10], '%Y-%m-%d')
                if sprache == 'de':
                    return dt.strftime('%d.%m.%Y')
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                return datum_str

        def hole_sortier_datum(b):
            d_str = b[7]  # Index 7 ist b.published_date
            if not d_str:
                return "0000-00-00"
            return str(d_str).strip()
            
        buecher.sort(key=hole_sortier_datum)

        @ui.refreshable
        def profil_kopf_refresh():
            user_ui_fresh = database.lade_user_settings(layout.aktiver_user_id)
            is_dark_fresh = user_ui_fresh['dark_mode']
            dark_prop_fresh = 'dark' if is_dark_fresh else ''
            
            bg_profile_card = 'bg-slate-800 border-slate-700 text-slate-200' if is_dark_fresh else 'bg-slate-50 border-slate-200 text-slate-700'
            text_name = 'text-slate-100' if is_dark_fresh else 'text-slate-800'
            text_bio = 'text-slate-300' if is_dark_fresh else 'text-slate-600'
            style_modal = 'background-color: #1e293b; color: #f8fafc;' if is_dark_fresh else ''
            
            autor = database.lade_autor_details(author_id)
            if not autor:
                ui.label(t('not_found')).classes('text-red-500 font-bold text-lg')
                return
                
            a_id, a_name, a_bio, a_birth, a_death, a_img, a_local_img = autor
            
            # --- AUTOREN KOPFZEILE (PROFIL) ---
            with ui.card().classes(f'w-full p-6 shadow-sm mb-6 border {bg_profile_card}'):
                with ui.row().classes('w-full items-center gap-6 no-wrap flex-col sm:flex-row'):
                    
                    if a_local_img:
                        ui.image(a_local_img).classes('w-32 h-32 rounded-full object-cover shadow-md')
                    else:
                        with ui.element('div').classes('w-32 h-32 rounded-full bg-slate-300 dark:bg-slate-700 text-slate-600 dark:text-slate-300 flex items-center justify-center text-4xl font-bold shadow-inner flex-shrink-0'):
                            ui.label(a_name[0] if a_name else '?')
                    
                    with ui.element('div').classes('flex-1 text-center sm:text-left'):
                        with ui.row().classes('w-full items-center justify-between sm:justify-start gap-2'):
                            ui.label(a_name).classes(f'text-3xl font-black {text_name}')
                            
                            with ui.row().classes('gap-1 items-center'):
                                async def api_abruf_starten():
                                    ui.notify(f'Suche Daten für {a_name} bei isbn.de...', type='info')
                                    api_data = await book_api.hole_autoren_metadaten_async(a_name, isbn_liste=autoren_isbns)
                                    
                                    if api_data:
                                        database.aktualisiere_autor_in_db(
                                            a_id, api_data['bio'], api_data['birth_date'], 
                                            api_data['death_date'], api_data['image_url']
                                        )
                                        ui.notify('Autorendaten erfolgreich aktualisiert! 🎉', type='positive')
                                        profil_kopf_refresh.refresh()
                                    else:
                                        ui.notify('Keine Daten auf isbn.de oder Open Library gefunden.', type='warning')

                                ui.button(icon='auto_fix_high', on_click=api_abruf_starten) \
                                    .props('round flat dense').classes('text-blue-500 dark:text-blue-400')
                                
                                def manuelles_editieren():
                                    with ui.dialog() as edit_dialog, ui.card().classes('w-full max-w-lg p-6 flex flex-col gap-4').style(style_modal):
                                        ui.label(f'"{a_name}" {t("edit_author_title")}').classes('text-lg font-bold text-slate-700 dark:text-slate-100')
                                        
                                        birth_input = ui.input(label=t('author_birth'), value=a_birth or '').classes('w-full').props(dark_prop_fresh)
                                        death_input = ui.input(label=t('author_death'), value=a_death or '').classes('w-full').props(dark_prop_fresh)
                                        img_input = ui.input(label=t('author_img_url'), value=a_img or '').classes('w-full').props(dark_prop_fresh)
                                        bio_input = ui.textarea(label=t('author_bio'), value=a_bio or '').classes('w-full').props(f'rows=5 {dark_prop_fresh}')
                                        
                                        async def daten_speichern():
                                            database.aktualisiere_autor_in_db(
                                                a_id, 
                                                bio_input.value.strip(), 
                                                birth_input.value.strip(), 
                                                death_input.value.strip(), 
                                                img_input.value.strip() if img_input.value else None
                                            )
                                            ui.notify(t('notify_author_updated'), type='positive')
                                            edit_dialog.close()
                                            profil_kopf_refresh.refresh()

                                        with ui.row().classes('w-full justify-end gap-2 mt-2'):
                                            ui.button(t('cancel'), on_click=edit_dialog.close).classes('text-slate-500 dark:text-slate-400').props('flat')
                                            ui.button(t('save'), on_click=daten_speichern).classes('bg-slate-700 dark:bg-slate-600 text-white px-4')
                                    
                                    edit_dialog.open()

                                ui.button(icon='edit', on_click=manuelles_editieren) \
                                    .props('round flat dense').classes('text-slate-500 dark:text-slate-400')
                        
                        sprache = translations.aktuelle_sprache
                        f_birth = formatiere_lebensdatum(a_birth, sprache)
                        f_death = formatiere_lebensdatum(a_death, sprache)
                        
                        if f_birth:
                            lebensdaten = f"*{f_birth}"
                            if f_death: lebensdaten += f"  †{f_death}"
                            ui.label(lebensdaten).classes('text-xs text-slate-400 dark:text-slate-500 font-mono mt-1')
                            
                        ui.label(a_bio if a_bio else t('no_bio_available')).classes(f'text-sm mt-3 italic max-w-2xl block whitespace-pre-line {text_bio}')

        profil_kopf_refresh()

        # --- BÜCHER DIESES AUTORS ---
        ui.label(t('books_by_author')).classes('text-xl font-bold text-slate-700 dark:text-slate-100 mb-4')
        
        bg_buch_karte = 'bg-slate-800 border-slate-700' if is_dark else 'bg-white border-slate-100'
        
        # Gridview
        with ui.grid().classes('w-full grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4'):
            # REPARIERT: Entpackt die ownership jetzt direkt linear aus dem bestehenden DB-Tuple, ohne Zusatz-SQL!
            for b_id, b_title, b_author, b_isbn, b_pages, b_status, b_rating, b_pub_date, b_ownership in buecher:
                
                # Symmetrisches visuelles Tuning für weggeliehene/weggegebene Bücher
                if b_ownership == 'GIVEN_AWAY':
                    card_style = 'border: 1px dashed #ef4444;'
                    cover_classes = 'w-full h-full object-cover opacity-40 grayscale transition-all'
                else:
                    card_style = ''
                    cover_classes = 'w-full h-full object-cover transition-all'

                with ui.card().classes(f'p-4 cursor-pointer hover:shadow-md transition-shadow border {bg_buch_karte}') \
                        .style(card_style).on('click', lambda _, current_book_id=b_id: ui.navigate.to(f'/book/{current_book_id}')):
                    with ui.row().classes('w-full items-center gap-3 no-wrap'):
                        cover_pfad = database.hole_cover_url(b_id)
                        with ui.element('div').classes('w-12 h-18 bg-slate-200 dark:bg-slate-900 rounded flex items-center justify-center text-xs text-slate-400 dark:text-slate-500 shadow-sm flex-shrink-0 overflow-hidden'):
                            if cover_pfad != "/covers/placeholder.jpg":
                                ui.image(cover_pfad).classes(cover_classes)
                            else:
                                ui.icon('book', size='sm').classes('opacity-40' if b_ownership == 'GIVEN_AWAY' else '')
                        
                        with ui.column().classes('overflow-hidden flex-1 gap-0.5'):
                            ui.label(b_title).classes('font-bold text-sm text-slate-700 dark:text-slate-100 line-clamp-2 leading-tight')
                            
                            # Bewertung in Form von Sternen unter dem Titel
                            with ui.row().classes('items-center gap-0.5 my-0.5'):
                                b_rating_val = b_rating if b_rating is not None else 0
                                if b_rating_val > 0:
                                    for star_idx in range(1, 6):
                                        star_icon = 'star' if star_idx <= b_rating_val else 'star_border'
                                        ui.icon(star_icon, size='14px').classes('text-amber-500')
                                else:
                                    ui.label(t('none')).classes('text-[11px] text-slate-400 italic')

                            with ui.row().classes('w-full items-center justify-between no-wrap'):
                                ui.label(f"{b_pages or '?'} {t('pages_short')}").classes('text-xs text-slate-400 dark:text-slate-500')
                                
                                # "Weggegeben" Hinweistext neben den Seiten ohne DB-Overhead
                                if b_ownership == 'GIVEN_AWAY':
                                    ui.label(t('ownership_given_away')).classes('text-[9px] text-red-500 dark:text-red-400 font-bold tracking-wide uppercase')

                            # Signalfarben für Lesestatustags
                            badge_color = 'teal' if b_status == 'READ' else ('orange' if b_status == 'READING' else 'slate')
                            ui.badge(t(b_status.lower()), color=badge_color).classes('text-[10px] px-1.5 py-0.5 mt-1 align-self-start')