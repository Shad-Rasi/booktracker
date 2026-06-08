from nicegui import ui
import database
import layout
from layout import basis_layout
from translations import t
import book_api

@ui.page('/authors')
def autoren_uebersicht():
    with basis_layout('authors'):
        ui.label(t('authors_title')).classes('text-2xl font-bold text-slate-700 mb-2')
        ui.label(t('authors_subtitle')).classes('text-sm text-slate-500 mb-6')
        
        alle_autoren = database.lade_alle_autoren_aus_db(layout.aktiver_user_id)
        
        if not alle_autoren:
            with ui.card().classes('w-full p-6 text-center text-slate-500'):
                ui.icon('people', size='lg').classes('mx-auto mb-2')
                ui.label(t('no_authors_found'))
            return

        # --- SUCHLEISTE ---
        with ui.card().classes('w-full p-4 bg-slate-100 shadow-sm border border-slate-200 mb-6 flex flex-col gap-3'):
            with ui.row().classes('w-full items-center gap-4'):
                suchfeld = ui.input(
                    placeholder=t('search'), 
                    on_change=lambda: autoren_raster_refresh.refresh()
                ).classes('flex-1 bg-white px-3 rounded border').props('clearable icon=search')

        # --- DYNAMISCHER KACHEL-CONTAINER ---
        @ui.refreshable
        def autoren_raster_refresh():
            suchbegriff = suchfeld.value.strip().lower() if suchfeld.value else ""
            gefilterte_autoren = [a for a in alle_autoren if suchbegriff in a[1].lower()]
            
            if not gefilterte_autoren:
                with ui.element('div').classes('w-full p-8 text-center text-slate-400 italic'):
                    ui.label(t('no_search_results') if 'no_search_results' in layout.translations.LANGUAGES[layout.translations.aktuelle_sprache] else 'Keine passenden Autoren gefunden')
                return

            with ui.element('div').classes('w-full grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6'):
                for a_id, a_name, a_bio, a_img, a_local_img in gefilterte_autoren:
                    with ui.card().classes('p-4 cursor-pointer hover:shadow-md transition-shadow items-center text-center bg-slate-50 border border-slate-200 h-full flex flex-col justify-between') \
                            .on('click', lambda _, current_id=a_id: ui.navigate.to(f'/author/{current_id}')):
                        
                        with ui.element('div').classes('flex flex-col items-center w-full'):
                            if a_local_img:
                                ui.image(a_local_img).classes('w-20 h-20 rounded-full object-cover shadow-sm mb-3')
                            else:
                                with ui.element('div').classes('w-20 h-20 rounded-full bg-slate-300 text-slate-600 flex items-center justify-center text-2xl font-bold mb-3 shadow-inner'):
                                    ui.label(a_name[0] if a_name else '?')
                            
                            ui.label(a_name).classes('font-bold text-slate-700 text-sm md:text-base line-clamp-2 leading-snug')
                        
                        ui.label(t('view_profile')).classes('text-[11px] text-blue-500 mt-3 uppercase tracking-wider font-semibold block')

        autoren_raster_refresh()


