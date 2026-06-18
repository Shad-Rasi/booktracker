import os
import asyncio
from datetime import datetime
from nicegui import app, ui
from starlette.staticfiles import StaticFiles

# 1. Ordner freigeben
COVER_DIR = os.path.join('data', 'covers')
os.makedirs(COVER_DIR, exist_ok=True)
AUTHOR_DIR = os.path.join('data', 'authors')
os.makedirs(AUTHOR_DIR, exist_ok=True)

app.add_static_files('/covers', COVER_DIR, follow_symlink=True)
app.add_static_files('/authors', AUTHOR_DIR, follow_symlink=True)
app.add_static_files('/static', 'static')
ui.add_head_html('<link rel="icon" type="image/png" href="/static/favicon.png">', shared=True)
ui.add_head_html('<link rel="manifest" href="/static/manifest.json">', shared=True)

ui.add_head_html('<link rel="apple-touch-icon" href="/static/app-icon.png">', shared=True)
ui.add_head_html('<meta name="apple-mobile-web-app-capable" content="yes">', shared=True)
ui.add_head_html('<meta name="apple-mobile-web-app-status-bar-style" content="default">', shared=True)


for route in app.routes:
    if route.path in ['/covers', '/authors'] and isinstance(route.app, StaticFiles):
        route.app.headers = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}

import database
database.init_db()

import book
import add_book
import layout
from layout import basis_layout 
import translations
from translations import t
import statistics
import authors
import reading_calendar
import settings
import series
import genres
import memory
from memory import REGAL_MEMORY

# Globale Variablen für UI-Referenzen und Cache
kachel_container = None
paginierungs_container = None
suchfeld = None
status_filter = None
format_filter = None
ownership_filter = None
location_filter = None
genre_filter = None
sort_filter = None
btn_reset = None

alle_buecher_cache = []
gefilterte_buecher_cache = []

REGAL_MEMORY = {
    'shelf_page': 1,
    'shelf_scroll': 0,
    'search_text': '',
    'filter_status': 'ALL',
    'filter_format': 'ALL',
    'filter_ownership': 'ALL',
    'filter_location': 'ALL',
    'filter_genre': 'ALL',  
    'filter_sort': 'title_asc'
}

BUECHER_PRO_SEITE = 24  
aktuelle_seite = 1


def sortiere_buecher_logik(buecher_liste, kriterium):
    if not buecher_liste: return []
    if kriterium == 'title_asc': return sorted(buecher_liste, key=lambda b: (b['title'] or "").lower())
    if kriterium == 'author_asc': return sorted(buecher_liste, key=lambda b: (b['author'] or "").lower())
    if kriterium == 'pages_desc': return sorted(buecher_liste, key=lambda b: b['pages'] or 0, reverse=True)
    if kriterium == 'pages_asc': return sorted(buecher_liste, key=lambda b: b['pages'] or 0)
    if kriterium == 'rating_desc': return sorted(buecher_liste, key=lambda b: b['rating'] or 0, reverse=True)
    return buecher_liste


