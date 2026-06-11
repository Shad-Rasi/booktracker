import csv
import io
import asyncio
import os
from datetime import datetime
from collections import Counter
from nicegui import ui
import database
import layout
import pdf_export_service
from layout import basis_layout
import translations
from translations import t

def berechne_grund_statistiken(user_id):
    """Berechnet globale Bestandsdaten der kompletten Bibliothek."""
    buecher = database.lade_buecher_aus_db(user_id)
    if not buecher:
        return None

    total_books = len(buecher)
    format_counts = Counter()
    status_counts = Counter()
    
    # Counter für alle vier Besitzstatusse
    ownership_counts = Counter({'OWNED': 0, 'BORROWED': 0, 'LENT': 0, 'GIVEN_AWAY': 0})
    
    sterne_counts = {str(i): 0 for i in range(1, 6)}
    verfuegbare_jahre = set()
    
    seiten_klassen = {
        "pages_under_200": 0,
        "pages_200_to_400": 0,
        "pages_400_to_600": 0,
        "pages_over_600": 0,
        "pages_unknown": 0
    }

    for b in buecher:
        status = b[5] or 'UNREAD'
        pages = b[4] or 0
        rating = b[6] or 0
        fmt = b[23] or 'PHYSICAL'
        ownership = b[24] or 'OWNED'
        finished_at = b[12]

        format_counts[fmt] += 1
        status_counts[status] += 1
        ownership_counts[ownership] += 1
        
        if rating > 0 and str(rating) in sterne_counts:
            sterne_counts[str(rating)] += 1
        
        if pages > 0:
            if pages < 200: seiten_klassen["pages_under_200"] += 1
            elif pages <= 400: seiten_klassen["pages_200_to_400"] += 1
            elif pages <= 600: seiten_klassen["pages_400_to_600"] += 1
            else: seiten_klassen["pages_over_600"] += 1
        else:
            seiten_klassen["pages_unknown"] += 1

        if status == 'READ' and finished_at:
            try:
                jahr = finished_at.split('-')[0]
                if len(jahr) == 4 and jahr.isdigit():
                    verfuegbare_jahre.add(jahr)
            except:
                pass

    jahres_liste = ['ALL'] + sorted(list(verfuegbare_jahre), reverse=True)

    return {
        'total_books': total_books,
        'format_data': [{'name': t(k), 'value': v} for k, v in format_counts.items()],
        'status_data': [{'name': t(k.lower()), 'value': v} for k, v in status_counts.items()],
        'ownership_counts': ownership_counts,
        'seiten_keys': [t(k) for k in seiten_klassen.keys()],
        'seiten_values': list(seiten_klassen.values()),
        'sterne_keys': [f"{k} ⭐" for k in sterne_counts.keys()],
        'sterne_values': list(sterne_counts.values()),
        'jahres_liste': jahres_liste,
        'rohe_buecher': buecher
    }


def berechne_zeitliche_statistiken(buecher, ziel_jahr):
    """Berechnet dynamisch die persönlichen Daten – gesplittet nach Jahr (Monate) oder ALL (Jahre)."""
    total_pages_read = 0
    buecher_gelesen_count = 0
    
    monats_seiten = {f"{i:02d}": 0 for i in range(1, 13)}
    monats_buecher = {f"{i:02d}": 0 for i in range(1, 13)}
    
    jahres_seiten = Counter()
    jahres_buecher = Counter()

    for b in buecher:
        status = b[5] or 'UNREAD'
        pages = b[4] or 0
        finished_at = b[12]

        if status == 'READ' and finished_at:
            try:
                jahr = finished_at.split('-')[0]
                monat = finished_at.split('-')[1]
                
                if ziel_jahr != 'ALL' and jahr != ziel_jahr:
                    continue
                
                buecher_gelesen_count += 1
                total_pages_read += pages
                    
                monats_seiten[monat] += pages
                monats_buecher[monat] += 1
                
                jahres_seiten[jahr] += pages
                jahres_buecher[jahr] += 1
            except:
                continue

    if ziel_jahr == 'ALL':
        sortierte_jahre = sorted(list(jahres_buecher.keys()))
        x_achse_keys = sortierte_jahre
        werte_buecher = [jahres_buecher[j] for j in sortierte_jahre]
        werte_seiten = [jahres_seiten[j] for j in sortierte_jahre]
    else:
        x_achse_keys = [t(f"month_{m}")for m in monats_seiten.keys()]
        werte_buecher = list(monats_buecher.values())
        werte_seiten = list(monats_seiten.values())

    return {
        'total_pages_read': total_pages_read,
        'buecher_gelesen_count': buecher_gelesen_count,
        'x_achse_keys': x_achse_keys,
        'werte_buecher': werte_buecher,
        'werte_seiten': werte_seiten
    }


