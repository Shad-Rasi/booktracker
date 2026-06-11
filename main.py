import os
import asyncio
from datetime import datetime
from nicegui import app, ui
from starlette.staticfiles import StaticFiles

# 1. ERST: Ordner erstellen und für NiceGUI freigeben
COVER_DIR = os.path.join('data', 'covers')
os.makedirs(COVER_DIR, exist_ok=True)

AUTHOR_DIR = os.path.join('data', 'authors')
os.makedirs(AUTHOR_DIR, exist_ok=True)

app.add_static_files('/covers', COVER_DIR, follow_symlink=True)
app.add_static_files('/authors', AUTHOR_DIR, follow_symlink=True)

# CRITICAL CACHE-FIX
for route in app.routes:
    if route.path in ['/covers', '/authors'] and isinstance(route.app, StaticFiles):
        route.app.headers = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}

# 2. DANN: Deine Datenbank initialisieren
import database
database.init_db()

# 3. ERST JETZT: Die Seiten-Module importieren
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

# Globale Variablen für Filter und Paginierung
kachel_container = None
paginierungs_container = None
alle_buecher_cache = []
gefilterte_buecher_cache = []

# ERWEITERT: Jetzt mit Gedächtnis für das Genre-Filter!
REGAL_MEMORY = {
    'shelf_page': 1,
    'shelf_scroll': 0,
    'search_text': '',
    'filter_status': 'ALL',
    'filter_format': 'ALL',
    'filter_ownership': 'ALL',
    'filter_location': 'ALL',
    'filter_genre': 'ALL',  # NEU
    'filter_sort': 'title_asc'
}

# Einstellungen für die Seitenaufteilung
BUECHER_PRO_SEITE = 24  # Passt perfekt in ein 6er-Grid (4 Reihen)
aktuelle_seite = 1


def sortiere_buecher_logik(buecher_liste, kriterium):
    """Sortiert die vorbereitete Bücherliste im RAM nach dem gewählten Kriterium."""
    if not buecher_liste:
        return []

    if kriterium == 'title_asc':
        return sorted(buecher_liste, key=lambda b: (b['title'] or "").lower())
    elif kriterium == 'author_asc':
        return sorted(buecher_liste, key=lambda b: (b['author'] or "").lower())
    elif kriterium == 'pages_desc':
        return sorted(buecher_liste, key=lambda b: b['pages'] or 0, reverse=True)
    elif kriterium == 'pages_asc':
        return sorted(buecher_liste, key=lambda b: b['pages'] or 0)
    elif kriterium == 'rating_desc':
        return sorted(buecher_liste, key=lambda b: b['rating'] or 0, reverse=True)
    
    return buecher_liste


def formatierte_daten_holen():
    """Holt die Rohdaten aus der DB und bereitet sie für das UI auf (inkl. n:m Genres)."""
    rows = database.lade_buecher_aus_db(layout.aktiver_user_id)
    status_text_mapping = {'READING': t('reading'), 'READ': t('read'), 'UNREAD': t('unread')}

    ergebnis = []
    for r in rows:
        b_id = r[0]
        lokaler_pfad = os.path.join(COVER_DIR, f"{b_id}.jpg")
        cover_url = f"/covers/{b_id}.jpg" if os.path.exists(lokaler_pfad) else "/covers/placeholder.jpg"

        # NEU: Holt die n:m Verknüpfungen für den RAM-Filter
        genres_des_buches = database.lade_genres_eines_buches(b_id)

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
            'genres': genres_des_buches,  # NEU
            'cover_url': cover_url
        })
    return ergebnis


