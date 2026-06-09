from nicegui import ui
import database
import layout
from layout import basis_layout
from translations import t
from collections import Counter
from datetime import datetime

def berechne_statistiken(user_id):
    """Lädt die rohen DB-Daten und bereitet sie für die Diagramme vor."""
    buecher = database.lade_buecher_aus_db(user_id)
    
    total_books = len(buecher)
    if total_books == 0:
        return None

    # 1. Status-Verteilung
    status_counts = Counter()
    
    # 2. Seiten-Klassen (Hier nutzen wir jetzt Übersetzungsschlüssel als Keys)
    seiten_klassen = {
        "pages_under_200": 0,
        "pages_200_to_400": 0,
        "pages_400_to_600": 0,
        "pages_over_600": 0
    }
    
    # 3. Gelesene Bücher pro Jahr
    gelesen_pro_jahr = Counter()
    total_pages_read = 0

    for b in buecher:
        status = b[5] or 'UNREAD'
        pages = b[4] or 0
        finished_at = b[12]

        status_counts[status] += 1

        if status == 'READ':
            total_pages_read += pages
            
        if pages > 0:
            if pages < 200: seiten_klassen["pages_under_200"] += 1
            elif pages <= 400: seiten_klassen["pages_200_to_400"] += 1
            elif pages <= 600: seiten_klassen["pages_400_to_600"] += 1
            else: seiten_klassen["pages_over_600"] += 1

        if status == 'READ' and finished_at:
            try:
                jahr = finished_at.split('-')[0]
                if len(jahr) == 4 and jahr.isdigit():
                    gelesen_pro_jahr[jahr] += 1
            except:
                pass

    return {
        'total_books': total_books,
        'total_pages_read': total_pages_read,
        'status_data': [{'name': t(k.lower()), 'value': v} for k, v in status_counts.items()],
        'seiten_keys': [t(k) for k in seiten_klassen.keys()],
        'seiten_values': list(seiten_klassen.values()),
        'jahre_keys': sorted(list(gelesen_pro_jahr.keys())),
        'jahre_values': [gelesen_pro_jahr[j] for j in sorted(list(gelesen_pro_jahr.keys()))]
    }