@ui.page('/statistics')
def statistik_seite():
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    is_dark = user_ui['dark_mode']
    
    axis_text_color = '#f8fafc' if is_dark else '#334155'
    grid_line_color = '#334155' if is_dark else '#e2e8f0'
    dark_prop = 'dark popup-content-class="dark"' if is_dark else ''
    
    bg_card = 'bg-slate-800 border-slate-700 text-slate-100' if is_dark else 'bg-slate-50 border-slate-200 text-slate-700'
    bg_kpi_card = 'bg-slate-800 border-slate-700 text-slate-100' if is_dark else 'bg-slate-50 border-slate-200 text-slate-700'
    text_kpi_num = 'text-slate-100' if is_dark else 'text-slate-700'
    style_modal = 'background-color: #1e293b; color: #f8fafc;' if is_dark else ''

    with basis_layout('stats_title'):
        ui.label(t('stats_title')).classes('text-2xl font-bold text-slate-700 dark:text-slate-100 mb-2')
        ui.label(t('stats_subtitle')).classes('text-sm text-slate-500 dark:text-slate-400 mb-6')

        global_stats = berechne_grund_statistiken(layout.aktiver_user_id)
        
        if not global_stats:
            with ui.card().classes(f'w-full p-6 text-center border {bg_card}'):
                ui.icon('bar_chart', size='lg').classes('mx-auto mb-2 text-slate-400')
                ui.label(t('stats_no_data'))
            return
        
        aktuelles_jahr = str(datetime.now().year)
        if aktuelles_jahr not in global_stats['jahres_liste']:
            global_stats['jahres_liste'].insert(1, aktuelles_jahr)

        # 1. Das Modal-Element definieren
        with ui.dialog() as share_modal, ui.card().classes('p-6 w-96').style(style_modal):
            ui.label(t('share_report_title')).classes('text-lg font-bold mb-4')
            ui.label(t('share_report_desc')).classes('mb-4 text-sm')
            
            modal_jahr = ui.select(
                options={j: (t('all_years') if j == 'ALL' else j) for j in global_stats['jahres_liste']},
                value=aktuelles_jahr
            ).classes('w-full mb-4').props(dark_prop)

            ui.button(t('share_report_btn_export'), icon='picture_as_pdf', 
                      on_click=lambda: starte_export(modal_jahr.value)).classes('w-full bg-indigo-600')
            ui.button(t('close'), on_click=share_modal.close).props('flat')

        # 2. Die Funktion im Hintergrund
        async def starte_export(jahr):
            ui.notify(t('generating_pdf'), type='info')
            share_modal.close()
            try:
                pdf_pfad = await pdf_export_service.export_personal_pdf(layout.aktiver_user_id, jahr)
                ui.download(pdf_pfad)
            except Exception as e:
                ui.notify(f"{t('share_report_error')}: {str(e)}", type='negative')

        # =========================================================================
        # SEKTION 1: PERSÖNLICHE STATISTIKEN
        # =========================================================================
        with ui.row().classes('w-full justify-between items-center mb-4 gap-4'):
            ui.label(t('stats_sec_personal')).classes('text-lg font-bold text-slate-700 dark:text-slate-200 uppercase tracking-wide')
            
            with ui.row().classes('gap-2 items-center'):
                ui.button(icon='share', on_click=share_modal.open) \
                    .props('flat round color="primary"') \
                    .classes('mr-2') \
                    .tooltip(t('export_report'))

                auswahl_chart_typ = ui.select(
                    options={'bar': '📊 ' + t('chart_type_bar'), 'line': '📈 ' + t('chart_type_line')},
                    value='bar',
                    on_change=lambda: personal_stats_container.refresh()
                ).classes('w-40 px-1') \
                 .props(f'dense outlined {dark_prop}')

                auswahl_jahr = ui.select(
                    options={j: (t('all_years') if j == 'ALL' else j) for j in global_stats['jahres_liste']},
                    value=aktuelles_jahr,  
                    on_change=lambda: personal_stats_container.refresh()
                ).classes('w-40 px-1') \
                 .props(f'dense outlined {dark_prop}')

        @ui.refreshable
        def personal_stats_container():
            jahr_filter = auswahl_jahr.value
            chart_typ = auswahl_chart_typ.value
            p_stats = berechne_zeitliche_statistiken(global_stats['rohe_buecher'], jahr_filter)

            # KPI Karten
            with ui.element('div').classes('w-full grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6'):
                with ui.card().classes(f'p-4 border-l-4 border-orange-500 shadow-sm {bg_kpi_card}'):
                    ui.label(t('stats_read_books_year')).classes('text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider')
                    ui.label(str(p_stats['buecher_gelesen_count'])).classes(f'text-3xl font-black mt-1 {text_kpi_num}')
                    
                with ui.card().classes(f'p-4 border-l-4 border-emerald-500 shadow-sm {bg_kpi_card}'):
                    ui.label(t('stats_total_pages_read')).classes('text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider')
                    ui.label(f"{p_stats['total_pages_read']:,}".replace(',', '.')).classes(f'text-3xl font-black mt-1 {text_kpi_num}')

            if jahr_filter != 'ALL' and p_stats['buecher_gelesen_count'] == 0:
                with ui.card().classes(f'w-full p-8 text-center italic border {bg_card}'):
                    ui.label(t('stats_no_data_year'))
                return

            with ui.element('div').classes('w-full grid grid-cols-1 md:grid-cols-2 gap-6 mb-10'):
                with ui.card().classes(f'p-4 w-full h-80 items-center border shadow-sm {bg_card}'):
                    label_buecher_verlauf = t('stats_chart_books_development')
                    ui.label(label_buecher_verlauf).classes('text-sm font-bold self-start text-slate-600 dark:text-slate-300')
                    
                    buecher_series = {'data': p_stats['werte_buecher'], 'type': chart_typ, 'smooth': True if chart_typ == 'line' else False}
                    if chart_typ == 'bar':
                        buecher_series['itemStyle'] = {'color': '#6366f1', 'borderRadius': [4, 4, 0, 0]}
                    else:
                        buecher_series['lineStyle'] = {'color': '#6366f1', 'width': 3}
                        buecher_series['itemStyle'] = {'color': '#6366f1'}
                        buecher_series['areaStyle'] = {'color': 'rgba(99, 102, 241, 0.1)'}

                    ui.echart({
                        'backgroundColor': 'transparent',
                        'xAxis': {'type': 'category', 'data': p_stats['x_achse_keys'], 'axisLabel': {'color': axis_text_color}},
                        'yAxis': {'type': 'value', 'minInterval': 1, 'axisLabel': {'color': axis_text_color}, 'splitLine': {'lineStyle': {'color': grid_line_color}}},
                        'tooltip': {'trigger': 'axis'},
                        'series': [buecher_series]
                    }).classes('w-full h-64')

                with ui.card().classes(f'p-4 w-full h-80 items-center border shadow-sm {bg_card}'):
                    ui.label(t('stats_chart_monthly_pages')).classes('text-sm font-bold self-start text-slate-600 dark:text-slate-300')
                    
                    seiten_series = {'data': p_stats['werte_seiten'], 'type': chart_typ, 'smooth': True if chart_typ == 'line' else False}
                    if chart_typ == 'bar':
                        seiten_series['itemStyle'] = {'color': '#10b981', 'borderRadius': [4, 4, 0, 0]}
                    else:
                        seiten_series['lineStyle'] = {'color': '#10b981', 'width': 3}
                        seiten_series['itemStyle'] = {'color': '#10b981'}
                        seiten_series['areaStyle'] = {'color': 'rgba(16, 185, 129, 0.1)'}

                    ui.echart({
                        'backgroundColor': 'transparent',
                        'xAxis': {'type': 'category', 'data': p_stats['x_achse_keys'], 'axisLabel': {'color': axis_text_color}},
                        'yAxis': {'type': 'value', 'axisLabel': {'color': axis_text_color}, 'splitLine': {'lineStyle': {'color': grid_line_color}}},
                        'tooltip': {'trigger': 'axis'},
                        'series': [seiten_series]
                    }).classes('w-full h-64')

        personal_stats_container()

        # =========================================================================
        # SEKTION 2: ALLGEMEINE TRACKER STATISTIKEN
        # =========================================================================
        ui.separator().classes('my-6 dark:bg-slate-700')
        ui.label(t('stats_sec_general')).classes('text-lg font-bold text-slate-700 dark:text-slate-200 mt-2 mb-4 uppercase tracking-wide')

        with ui.element('div').classes('w-full grid grid-cols-1 md:grid-cols-3 gap-6 mb-6'):
            
            # 1. ANZEIGE: KPI Karte mit Textaufteilung
            with ui.card().classes(f'p-4 border-l-4 border-blue-500 shadow-sm flex flex-col justify-between h-auto min-h-[19rem] {bg_kpi_card}'):
                with ui.element('div'):
                    ui.label(t('stats_total_books')).classes('text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider')
                    ui.label(str(global_stats['total_books'])).classes(f'text-4xl font-black mt-1 mb-2 {text_kpi_num}')
                
                oc = global_stats['ownership_counts']
                with ui.element('div').classes('w-full flex flex-col gap-1.5 pt-2 border-t border-slate-200 dark:border-slate-700 text-xs'):
                    with ui.row().classes('w-full justify-between items-center bg-blue-500/10 dark:bg-blue-500/5 px-2 py-1 rounded'):
                        ui.label(t('OWNED')).classes('font-medium')
                        ui.badge(str(oc['OWNED']), color='blue').classes('text-[10px] font-bold px-2')
                        
                    with ui.row().classes('w-full justify-between items-center bg-amber-500/10 dark:bg-amber-500/5 px-2 py-1 rounded'):
                        ui.label(t('BORROWED')).classes('font-medium')
                        ui.badge(str(oc['BORROWED']), color='amber').classes('text-[10px] font-bold px-2')
                        
                    with ui.row().classes('w-full justify-between items-center bg-purple-500/10 dark:bg-purple-500/5 px-2 py-1 rounded'):
                        ui.label(t('LENT')).classes('font-medium')
                        ui.badge(str(oc['LENT']), color='purple').classes('text-[10px] font-bold px-2')
                        
                    with ui.row().classes('w-full justify-between items-center bg-red-500/10 dark:bg-red-500/5 px-2 py-1 rounded'):
                        ui.label(t('ownership_given_away')).classes('font-medium')
                        ui.badge(str(oc['GIVEN_AWAY']), color='red').classes('text-[10px] font-bold px-2')

            # 2. ANZEIGE: Ownership Kuchendiagramm daneben
            with ui.card().classes(f'p-4 h-auto min-h-[19rem] flex flex-col justify-between border shadow-sm {bg_card}'):
                label_ownership_chart = t('ownership')
                ui.label(label_ownership_chart).classes('text-sm font-bold self-start text-slate-600 dark:text-slate-300')
                
                ownership_chart_data = [
                    {'name': t('OWNED'), 'value': oc['OWNED'], 'itemStyle': {'color': '#3b82f6'}},
                    {'name': t('BORROWED'), 'value': oc['BORROWED'], 'itemStyle': {'color': '#f59e0b'}},
                    {'name': t('LENT'), 'value': oc['LENT'], 'itemStyle': {'color': '#a855f7'}},
                    {'name': t('ownership_given_away'), 'value': oc['GIVEN_AWAY'], 'itemStyle': {'color': '#ef4444'}}
                ]
                
                ui.echart({
                    'tooltip': {'trigger': 'item'},
                    'legend': {'bottom': '0%', 'left': 'center', 'textStyle': {'color': axis_text_color}},
                    'backgroundColor': 'transparent',
                    'series': [{
                        'name': label_ownership_chart, 'type': 'pie', 'radius': '60%', 'center': ['50%', '45%'],
                        'label': {'show': False, 'formatter': '{d}%', 'textStyle': {'color': axis_text_color}},
                        'data': ownership_chart_data
                    }]
                }).classes('w-full h-56')

            # 3. ANZEIGE: Buchtyp-Kuchendiagramm (1/3 Breite)
            with ui.card().classes(f'p-4 h-auto min-h-[19rem] flex flex-col justify-between border shadow-sm {bg_card}'):
                ui.label(t('stats_chart_formats')).classes('text-sm font-bold self-start text-slate-600 dark:text-slate-300')
                
                ui.echart({
                    'tooltip': {'trigger': 'item'},
                    'legend': {'bottom': '0%', 'left': 'center', 'textStyle': {'color': axis_text_color}},
                    'backgroundColor': 'transparent',
                    'series': [{
                        'name': t('format'), 'type': 'pie', 'radius': '60%', 'center': ['50%', '45%'],
                        'label': {'show': False, 'formatter': '{d}%', 'textStyle': {'color': axis_text_color}},
                        'data': global_stats['format_data']
                    }]
                }).classes('w-full h-56')

        # ==========================================
        # REIHE: BUCHLÄNGEN & GENRE-VERTEILUNG
        # ==========================================
        with ui.element('div').classes('w-full grid grid-cols-1 md:grid-cols-2 gap-6 mt-4 mb-6'):
            
            # --- LINKS: BUCHLÄNGEN (Vertikale Balken) ---
            with ui.card().classes(f'p-4 w-full h-80 border shadow-sm {bg_card}'):
                ui.label(t('stats_chart_lengths')).classes('text-sm font-bold self-start text-slate-600 dark:text-slate-300 mb-2')
                
                ui.echart({
                    'backgroundColor': 'transparent',
                    'xAxis': {'type': 'category', 'data': global_stats['seiten_keys'], 'axisLabel': {'color': axis_text_color}},
                    'yAxis': {'type': 'value', 'axisLabel': {'color': axis_text_color}, 'splitLine': {'lineStyle': {'color': grid_line_color}}, 'minInterval': 1},
                    'tooltip': {'trigger': 'axis'},
                    'series': [{
                        'data': global_stats['seiten_values'], 'type': 'bar',
                        'itemStyle': {'color': '#3b82f6', 'borderRadius': [4, 4, 0, 0]}
                    }]
                }).classes('w-full h-64')

            # --- RECHTS: GENRE-VERTEILUNG (Vertikale Balken) ---
            with ui.card().classes(f'p-4 w-full h-80 border shadow-sm {bg_card}'):
                ui.label(t('stats_chart_genres')).classes('text-sm font-bold self-start text-slate-600 dark:text-slate-300 mb-2')
                
                genre_daten = database.hole_genre_verteilung_stats(layout.aktiver_user_id)
                
                if not genre_daten:
                    with ui.column().classes('w-full h-64 items-center justify-center'):
                        ui.label(t('no_genres_hint')).classes('text-xs italic text-slate-400 text-center')
                else:
                    genre_labels = [row[0] for row in genre_daten]
                    genre_werte = [row[1] for row in genre_daten]
                    
                    ui.echart({
                        'backgroundColor': 'transparent',
                        'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}},
                        'xAxis': {
                            'type': 'category', 
                            'data': genre_labels, 
                            'axisLabel': {'color': axis_text_color, 'interval': 0, 'rotate': 25} # Text leicht schräg, falls die Genrenamen länger sind
                        },
                        'yAxis': {
                            'type': 'value', 
                            'axisLabel': {'color': axis_text_color}, 
                            'splitLine': {'lineStyle': {'color': grid_line_color}},
                            'minInterval': 1
                        },
                        'series': [{
                            'name': t('books_count'), 
                            'type': 'bar',
                            'data': genre_werte,
                            'label': {
                                'show': True, 
                                'position': 'top', 
                                'color': axis_text_color
                            },
                            'itemStyle': {
                                'color': '#10b981', 
                                'borderRadius': [4, 4, 0, 0] # Wächst nach oben, Ecken oben abgerundet
                            }
                        }]
                    }).classes('w-full h-64')

        ui.separator().classes('my-6 dark:bg-slate-700')

        # ==========================================
        # REIHE: LESESTATUS & BEWERTUNGEN
        # ==========================================
        with ui.element('div').classes('w-full grid grid-cols-1 md:grid-cols-2 gap-6'):
            with ui.card().classes(f'p-4 w-full h-80 items-center border shadow-sm {bg_card}'):
                ui.label(t('stats_chart_status')).classes('text-sm font-bold self-start text-slate-600 dark:text-slate-300')
                
                ui.echart({
                    'tooltip': {'trigger': 'item'},
                    'legend': {'bottom': '0%', 'left': 'center', 'textStyle': {'color': axis_text_color}},
                    'backgroundColor': 'transparent',
                    'series': [{
                        'name': t('books'), 'type': 'pie', 'radius': ['40%', '70%'],
                        'itemStyle': {'borderRadius': 6, 'borderColor': '#1e293b' if is_dark else '#fff', 'borderWidth': 2},
                        'label': {'show': False}, 'data': global_stats['status_data']
                    }]
                }).classes('w-full h-64')

            with ui.card().classes(f'p-4 w-full h-80 items-center border shadow-sm {bg_card}'):
                ui.label(t('stats_chart_ratings')).classes('text-sm font-bold self-start text-slate-600 dark:text-slate-300')
                
                ui.echart({
                    'backgroundColor': 'transparent',
                    'xAxis': {'type': 'category', 'data': global_stats['sterne_keys'], 'axisLabel': {'color': axis_text_color}},
                    'yAxis': {'type': 'value', 'minInterval': 1, 'axisLabel': {'color': axis_text_color}, 'splitLine': {'lineStyle': {'color': grid_line_color}}},
                    'tooltip': {'trigger': 'axis'},
                    'series': [{
                        'data': global_stats['sterne_values'], 'type': 'bar',
                        'itemStyle': {'color': '#f59e0b', 'borderRadius': [4, 4, 0, 0]}
                    }]
                }).classes('w-full h-64')