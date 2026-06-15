import asyncio
from datetime import datetime
import calendar
from nicegui import ui
import database
import layout
import translations
from layout import basis_layout
from translations import t

# Globale Steuerung des Kalenders
kalender_status = {
    'jahr': datetime.now().year,
    'monat': datetime.now().month,
    'modus': 'COVER'
}

details_dialog = None
details_container = None
details_titel = None


# --- ENTFERNEN-LOGIK ---
async def log_eintrag_löschen(log_date, cycle_id, progress_page):
    if database.loesche_reading_log_aus_db(log_date, cycle_id, progress_page):
        ui.notify(t('log_deleted'), type='positive')
        if details_dialog:
            details_dialog.close()
        await asyncio.sleep(0.05)
        kalender_rendering_zone.refresh()
    else:
        ui.notify(t('log_delete_error'), type='warning')


# --- DIALOG-ÖFFNER ---
def zeige_tages_details(datum_str, tages_logs, text_main, text_sub):
    global details_dialog, details_container, details_titel
    formatiertes_datum = datetime.strptime(datum_str, '%Y-%m-%d').strftime('%d.%m.%Y')
    
    details_titel.set_text(f"{t('cal_logs_for')} {formatiertes_datum}")
    details_container.clear()
    
    with details_container:
        if not tages_logs:
            ui.label(t('no_logs_day')).classes(f'text-xs italic {text_sub}')
        else:
            with ui.column().classes('w-full gap-2 max-h-60 overflow-y-auto overflow-x-hidden no-wrap'):
                for log in tages_logs:
                    # REPARIERT: Holt rl.progress_page als log[5] ab
                    l_date, b_title, p_read, c_id, p_page = log[0], log[1], log[2], log[4], log[5]
                    
                    with ui.row().classes('w-full justify-between items-center bg-slate-100/10 p-2 rounded gap-2 no-wrap'):
                        with ui.element('div').classes('flex flex-col truncate w-3/4'):
                            ui.label(b_title).classes(f'text-xs font-bold truncate {text_main}')
                            ui.label(f"+{p_read} {t('pages_short')}").classes(f'text-[11px] {text_sub}')
                        
                        # REPARIERT: Übergibt jetzt p_page (absolute Seite) statt p_read (Differenz)
                        ui.button(icon='delete', on_click=lambda d=l_date, cy_id=c_id, pg=p_page: log_eintrag_löschen(d, cy_id, pg)) \
                            .props('flat round dense').classes('text-red-500 hover:bg-red-500/10 flex-shrink-0')
                            
    details_dialog.open()


def modus_wechseln(neuer_modus):
    kalender_status['modus'] = neuer_modus
    kalender_rendering_zone.refresh()