def filter_anwenden(behalte_seite=False):
    """Filtert den Cache im Arbeitsspeicher und sichert den Zustand im REGAL_MEMORY."""
    global gefilterte_buecher_cache, aktuelle_seite
    
    # Aktuelle Werte aus der UI auslesen
    suchtext = suchfeld.value.lower().strip() if suchfeld.value else ""
    f_status = status_filter.value
    f_format = format_filter.value
    f_ownership = ownership_filter.value
    f_location = location_filter.value
    f_genre = genre_filter.value  # NEU
    f_sort = sort_filter.value

    # Sicherung des Filterzustands ins App-Gedächtnis
    REGAL_MEMORY['search_text'] = suchfeld.value if suchfeld.value else ""
    REGAL_MEMORY['filter_status'] = f_status
    REGAL_MEMORY['filter_format'] = f_format
    REGAL_MEMORY['filter_ownership'] = f_ownership
    REGAL_MEMORY['filter_location'] = f_location
    REGAL_MEMORY['filter_genre'] = f_genre  # NEU
    REGAL_MEMORY['filter_sort'] = f_sort

    gefiltert = []
    for b in alle_buecher_cache:
        if suchtext and (suchtext not in b['title'].lower() and 
                         suchtext not in (b['subtitle'] or '').lower() and 
                         suchtext not in b['author'].lower() and
                         suchtext not in (b['reihen_anzeige'] or '').lower()):
            continue
        if f_status != 'ALL' and b['status'] != f_status:
            continue
        if f_format != 'ALL' and b['format'] != f_format:
            continue
        if f_ownership != 'ALL' and b['ownership'] != f_ownership:
            continue
        if f_location != 'ALL' and b['location_id'] != f_location:
            continue
        # NEU: n:m Match-Prüfung in der String-Liste des Buches
        if f_genre != 'ALL' and f_genre not in b['genres']:
            continue
        gefiltert.append(b)

    # Sortierung anwenden
    gefilterte_buecher_cache = sortiere_buecher_logik(gefiltert, f_sort)
    
    # Seitennummerierung synchronisieren
    if behalte_seite:
        aktuelle_seite = REGAL_MEMORY['shelf_page']
    else:
        aktuelle_seite = 1
        REGAL_MEMORY['shelf_page'] = 1
    
    kacheln_rendern()
    paginierung_rendern()


def kacheln_rendern():
    """Zeichnet die Kacheln – entweder paginiert oder als Endlos-Liste."""
    if kachel_container is None:
        return

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
            with ui.card().classes('w-full p-8 text-center bg-slate-50 col-span-full'):
                ui.label(t('empty_shelf')).classes('text-slate-500 text-lg')
            return

        for buch in buecher_anzeige:
            async def kachel_klick(b=buch):
                try:
                    scroll_y = await ui.run_javascript('window.pageYOffset || document.documentElement.scrollTop')
                    REGAL_MEMORY['shelf_scroll'] = int(scroll_y)
                except Exception:
                    REGAL_MEMORY['shelf_scroll'] = 0
                
                REGAL_MEMORY['shelf_page'] = aktuelle_seite
                ui.navigate.to(f'/book/{b["id"]}')

            if buch['ownership'] == 'GIVEN_AWAY':
                card_style = 'border: 1px dashed #ef4444;'
                cover_classes = 'w-full h-full object-cover opacity-40 grayscale transition-all'
            else:
                card_style = ''
                cover_classes = 'w-full h-full object-cover transition-all'

            with ui.card().classes('w-full max-w-[180px] h-auto p-0 overflow-hidden hover:shadow-lg transition-shadow duration-200 cursor-pointer flex flex-col relative mx-auto') \
                     .style(card_style).on('click', kachel_klick):
                
                with ui.element('div').classes('relative w-full aspect-[2/3] bg-slate-50 flex items-center justify-center overflow-hidden border-b border-slate-100'):
                    ui.image(buch['cover_url']).classes(cover_classes)

                    # Status Badge (Oben rechts)
                    with ui.row().classes('absolute top-2 right-2 items-center gap-0.5 bg-white/90 backdrop-blur-sm px-1.5 py-0.5 rounded shadow-sm--'):
                        ui.icon(buch['status_icon']).classes(f'text-[10px] {buch["status_color"]}')
                        ui.label(buch['status_text']).classes('text-[8px] font-bold text-slate-700 uppercase tracking-wider')

                    if buch['rating'] > 0:
                        with ui.row().classes('absolute bottom-1.5 right-1.5 items-center gap-px bg-slate-900/70 backdrop-blur-sm px-1 py-0.5 rounded shadow-sm text-amber-400'):
                            for star_idx in range(1, 6):
                                star_icon = 'star' if star_idx <= buch['rating'] else 'star_border'
                                ui.icon(star_icon, size='11px')

                # Textbereich
                with ui.element('div').classes('w-full h-[106px] p-2 flex flex-col justify-between border-t border-slate-100 dark:border-slate-700'):
                    with ui.element('div').classes('flex flex-col gap-0.5'):
                        anzeige_titel = buch['title']
                        if ' (' in anzeige_titel and anzeige_titel.endswith(')'):
                            anzeige_titel = anzeige_titel.split(' (')[0]
                            
                        ui.label(anzeige_titel).classes('text-xs font-bold line-clamp-2 text-slate-800 dark:text-slate-100 leading-tight')
                        ui.label(buch['author']).classes('text-[11px] text-slate-500 dark:text-slate-300 line-clamp-1')
                    
                    with ui.element('div').classes('w-full pt-1 border-t border-slate-100 dark:border-slate-700 flex flex-col justify-end min-h-[32px]'):
                        if buch['reihen_anzeige']:
                            ui.label(f" {buch['reihen_anzeige']}").classes('text-blue-600 dark:text-blue-400 font-medium line-clamp-1 text-[10px]')
                        
                        if buch['ownership'] == 'GIVEN_AWAY':
                            ui.label(t('ownership_given_away')).classes('text-[9px] text-red-500 dark:text-red-400 font-bold tracking-wide uppercase mt-0.5')


