import os
import asyncio
from datetime import datetime
from nicegui import ui
import database
import layout
from layout import basis_layout
import translations
from translations import t

@ui.page('/series')
def reihen_uebersicht():
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    is_dark = user_ui['dark_mode']
    
    # REPARIERT: Nutzt jetzt den eindeutigen Key 'series_title' für den Tab ("Buchreihen")
    with basis_layout('series_title'):
        ui.label(t('series_title')).classes('text-2xl font-bold text-slate-700 dark:text-slate-100 mb-2')
        ui.label(t('series_subtitle')).classes('text-sm text-slate-500 dark:text-slate-400 mb-6')
        
        alle_buecher = database.lade_buecher_aus_db(layout.aktiver_user_id)
        
        reihen_dict = {}
        for b in alle_buecher:
            b_id = b[0]
            is_series = bool(b[8])
            s_name = b[9]
            author = b[2] or t('unknown_author')
            s_num = b[10] if b[10] is not None else 999
            
            if is_series and s_name and s_name.strip():
                s_name_clean = s_name.strip()
                if s_name_clean not in reihen_dict:
                    reihen_dict[s_name_clean] = {
                        'count': 0, 
                        'author': author,
                        'first_book_id': b_id,
                        'lowest_num': s_num
                    }
                
                reihen_dict[s_name_clean]['count'] += 1
                
                if s_num < reihen_dict[s_name_clean]['lowest_num']:
                    reihen_dict[s_name_clean]['lowest_num'] = s_num
                    reihen_dict[s_name_clean]['first_book_id'] = b_id

        if not reihen_dict:
            with ui.card().classes('w-full p-6 text-center bg-slate-50 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700'):
                ui.icon('layers', size='lg').classes('mx-auto mb-2')
                ui.label(t('no_series_found'))
            return

        # --- SUCHLEISTE ---
        with ui.card().classes('w-full p-4 bg-slate-100 dark:bg-slate-800 shadow-sm border border-slate-200 dark:border-slate-700 mb-6 flex flex-col gap-3'):
            with ui.row().classes('w-full items-center gap-4'):
                suchfeld = ui.input(
                    placeholder=t('search'), 
                    on_change=lambda: reihen_raster_refresh.refresh()
                ).classes('flex-1 px-3 text-slate-800 dark:text-slate-100') \
                 .props(f'clearable icon=search outlined {"dark" if is_dark else ""}')

        # --- DYNAMISCHER KACHEL-CONTAINER ---
        @ui.refreshable
        def reihen_raster_refresh():
            user_ui_fresh = database.lade_user_settings(layout.aktiver_user_id)
            is_dark_fresh = user_ui_fresh['dark_mode']
            
            bg_card = 'bg-slate-800 border-slate-700 text-slate-100' if is_dark_fresh else 'bg-slate-50 border-slate-200 text-slate-700'
            text_title = 'text-slate-100' if is_dark_fresh else 'text-slate-800'
            text_sub = 'text-slate-400' if is_dark_fresh else 'text-slate-500'
            
            suchbegriff = suchfeld.value.strip().lower() if suchfeld.value else ""
            
            gefilterte_reihen = sorted(
                [(name, data) for name, data in reihen_dict.items() if suchbegriff in name.lower()],
                key=lambda x: x[0].lower()
            )
            
            if not gefilterte_reihen:
                with ui.element('div').classes('w-full p-8 text-center text-slate-400 italic'):
                    ui.label(t('no_search_results'))
                return

            with ui.grid().classes('w-full grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-6'):
                for r_name, r_data in gefilterte_reihen:
                    cover_pfad = database.hole_cover_url(r_data['first_book_id'])
                    
                    with ui.card().classes(f'p-2 cursor-pointer hover:shadow-md transition-all h-full flex flex-col justify-between overflow-hidden border {bg_card}') \
                            .on('click', lambda _, name=r_name: ui.navigate.to(f'/series/{name}')):
                        
                        with ui.element('div').classes('w-full flex flex-col gap-2'):
                            with ui.element('div').classes('relative w-full aspect-[2/3] rounded shadow-sm bg-slate-200 dark:bg-slate-900 flex items-center justify-center overflow-hidden'):
                                if cover_pfad != "/covers/placeholder.jpg":
                                    ui.image(cover_pfad).classes('w-full h-full object-cover')
                                else:
                                    with ui.element('div').classes('flex flex-col items-center text-slate-400 dark:text-slate-600 gap-1'):
                                        ui.icon('layers', size='md')
                            
                            with ui.element('div').classes('px-1 flex flex-col gap-0.5'):
                                ui.label(r_name).classes(f'font-bold text-xs md:text-sm line-clamp-2 leading-tight {text_title}')
                                ui.label(r_data['author']).classes(f'text-[11px] italic truncate {text_sub}')
                        
                        with ui.row().classes('w-full justify-between items-center mt-2 px-1 pt-1 border-t border-slate-200/10'):
                            text_buecher = t('book') if r_data['count'] == 1 else t('books_count')
                            ui.badge(f"{r_data['count']} {text_buecher}", color='blue').classes('text-[9px] px-1.5 py-0.5')

        reihen_raster_refresh()


