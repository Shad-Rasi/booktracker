from contextlib import contextmanager
from datetime import datetime
import sys
import random
from nicegui import app, ui
import database
import translations
from translations import t
from logger import ui_log_lang

# Globale Referenz für das Vorschlagsmodal, damit andere Module es öffnen können
_letztes_vorschlag_modal = None


def global_vorschlag_modal_oeffnen():
    """Erlaubt es anderen Modulen (z.B. der Buch-Detailseite), das Würfel-Modal direkt zu triggern."""
    global _letztes_vorschlag_modal
    if _letztes_vorschlag_modal:
        _letztes_vorschlag_modal.open()


def vorschlag_modal_erstellen(current_user_id, is_dark, bg_modal_card, text_modal_main, select_modal_prop):
    """Erstellt das Vorschlags-Modal separat, um Scope-Probleme zu vermeiden."""
    global _letztes_vorschlag_modal

    with ui.dialog().classes('w-full max-w-md') as vorschlag_modal, ui.card().classes(f'w-full p-6 gap-4 {bg_modal_card}'):
        ui.label(t('book_suggestion_title')).classes(f'text-lg font-bold {text_modal_main} mb-1')
        
        globale_genres = database.lade_alle_genres(current_user_id)
        genre_opts = {'ALL': '🎲 ' + t('book_suggestion_all')}
        for g_id, g_name in globale_genres:
            genre_opts[g_name] = f"🏷️ {g_name}"
            
        genre_auswahl = ui.select(options=genre_opts, value='ALL').classes('w-full').props(f'outlined dense {select_modal_prop}')
        ergebnis_container = ui.column().classes('w-full items-center gap-2 mt-2')
        
        def vorschlag_generieren():
            ergebnis_container.clear()
            buch = database.hole_zufaelliges_buch_vorschlag(current_user_id, genre_auswahl.value)
            
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
    return vorschlag_modal, ergebnis_container


def quick_log_modal():
    """Öffnet ein globales Dialogfenster für den schnellen Lese-Eintrag – optimiert für Querformat."""
    current_user_id = sys.modules[__name__].aktiver_user_id
    
    user_ui = database.lade_user_settings(current_user_id)
    is_dark = user_ui['dark_mode']
    sprache = translations.aktuelle_sprache
    
    bg_card = 'bg-slate-800 text-slate-100 border border-slate-700' if is_dark else 'bg-white text-slate-700'
    text_main = 'text-slate-100' if is_dark else 'text-slate-700'
    input_prop = 'dark' if is_dark else ''
    
    aktive_buecher = database.lade_aktuelle_buecher(current_user_id)
    
    if not aktive_buecher:
        ui.notify(t('quick_log_no_books'), type='warning')
        return

    buch_optionen = {b_id: b_title for b_id, b_title in aktive_buecher}

    with ui.dialog() as log_dialog, ui.card().classes(f'w-full max-w-md max-h-[85vh] p-4 md:p-6 flex flex-col gap-4 overflow-y-auto no-scrollbar {bg_card}'):
        ui.label(t('quick_log_title')).classes(f'text-lg font-bold {text_main} mb-1 shrink-0')
        
        with ui.column().classes('w-full flex flex-col gap-3'):
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

            # REPARIERT: Titel direkt mithub, damit wir ihn fürs Log parat haben
            with database.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT title, pages FROM books WHERE id = ?", (b_id,))
                row = cursor.fetchone()
                book_title = row[0] if row and row[0] else "Unbekanntes Buch"
                max_pages = row[1] if row and row[1] else 0

            erfolg, meldung = database.trage_lese_log_ein(current_user_id, b_id, int(neue_seite), gewaehltes_datum)
            
            if erfolg:
                ui.notify(f"{t('entry_saved')} +{meldung} {t('pages_short')}.", type='positive')
                ui_log_lang('log_progress_saved', pages=meldung, title=book_title)
                
                if max_pages > 0 and int(neue_seite) >= max_pages:
                    database.schliesse_aktiven_zyklus_ab(current_user_id, b_id, end_datum=gewaehltes_datum)
                    with database.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE user_books SET status = 'READ' WHERE user_id = ? AND book_id = ?", (current_user_id, b_id))
                        conn.commit()
                    
                    
                    ui.notify(f"{t('book_finished')} 🎉", type='positive')
                    ui_log_lang('log_book_finished', title=book_title)

                    user_settings = database.lade_user_settings(current_user_id)
                    if user_settings.get('buch_vorschlag_aktiv', False):
                        log_dialog.close()
                        ui.timer(0.5, global_vorschlag_modal_oeffnen, once=True)
                        return

                log_dialog.close()
                ui.run_javascript('window.location.reload()')
            else:
                # API- oder Eingabefehler im Terminal vermerken
                ui_log_lang(f"[Leseprotokoll] WARNUNG: Eintrag fehlgeschlagen für '{book_title}': {meldung}")
                ui.notify(meldung, type='warning')

        with ui.row().classes('w-full justify-end gap-2 mt-auto pt-2 flex-wrap shrink-0'):
            ui.button(t('cancel'), on_click=log_dialog.close).classes('text-slate-500').props('flat')
            ui.button(t('save'), on_click=schnell_log_speichern).classes('bg-emerald-600 text-white px-4')

    log_dialog.open()