def paginierung_rendern():
    """Erstellt Seitenzahlen – wird bei 'INFINITE' automatisch unsichtbar."""
    global paginierungs_container
    if paginierungs_container is None:
        return

    paginierungs_container.clear()
    
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    if user_ui['view_mode'] == 'INFINITE':
        return

    import math
    gesamtzahl_buecher = len(gefilterte_buecher_cache)
    seiten_anzahl = math.ceil(gesamtzahl_buecher / BUECHER_PRO_SEITE)

    if seiten_anzahl <= 1:
        return

    with paginierungs_container:
        def seite_whitespace(neue_seite):
            global aktuelle_seite
            aktuelle_seite = neue_seite
            REGAL_MEMORY['shelf_page'] = neue_seite
            kacheln_rendern()
            paginierung_rendern()
            ui.run_javascript('window.scrollTo({top: 0, behavior: "smooth"});')

        prev_btn = ui.button(icon='chevron_left', on_click=lambda: seite_whitespace(aktuelle_seite - 1)).props('flat dense')
        prev_btn.set_visibility(aktuelle_seite > 1)

        for i in range(1, seiten_anzahl + 1):
            ist_aktiv = (i == aktuelle_seite)
            ui.button(str(i), on_click=lambda idx=i: seite_whitespace(idx)) \
                .props('outline' if not ist_aktiv else 'flat') \
                .classes('px-3 py-1 font-bold text-xs rounded' + (' bg-slate-700 text-white' if ist_aktiv else ' text-slate-700'))

        next_btn = ui.button(icon='chevron_right', on_click=lambda: seite_whitespace(aktuelle_seite + 1)).props('flat dense')
        next_btn.set_visibility(aktuelle_seite < seiten_anzahl)