@ui.page('/statistics')
def statistik_seite():
    # 1. Darkmode-Zustand des Users ermitteln
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    is_dark = user_ui['dark_mode']
    
    # Diagramm-Theme und Textfarben vorbereiten
    chart_theme = 'dark' if is_dark else None
    axis_text_color = '#f8fafc' if is_dark else '#334155'
    grid_line_color = '#334155' if is_dark else '#e2e8f0'
    
    # Farbvariablen für die Container-Struktur
    bg_card = 'bg-slate-800 border-slate-700 text-slate-100' if is_dark else 'bg-slate-50 border-slate-200 text-slate-700'
    bg_kpi_card = 'bg-slate-800 border-slate-700' if is_dark else 'bg-slate-50 border-slate-200'
    text_kpi_num = 'text-slate-100' if is_dark else 'text-slate-700'
    text_label = 'text-slate-700 dark:text-slate-100'
    text_sub = 'text-slate-500 dark:text-slate-400'

    with basis_layout('statistics'):
        ui.label(t('stats_title')).classes(f'text-2xl font-bold mb-2 {text_label}')
        ui.label(t('stats_subtitle')).classes(f'text-sm mb-6 {text_sub}')
        
        stats = berechne_statistiken(layout.aktiver_user_id)
        
        # Lokalisierter Fallback, wenn keine Daten vorhanden sind
        if not stats:
            with ui.card().classes(f'w-full p-6 text-center border {bg_card}'):
                ui.icon('bar_chart', size='lg').classes('mx-auto mb-2 text-slate-400')
                ui.label(t('stats_no_data'))
            return

        # --- OBERE KPI KARTEN (DARKMODE REPARIERT) ---
        with ui.element('div').classes('w-full grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6'):
            with ui.card().classes(f'p-4 border-l-4 border-blue-500 shadow-sm {bg_kpi_card}'):
                ui.label(t('stats_total_books')).classes('text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider')
                ui.label(str(stats['total_books'])).classes(f'text-3xl font-black mt-1 {text_kpi_num}')
                
            with ui.card().classes(f'p-4 border-l-4 border-emerald-500 shadow-sm {bg_kpi_card}'):
                ui.label(t('stats_total_pages_read')).classes('text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider')
                ui.label(f"{stats['total_pages_read']:,}".replace(',', '.')).classes(f'text-3xl font-black mt-1 {text_kpi_num}')

        # --- GRID FÜR DIAGRAMME ---
        with ui.element('div').classes('w-full grid grid-cols-1 md:grid-cols-2 gap-6'):
            
            # DIAGRAMM 1: Status (Donut)
            with ui.card().classes(f'p-4 w-full h-80 items-center border shadow-sm {bg_card}'):
                ui.label(t('stats_chart_status')).classes('text-sm font-bold self-start text-slate-600 dark:text-slate-300')
                ui.echart({
                    'tooltip': {'trigger': 'item'},
                    'legend': {'bottom': '0%', 'left': 'center', 'textStyle': {'color': axis_text_color}},
                    'backgroundColor': 'transparent',
                    'series': [{
                        'name': t('books'),
                        'type': 'pie',
                        'radius': ['40%', '70%'],
                        'avoidLabelOverlap': False,
                        'itemStyle': {
                            'borderRadius': 6, 
                            'borderColor': '#1e293b' if is_dark else '#fff', 
                            'borderWidth': 2
                        },
                        'label': {'show': False},
                        'data': stats['status_data']
                    }]
                }, theme=chart_theme).classes('w-full h-64')

            # DIAGRAMM 2: Seiten-Klassen (Balken)
            with ui.card().classes(f'p-4 w-full h-80 items-center border shadow-sm {bg_card}'):
                ui.label(t('stats_chart_lengths')).classes('text-sm font-bold self-start text-slate-600 dark:text-slate-300')
                ui.echart({
                    'backgroundColor': 'transparent',
                    'xAxis': {
                        'type': 'category', 
                        'data': stats['seiten_keys'],
                        'axisLabel': {'color': axis_text_color}
                    },
                    'yAxis': {
                        'type': 'value',
                        'axisLabel': {'color': axis_text_color},
                        'splitLine': {'lineStyle': {'color': grid_line_color}}
                    },
                    'tooltip': {'trigger': 'axis'},
                    'series': [{
                        'data': stats['seiten_values'],
                        'type': 'bar',
                        'itemStyle': {'color': '#3b82f6', 'borderRadius': [4, 4, 0, 0]}
                    }]
                }, theme=chart_theme).classes('w-full h-64')

        # --- MEILENSTEINE / ENTWICKLUNG ---
        if stats['jahre_keys']:
            with ui.card().classes(f'w-full p-4 mt-6 border shadow-sm h-80 {bg_card}'):
                ui.label(t('stats_chart_development')).classes('text-sm font-bold text-slate-600 dark:text-slate-300')
                ui.echart({
                    'backgroundColor': 'transparent',
                    'xAxis': {
                        'type': 'category', 
                        'data': stats['jahre_keys'],
                        'axisLabel': {'color': axis_text_color}
                    },
                    'yAxis': {
                        'type': 'value', 
                        'minInterval': 1,
                        'axisLabel': {'color': axis_text_color},
                        'splitLine': {'lineStyle': {'color': grid_line_color}}
                    },
                    'tooltip': {'trigger': 'axis'},
                    'series': [{
                        'data': stats['jahre_values'],
                        'type': 'line',
                        'smooth': True,
                        'lineStyle': {'color': '#10b981', 'width': 3},
                        'itemStyle': {'color': '#10b981'},
                        'areaStyle': {'color': 'rgba(16, 185, 129, 0.1)'}
                    }]
                }, theme=chart_theme).classes('w-full h-64')