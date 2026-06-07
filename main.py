import os
from datetime import datetime
from nicegui import ui

import database
import book
import add_book
import layout
from layout import basis_layout 
import translations
from translations import t

database.init_db()

# Globale Container-Referenz, um den Inhalt bei Filtern live auszutauschen
kachel_container = None
alle_buecher_cache = []

def formatierte_daten_holen():
    """Holt die Rohdaten aus der DB und bereitet sie für das UI auf (inkl. Übersetzungen)."""
    # Holt die ID dynamisch aus dem Layout-Zustand!
    rows = database.lade_buecher_aus_db(layout.aktiver_user_id)
    
    status_text_mapping = {'READING': t('reading'), 'READ': t('read'), 'UNREAD': t('unread')}

    return [{
        'id': r[0],
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
        'reihe_anzeige': f"{r[9]} ({t('series_num')} {r[10]})" if r[8] and r[9] else None,
        'subtitle': r[13],
        'format': r[23] if r[23] else 'PHYSICAL',
        'ownership': r[24] if r[24] else 'OWNED',
        'location_id': r[26],
        'location_name': r[27] if r[27] else None
    } for r in rows]


def filter_anwenden():
    """Filtert den Cache im Arbeitsspeicher und zeichnet die Kacheln neu."""
    if kachel_container is None:
        return

    suchtext = suchfeld.value.lower().strip()
    f_status = status_filter.value
    f_format = format_filter.value
    f_ownership = ownership_filter.value
    f_location = location_filter.value

    # Filter-Logik
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

    # UI-Refresh im Container
    kachel_container.clear()
    with kachel_container:
        if not gefiltert:
            with ui.card().classes('w-full p-8 text-center bg-slate-50 col-span-full'):
                ui.label(t('empty_shelf')).classes('text-slate-500 text-lg')
            return

        for buch in gefiltert:
            with ui.card().classes('w-full h-[340px] p-0 overflow-hidden hover:shadow-lg transition-shadow duration-200 cursor-pointer flex flex-col relative') \
                 .on('click', lambda b=buch: ui.navigate.to(f'/book/{b["id"]}')):
                
                ui.image(f'https://picsum.photos/seed/{buch["id"]}/300/400').classes('w-full h-48 object-cover')

                # Status Badge
                with ui.row().classes('absolute top-3 right-3 items-center gap-1 bg-white/90 backdrop-blur-sm px-2 py-1 rounded-md shadow-sm'):
                    ui.icon(buch['status_icon']).classes(f'text-sm {buch["status_color"]}')
                    ui.label(buch['status_text']).classes('text-[10px] font-bold text-slate-700 uppercase tracking-wider')

                # Textbereich
                with ui.element('div').classes('p-4 flex flex-col gap-1'):
                    ui.label(buch['title']).classes('text-base font-bold line-clamp-1 text-slate-800 leading-tight')
                    ui.label(buch['author']).classes('text-sm text-slate-500 line-clamp-1')
                    
                    if buch['location_name']:
                        ui.label(f"📍 {buch['location_name']}").classes('text-xs text-slate-400 line-clamp-1 mt-1')
                    elif buch['reihe_anzeige']:
                        ui.label(buch['reihe_anzeige']).classes('text-xs text-blue-600 font-medium line-clamp-1 mt-1')
                    else:
                        ui.label(f"{buch['pages']} {t('pages')}").classes('text-xs text-slate-400 mt-1')


@ui.page('/')
def hauptseite():
    global kachel_container, alle_buecher_cache, suchfeld, status_filter, format_filter, ownership_filter, location_filter
    
    # Daten für aktuellen User frisch laden
    alle_buecher_cache = formatierte_daten_holen()
    regale = database.lade_alle_regale()

    with basis_layout('my_shelf'):
        
        # Header-Zeile mit Titel und Hinzufügen-Button
        with ui.row().classes('w-full justify-between items-center mb-4'):
            ui.label(t('my_shelf')).classes('text-2xl font-bold text-slate-700')
            ui.button(t('add_book'), on_click=lambda: ui.navigate.to('/add')) \
                .classes('bg-green-600 text-white')

        # --- REICHWEITEN-SUCHE & EXPANDABLE FILTER ---
        with ui.card().classes('w-full p-4 bg-slate-100 shadow-sm border border-slate-200 mb-4 flex flex-col gap-3'):
            with ui.row().classes('w-full items-center gap-4'):
                suchfeld = ui.input(placeholder=t('search'), on_change=filter_anwenden).classes('flex-1 bg-white px-3 rounded border').props('clearable icon=search')
                
                # EXPLIZITE FUNKTION: Schaltet die Sichtbarkeit sauber um
                def toggle_filter():
                    filter_sektion.visible = not filter_sektion.visible

                ui.button(icon='tune', color='slate', on_click=toggle_filter) \
                    .classes('bg-slate-200 text-slate-700')
            
            # Die ausklappbare Sektion - startet direkt als unsichtbar via NiceGUI-Property
            with ui.row().classes('w-full gap-4 p-2 bg-slate-50 rounded border border-slate-200 transition-all') as filter_sektion:
                filter_sektion.visible = False # Hier nutzen wir direkt das Property
                
                # 1. Status Filter
                status_opts = {'ALL': '🔍 ' + t('status') + ': ' + t('none'), 'UNREAD': t('unread'), 'READING': t('reading'), 'READ': t('read')}
                status_filter = ui.select(options=status_opts, value='ALL', on_change=filter_anwenden).classes('w-44 bg-white px-2 rounded')
                
                # 2. Format Filter
                format_opts = {'ALL': '📱 ' + t('format') + ': ' + t('none'), 'PHYSICAL': t('PHYSICAL'), 'AUDIOBOOK': t('AUDIOBOOK'), 'EBOOK': t('EBOOK')}
                format_filter = ui.select(options=format_opts, value='ALL', on_change=filter_anwenden).classes('w-44 bg-white px-2 rounded')
                
                # 3. Besitz Filter
                own_opts = {'ALL': '🤝 ' + t('ownership') + ': ' + t('none'), 'OWNED': t('OWNED'), 'BORROWED': t('BORROWED'), 'LENT': t('LENT')}
                ownership_filter = ui.select(options=own_opts, value='ALL', on_change=filter_anwenden).classes('w-44 bg-white px-2 rounded')
                
                # 4. Regal/Standort Filter
                regal_opts = {'ALL': '📍 ' + t('location') + ': ' + t('none')}
                for r_id, r_name in regale:
                    regal_opts[r_id] = r_name
                location_filter = ui.select(options=regal_opts, value='ALL', on_change=filter_anwenden).classes('w-56 bg-white px-2 rounded')
        
        # Kachel-Grid Container initialisieren
        kachel_container = ui.row().classes('w-full grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6')
        
        # Kacheln das erste Mal zeichnen
        filter_anwenden()

ui.run(port=8080, title="Booktracker", reload=True)