@ui.page('/')
def hauptseite():
    global kachel_container, paginierungs_container, alle_buecher_cache, suchfeld, status_filter, format_filter, ownership_filter, location_filter, genre_filter, sort_filter, aktuelle_seite
    
    alle_buecher_cache = formatierte_daten_holen()
    regale = database.lade_alle_regale()
    
    # NEU: Alle globalen Genres für die Filteroptionen laden
    globale_genres = database.lade_alle_genres(layout.aktiver_user_id)

    # Seitenzahl aus dem persistenten RAM-Gedächtnis laden
    aktuelle_seite = REGAL_MEMORY['shelf_page']

    with basis_layout('my_shelf'):
        
        # Header-Zeile
        with ui.row().classes('w-full justify-between items-center mb-4'):
            ui.label(t('my_shelf')).classes('text-2xl font-bold text-slate-700 dark:text-slate-100')
            ui.button(t('add_book'), on_click=lambda: ui.navigate.to('/add')).classes('bg-green-600 text-white')

        # --- SUCHLEISTE & EXPANDABLE FILTER ---
        user_ui = database.lade_user_settings(layout.aktiver_user_id)
        is_dark = user_ui['dark_mode']
        dark_prop = 'dark popup-content-class="dark"' if is_dark else ''

        with ui.card().classes('w-full p-4 bg-slate-100 dark:bg-slate-800 shadow-sm border border-slate-200 dark:border-slate-700 mb-4 flex flex-col gap-3'):
            
            filter_sektion = None

            # REFRESHABLE FILTER-ZEILE
            @ui.refreshable
            def filter_kontroll_zeile_rendern():
                filter_aktiv = any([
                    REGAL_MEMORY['search_text'] != '',
                    REGAL_MEMORY['filter_status'] != 'ALL',
                    REGAL_MEMORY['filter_format'] != 'ALL',
                    REGAL_MEMORY['filter_ownership'] != 'ALL',
                    REGAL_MEMORY['filter_location'] != 'ALL',
                    REGAL_MEMORY['filter_genre'] != 'ALL'
                ])
                
                with ui.row().classes('w-full items-center gap-3 no-wrap'):
                    global suchfeld, sort_filter
                    
                    suchfeld = ui.input(placeholder=t('search'), value=REGAL_MEMORY['search_text'], 
                                        on_change=lambda e: [filter_anwenden(), filter_kontroll_zeile_rendern.refresh()])\
                        .classes('flex-1 px-1')\
                        .props(f'clearable icon=search outlined {"dark" if is_dark else ""}')
                    
                    sort_opts = {
                        'title_asc': '🔤 ' + t('sort_title'),
                        'author_asc': '✍️ ' + t('sort_author'),
                        'pages_desc': '📄 ' + t('sort_pages_desc'),
                        'pages_asc': '📄 ' + t('sort_pages_asc'),
                        'rating_desc': '⭐ ' + t('sort_rating')
                    }
                    
                    sort_filter = ui.select(options=sort_opts, value=REGAL_MEMORY['filter_sort'], on_change=lambda: filter_anwenden())\
                        .classes('w-48 px-1')\
                        .props(f'outlined dense {dark_prop}')
                    
                    # REPARIERT: Funktion heißt jetzt einheitlich 'hauptseite_filter_dropdowns_synchronisieren'
                    if filter_aktiv:
                        def alle_filter_zuruecksetzen():
                            REGAL_MEMORY['search_text'] = ''
                            REGAL_MEMORY['filter_status'] = 'ALL'
                            REGAL_MEMORY['filter_format'] = 'ALL'
                            REGAL_MEMORY['filter_ownership'] = 'ALL'
                            REGAL_MEMORY['filter_location'] = 'ALL'
                            REGAL_MEMORY['filter_genre'] = 'ALL'
                            filter_anwenden()
                            hauptseite_filter_dropdowns_synchronisieren()
                            filter_kontroll_zeile_rendern.refresh()

                        ui.button(icon='filter_alt_off', on_click=alle_filter_zuruecksetzen)\
                            .props('flat round color="negative"')\
                            .tooltip(t('clear_filters') if 'clear_filters' in translations.TRANSLATIONS[translations.aktuelle_sprache] else 'Alle Filter zurücksetzen')
                    
                    def toggle_filter():
                        if filter_sektion:
                            filter_sektion.visible = not filter_sektion.visible

                    ui.button(icon='tune', color='slate', on_click=toggle_filter).classes('bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200')

            # REPARIERT: Name matched jetzt exakt mit dem Button-Aufruf weiter oben
            def hauptseite_filter_dropdowns_synchronisieren():
                status_filter.value = 'ALL'
                format_filter.value = 'ALL'
                ownership_filter.value = 'ALL'
                location_filter.value = 'ALL'
                genre_filter.value = 'ALL'
                suchfeld.value = ''

            filter_kontroll_zeile_rendern()
            
            # Ausklappbare Sektion
            with ui.row().classes('w-full gap-4 p-2 bg-slate-50 dark:bg-slate-900 rounded border border-slate-200 dark:border-slate-700 transition-all flex-wrap') as filter_sektion:
                erweiterte_filter_aktiv = any([
                    REGAL_MEMORY['filter_status'] != 'ALL',
                    REGAL_MEMORY['filter_format'] != 'ALL',
                    REGAL_MEMORY['filter_ownership'] != 'ALL',
                    REGAL_MEMORY['filter_location'] != 'ALL',
                    REGAL_MEMORY['filter_genre'] != 'ALL'
                ])
                filter_sektion.visible = erweiterte_filter_aktiv
                
                status_opts = {'ALL': '🔍 ' + t('status') + ': ' + t('none'), 'UNREAD': t('unread'), 'READING': t('reading'), 'READ': t('read')}
                status_filter = ui.select(options=status_opts, value=REGAL_MEMORY['filter_status'], 
                                          on_change=lambda: [filter_anwenden(), filter_kontroll_zeile_rendern.refresh()])\
                    .classes('flex-1 min-w-[180px] px-1')\
                    .props(f'outlined dense {dark_prop}')
                
                format_opts = {'ALL': '📱 ' + t('format') + ': ' + t('none'), 'PHYSICAL': t('PHYSICAL'), 'AUDIOBOOK': t('AUDIOBOOK'), 'EBOOK': t('EBOOK')}
                format_filter = ui.select(options=format_opts, value=REGAL_MEMORY['filter_format'], 
                                          on_change=lambda: [filter_anwenden(), filter_kontroll_zeile_rendern.refresh()])\
                    .classes('flex-1 min-w-[180px] px-1')\
                    .props(f'outlined dense {dark_prop}')
                
                own_opts = {'ALL': '🤝 ' + t('ownership') + ': ' + t('none'), 'OWNED': t('OWNED'), 'BORROWED': t('BORROWED'), 'LENT': t('LENT'), 'GIVEN_AWAY': t('ownership_given_away')}
                ownership_filter = ui.select(options=own_opts, value=REGAL_MEMORY['filter_ownership'], 
                                             on_change=lambda: [filter_anwenden(), filter_kontroll_zeile_rendern.refresh()])\
                    .classes('flex-1 min-w-[180px] px-1')\
                    .props(f'outlined dense {dark_prop}')
                
                regale_opts = {'ALL': '📍 ' + t('location') + ': ' + t('none')}
                for r_id, r_name in regale:
                    regale_opts[r_id] = r_name
                location_filter = ui.select(options=regale_opts, value=REGAL_MEMORY['filter_location'], 
                                            on_change=lambda: [filter_anwenden(), filter_kontroll_zeile_rendern.refresh()])\
                    .classes('flex-1 min-w-[180px] px-1')\
                    .props(f'outlined dense {dark_prop}')

                genre_opts = {'ALL': '🏷️ ' + t('manage_genres') + ': ' + t('none')}
                for g_id, g_name in globale_genres:
                    genre_opts[g_name] = g_name
                
                genre_filter = ui.select(options=genre_opts, value=REGAL_MEMORY['filter_genre'], 
                                           on_change=lambda: [filter_anwenden(), filter_kontroll_zeile_rendern.refresh()])\
                    .classes('flex-1 min-w-[180px] px-1')\
                    .props(f'outlined dense with-input {dark_prop}')
        
        # Kachel-Grid Container initialisieren
        kachel_container = ui.row().classes('w-full grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6')
        
        # Container für die Seitennummerierung ganz unten am Regal
        paginierungs_container = ui.row().classes('w-full justify-center items-center gap-2 mt-8 mb-4')

        # Synchronisations-Logik beim Betreten der Seite
        async def initialisiere_regal_stand():
            global aktuelle_seite
            try:
                nav_type = await ui.run_javascript('performance.navigation.type')
                kam_ueber_zurueck = (nav_type == 2)
            except Exception:
                kam_ueber_zurueck = True

            filter_anwenden(behalte_seite=True)
            
            # Scrollstand wiederherstellen
            gespeicherter_scrollstand = REGAL_MEMORY['shelf_scroll']
            if gespeicherter_scrollstand > 0:
                await asyncio.sleep(0.15)
                await ui.run_javascript(f'window.scrollTo(0, {gespeicherter_scrollstand});')
                
            REGAL_MEMORY['shelf_scroll'] = 0

        ui.context.client.on_connect(initialisiere_regal_stand)

ui.run(port=8080, title="Booktracker", reload=True, storage_secret="dein_sicheres_geheimnis_hier")