def navigation_regal_klick():
    from memory import REGAL_MEMORY
    
    REGAL_MEMORY['shelf_page'] = 1
    REGAL_MEMORY['search_text'] = ''
    REGAL_MEMORY['filter_status'] = 'ALL'
    REGAL_MEMORY['filter_format'] = 'ALL'
    REGAL_MEMORY['filter_ownership'] = 'ALL'
    REGAL_MEMORY['filter_location'] = 'ALL'
    REGAL_MEMORY['filter_genre'] = 'ALL'
    REGAL_MEMORY['filter_sort'] = 'title_asc'

    ui.navigate.to('/')


@contextmanager
def basis_layout(titel_key: str = None):
    global _letztes_vorschlag_modal
    
    # 1. Den Header remote-user aus dem HTTP-Request fischen
    try:
        request = ui.context.client.request
        proxy_user_name = request.session.get('authelia_user_name')
    except Exception:
        proxy_user_name = None

    # 2. FLANKEN-MERKER: Wurde der Authelia-User für diesen Tab schon initialisiert?
    # Wir speichern den Merker direkt im app.storage.user (NiceGUI-sicher!)
    proxy_erledigt = app.storage.user.get('authelia_initial_erledigt', False)

    # 3. FIRST SCAN: Nur beim allerersten Laden der Seite ausführen!
    if not proxy_erledigt and proxy_user_name:
        try:
            alle_user = database.lade_alle_user()
            user_gefunden = False
            
            for u_id, u_name in alle_user:
                if u_name.strip().lower() == proxy_user_name:
                    app.storage.user['aktiver_user_id'] = u_id
                    user_gefunden = True
                    break
            
            # Sicherheitsnetz: Wenn die Schleife durchläuft und niemanden findet
            if not user_gefunden:
                app.storage.user['aktiver_user_id'] = 1 # Fallback auf ID 1
            
            app.storage.user['authelia_initial_erledigt'] = True
            
        except Exception as e:
            print(f"Fehler bei initialer Layout-User-Zuweisung: {e}")

    
    current_user_id = sys.modules[__name__].aktiver_user_id
    
    alle_user = database.lade_alle_user()
    user_options = {u[0]: u[1] for u in alle_user}
    
    if current_user_id not in user_options and user_options:
        current_user_id = list(user_options.keys())[0]
        sys.modules[__name__].aktiver_user_id = current_user_id

    user_ui = database.lade_user_settings(current_user_id)
    is_dark = user_ui['dark_mode']
    ui.dark_mode().value = is_dark

    titel_text = translations.t(titel_key)
    ui.page_title(titel_text)
    
    bg_modal_card = 'bg-slate-800 text-slate-100 border border-slate-700' if is_dark else 'bg-white text-slate-700'
    text_modal_main = 'text-slate-100' if is_dark else 'text-slate-800'
    select_modal_prop = 'dark popup-content-class="dark"' if is_dark else ''

    ui.add_head_html('''
        <style>
            body {
                padding: 0 !important;
                margin: 0 !important;
            }
            .no-scrollbar::-webkit-scrollbar { display: none; }
            .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
            .footer-safe {
                padding-bottom: max(4px, env(safe-area-inset-bottom));
            }
            .content-safe {
                padding-bottom: calc(5rem + env(safe-area-inset-bottom, 0px));
            }
            @media (min-width: 768px) {
                .desktop-nav { display: flex !important; }
                .mobile-nav-container { display: none !important; }
            }
            @media (max-width: 767px) {
                .desktop-nav { display: none !important; }
                .mobile-nav-container { display: block !important; }
            }
            @media (max-width: 950px) and (max-height: 500px) {
                .mobile-nav-container { display: none !important; }
                .desktop-nav { 
                    display: flex !important; 
                    padding: 4px 12px !important; 
                }
                .desktop-nav .nav-title-zone { display: none !important; }
                .desktop-nav .text-lg { font-size: 13px !important; }
            }
        </style>
    ''')
    
    nav_items = [
        ('menu_book', 'my_shelf', '/'),
        ('people', 'authors', '/authors'),
        ('layers', 'series', '/series'),
        ('local_offer', 'genres', '/genres'),
        ('trending_up', 'stats', '/statistics'),
        ('calendar_month', 'calendar', '/calendar'),
        ('settings', 'settings', '/settings')
    ]

    with ui.element('div').classes('w-full desktop-nav').style('display: none;'):
        with ui.element('header').classes('w-full bg-slate-800 text-white p-4 flex flex-row justify-between items-center shadow-md z-[100] fixed top-0 left-0 right-0'):
            with ui.row().classes('gap-6 font-medium items-center'):
                with ui.link('', '/').classes('flex items-center no-underline hover:opacity-80 transition-opacity nav-title-zone'):
                    ui.image('/static/favicon.png').classes('w-10 h-10 rounded-md object-cover shadow-sm bg-white p-0.5 mr-2')

                ui.link(t('my_shelf'), '#').classes('text-white hover:text-slate-300 no-underline text-lg').on('click', navigation_regal_klick)
                ui.link(t('authors'), '/authors').classes('text-white hover:text-slate-300 no-underline text-lg')
                ui.link(t('series'), '/series').classes('text-white hover:text-slate-300 no-underline text-lg')
                ui.link(t('genres'), '/genres').classes('text-white hover:text-slate-300 no-underline text-lg')
                ui.link(t('stats'), '/statistics').classes('text-white hover:text-slate-300 no-underline text-lg')
                ui.link(t('calendar'), '/calendar').classes('text-white hover:text-slate-300 no-underline text-lg')
                ui.link(t('settings'), '/settings').classes('text-white hover:text-slate-300 no-underline text-lg')
            
            with ui.row().classes('items-center gap-4'):
                if user_ui.get('buch_vorschlag_aktiv', False):
                    # HIER DIE KORREKTUR: Ausgelagerte Funktion aufrufen
                    v_modal, e_container = vorschlag_modal_erstellen(current_user_id, is_dark, bg_modal_card, text_modal_main, select_modal_prop)

                    ui.button(icon='casino', on_click=lambda: [e_container.clear(), v_modal.open()]) \
                        .props('round flat dense size=md') \
                        .classes('text-blue-400 hover:bg-slate-700') \
                        .tooltip(t('roll_book'))

                ui.button(icon='bookmark_add', on_click=quick_log_modal).props('round flat dense size=md').classes('text-emerald-400 hover:bg-slate-700').tooltip(t('quick_log_title'))

                def user_wechseln(e):
                    app.storage.user['aktiver_user_id'] = e.value
                    ui.run_javascript('window.location.reload()')

                ui.select(options=user_options, value=current_user_id, on_change=user_wechseln).props('dark dense options-dense borderless').classes('w-36 text-white text-sm font-bold bg-slate-700 px-2 py-1 rounded')
                ui.separator().props('vertical').classes('bg-slate-600 h-6')

                def sprache_wechseln(e):
                    app.storage.user['aktuelle_sprache'] = e.value
                    translations.aktuelle_sprache = e.value
                    ui.run_javascript('window.location.reload()')

                ui.select(options={'de': '🇩🇪 DE', 'en': '🇬🇧 EN'}, 
                        value=sys.modules[__name__].aktuelle_sprache, 
                        on_change=sprache_wechseln) \
                    .props('dark dense options-dense borderless').classes('w-20 text-white text-sm')

    with ui.element('div').classes('w-full mobile-nav-container').style('display: none;'):
        with ui.element('div').classes('fixed top-3 right-3 z-[101] flex items-center gap-2'):
            if user_ui.get('buch_vorschlag_aktiv', False):
                ui.button(icon='casino', on_click=global_vorschlag_modal_oeffnen) \
                    .props('round flat dense size=sm') \
                    .classes('text-blue-500 bg-white/80 dark:bg-slate-800/80 backdrop-blur-md shadow-sm border border-slate-200 dark:border-slate-700')

            with ui.button(icon='manage_accounts', on_click=lambda: steuerzentrum_modal.open()) \
                .props('flat dense size=sm') \
                .classes('text-slate-600 dark:text-slate-300 bg-white/80 dark:bg-slate-800/80 backdrop-blur-md shadow-sm border border-slate-200 dark:border-slate-700 px-2 rounded-full flex items-center gap-1'):
                
                ui.label(user_options.get(current_user_id, t('user'))).classes('text-[11px] font-semibold tracking-wide pr-1')

        with ui.dialog() as steuerzentrum_modal, ui.card().classes(f'w-full max-w-sm p-5 gap-4 rounded-2xl shadow-xl {bg_modal_card}'):
            with ui.row().classes('w-full justify-between items-center border-b border-slate-200 dark:border-slate-700 pb-2'):
                ui.label(t('settings')).classes(f'text-base font-bold {text_modal_main}')
                ui.button(icon='close', on_click=steuerzentrum_modal.close).props('flat round dense size=sm').classes('text-slate-400')

            with ui.column().classes('w-full gap-1'):
                ui.label(t('User')).classes('text-xs text-slate-400 uppercase tracking-wider font-semibold')
                
                def mobile_user_wechseln(e):
                    app.storage.user['aktiver_user_id'] = e.value
                    ui.run_javascript('window.location.reload()')
                
                ui.select(options=user_options, value=current_user_id, on_change=mobile_user_wechseln) \
                    .props(f'outlined dense {select_modal_prop}').classes('w-full text-sm')

            with ui.column().classes('w-full gap-1 mt-2'):
                ui.label(t('language')).classes('text-xs text-slate-400 uppercase tracking-wider font-semibold')
                
                def mobile_sprache_wechseln(e):
                    app.storage.user['aktuelle_sprache'] = e.value
                    translations.aktuelle_sprache = e.value
                    ui.run_javascript('window.location.reload()')

                ui.select(options={'de': '🇩🇪 Deutsch', 'en': '🇬🇧 English'}, 
                        value=sys.modules[__name__].aktuelle_sprache, 
                        on_change=mobile_sprache_wechseln) \
                    .props(f'outlined dense {select_modal_prop}').classes('w-full text-sm')

    with ui.element('div').classes('w-full mobile-nav-container').style('display: none;'):
        with ui.element('footer').classes('flex items-center justify-around px-1 pt-1 border-t shadow-lg fixed bottom-0 left-0 right-0 z-[100] footer-safe ' + 
                                         ('bg-slate-800 border-slate-700 text-white' if is_dark else 'bg-white border-slate-200 text-slate-700')):
            aktueller_pfad = ui.context.client.page.path
            
            for icon, lang_key, route in nav_items:
                ist_aktiv = False
                if route == '/':
                    ist_aktiv = (aktueller_pfad == '/') or (titel_key == 'my_shelf')
                else:
                    route_base = route.rstrip('s')
                    ist_aktiv = (lang_key in str(titel_key)) or (aktueller_pfad.startswith(route_base))
                
                with ui.column().classes('items-center justify-center gap-0.5 cursor-pointer flex-1 py-0.5 rounded-lg') \
                        .on('click', lambda r=route: ui.navigate.to(r)):
                    
                    icon_color = 'text-blue-500 scale-105' if ist_aktiv else 'text-slate-400 dark:text-slate-500'
                    text_color = 'text-blue-500 font-bold' if ist_aktiv else 'text-slate-400 dark:text-slate-400'
                    
                    ui.icon(icon, size='xs').classes(f'{icon_color} transition-transform')
                    ui.label(t(lang_key)).classes(f'text-[8px] tracking-tight {text_color} line-clamp-1 text-center')

            ui.button(icon='bookmark_add', on_click=quick_log_modal).props('flat round dense size=sm').classes('text-emerald-400 shrink-0 ml-1')

    with ui.element('div').classes('w-full p-4 md:p-6 max-w-7xl mx-auto pt-2 md:pt-24 bg-slate-50 dark:bg-slate-900 content-safe'):
        yield


# =========================================================================
# MAGIC SESSION-WRAPPER (Version 0.6.4 - Bereinigt ohne Authelia-Zwang)
# =========================================================================
class LayoutModuleWrapper:
    def __init__(self, wrapped_module):
        self._wrapped_module = wrapped_module

    @property
    def aktiver_user_id(self):
        return app.storage.user.get('aktiver_user_id', 1)

    @aktiver_user_id.setter
    def aktiver_user_id(self, value):
        app.storage.user['aktiver_user_id'] = value

    @property
    def aktuelle_sprache(self):
        return app.storage.user.get('aktuelle_sprache', 'de')

    @aktuelle_sprache.setter
    def aktuelle_sprache(self, value):
        app.storage.user['aktuelle_sprache'] = value

    def __getattr__(self, name):
        return getattr(self._wrapped_module, name)

sys.modules[__name__] = LayoutModuleWrapper(sys.modules[__name__])