# =========================================================================
# --- DYNAMISCHE KALENDER-REWRITE-ZONE (NUR NOCH FÜR OPTIK & INHALT) ---
# =========================================================================
@ui.refreshable
def kalender_rendering_zone(text_main, text_sub, bg_tages_kachel, bg_card, btn_cover, btn_time):
    mod = kalender_status['modus']
    
    # REPARIERT: Innerhalb der Zone werden NUR NOCH die Klassen getauscht. KEINE .on('click') Events mehr!
    if mod == 'COVER':
        btn_cover.classes('bg-slate-700 text-white px-3 py-1 rounded', remove='text-slate-500 dark:text-slate-400')
        btn_time.classes('text-slate-500 dark:text-slate-400 px-3 py-1', remove='bg-slate-700 text-white rounded')
    else:
        btn_time.classes('bg-slate-700 text-white px-3 py-1 rounded', remove='text-slate-500 dark:text-slate-400')
        btn_cover.classes('text-slate-500 dark:text-slate-400 px-3 py-1', remove='bg-slate-700 text-white rounded')

    jahr, monat = kalender_status['jahr'], kalender_status['monat']
    raw_logs = database.hole_kalender_daten_fuer_user(layout.aktiver_user_id)
    
    # Blätter-Leiste
    with ui.row().classes('w-full justify-between items-center mb-4 bg-slate-100 dark:bg-slate-800/50 p-2 rounded-lg border border-slate-200/50 dark:border-slate-700/50'):
        def blättern_klick(delta):
            if kalender_status['modus'] == 'TIMELINE':
                kalender_status['jahr'] += delta
            else:
                kalender_status['monat'] += delta
                if kalender_status['monat'] > 12:
                    kalender_status['monat'] = 1
                    kalender_status['jahr'] += 1
                elif kalender_status['monat'] < 1:
                    kalender_status['monat'] = 12
                    kalender_status['jahr'] -= 1
            kalender_rendering_zone.refresh()

        ui.button(icon='chevron_left', on_click=lambda: blättern_klick(-1)).props('flat round dense').classes(text_main)
        titel_anzeige = f"{jahr}" if mod == 'TIMELINE' else f"{t(f'month_{monat}')} {jahr}"
        ui.label(titel_anzeige).classes(f'text-lg font-black tracking-wide {text_main}')
        ui.button(icon='chevron_right', on_click=lambda: blättern_klick(1)).props('flat round dense').classes(text_main)

    # --- COVER-ANSICHT ---
    if mod == 'COVER':
        wochentage = [t('day_mo'), t('day_di'), t('day_mi'), t('day_do'), t('day_fr'), t('day_sa'), t('day_so')]
        with ui.grid().classes('w-full grid grid-cols-7 gap-2 text-center font-bold text-xs uppercase tracking-wider mb-1 text-slate-400 dark:text-slate-500'):
            for tag in wochentage: ui.label(tag)

        monats_wochen = calendar.monthcalendar(jahr, monat)
        with ui.grid().classes('w-full grid grid-cols-7 gap-2 auto-rows-[110px] sm:auto-rows-[130px]'):
            for woche in monats_wochen:
                for tag in woche:
                    if tag == 0:
                        ui.element('div').classes('w-full h-full bg-slate-100/30 dark:bg-slate-800/10 rounded-lg border border-dashed border-slate-200/30 dark:border-slate-700/20')
                    else:
                        datum_str = f"{jahr}-{monat:02d}-{tag:02d}"
                        tages_logs = [log for log in raw_logs if log[0] == datum_str]
                        
                        with ui.element('div').classes(f'w-full h-full p-1 flex flex-col justify-between rounded-lg border shadow-xs relative overflow-hidden group cursor-pointer transition-colors hover:bg-slate-100/50 dark:hover:bg-slate-800/40 {bg_tages_kachel}') \
                                .on('click', lambda _, d_str=datum_str, logs=tages_logs: zeige_tages_details(d_str, logs, text_main, text_sub)):
                            
                            ui.label(str(tag)).classes(f'text-xs font-mono font-bold z-10 pl-0.5 {text_sub}')
                            
                            if tages_logs:
                                with ui.row().classes('w-full justify-start gap-1 px-1 absolute bottom-1 left-0 right-0 no-wrap overflow-x-auto overflow-y-hidden invisible-scrollbar z-20 pointer-events-none'):
                                    for log in tages_logs:
                                        b_title, p_read, b_id = log[1], log[2], log[3]
                                        cover_url = database.hole_cover_url(b_id)
                                        
                                        with ui.element('div').classes('w-8 h-11 sm:w-14 sm:h-20 bg-slate-200 dark:bg-slate-900 rounded shadow-sm overflow-hidden hover:scale-105 transition-transform flex-shrink-0 pointer-events-auto') \
                                                .on('click.stop', lambda _, id=b_id: ui.navigate.to(f'/book/{id}')):
                                            
                                            if cover_url != "/covers/placeholder.jpg":
                                                ui.image(cover_url).classes('w-full h-full object-cover').tooltip(f"{b_title} (+{p_read} {t('pages_short')})")
                                            else:
                                                ui.icon('book', size='xs').classes('mx-auto mt-3 text-slate-400').tooltip(f"{b_title} (+{p_read} {t('pages_short')})")

    # --- TIMELINE-ANSICHT ---
    elif mod == 'TIMELINE':
        alle_buecher = database.lade_buecher_aus_db(layout.aktiver_user_id)
        zeitraeume_dieses_jahr = []
        
        start_des_jahres = datetime(jahr, 1, 1)
        ende_des_jahres = datetime(jahr, 12, 31)
        tage_im_jahr = 366 if calendar.isleap(jahr) else 365

        for b in alle_buecher:
            b_id, b_title, start_str, end_str = b[0], b[1], b[11], b[12]
            if start_str:
                try:
                    s_dt = datetime.strptime(start_str, '%Y-%m-%d')
                    e_dt = datetime.strptime(end_str, '%Y-%m-%d') if end_str else datetime.now()
                    if s_dt <= ende_des_jahres and e_dt >= start_des_jahres:
                        zeitraeume_dieses_jahr.append({'id': b_id, 'title': b_title, 'start': s_dt, 'end': e_dt})
                except: pass

        zeitraeume_dieses_jahr.sort(key=lambda x: x['start'])

        with ui.card().classes(f'w-full p-4 flex flex-col gap-3 border shadow-sm {bg_card}'):
            if not zeitraeume_dieses_jahr:
                ui.label(t('cal_no_timeline_data_year')).classes(f'text-sm italic text-center py-8 {text_sub}')
            else:
                with ui.row().classes('w-full items-center no-wrap gap-2 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase border-b border-slate-200/10 pb-1'):
                    ui.element('div').classes('w-1/4')
                    with ui.element('div').classes('w-3/4 relative h-4'):
                        for m in range(1, 13):
                            m_start = datetime(jahr, m, 1)
                            linke_pos = ((m_start - start_des_jahres).days / tage_im_jahr) * 100
                            
                            # Ein einziges Label, das per Tailwind-Content-Klassen den Text im Browser umschaltet!
                            ui.label('') \
                                .classes('absolute -translate-x-1/2 text-center text-[10px] font-bold') \
                                .classes('before:content-["' + str(m) + '"] sm:before:content-["' + t(f'month_{m}')[:3] + '"]') \
                                .style(f"left: {linke_pos}%;")

        # ... (Ab hier läuft deine bestehende for-Schleife für die Bücher-Zeilen eins zu eins weiter)

                for item in zeitraeume_dieses_jahr:
                    with ui.row().classes('w-full items-center no-wrap gap-2 py-1.5 border-b border-slate-200/5 dark:border-slate-700/30'):
                        with ui.row().classes('w-1/4 items-center gap-2 no-wrap cursor-pointer group').on('click', lambda _, id=item['id']: ui.navigate.to(f'/book/{id}')):
                            cover_url = database.hole_cover_url(item['id'])
                            with ui.element('div').classes('w-5 h-7 rounded bg-slate-200 dark:bg-slate-900 overflow-hidden shadow-xs flex-shrink-0'):
                                if cover_url != "/covers/placeholder.jpg":
                                    ui.image(cover_url).classes('w-full h-full object-cover')
                                else:
                                    ui.icon('book', size='12px').classes('mx-auto mt-1 text-slate-400')
                            ui.label(item['title']).classes(f'text-xs font-bold truncate group-hover:text-blue-500 transition-colors {text_main}')
                        
                        with ui.element('div').classes('w-3/4 h-5 bg-slate-200/20 dark:bg-slate-900/40 rounded relative overflow-hidden'):
                            tag_start = max(1, (item['start'] - start_des_jahres).days + 1)
                            tag_ende = min(tage_im_jahr, (item['end'] - start_des_jahres).days + 1)
                            linke_position = ((tag_start - 1) / tage_im_jahr) * 100
                            breite = ((tag_ende - tag_start + 1) / tage_im_jahr) * 100
                            
                            ui.element('div').classes('absolute h-full bg-blue-500/70 hover:bg-blue-500 rounded-sm cursor-pointer transition-all hover:scale-y-105') \
                                .style(f"left: {linke_position}%; width: {breite}%;") \
                                .on('click', lambda _, id=item['id']: ui.navigate.to(f'/book/{id}'))
                            ui.tooltip(f"{item['title']}: {item['start'].strftime('%d.%m.%Y')} - {item['end'].strftime('%d.%m.%Y')}")


