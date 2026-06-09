import os
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
import import_export
import statistics
import authors
import reading_calendar
import settings
import series

# Globale Variablen für Filter und Paginierung
kachel_container = None
paginierungs_container = None
alle_buecher_cache = []
gefilterte_buecher_cache = []

# Einstellungen für die Seitenaufteilung
BUECHER_PRO_SEITE = 24  # Passt perfekt in ein 6er-Grid (4 Reihen)
aktuelle_seite = 1

def formatierte_daten_holen():
    """Holt die Rohdaten aus der DB und bereitet sie für das UI auf (inkl. Übersetzungen)."""
    rows = database.lade_buecher_aus_db(layout.aktiver_user_id)
    status_text_mapping = {'READING': t('reading'), 'READ': t('read'), 'UNREAD': t('unread')}

    ergebnis = []
    for r in rows:
        b_id = r[0]
        # OPTIMIERUNG: Wir prüfen den Pfad direkt hier im Speicher, statt die DB erneut anzufragen
        lokaler_pfad = os.path.join(COVER_DIR, f"{b_id}.jpg")
        cover_url = f"/covers/{b_id}.jpg" if os.path.exists(lokaler_pfad) else "/covers/placeholder.jpg"

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
            'cover_url': cover_url  # Direkt gecacht!
        })
    return ergebnis


def filter_anwenden():
    """Filtert den Cache im Arbeitsspeicher und beachtet den User-Ansichtsmodus."""
    global gefilterte_buecher_cache, aktuelle_seite
    
    suchtext = suchfeld.value.lower().strip()
    f_status = status_filter.value
    f_format = format_filter.value
    f_ownership = ownership_filter.value
    f_location = location_filter.value

    gefiltert = []
    for b in alle_buecher_cache:
        if suchtext and (suchtext not in b['title'].lower() and 
                         suchtext not in (b['subtitle'] or '').lower() and 
                         suchtext not in b['author'].lower()):
            continue
        if f_status != 'ALL' and b['status'] != f_status:
            continue
        if f_format != 'ALL' and b['format'] != f_format:
            continue
        if f_ownership != 'ALL' and b['ownership'] != f_ownership:
            continue
        if f_location != 'ALL' and b['location_id'] != f_location:
            continue
        gefiltert.append(b)

    gefilterte_buecher_cache = gefiltert
    aktuelle_seite = 1  # Zurück auf Seite 1 bei neuem Filter
    
    kacheln_rendern()
    paginierung_rendern()


def kacheln_rendern():
    """Zeichnet die Kacheln – entweder paginiert oder als Endlos-Liste."""
    if kachel_container is None:
        return

    # User-Einstellung aus der DB holen
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    
    # Weichenstellung: Seitenansicht oder Endlos?
    if user_ui['view_mode'] == 'INFINITE':
        buecher_anzeige = gefilterte_buecher_cache  # Komplettes Regal anzeigen
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
            with ui.card().classes('w-full max-w-[180px] h-auto p-0 overflow-hidden hover:shadow-lg transition-shadow duration-200 cursor-pointer flex flex-col relative mx-auto') \
                     .on('click', lambda b=buch: ui.navigate.to(f'/book/{b["id"]}')):
                
                with ui.element('div').classes('w-full aspect-[2/3] bg-slate-50 flex items-center justify-center overflow-hidden border-b border-slate-100'):
                    ui.image(buch['cover_url']).classes('w-full h-full object-cover')

                # Status Badge
                with ui.row().classes('absolute top-2 right-2 items-center gap-0.5 bg-white/90 backdrop-blur-sm px-1.5 py-0.5 rounded shadow-sm'):
                    ui.icon(buch['status_icon']).classes(f'text-[10px] {buch["status_color"]}')
                    ui.label(buch['status_text']).classes('text-[8px] font-bold text-slate-700 uppercase tracking-wider')

                # Textbereich (Jetzt ohne festes bg-white, damit umschalten klappt!)
                with ui.element('div').classes('w-full h-[90px] p-2 flex flex-col justify-between border-t border-slate-100 dark:border-slate-700'):
                    with ui.element('div').classes('flex flex-col gap-0.5'):
                        anzeige_titel = buch['title']
                        if ' (' in anzeige_titel and anzeige_titel.endswith(')'):
                            anzeige_titel = anzeige_titel.split(' (')[0]
                            
                        # REPARIERT: dark:text-slate-100 und dark:text-slate-300 hinzugefügt!
                        ui.label(anzeige_titel).classes('text-xs font-bold line-clamp-2 text-slate-800 dark:text-slate-100 leading-tight')
                        ui.label(buch['author']).classes('text-[11px] text-slate-500 dark:text-slate-300 line-clamp-1')
                    
                    with ui.element('div').classes('w-full pt-1 border-t border-slate-100 dark:border-slate-700 text-[10px] text-slate-400 min-h-[16px]'):
                        if buch['reihen_anzeige']:
                            # Auch die Reihe kriegt ein helleres Blau im Darkmode
                            ui.label(f" {buch['reihen_anzeige']}").classes('text-blue-600 dark:text-blue-400 font-medium line-clamp-1')


