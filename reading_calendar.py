from nicegui import ui
import database
import layout
from layout import basis_layout
from translations import t
from datetime import datetime, timedelta
import calendar

# Wir nutzen einen session-weiten Zustand für den aktuell angezeigten Kalendermonat
# und den gewählten Ansichtsmodus ('COVER' oder 'TIMELINE')
kalender_status = {
    'jahr': datetime.now().year,
    'monat': datetime.now().month,
    'modus': 'COVER'  # Alternativ: 'TIMELINE'
}

@ui.page('/calendar')
def kalender_ansicht():
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    is_dark = user_ui['dark_mode']
    
    # Design-System-Variablen
    bg_card = 'bg-slate-800 border-slate-700 text-slate-100' if is_dark else 'bg-slate-50 border-slate-200 text-slate-700'
    bg_tages_kachel = 'bg-slate-900/40 border-slate-700/50' if is_dark else 'bg-white border-slate-100'
    text_main = 'text-slate-100' if is_dark else 'text-slate-700'
    text_sub = 'text-slate-400' if is_dark else 'text-slate-500'
    
    # 1. Monats-Wechsel Logik
    def monat_aendern(delta):
        kalender_status['monat'] += delta
        if kalender_status['monat'] > 12:
            kalender_status['monat'] = 1
            kalender_status['jahr'] += 1
        elif kalender_status['monat'] < 1:
            kalender_status['monat'] = 12
            kalender_status['jahr'] -= 1
        kalender_rendering_zone.refresh()

    def modus_wechseln(neuer_modus):
        kalender_status['modus'] = neuer_modus
        kalender_rendering_zone.refresh()

    with basis_layout('calendar'):
        # --- HEADER MIT SWITCH-BUTTONS ---
        with ui.row().classes('w-full justify-between items-center mb-6 flex-wrap gap-4'):
            with ui.element('div'):
                ui.label(t('calendar_title')).classes(f'text-2xl font-bold {text_main}')
                ui.label(t('calendar_subtitle')).classes(f'text-sm {text_sub}')
            
            # Die umschaltbaren Buttons für den Modus
            with ui.row().classes('bg-slate-200 dark:bg-slate-800 p-1 rounded-lg shadow-inner'):
                btn_cover = ui.button(t('cal_mode_covers'), on_click=lambda: modus_wechseln('COVER')).props('flat dense')
                btn_time = ui.button(t('cal_mode_timeline'), on_click=lambda: modus_wechseln('TIMELINE')).props('flat dense')

        # --- DYNAMISCHE KALENDER-REWRITE-ZONE ---
        @ui.refreshable
        def kalender_rendering_zone():
            # Buttons stylen je nachdem was aktiv ist
            mod = kalender_status['modus']
            btn_cover.classes('bg-slate-700 text-white px-3 py-1 rounded' if mod == 'COVER' else 'text-slate-500 px-3 py-1')
            btn_time.classes('bg-slate-700 text-white px-3 py-1 rounded' if mod == 'TIMELINE' else 'text-slate-500 px-3 py-1')

            jahr, monat = kalender_status['jahr'], kalender_status['monat']
            
            # Kalenderdaten berechnen
            monats_name = t(f'month_{monat}')
            wochentage = [t('day_mo'), t('day_di'), t('day_mi'), t('day_do'), t('day_fr'), t('day_sa'), t('day_so')]
            
            # Alle Lese-Logs für diesen Monat aus der DB fischen
            raw_logs = database.hole_kalender_daten_fuer_user(layout.aktiver_user_id)
            
            # --- BLATT-NAVIGATION ---
            with ui.row().classes('w-full justify-between items-center mb-4 bg-slate-100 dark:bg-slate-800/50 p-2 rounded-lg border border-slate-200/50 dark:border-slate-700/50'):
                ui.button(icon='chevron_left', on_click=lambda: monat_aendern(-1)).props('flat round dense').classes(text_main)
                ui.label(f"{monats_name} {jahr}").classes(f'text-lg font-black tracking-wide {text_main}')
                ui.button(icon='chevron_right', on_click=lambda: monat_aendern(1)).props('flat round dense').classes(text_main)

            # --- WOCHENTAGE HEADER ---
            with ui.grid().classes('w-full grid grid-cols-7 gap-2 text-center font-bold text-xs uppercase tracking-wider mb-1 text-slate-400 dark:text-slate-500'):
                for tag in wochentage:
                    ui.label(tag)

            # Generiere die Tage (calendar.monthcalendar startet standardmäßig mit Montag = 0)
            monats_wochen = calendar.monthcalendar(jahr, monat)

            # =========================================================================
            # ANSICHT 1: COVER-ANSICHT (GRÖSSERE COVER & ENDLOS-SCROLL-SUPPORT)
            # =========================================================================
            if mod == 'COVER':
                # auto-rows leicht erhöht (von 120px/140px auf 140px/160px) für mehr vertikalen Spielraum
                with ui.grid().classes('w-full grid grid-cols-7 gap-2 auto-rows-[140px] sm:auto-rows-[160px]'):
                    for woche in monats_wochen:
                        for tag in woche:
                            if tag == 0:
                                ui.element('div').classes('w-full h-full bg-slate-100/30 dark:bg-slate-800/10 rounded-lg border border-dashed border-slate-200/30 dark:border-slate-700/20')
                            else:
                                datum_str = f"{jahr}-{monat:02d}-{tag:02d}"
                                tages_logs = [log for log in raw_logs if log[0] == datum_str]
                                
                                with ui.element('div').classes(f'w-full h-full p-1.5 flex flex-col justify-between rounded-lg border shadow-xs relative overflow-hidden group {bg_tages_kachel}'):
                                    ui.label(str(tag)).classes(f'text-xs font-mono font-bold z-10 {text_sub}')
                                    
                                    if tages_logs:
                                        # HINWEIS: Das [:3] Limit ist weg! Alle Logs werden geladen. 
                                        # overflow-x-auto erlaubt unendliches horizontales Scrollen pro Tag.
                                        with ui.row().classes('w-full justify-start gap-1 px-1.5 absolute bottom-1.5 left-0 right-0 no-wrap overflow-x-auto invisible-scrollbar z-20 pointer-events-none'):
                                            for log in tages_logs:
                                                b_title, p_read, b_id = log[1], log[2], log[3]
                                                cover_url = database.hole_cover_url(b_id)
                                                
                                                # Cover-Größe hochgeschraubt von w-7/w-8 auf w-9/w-10 (und h-12/h-14)
                                                with ui.element('div').classes('w-9 h-12 sm:w-10 sm:h-14 bg-slate-200 dark:bg-slate-900 rounded shadow-sm overflow-hidden cursor-pointer hover:scale-105 transition-transform flex-shrink-0 pointer-events-auto') \
                                                        .on('click', lambda _, id=b_id: ui.navigate.to(f'/book/{id}')):
                                                    
                                                    if cover_url != "/covers/placeholder.jpg":
                                                        ui.image(cover_url).classes('w-full h-full object-cover') \
                                                            .tooltip(f"{b_title} (+{p_read} {t('pages_short')})")
                                                    else:
                                                        ui.icon('book', size='sm').classes('mx-auto mt-3 text-slate-400') \
                                                            .tooltip(f"{b_title} (+{p_read} {t('pages_short')})")

            # =========================================================================
            # ANSICHT 2: TIMELINE / GANTT-CHART ANSICHT
            # =========================================================================
            elif mod == 'TIMELINE':
                # Alle gelesenen Bücher des Nutzers holen, um die Zeiträume (Start -> Ende) zu ermitteln
                alle_buecher = database.lade_buecher_aus_db(layout.aktiver_user_id)
                aktive_zeitraeume = []
                
                # Monatsgrenzen als datetime-Objekte festlegen
                erster_tag_monat = datetime(jahr, monat, 1)
                letzter_tag_monat = datetime(jahr, monat, calendar.monthrange(jahr, monat)[1])

                for b in alle_buecher:
                    b_id, b_title, start_str, end_str = b[0], b[1], b[11], b[12]
                    
                    if start_str:
                        try:
                            s_dt = datetime.strptime(start_str, '%Y-%m-%d')
                            # Wenn kein Enddatum da ist, aber der Status READING ist, läuft es bis heute
                            e_dt = datetime.strptime(end_str, '%Y-%m-%d') if end_str else datetime.now()
                            
                            # Prüfen, ob das Buch den aktuellen Monat überschneidet
                            if s_dt <= letzter_tag_monat and e_dt >= erster_tag_monat:
                                aktive_zeitraeume.append({
                                    'id': b_id, 'title': b_title, 'start': s_dt, 'end': e_dt
                                })
                        except: pass

                with ui.card().classes(f'w-full p-4 flex flex-col gap-3 border shadow-sm {bg_card}'):
                    if not aktive_zeitraeume:
                        ui.label(t('cal_no_timeline_data')).classes(f'text-sm italic text-center py-8 {text_sub}')
                    else:
                        anzahl_tage = letzter_tag_monat.day
                        
                        # Wir loopen durch jedes Buch, das in diesem Monat gelesen wurde
                        for item in aktive_zeitraeume:
                            with ui.row().classes('w-full items-center no-wrap gap-2 py-1 border-b border-slate-200/10'):
                                # Linker Buch-Titel (Feste Breite, klickbar)
                                ui.label(item['title']).classes(f'w-1/4 text-xs font-bold truncate cursor-pointer hover:text-blue-500 {text_main}') \
                                    .on('click', lambda _, id=item['id']: ui.navigate.to(f'/book/{id}'))
                                
                                # Rechter Timeline-Balken-Container
                                with ui.element('div').classes('w-3/4 h-5 bg-slate-200/30 dark:bg-slate-900/50 rounded-md relative overflow-hidden'):
                                    # relative Positionen im Monat berechnen
                                    tag_start = max(1, (item['start'] - erster_tag_monat).days + 1)
                                    tag_ende = min(anzahl_tage, (item['end'] - erster_tag_monat).days + 1)
                                    
                                    linke_position = ((tag_start - 1) / anzahl_tage) * 100
                                    breite = ((tag_ende - tag_start + 1) / anzahl_tage) * 100
                                    
                                    # Der farbige Balken
                                    ui.element('div').classes('absolute h-full bg-emerald-500/80 hover:bg-emerald-500 rounded shadow-xs cursor-pointer transition-colors') \
                                        .style(f"left: {linke_position}%; width: {breite}%;") \
                                        .on('click', lambda _, id=item['id']: ui.navigate.to(f'/book/{id}'))
                                    
                                    # Tooltip für den Balken verrät den exakten Zeitraum
                                    ui.tooltip(f"{item['title']}: {item['start'].strftime('%d.%m.')} - {item['end'].strftime('%d.%m.')}")

        kalender_rendering_zone()