def formatierte_daten_holen():
    rows = database.lade_buecher_aus_db(layout.aktiver_user_id)
    status_text_mapping = {'READING': t('reading'), 'READ': t('read'), 'UNREAD': t('unread')}
    existierende_covers = set(os.listdir(COVER_DIR))

    ergebnis = []
    for r in rows:
        b_id = r[0]
        cover_datei = f"{b_id}.jpg"
        cover_url = f"/covers/{cover_datei}" if cover_datei in existierende_covers else "/covers/placeholder.jpg"
        genres_des_buches = database.lade_genres_eines_buches(b_id, layout.aktiver_user_id)

        ergebnis.append({
            'id': b_id,
            'title': r[1],
            'author': r[2] if r[2] else t('unknown_author'),
            'isbn_13': r[3],
            'pages': r[4],
            'status': r[5] if r[5] else 'UNREAD',
            'status_icon': 'menu_book' if r[5] == 'READING' else ('check_circle' if r[5] == 'READ' else 'bookmark_border'),
            'status_color': 'text-amber-500' if r[5] == 'READING' else ('text-green-500' if r[5] == 'READ' else 'text-slate-400'),
            'status_text': status_text_mapping.get(r[5] if r[5] else 'UNREAD', t('unread')),
            'rating': r[6] if r[6] else 0,
            'special': bool(r[7]),
            'reihen_anzeige': f"{r[9]} - {t('series_num')} {r[10]}" if r[8] and r[9] else None,
            'subtitle': r[13],
            'format': r[23] if r[23] else 'PHYSICAL',
            'ownership': r[24] if r[24] else 'OWNED',       
            'location_id': r[26],
            'location_name': r[27] if r[27] else None,
            'genres': genres_des_buches,  
            'cover_url': cover_url
        })
    return ergebnis


def ist_ein_filter_aktiv():
    """Prüft sauber, ob aktuell irgendein Filter oder eine Suche aktiv ist."""
    return any([
        suchfeld.value != '' if suchfeld and suchfeld.value else False,
        status_filter.value != 'ALL' if status_filter and status_filter.value else False,
        format_filter.value != 'ALL' if format_filter and format_filter.value else False,
        ownership_filter.value != 'ALL' if ownership_filter and ownership_filter.value else False,
        location_filter.value != 'ALL' if location_filter and location_filter.value else False,
        genre_filter.value != 'ALL' if genre_filter and genre_filter.value else False
    ])


def filter_anwenden():
    global gefilterte_buecher_cache, aktuelle_seite
    if not suchfeld: return  # Falls UI noch nicht bereit ist
    
    memory.REGAL_MEMORY['shelf_page'] = 1
    aktuelle_seite = 1

    suchtext = suchfeld.value.lower().strip() if suchfeld.value else ""
    f_status = status_filter.value
    f_format = format_filter.value
    f_ownership = ownership_filter.value
    f_location = location_filter.value
    f_genre = genre_filter.value  
    f_sort = sort_filter.value

    # =========================================================================
    # JETZT REPARIERT: Werte direkt in das zentrale memory-Modul schreiben!
    # =========================================================================
    memory.REGAL_MEMORY['search_text'] = suchfeld.value if suchfeld.value else ""
    memory.REGAL_MEMORY['filter_status'] = f_status
    memory.REGAL_MEMORY['filter_format'] = f_format
    memory.REGAL_MEMORY['filter_ownership'] = f_ownership
    memory.REGAL_MEMORY['filter_location'] = f_location
    memory.REGAL_MEMORY['filter_genre'] = f_genre  
    memory.REGAL_MEMORY['filter_sort'] = f_sort
    # =========================================================================

    gefiltert = []
    for b in alle_buecher_cache:
        if suchtext and (suchtext not in b['title'].lower() and 
                         suchtext not in (b['subtitle'] or '').lower() and 
                         suchtext not in b['author'].lower() and
                         suchtext not in (b['reihen_anzeige'] or '').lower() and
                         suchtext not in (b['isbn_13'] or '').lower()):
            continue
        if f_status != 'ALL' and b['status'] != f_status:
            continue
        if f_format != 'ALL' and b['format'] != f_format:
            continue
        if f_ownership != 'ALL' and b['ownership'] != f_ownership:
            continue
        if f_location != 'ALL' and b['location_id'] != f_location:
            continue
        if f_genre != 'ALL' and f_genre not in b['genres']:
            continue
        gefiltert.append(b)

    gefilterte_buecher_cache = sortiere_buecher_logik(gefiltert, f_sort)
    kacheln_rendern()
    paginierung_rendern()

    # Sichtbarkeit des Reset-Buttons live umschalten
    if btn_reset and ui.context.client.has_socket_connection:
        btn_reset.set_visibility(ist_ein_filter_aktiv())