def paginierung_rendern():
    """Erstellt Seitenzahlen – wird bei 'INFINITE' automatisch unsichtbar."""
    global paginierungs_container
    if paginierungs_container is None:
        return

    paginierungs_container.clear()
    
    # Überprüfen, ob der Nutzer überhaupt die Seitenansicht will
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    if user_ui['view_mode'] == 'INFINITE':
        return  # Bei Endlos-Scrollen brauchen wir unten keine Buttons

    import math
    gesamtzahl_buecher = len(gefilterte_buecher_cache)
    seiten_anzahl = math.ceil(gesamtzahl_buecher / BUECHER_PRO_SEITE)

    if seiten_anzahl <= 1:
        return

    with paginierungs_container:
        def seite_wechseln(neue_seite):
            global aktuelle_seite
            aktuelle_seite = neue_seite
            kacheln_rendern()
            paginierung_rendern()
            ui.run_javascript('window.scrollTo({top: 0, behavior: "smooth"});')

        prev_btn = ui.button(icon='chevron_left', on_click=lambda: seite_wechseln(aktuelle_seite - 1)).props('flat dense')
        prev_btn.set_visibility(aktuelle_seite > 1)

        for i in range(1, seiten_anzahl + 1):
            ist_aktiv = (i == aktuelle_seite)
            ui.button(str(i), on_click=lambda idx=i: seite_wechseln(idx)) \
                .props('outline' if not ist_aktiv else 'flat') \
                .classes('px-3 py-1 font-bold text-xs rounded' + (' bg-slate-700 text-white' if ist_aktiv else ' text-slate-700'))

        next_btn = ui.button(icon='chevron_right', on_click=lambda: seite_wechseln(aktuelle_seite + 1)).props('flat dense')
        next_btn.set_visibility(aktuelle_seite < seiten_anzahl)

@ui.page('/')
def hauptseite():
    global kachel_container, paginierungs_container, alle_buecher_cache, suchfeld, status_filter, format_filter, ownership_filter, location_filter
    
    # Daten für aktuellen User frisch laden
    alle_buecher_cache = formatierte_daten_holen()
    regale = database.lade_alle_regale()

    with basis_layout('my_shelf'):
        
        # Header-Zeile
        with ui.row().classes('w-full justify-between items-center mb-4'):
            ui.label(t('my_shelf')).classes('text-2xl font-bold text-slate-700 dark:text-slate-100')
            ui.button(t('add_book'), on_click=lambda: ui.navigate.to('/add')).classes('bg-green-600 text-white')

        # --- SUCHLEISTE & EXPANDABLE FILTER (DARKMODE COMPATIBLE) ---
        # --- SUCHLEISTE & EXPANDABLE FILTER (FIXED FOR DARKMODE) ---
        # 1. Wir holen uns kurz den aktuellen Darkmode-Zustand aus der DB für diese Seite
        user_ui = database.lade_user_settings(layout.aktiver_user_id)
        is_dark = user_ui['dark_mode']
        dark_prop = 'dark popup-content-class="dark"' if is_dark else ''

        with ui.card().classes('w-full p-4 bg-slate-100 dark:bg-slate-800 shadow-sm border border-slate-200 dark:border-slate-700 mb-4 flex flex-col gap-3'):
            with ui.row().classes('w-full items-center gap-4'):
                
                # REPARIERT: .props('dark') steuert das komplette Innenleben des Feldes perfekt!
                suchfeld = ui.input(placeholder=t('search'), on_change=filter_anwenden)\
                    .classes('flex-1 px-3')\
                    .props(f'clearable icon=search outlined {"dark" if is_dark else ""}')
                
                def toggle_filter():
                    filter_sektion.visible = not filter_sektion.visible

                ui.button(icon='tune', color='slate', on_click=toggle_filter).classes('bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-200')
            
            # Ausklappbare Sektion
            with ui.row().classes('w-full gap-4 p-2 bg-slate-50 dark:bg-slate-900 rounded border border-slate-200 dark:border-slate-700 transition-all') as filter_sektion:
                filter_sektion.visible = False
                
                status_opts = {'ALL': '🔍 ' + t('status') + ': ' + t('none'), 'UNREAD': t('unread'), 'READING': t('reading'), 'READ': t('read')}
                # REPARIERT: bg-white entfernt, props() für Darkmode und Popup hinzugefügt
                status_filter = ui.select(options=status_opts, value='ALL', on_change=filter_anwenden)\
                    .classes('w-44 px-2 rounded dark:bg-slate-800')\
                    .props(f'outlined dense {dark_prop}')
                
                format_opts = {'ALL': '📱 ' + t('format') + ': ' + t('none'), 'PHYSICAL': t('PHYSICAL'), 'AUDIOBOOK': t('AUDIOBOOK'), 'EBOOK': t('EBOOK')}
                format_filter = ui.select(options=format_opts, value='ALL', on_change=filter_anwenden)\
                    .classes('w-44 px-2 rounded dark:bg-slate-800')\
                    .props(f'outlined dense {dark_prop}')
                
                own_opts = {'ALL': '🤝 ' + t('ownership') + ': ' + t('none'), 'OWNED': t('OWNED'), 'BORROWED': t('BORROWED'), 'LENT': t('LENT')}
                ownership_filter = ui.select(options=own_opts, value='ALL', on_change=filter_anwenden)\
                    .classes('w-44 px-2 rounded dark:bg-slate-800')\
                    .props(f'outlined dense {dark_prop}')
                
                regal_opts = {'ALL': '📍 ' + t('location') + ': ' + t('none')}
                for r_id, r_name in regale:
                    regal_opts[r_id] = r_name
                location_filter = ui.select(options=regal_opts, value='ALL', on_change=filter_anwenden)\
                    .classes('w-56 px-2 rounded dark:bg-slate-800')\
                    .props(f'outlined dense {dark_prop}')
        # Kachel-Grid Container initialisieren
        kachel_container = ui.row().classes('w-full grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6')
        
        # NEU: Container für die Seitennummerierung ganz unten am Regal
        paginierungs_container = ui.row().classes('w-full justify-center items-center gap-2 mt-8 mb-4')
        
        # Erste Berechnung & Zeichnung starten
        filter_anwenden()

ui.run(port=8080, title="Booktracker", reload=True)