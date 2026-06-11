from contextlib import contextmanager
from datetime import datetime
import random
from nicegui import ui
import database
import translations
from translations import t

# Sitzungsspeicher für den aktuell ausgewählten User (Standard: ID 1)
aktiver_user_id = 1

# Globale Referenz für das Vorschlagsmodal, damit andere Module es öffnen können
_letztes_vorschlag_modal = None


def global_vorschlag_modal_oeffnen():
    """Erlaubt es anderen Modulen (z.B. der Buch-Detailseite), das Würfel-Modal direkt zu triggern."""
    global _letztes_vorschlag_modal
    if _letztes_vorschlag_modal:
        _letztes_vorschlag_modal.open()


def quick_log_modal():
    """Öffnet ein globales Dialogfenster für den schnellen Lese-Eintrag."""
    global aktiver_user_id
    
    user_ui = database.lade_user_settings(aktiver_user_id)
    is_dark = user_ui['dark_mode']
    sprache = translations.aktuelle_sprache
    
    bg_card = 'bg-slate-800 text-slate-100 border border-slate-700' if is_dark else 'bg-white text-slate-700'
    text_main = 'text-slate-100' if is_dark else 'text-slate-700'
    input_prop = 'dark' if is_dark else ''
    
    aktive_buecher = database.lade_aktuelle_buecher(aktiver_user_id)
    
    if not aktive_buecher:
        ui.notify(t('quick_log_no_books'), type='warning')
        return

    buch_optionen = {b_id: b_title for b_id, b_title in aktive_buecher}

    with ui.dialog() as log_dialog, ui.card().classes(f'w-full max-w-md p-6 flex flex-col gap-4 {bg_card}'):
        ui.label(t('quick_log_title')).classes(f'text-lg font-bold {text_main} mb-2')
        
        buch_select = ui.select(options=buch_optionen, label=t('select_book')).classes('w-full').props(f'outlined dense {input_prop} popup-content-class="dark"' if is_dark else 'outlined dense')
        seiten_input = ui.number(label=t('pages_read_to'), value=None, min=1).classes('w-full').props(f'outlined dense {input_prop}')
        
        heute_str = datetime.now().strftime('%Y/%m-%d').replace('-', '/')
        kalender_locale = translations.hole_kalender_locale(sprache)
        
        with ui.input(label=t('date'), value=heute_str).classes('w-full').props(f'outlined dense {input_prop}') as datum_input:
            with datum_input.add_slot('append'):
                ui.icon('access_time').classes('cursor-pointer').on('click', lambda: menu.open())
                with ui.menu() as menu:
                    ui.date().bind_value(datum_input).props(f'first-day-of-week="1" :locale="{kalender_locale}" {"dark" if is_dark else ""}')

        async def schnell_log_speichern():
            b_id = buch_select.value
            neue_seite = seiten_input.value
            
            gewaehltes_datum = datum_input.value.replace('/', '-') if datum_input.value else datetime.now().strftime('%Y-%m-%d')
            
            if not b_id or not neue_seite:
                ui.notify(t('quick_log_warn_fields'), type='warning')
                return

            with database.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT pages FROM books WHERE id = ?", (b_id,))
                row = cursor.fetchone()
                max_pages = row[0] if row and row[0] else 0

            erfolg, meldung = database.trage_lese_log_ein(aktiver_user_id, b_id, int(neue_seite), gewaehltes_datum)
            
            if erfolg:
                ui.notify(f"{t('entry_saved')} +{meldung} {t('pages_short')}.", type='positive')
                if max_pages > 0 and int(neue_seite) >= max_pages:
                    database.schliesse_aktiven_zyklus_ab(aktiver_user_id, b_id, end_datum=gewaehltes_datum)
                    with database.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE user_books SET status = 'READ' WHERE user_id = ? AND book_id = ?", (aktiver_user_id, b_id))
                        conn.commit()
                    ui.notify(f"{t('book_finished')} 🎉", type='positive')

                    # Spaßprojekt-Trigger beim Schnellbuchen, falls das Buch beendet wurde
                    user_settings = database.lade_user_settings(aktiver_user_id)
                    if user_settings.get('buch_vorschlag_aktiv', False):
                        log_dialog.close()
                        ui.timer(0.5, global_vorschlag_modal_oeffnen, once=True)
                        return

                log_dialog.close()
                ui.run_javascript('window.location.reload()')
            else:
                ui.notify(meldung, type='warning')

        with ui.row().classes('w-full justify-end gap-2 mt-2'):
            ui.button(t('cancel'), on_click=log_dialog.close).classes('text-slate-500').props('flat')
            ui.button(t('save'), on_click=schnell_log_speichern).classes('bg-emerald-600 text-white px-4')

    log_dialog.open()