def alle_filter_zuruecksetzen():
    if not suchfeld: return
    suchfeld.value = ''
    status_filter.value = 'ALL'
    format_filter.value = 'ALL'
    ownership_filter.value = 'ALL'
    location_filter.value = 'ALL'
    genre_filter.value = 'ALL'
    sort_filter.value = 'title_asc'
    filter_anwenden()


def kacheln_rendern():
    if kachel_container is None: return
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    
    if user_ui['view_mode'] == 'INFINITE':
        buecher_anzeige = gefilterte_buecher_cache
    else:
        start_index = (aktuelle_seite - 1) * BUECHER_PRO_SEITE
        end_index = start_index + BUECHER_PRO_SEITE
        buecher_anzeige = gefilterte_buecher_cache[start_index:end_index]

    kachel_container.clear()
    with kachel_container:
        if not buecher_anzeige:
            with ui.card().classes('w-full p-8 text-center bg-slate-50 dark:bg-slate-900 col-span-full border border-dashed border-slate-200 dark:border-slate-700'):
                ui.label(t('empty_shelf')).classes('text-slate-500 text-lg')
            return

        for buch in buecher_anzeige:
            async def kachel_klick(b=buch):
                try:
                    scroll_y = await ui.run_javascript('window.pageYOffset || document.documentElement.scrollTop')
                    memory.REGAL_MEMORY['shelf_scroll'] = int(scroll_y)
                except Exception:
                    memory.REGAL_MEMORY['shelf_scroll'] = 0
                memory.REGAL_MEMORY['shelf_page'] = aktuelle_seite
                ui.navigate.to(f'/book/{b["id"]}')

            card_style = 'border: 1px dashed #ef4444;' if buch['ownership'] == 'GIVEN_AWAY' else ''
            cover_classes = 'w-full h-full object-cover opacity-40 grayscale transition-all' if buch['ownership'] == 'GIVEN_AWAY' else 'w-full h-full object-cover transition-all'

            with ui.card().classes('w-full h-auto p-0 overflow-hidden hover:shadow-lg transition-shadow duration-200 cursor-pointer flex flex-col relative').style(card_style).on('click', kachel_klick):
                with ui.element('div').classes('relative w-full aspect-[2/3] bg-slate-50 flex items-center justify-center overflow-hidden border-b border-slate-100'):
                    ui.image(buch['cover_url']).classes(cover_classes)
                    with ui.row().classes('absolute top-2 right-2 items-center gap-0.5 bg-white/90 backdrop-blur-sm px-1.5 py-0.5 rounded shadow-sm'):
                        ui.icon(buch['status_icon']).classes(f'text-[10px] {buch["status_color"]}')
                        ui.label(buch['status_text']).classes('text-[8px] font-bold text-slate-700 uppercase tracking-wider')

                    if buch['rating'] > 0:
                        with ui.row().classes('absolute bottom-1.5 right-1.5 items-center gap-px bg-slate-900/70 backdrop-blur-sm px-1 py-0.5 rounded shadow-sm text-amber-400'):
                            for star_idx in range(1, 6):
                                ui.icon('star' if star_idx <= buch['rating'] else 'star_border', size='11px')

                with ui.element('div').classes('w-full h-[106px] p-2 flex flex-col justify-between border-t border-slate-100 dark:border-slate-700'):
                    with ui.element('div').classes('flex flex-col gap-0.5'):
                        anzeige_titel = buch['title'].split(' (')[0] if ' (' in buch['title'] and buch['title'].endswith(')') else buch['title']
                        ui.label(anzeige_titel).classes('text-xs font-bold line-clamp-2 text-slate-800 dark:text-slate-100 leading-tight')
                        ui.label(buch['author']).classes('text-[11px] text-slate-500 dark:text-slate-300 line-clamp-1')
                    with ui.element('div').classes('w-full pt-1 border-t border-slate-100 dark:border-slate-700 flex flex-col justify-end min-h-[32px]'):
                        if buch['reihen_anzeige']:
                            ui.label(f" {buch['reihen_anzeige']}").classes('text-blue-600 dark:text-blue-400 font-medium line-clamp-1 text-[10px]')
                        if buch['ownership'] == 'GIVEN_AWAY':
                            ui.label(t('ownership_given_away')).classes('text-[9px] text-red-500 dark:text-red-400 font-bold tracking-wide uppercase mt-0.5')