@ui.page('/series/{series_name}')
def reihen_detailseite(series_name: str):
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    is_dark = user_ui['dark_mode']
    
    bg_buch_karte = 'bg-slate-800 border-slate-700' if is_dark else 'bg-white border-slate-100'
    text_main = 'text-slate-100' if is_dark else 'text-slate-700'
    text_sub = 'text-slate-400' if is_dark else 'text-slate-500'

    # REPARIERT: Schreibt den Namen der Reihe starr oben in den Browsertab
    with basis_layout(series_name):
        ui.button(t('back_to_series'), icon='arrow_back', on_click=lambda: ui.navigate.to('/series')) \
            .props('flat dense').classes('text-slate-500 dark:text-slate-400 mb-4')
            
        alle_buecher = database.lade_buecher_aus_db(layout.aktiver_user_id)
        reihen_buecher = []
        
        for b in alle_buecher:
            if bool(b[8]) and b[9] and b[9].strip().lower() == series_name.strip().lower():
                reihen_buecher.append(b)
                
        reihen_buecher.sort(key=lambda x: x[10] if x[10] is not None else 999)

        # --- HEADER ---
        ui.label(series_name).classes(f'text-3xl font-black mb-1 {text_main}')
        
        if reihen_buecher:
            autor_name = reihen_buecher[0][2] or t('unknown_author')
            autor_id = database.hole_autoren_id_durch_name(layout.aktiver_user_id, autor_name)
            
            if autor_id:
                ui.label(autor_name) \
                    .classes('text-base text-slate-500 dark:text-slate-400 italic mb-6 w-fit cursor-pointer hover:text-blue-600 dark:hover:text-blue-400 hover:underline transition-colors') \
                    .on('click', lambda: ui.navigate.to(f'/author/{autor_id}')) \
                    .tooltip(t('view_profile'))
            else:
                ui.label(autor_name).classes(f'text-base mb-6 {text_sub} italic w-fit')
        
        with ui.grid().classes('w-full grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-6'):
            for b in reihen_buecher:
                b_id, b_title, b_author = b[0], b[1], b[2]
                b_pages, b_status, b_rating, b_num = b[4], b[5] or 'UNREAD', b[6], b[10]
                b_ownership = b[24] if len(b) > 24 else 'OWNED'
                
                if b_ownership == 'GIVEN_AWAY':
                    card_style = 'border: 1px dashed #ef4444;'
                    cover_classes = 'w-full h-full object-cover opacity-40 grayscale transition-all'
                else:
                    card_style = ''
                    cover_classes = 'w-full h-full object-cover transition-all'
                
                with ui.card().classes(f'p-2 cursor-pointer hover:shadow-md transition-shadow border {bg_buch_karte}') \
                        .style(card_style).on('click', lambda _, current_book_id=b_id: ui.navigate.to(f'/book/{current_book_id}')):
                    
                    with ui.element('div').classes('w-full flex flex-col justify-between h-full'):
                        with ui.element('div').classes('w-full flex flex-col gap-2'):
                            cover_pfad = database.hole_cover_url(b_id)
                            
                            with ui.element('div').classes('relative w-full aspect-[2/3] rounded shadow-sm bg-slate-200 dark:bg-slate-900 flex items-center justify-center overflow-hidden'):
                                if cover_pfad != "/covers/placeholder.jpg":
                                    ui.image(cover_pfad).classes(cover_classes)
                                else:
                                    ui.icon('book', size='sm').classes('text-slate-400' + (' opacity-40' if b_ownership == 'GIVEN_AWAY' else ''))
                                
                                with ui.element('div').classes('absolute top-1 left-1 bg-blue-600 text-white text-[9px] font-bold px-1.5 py-0.5 rounded shadow'):
                                    ui.label(f"#{b_num or '?'}")
                                    
                            with ui.column().classes('px-1 gap-0.5 flex-1 justify-between min-h-[96px]'):
                                with ui.element('div').classes('w-full'):
                                    ui.label(b_title).classes(f'font-bold text-xs md:text-sm line-clamp-2 leading-tight {text_main}')
                                
                                with ui.element('div').classes('w-full flex flex-col gap-0.5 mt-auto'):
                                    with ui.row().classes('items-center gap-0.5 my-0.5'):
                                        b_rating_val = b_rating if b_rating is not None else 0
                                        if b_rating_val > 0:
                                            for star_idx in range(1, 6):
                                                star_icon = 'star' if star_idx <= b_rating_val else 'star_border'
                                                ui.icon(star_icon, size='14px').classes('text-amber-500')
                                        else:
                                            ui.label(t('none')).classes('text-[11px] text-slate-400 italic')
                                    
                                    with ui.row().classes('w-full items-center justify-between no-wrap'):
                                        ui.label(f"{b_pages or '?'} {t('pages_short')}").classes(f'text-[10px] {text_sub}')
                                        
                                        if b_ownership == 'GIVEN_AWAY':
                                            ui.label(t('ownership_given_away')).classes('text-[9px] text-red-500 dark:text-red-400 font-bold tracking-wide uppercase')
                        
                        with ui.row().classes('w-full mt-2 pt-1 px-1 border-t border-slate-200/10'):
                            badge_color = 'teal' if b_status == 'READ' else ('orange' if b_status == 'READING' else 'slate')
                            ui.badge(t(b_status.lower()), color=badge_color).classes('text-[9px] px-1.5 py-0.5')