@contextmanager
def basis_layout(titel_key: str = None):
    global aktiver_user_id, _letztes_vorschlag_modal
    
    alle_user = database.lade_alle_user()
    user_options = {u[0]: u[1] for u in alle_user}
    
    if aktiver_user_id not in user_options and user_options:
        aktiver_user_id = list(user_options.keys())[0]

    user_ui = database.lade_user_settings(aktiver_user_id)
    is_dark = user_ui['dark_mode']
    ui.dark_mode().value = is_dark

    titel_text = translations.t(titel_key)
    ui.page_title(titel_text)
    
    bg_modal_card = 'bg-slate-800 text-slate-100 border border-slate-700' if is_dark else 'bg-white text-slate-700'
    text_modal_main = 'text-slate-100' if is_dark else 'text-slate-800'
    select_modal_prop = 'dark popup-content-class="dark"' if is_dark else ''
    
    # Header-Navigation
    with ui.header().classes('bg-slate-800 text-white p-4 flex justify-between items-center shadow-md z-[100]'):
        with ui.row().classes('gap-6 font-medium items-center'):

            with ui.link('', '/').classes('flex items-center no-underline hover:opacity-80 transition-opacity'):
                ui.image('/static/favicon.png').classes('w-10 h-10 rounded-md object-cover shadow-sm bg-white p-0.5')

            ui.link(t('my_shelf'), '/').classes('text-white hover:text-slate-300 no-underline text-lg')
            ui.link(t('authors'), '/authors').classes('text-white hover:text-slate-300 no-underline text-lg')
            ui.link(t('series'), '/series').classes('text-white hover:text-slate-300 no-underline text-lg')
            ui.link(t('genres'), '/genres').classes('text-white hover:text-slate-300 no-underline text-lg')
            ui.link(t('stats'), '/statistics').classes('text-white hover:text-slate-300 no-underline text-lg')
            ui.link(t('calendar'), '/calendar').classes('text-white hover:text-slate-300 no-underline text-lg')
            ui.link(t('settings'), '/settings').classes('text-white hover:text-slate-300 no-underline text-lg')
        
        with ui.row().classes('items-center gap-4'):
            
            # =========================================================================
            # LOKALISIERTER CASINO-BUTTON & VORSCHLAG-MODAL
            # =========================================================================
            if user_ui.get('buch_vorschlag_aktiv', False):
                
                with ui.dialog().classes('w-full max-w-md') as vorschlag_modal, ui.card().classes(f'w-full p-6 gap-4 {bg_modal_card}'):
                    ui.label(t('book_suggestion_title')).classes(f'text-lg font-bold {text_modal_main} mb-1')
                    
                    globale_genres = database.lade_alle_genres(aktiver_user_id)
                    genre_opts = {'ALL': '🎲 ' + t('book_suggestion_all')}
                    for g_id, g_name in globale_genres:
                        genre_opts[g_name] = f"🏷️ {g_name}"
                        
                    genre_auswahl = ui.select(options=genre_opts, value='ALL').classes('w-full').props(f'outlined dense {select_modal_prop}')
                    
                    ergebnis_container = ui.column().classes('w-full items-center gap-2 mt-2')
                    
                    def vorschlag_generieren():
                        ergebnis_container.clear()
                        buch = database.hole_zufaelliges_buch_vorschlag(aktiver_user_id, genre_auswahl.value)
                        
                        with ergebnis_container:
                            if not buch:
                                ui.label(t('book_suggestion_empty')).classes('text-red-500 italic text-sm text-center')
                                return
                            
                            ui.label(t('book_suggestion_hint')).classes('text-xs text-slate-400 uppercase tracking-wider mt-1 w-full text-left')
                            
                            cover_url = database.hole_cover_url(buch['id'])
                            
                            bg_card_suggestion = 'bg-slate-900 border-slate-700' if is_dark else 'bg-blue-50/40 border-blue-100'
                            text_title = 'text-slate-100' if is_dark else 'text-slate-800'
                            
                            with ui.card().classes(f'w-full p-2 border flex flex-row gap-4 items-stretch cursor-pointer hover:scale-[1.01] transition-transform overflow-hidden rounded-xl {bg_card_suggestion}') \
                                    .on('click', lambda b_id=buch['id']: [vorschlag_modal.close(), ui.navigate.to(f'/book/{b_id}')]):
                                
                                with ui.element('div').classes('w-20 aspect-[2/3] rounded-lg bg-slate-200 dark:bg-slate-800 flex items-center justify-center overflow-hidden shadow-xs flex-shrink-0'):
                                    if cover_url != "/covers/placeholder.jpg":
                                        ui.image(cover_url).classes('w-full h-full object-cover')
                                    else:
                                        ui.icon('book', size='sm').classes('text-slate-400')
                                
                                with ui.column().classes('flex-1 justify-between py-1 gap-1'):
                                    with ui.element('div').classes('w-full flex flex-col gap-1'):
                                        ui.label(buch['title']).classes(f'font-bold text-sm md:text-base leading-tight {text_title} line-clamp-2')
                                        
                                        if buch['is_series']:
                                            ui.badge(f"{t('series_num')}: {buch['series_name']}", color='orange').classes('text-[9px] px-1.5 py-0.5 rounded font-medium self-start mt-0.5')
                                    
                                    if buch.get('genres'):
                                        with ui.row().classes('flex-wrap gap-1 mt-auto pt-2'):
                                            for g_name in buch['genres']:
                                                ui.badge(g_name, color='slate').classes('text-[9px] px-1.5 py-0.5 rounded-md font-normal opacity-80')
                            
                            ui.label(t('book_suggestion_click_to_open')).classes('text-[10px] text-slate-400 italic mt-1 w-full text-center')

                    with ui.row().classes('w-full justify-end gap-2 mt-4'):
                        ui.button(t('cancel'), on_click=vorschlag_modal.close).classes('text-slate-500').props('flat')
                        ui.button(t('roll_book'), on_click=vorschlag_generieren).classes('bg-blue-600 text-white px-4')

                _letztes_vorschlag_modal = vorschlag_modal

                ui.button(icon='casino', on_click=lambda: [ergebnis_container.clear(), vorschlag_modal.open()]) \
                    .props('round flat dense size=md') \
                    .classes('text-blue-400 hover:bg-slate-700') \
                    .tooltip(t('roll_book'))

            # SCHNELLZUGRIFFS-BUTTON
            ui.button(
                icon='bookmark_add', 
                on_click=quick_log_modal
            ).props('round flat dense size=md') \
             .classes('text-emerald-400 hover:bg-slate-700') \
             .tooltip(t('quick_log_title'))

            # DYNAMISCHER PERSONENUMSCHALTER
            def user_wechseln(e):
                global aktiver_user_id
                aktiver_user_id = e.value
                ui.run_javascript('window.location.reload()')

            ui.select(options=user_options, value=aktiver_user_id, on_change=user_wechseln) \
                .props('dark dense options-dense borderless').classes('w-36 text-white text-sm font-bold bg-slate-700 px-2 py-1 rounded')

            ui.separator().props('vertical').classes('bg-slate-600 h-6')

            # SPRACHUMSCHALTER
            def sprache_wechseln(e):
                translations.aktuelle_sprache = e.value
                ui.run_javascript('window.location.reload()')

            ui.select(options={'de': '🇩🇪 DE', 'en': '🇬🇧 EN'}, value=translations.aktuelle_sprache, on_change=sprache_wechseln) \
                .props('dark dense options-dense borderless').classes('w-20 text-white text-sm')
        
    with ui.element('div').classes('w-full p-6 max-w-7xl mx-auto pt-5 bg-slate-50 dark:bg-slate-900'):
        yield