def paginierung_rendern():
    global paginierungs_container
    if paginierungs_container is None: return
    paginierungs_container.clear()
    
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    if user_ui['view_mode'] == 'INFINITE': return

    import math
    seiten_anzahl = math.ceil(len(gefilterte_buecher_cache) / BUECHER_PRO_SEITE)
    if seiten_anzahl <= 1: return

    with paginierungs_container:
        def seite_wechseln(neue_seite):
            global aktuelle_seite
            aktuelle_seite = neue_seite
            memory.REGAL_MEMORY['shelf_page'] = neue_seite
            kacheln_rendern()
            paginierung_rendern()
            ui.run_javascript('window.scrollTo({top: 0, behavior: "smooth"});')

        ui.button(icon='chevron_left', on_click=lambda: seite_wechseln(aktuelle_seite - 1)).props('flat dense').set_visibility(aktuelle_seite > 1)
        for i in range(1, seiten_anzahl + 1):
            ist_aktiv = (i == aktuelle_seite)
            ui.button(str(i), on_click=lambda idx=i: seite_wechseln(idx)).props('outline' if not ist_aktiv else 'flat').classes('px-3 py-1 font-bold text-xs rounded' + (' bg-slate-700 text-white dark:bg-slate-600' if ist_aktiv else ' text-slate-700 dark:text-slate-300'))
        ui.button(icon='chevron_right', on_click=lambda: seite_wechseln(aktuelle_seite + 1)).props('flat dense').set_visibility(aktuelle_seite < seiten_anzahl)


