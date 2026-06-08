from nicegui import ui
import database
import layout
import translations
from layout import basis_layout
from translations import t
from collections import defaultdict
from datetime import datetime

@ui.page('/calendar')
def kalender_ansicht():
    with basis_layout('calendar'):
        ui.label('Mein Lese-Kalender').classes('text-2xl font-bold text-slate-700 mb-2')
        ui.label('Hier siehst du deine täglichen Lese-Einheiten im Überblick.').classes('text-sm text-slate-500 mb-6')
        
        # 1. Heutiges Datum im passenden Format ermitteln ('YYYY/MM/DD' - Quasar nutzt intern Slashes!)
        heute_str = datetime.now().strftime('%Y/%m-%d').replace('-', '/')
        
        # Logs aus der DB laden
        raw_logs = database.hole_kalender_daten_fuer_user(layout.aktiver_user_id)
        
        # Quasar-Kalender braucht das Datumsformat zwingend mit Slashes: '2026/06/08'
        lese_tage = list(set([row[0].replace('-', '/') for row in raw_logs]))
        
        # Für die rechte Liste behalten wir die Bindung bei (wird von ui.date als 'YYYY-MM-DD' oder 'YYYY/MM/DD' geliefert)
        logs_nach_datum = defaultdict(list)
        for row in raw_logs:
            d_date = row[0].replace('-', '/')  # Einheitlich auf Slashes bringen
            b_title = row[1]
            p_read = row[2]
            b_id = row[3] if len(row) > 3 else None
            logs_nach_datum[d_date].append({'title': b_title, 'pages': p_read, 'id': b_id})

        with ui.element('div').classes('w-full grid grid-cols-1 md:grid-cols-3 gap-6 items-start'):
            
            # LINKE SEITE: Der interaktive Kalender
            with ui.card().classes('p-4 border border-slate-200 shadow-sm md:col-span-1 items-center'):
                
                # --- NEU: Holt das saubere Locale direkt aus der translations.py ---
                # Falls du ein globales System für die aktuelle Sprache hast (z.B. layout.aktive_sprache), 
                # kannst du das hier statt 'de' übergeben.
                kalender_locale = translations.hole_kalender_locale('de')

                # Kalender initialisieren
                kalender = ui.date(value=heute_str, on_change=lambda e: update_detail_liste(e.value)) \
                    .props(f'today-btn outline first-day-of-week="1" :locale="{kalender_locale}"') \
                    .classes('shadow-none border-none')
                
                # Die JS-Prüffunktion für die grünen Punkte
                kalender.props(f':events="date => {lese_tage}.includes(date)" event-color="emerald"')
                
                # --- CSS-Hintergrund-Injekt (Kacheln voll ausfüllen) ---
                ui.add_head_html('''
                    <style>
                        /* Hintergrund für alle Tage mit Lese-Eintrag (die kleinen Punkte werden zu Kacheln expandiert) */
                        .q-date__calendar-days .q-date__event {
                            top: 2px !important;
                            left: 2px !important;
                            right: 2px !important;
                            bottom: 2px !important;
                            width: auto !important;
                            height: auto !important;
                            border-radius: 6px !important;
                            background-color: #10b981 !important; /* Smaragdgrün */
                            opacity: 0.18 !important; /* Angenehme Transparenz */
                            z-index: 0 !important;
                        }
                        /* Schiebt den Text der Zahl über die farbige Kachel */
                        .q-date__calendar-days .q-btn__content {
                            z-index: 2 !important;
                        }
                    </style>
                ''')

            # RECHTE SEITE: Die Info-Box für den ausgewählten Tag
            with ui.card().classes('p-6 border border-slate-200 shadow-sm md:col-span-2 min-h-[350px] flex flex-col justify-between'):
                detail_container = ui.element('div').classes('w-full')
                
                def update_detail_liste(gewaehltes_datum):
                    detail_container.clear()
                    with detail_container:
                        if not gewaehltes_datum:
                            ui.label('Wähle einen markierten Tag im Kalender aus, um deine Einheiten zu sehen.') \
                                .classes('text-slate-400 italic text-sm')
                            return
                        
                        # Formatierung vereinheitlichen
                        such_datum = gewaehltes_datum.replace('-', '/')
                        
                        ui.label(f"Aktivitäten am {such_datum}:").classes('text-base font-bold text-slate-700 mb-4')
                        
                        tages_logs = logs_nach_datum.get(such_datum, [])
                        if not tages_logs:
                            ui.label('An diesem Tag hast du keine Lese-Etappe eingetragen.').classes('text-sm text-slate-400 italic')
                            return
                            
                        for log in tages_logs:
                            ziel_url = f"/book/{log['id']}" if log['id'] else "#"
                            
                            with ui.link(target=ziel_url).classes('block no-underline hover:opacity-80 transition-opacity mb-2'):
                                with ui.element('div').classes('flex justify-between items-center bg-slate-50 hover:bg-slate-100 p-3 rounded border-l-4 border-emerald-500 cursor-pointer shadow-xs'):
                                    
                                    with ui.row().classes('items-center gap-2 flex-1 pr-4 no-wrap'):
                                        ui.icon('book', color='slate-400').classes('text-sm shrink-0')
                                        ui.label(log['title']).classes('font-medium text-slate-700 text-sm line-clamp-1')
                                        
                                    ui.badge(f"+{log['pages']} Seiten", color='emerald').classes('py-1 px-2 text-xs font-bold shrink-0')
                
                # Initialisiert die rechte Box direkt mit den Daten von HEUTE
                update_detail_liste(heute_str)