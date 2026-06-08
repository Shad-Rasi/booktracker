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
        # Status-Keys werden zu Kleinbuchstaben formatiert (unread, reading, read) passend zu deinen Übersetzungen
        'status_data': [{'name': t(k.lower()), 'value': v} for k, v in status_counts.items()],
        # Die Keys jagen wir hier durch t(), damit ECharts die übersetzten Achsenbeschriftungen anzeigt
        'seiten_keys': [t(k) for k in seiten_klassen.keys()],
        'seiten_values': list(seiten_klassen.values()),
        'jahre_keys': sorted(list(gelesen_pro_jahr.keys())),
        'jahre_values': [gelesen_pro_jahr[j] for j in sorted(list(gelesen_pro_jahr.keys()))]
    }

@ui.page('/statistics')
def statistik_seite():
    with basis_layout('statistics'):
        ui.label(t('stats_title')).classes('text-2xl font-bold text-slate-700 mb-2')
        ui.label(t('stats_subtitle')).classes('text-sm text-slate-500 mb-6')
        
        stats = berechne_statistiken(layout.aktiver_user_id)
        
        if not stats:
            with ui.card().classes('w-full p-6 text-center text-slate-500'):
                ui.icon('bar_chart', size='lg').classes('mx-auto mb-2')
                ui.label(t('stats_no_data'))
            return

        # --- OBERE KPI KARTEN ---
        with ui.element('div').classes('w-full grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6'):
            with ui.card().classes('p-4 border-l-4 border-blue-500 bg-slate-50 shadow-sm'):
                ui.label(t('stats_total_books')).classes('text-xs font-bold text-slate-400 uppercase tracking-wider')
                ui.label(str(stats['total_books'])).classes('text-3xl font-black text-slate-700 mt-1')
                
            with ui.card().classes('p-4 border-l-4 border-emerald-500 bg-slate-50 shadow-sm'):
                ui.label(t('stats_total_pages_read')).classes('text-xs font-bold text-slate-400 uppercase tracking-wider')
                ui.label(f"{stats['total_pages_read']:,}".replace(',', '.')).classes('text-3xl font-black text-slate-700 mt-1')

        # --- GRID FÜR DIAGRAMME ---
        with ui.element('div').classes('w-full grid grid-cols-1 md:grid-cols-2 gap-6'):
            
            # DIAGRAMM 1: Status (Donut)
            with ui.card().classes('p-4 w-full h-80 items-center border border-slate-200 shadow-sm'):
                ui.label(t('stats_chart_status')).classes('text-sm font-bold text-slate-600 self-start')
                ui.echart({
                    'tooltip': {'trigger': 'item'},
                    'legend': {'bottom': '0%', 'left': 'center'},
                    'series': [{
                        'name': t('books'),
                        'type': 'pie',
                        'radius': ['40%', '70%'],
                        'avoidLabelOverlap': False,
                        'itemStyle': {'borderRadius': 6, 'borderColor': '#fff', 'borderWidth': 2},
                        'label': {'show': False},
                        'data': stats['status_data']
                    }]
                }).classes('w-full h-64')

            # DIAGRAMM 2: Seiten-Klassen (Balken)
            with ui.card().classes('p-4 w-full h-80 items-center border border-slate-200 shadow-sm'):
                ui.label(t('stats_chart_lengths')).classes('text-sm font-bold text-slate-600 self-start')
                ui.echart({
                    'xAxis': {'type': 'category', 'data': stats['seiten_keys']},
                    'yAxis': {'type': 'value'},
                    'tooltip': {'trigger': 'axis'},
                    'series': [{
                        'data': stats['seiten_values'],
                        'type': 'bar',
                        'itemStyle': {'color': '#3b82f6', 'borderRadius': [4, 4, 0, 0]}
                    }]
                }).classes('w-full h-64')

        # --- MEILENSTEINE / ENTWICKLUNG ---
        if stats['jahre_keys']:
            with ui.card().classes('w-full p-4 mt-6 border border-slate-200 shadow-sm h-80'):
                ui.label(t('stats_chart_development')).classes('text-sm font-bold text-slate-600')
                ui.echart({
                    'xAxis': {'type': 'category', 'data': stats['jahre_keys']},
                    'yAxis': {'type': 'value', 'minInterval': 1},
                    'tooltip': {'trigger': 'axis'},
                    'series': [{
                        'data': stats['jahre_values'],
                        'type': 'line',
                        'smooth': True,
                        'lineStyle': {'color': '#10b981', 'width': 3},
                        'itemStyle': {'color': '#10b981'},
                        'areaStyle': {'color': 'rgba(16, 185, 129, 0.1)'}
                    }]
                }).classes('w-full h-64')