@ui.page('/')
def hauptseite():
    global kachel_container, paginierungs_container, alle_buecher_cache, suchfeld, status_filter, format_filter, ownership_filter, location_filter, genre_filter, sort_filter, aktuelle_seite, btn_reset    
    
    alle_buecher_cache = formatierte_daten_holen()
    regale = database.lade_alle_regale()
    globale_genres = database.lade_alle_genres(layout.aktiver_user_id)
    aktuelle_seite = memory.REGAL_MEMORY['shelf_page']

    # =========================================================================
    # MULTI-USER ABSICHERUNG: Ungültige Filterwerte beim Nutzerwechsel abfangen
    # =========================================================================
    
    # 1. Standort/Regal validieren
    erlaubte_regal_ids = {r_id for r_id, _ in regale}
    if REGAL_MEMORY['filter_location'] != 'ALL' and REGAL_MEMORY['filter_location'] not in erlaubte_regal_ids:
        REGAL_MEMORY['filter_location'] = 'ALL'

    # 2. Genre validieren
    erlaubte_genre_namen = {g_name for _, g_name in globale_genres}
    if REGAL_MEMORY['filter_genre'] != 'ALL' and REGAL_MEMORY['filter_genre'] not in erlaubte_genre_namen:
        REGAL_MEMORY['filter_genre'] = 'ALL'
        
    # =========================================================================

    with basis_layout('my_shelf'):
        with ui.row().classes('w-full justify-between items-center mb-4'):
            ui.label(t('my_shelf')).classes('text-2xl font-bold text-slate-700 dark:text-slate-100')
            ui.button(t('add_book'), on_click=lambda: ui.navigate.to('/add')).classes('bg-green-600 text-white')

        user_ui = database.lade_user_settings(layout.aktiver_user_id)
        is_dark = user_ui['dark_mode']
        dark_prop = 'dark popup-content-class="dark"' if is_dark else ''

        with ui.card().classes('w-full p-4 bg-slate-100 dark:bg-slate-800 shadow-sm border border-slate-200 dark:border-slate-700 mb-4 flex flex-col gap-3'):
            
            with ui.card().classes('w-full p-4 bg-slate-100 dark:bg-slate-800 shadow-sm border border-slate-200 dark:border-slate-700 mb-4 flex flex-col gap-3'):
            
                # --- ZEILE 1: Suchfeld + Sortierungs- & Button-Zone ---
                # flex-col auf Mobile (Suchfeld oben, Sortier-Zeile darunter). md:flex-row auf Desktop (alles auf einer Linie)
                with ui.row().classes('w-full items-center gap-2 flex-col md:flex-row flex-nowrap'):
                    
                    # Suchfeld: Volle Breite auf Mobile (w-full), flex-1 auf Desktop
                    suchfeld = ui.input(placeholder=t('search'), value=memory.REGAL_MEMORY['search_text']).classes('w-full md:flex-1 px-1').props(f'clearable icon=search outlined debounce=200 {"dark" if is_dark else ""}')\
                        .on_value_change(lambda: filter_anwenden())

                    # --- HIER IST DIE NEUE MOBIL-REIHE ---
                    # Hält Dropdown und Buttons auf dem Handy starr nebeneinander (w-full flex-row no-wrap).
                    # Auf dem Desktop (md:w-auto md:p-0) löst sich die Box optisch auf.
                    with ui.row().classes('w-full md:w-auto items-center gap-2 flex-row flex-nowrap px-1'):
                        
                        # Sortierung: Nimmt auf dem Handy den restlichen Platz ein (flex-1), am PC eine feste Breite (md:w-56)
                        sort_opts = {'title_asc': '🔤 ' + t('sort_title'), 'author_asc': '✍️ ' + t('sort_author'), 'pages_desc': '📄 ' + t('sort_pages_desc'), 'pages_asc': '📄 ' + t('sort_pages_asc'), 'rating_desc': '⭐ ' + t('sort_rating')}
                        sort_filter = ui.select(options=sort_opts, value=memory.REGAL_MEMORY['filter_sort'], on_change=lambda: filter_anwenden()).classes('flex-1 md:w-56').props(f'outlined dense {dark_prop}')

                        # REPARIERT: Tooltip wird jetzt über t() dynamisch übersetzt
                        btn_reset = ui.button(icon='filter_alt_off', on_click=alle_filter_zuruecksetzen).props('flat round color="negative"').tooltip(t('clear_filters'))
                        btn_reset.set_visibility(ist_ein_filter_aktiv())
                        
                        # Der Zahnrad-Button für die erweiterten Filter
                        ui.button(icon='tune', color='slate', on_click=lambda: setattr(filter_sektion, 'visible', not filter_sektion.visible)).classes('bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200 shrink-0')
                
            # --- ZEILE 2: Die erweiterten Filter (Status, Format etc.) ---
            with ui.row().classes('w-full gap-4 p-2 bg-slate-50 dark:bg-slate-900 rounded border border-slate-200 dark:border-slate-700 transition-all flex-wrap') as filter_sektion:
                filter_sektion.visible = any([memory.REGAL_MEMORY['filter_status'] != 'ALL', REGAL_MEMORY['filter_format'] != 'ALL', REGAL_MEMORY['filter_ownership'] != 'ALL', REGAL_MEMORY['filter_location'] != 'ALL', REGAL_MEMORY['filter_genre'] != 'ALL'])
                
                status_opts = {'ALL': '🔍 ' + t('status') + ': ' + t('none'), 'UNREAD': t('unread'), 'READING': t('reading'), 'READ': t('read')}
                status_filter = ui.select(options=status_opts, value=memory.REGAL_MEMORY['filter_status'], on_change=lambda: filter_anwenden()).classes('flex-1 min-w-[180px] px-1').props(f'outlined dense {dark_prop}')
                
                format_opts = {'ALL': '📱 ' + t('format') + ': ' + t('none'), 'PHYSICAL': t('PHYSICAL'), 'AUDIOBOOK': t('AUDIOBOOK'), 'EBOOK': t('EBOOK')}
                format_filter = ui.select(options=format_opts, value=memory.REGAL_MEMORY['filter_format'], on_change=lambda: filter_anwenden()).classes('flex-1 min-w-[180px] px-1').props(f'outlined dense {dark_prop}')
                
                own_opts = {'ALL': '🤝 ' + t('ownership') + ': ' + t('none'), 'OWNED': t('OWNED'), 'BORROWED': t('BORROWED'), 'LENT': t('LENT'), 'GIVEN_AWAY': t('ownership_given_away')}
                ownership_filter = ui.select(options=own_opts, value=memory.REGAL_MEMORY['filter_ownership'], on_change=lambda: filter_anwenden()).classes('flex-1 min-w-[180px] px-1').props(f'outlined dense {dark_prop}')
                
                regale_opts = {'ALL': '📍 ' + t('location') + ': ' + t('none')}
                for r_id, r_name in regale: regale_opts[r_id] = r_name
                location_filter = ui.select(options=regale_opts, value=memory.REGAL_MEMORY['filter_location'], on_change=lambda: filter_anwenden()).classes('flex-1 min-w-[180px] px-1').props(f'outlined dense {dark_prop}')

                genre_opts = {'ALL': '🏷️ ' + t('manage_genres') + ': ' + t('none')}
                for g_id, g_name in globale_genres: genre_opts[g_name] = g_name
                genre_filter = ui.select(options=genre_opts, value=memory.REGAL_MEMORY['filter_genre'], on_change=lambda: filter_anwenden()).classes('flex-1 min-w-[180px] px-1').props(f'outlined dense with-input {dark_prop}')
        
        kachel_container = ui.element('div').classes('w-full grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 sm:gap-6')
        paginierungs_container = ui.row().classes('w-full justify-center items-center gap-2 mt-8 mb-4')

        # Filter initial triggern
        filter_anwenden()

        async def initialisiere_scroll_stand():
            if btn_reset:
                btn_reset.set_visibility(ist_ein_filter_aktiv())

            gespeicherter_scrollstand = REGAL_MEMORY['shelf_scroll']
            if gespeicherter_scrollstand > 0:
                await asyncio.sleep(0.1)
                await ui.run_javascript(f'window.scrollTo(0, {gespeicherter_scrollstand});')
            REGAL_MEMORY['shelf_scroll'] = 0

        ui.context.client.on_connect(initialisiere_scroll_stand)

from fastapi import Request

# === PROXY MIDDLEWARE FÜR NICEGUI ===
## If you use a proxy (e.g. authelia), here you check if the proxy user is in booktracker
## If the user exists, the user will be chosen automatically
@app.middleware("http")
async def proxy_header_middleware(request: Request, call_next):
    # Wir holen den Header direkt aus dem echten HTTP-Request
    proxy_user = request.headers.get("remote-user") or request.headers.get("Remote-User")
    
    if proxy_user:
        proxy_user = proxy_user.strip().lower()
        try:
            alle_user = database.lade_alle_user()
            for u_id, u_name in alle_user:
                if u_name.strip().lower() == proxy_user:
                   
                    request.session['aktiver_user_id'] = u_id
                    
                    app.storage.user['aktiver_user_id'] = u_id
                    break
        except Exception as e:
            print(f"Fehler in Middleware-Datenbankabfrage: {e}")

    response = await call_next(request)
    return response


ui.run(
    port=int(os.getenv("PORT", 8080)),
    title="Booktracker",
    favicon="📚",
    reload=True,
    storage_secret=os.getenv("STORAGE_SECRET", "change_me_in_production"),
)