# =========================================================================
# --- DIE HAUPT-PAGE ---
# =========================================================================
@ui.page('/calendar')
def kalender_ansicht():
    global details_dialog, details_container, details_titel
    
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    is_dark = user_ui['dark_mode']
    
    bg_card = 'bg-slate-800 border-slate-700 text-slate-100' if is_dark else 'bg-slate-50 border-slate-200 text-slate-700'
    bg_tages_kachel = 'bg-slate-900/40 border-slate-700/50' if is_dark else 'bg-white border-slate-100'
    text_main = 'text-slate-100' if is_dark else 'text-slate-800'
    text_sub = 'text-slate-400' if is_dark else 'text-slate-500'
    
    with basis_layout('calendar'):
        # Globaler Dialog
        with ui.dialog() as details_dialog, ui.card().classes(f'w-full max-w-sm p-4 {bg_card}'):
            details_titel = ui.label("").classes(f'text-base font-bold {text_main} mb-2')
            details_container = ui.column().classes('w-full gap-2')
            
            with ui.row().classes('w-full justify-end mt-2'):
                ui.button(t('cancel'), on_click=details_dialog.close).props('flat').classes('text-slate-500 text-xs')

        # Header Struktur
        with ui.row().classes('w-full justify-between items-center mb-6 flex-wrap gap-4'):
            with ui.element('div'):
                ui.label(t('calendar_title')).classes(f'text-2xl font-bold {text_main}')
                ui.label(t('calendar_subtitle')).classes(f'text-sm {text_sub}')
            
            with ui.row().classes('bg-slate-200 dark:bg-slate-800 p-1 rounded-lg shadow-inner'):
                # REPARIERT: Klick-Events werden JETZT HIER exakt EINMAL beim Seitenaufruf gebunden
                btn_cover = ui.button(t('cal_mode_covers'), on_click=lambda: modus_wechseln('COVER')).props('flat dense')
                btn_time = ui.button(t('cal_mode_timeline'), on_click=lambda: modus_wechseln('TIMELINE')).props('flat dense')

        # Erste Ausführung der globalen Rendering-Zone
        kalender_rendering_zone(text_main, text_sub, bg_tages_kachel, bg_card, btn_cover, btn_time)