@ui.page('/author/{author_id}')
def autor_detailseite(author_id: int):
    with basis_layout('authors'):
        
        ui.button(t('back_to_authors'), icon='arrow_back', on_click=lambda: ui.navigate.to('/authors')) \
            .props('flat dense').classes('text-slate-500 mb-4')

        @ui.refreshable
        def profil_kopf_refresh():
            autor = database.lade_autor_details(author_id)
            if not autor:
                ui.label('Autor nicht gefunden!').classes('text-red-500')
                return
                
            a_id, a_name, a_bio, a_birth, a_death, a_img, a_local_img = autor
            
            # --- AUTOREN KOPFZEILE (PROFIL) ---
            with ui.card().classes('w-full p-6 bg-slate-50 border border-slate-200 shadow-sm mb-6'):
                with ui.row().classes('w-full items-center gap-6 no-wrap flex-col sm:flex-row'):
                    
                    if a_local_img:
                        ui.image(a_local_img).classes('w-32 h-32 rounded-full object-cover shadow-md')
                    else:
                        with ui.element('div').classes('w-32 h-32 rounded-full bg-slate-300 text-slate-600 flex items-center justify-center text-4xl font-bold shadow-inner flex-shrink-0'):
                            ui.label(a_name[0] if a_name else '?')
                    
                    with ui.element('div').classes('flex-1 text-center sm:text-left'):
                        with ui.row().classes('w-full items-center justify-between sm:justify-start gap-2'):
                            ui.label(a_name).classes('text-3xl font-black text-slate-800')
                            
                            # BUTTON-BOX FÜR UTILITIES
                            with ui.row().classes('gap-1 items-center'):
                                # 1. Zauberstab (API)
                                async def api_abruf_starten():
                                    ui.notify(f'Suche Daten für {a_name}...', type='info')
                                    api_data = await book_api.hole_autoren_metadaten_async(a_name)
                                    
                                    if api_data:
                                        database.aktualisiere_autor_in_db(
                                            a_id, api_data['bio'], api_data['birth_date'], 
                                            api_data['death_date'], api_data['image_url']
                                        )
                                        ui.notify('Autorendaten erfolgreich aktualisiert!', type='positive')
                                        profil_kopf_refresh.refresh()
                                    else:
                                        ui.notify('Keine Daten bei Open Library gefunden.', type='warning')

                                ui.button(icon='auto_fix_high', on_click=api_abruf_starten) \
                                    .props('round flat dense').classes('text-blue-500 hover:bg-blue-50')
                                
                                # 2. Stift (Manuelles Editieren via Dialog)
                                def manuelles_editieren():
                                    with ui.dialog() as edit_dialog, ui.card().classes('w-full max-w-lg p-6 flex flex-col gap-4'):
                                        ui.label(f'"{a_name}" {t("edit_author_title")}').classes('text-lg font-bold text-slate-700')
                                        
                                        # Eingabefelder vorbefüllen
                                        birth_input = ui.input(label=t('author_birth'), value=a_birth or '').classes('w-full')
                                        death_input = ui.input(label=t('author_death'), value=a_death or '').classes('w-full')
                                        img_input = ui.input(label=t('author_img_url'), value=a_img or '').classes('w-full')
                                        bio_input = ui.textarea(label=t('author_bio'), value=a_bio or '').classes('w-full').props('rows=5')
                                        
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
                                            profil_kopf_refresh.refresh() # Aktualisiert den Kopfbereich live

                                        with ui.row().classes('w-full justify-end gap-2 mt-2'):
                                            ui.button(t('cancel'), on_click=edit_dialog.close).classes('text-slate-500').props('flat')
                                            ui.button(t('save'), on_click=daten_speichern).classes('bg-slate-700 text-white px-4')
                                    
                                    edit_dialog.open()

                                ui.button(icon='edit', on_click=manuelles_editieren) \
                                    .props('round flat dense').classes('text-slate-500 hover:bg-slate-100')
                        
                        if a_birth:
                            lebensdaten = f"*{a_birth}"
                            if a_death: lebensdaten += f"  †{a_death}"
                            ui.label(lebensdaten).classes('text-xs text-slate-400 font-mono mt-1')
                            
                        ui.label(a_bio if a_bio else t('no_bio_available')).classes('text-sm text-slate-600 mt-3 italic max-w-2xl block whitespace-pre-line')

        profil_kopf_refresh()

        # --- BÜCHER DIESES AUTORS ---
        ui.label(t('books_by_author')).classes('text-xl font-bold text-slate-700 mb-4')
        autor_name_fuer_buecher = database.lade_autor_details(author_id)[1]
        buecher = database.lade_buecher_von_autor(layout.aktiver_user_id, autor_name_fuer_buecher)
        
        with ui.grid(columns='1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4').classes('gap-4 w-full'):
            for b_id, b_title, b_author, b_isbn, b_pages, b_status, b_rating in buecher:
                with ui.card().classes('p-4 cursor-pointer hover:shadow-md transition-shadow bg-white border border-slate-100') \
                        .on('click', lambda _, current_book_id=b_id: ui.navigate.to(f'/book/{current_book_id}')):
                    with ui.row().classes('w-full items-center gap-3 no-wrap'):
                        cover_pfad = database.hole_cover_url(b_id)
                        with ui.element('div').classes('w-12 h-18 bg-slate-200 rounded flex items-center justify-center text-xs text-slate-400 shadow-sm flex-shrink-0 overflow-hidden'):
                            if cover_pfad != "/covers/placeholder.jpg":
                                ui.image(cover_pfad).classes('w-full h-full object-cover')
                            else:
                                ui.icon('book', size='sm')
                        with ui.element('div').classes('overflow-hidden flex-1'):
                            ui.label(b_title).classes('font-bold text-sm text-slate-700 line-clamp-2 leading-tight')
                            ui.label(f"{b_pages or '?'} {t('pages_short')}").classes('text-xs text-slate-400 mt-0.5')
                            badge_color = 'emerald' if b_status == 'READ' else ('amber' if b_status == 'READING' else 'slate')
                            ui.badge(t(b_status.lower()), color=badge_color).classes('text-[10px] px-1.5 py-0.5 mt-1')