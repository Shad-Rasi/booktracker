from contextlib import contextmanager
from datetime import datetime
from nicegui import ui
import database
import translations

# Sitzungsspeicher für den aktuell ausgewählten User (Standard: ID 1)
aktiver_user_id = 1

def quick_log_modal():
    """Öffnet ein globales Dialogfenster für den schnellen Lese-Eintrag."""
    global aktiver_user_id
    
    # Aktive Bücher aus der DB holen (nur solche mit Status 'READING')
    aktive_buecher = database.lade_aktuelle_buecher(aktiver_user_id)
    
    if not aktive_buecher:
        ui.notify('Du hast aktuell keine Bücher auf "Am Lesen" stehen!', type='warning')
        return

    # Optionen-Dict für das Dropdown bauen: {buch_id: "Buchtitel"}
    buch_optionen = {b_id: b_title for b_id, b_title in aktive_buecher}

    with ui.dialog() as log_dialog, ui.card().classes('w-full max-w-md p-6 flex flex-col gap-4'):
        ui.label('Lese-Etappe schnellbuchen ⚡').classes('text-lg font-bold text-slate-700 mb-2')
        
        # 1. Buch-Auswahl Dropdown
        buch_select = ui.select(options=buch_optionen, label='Buch auswählen') \
            .classes('w-full').props('outlined dense')
        
        # 2. Seiten-Eingabe
        seiten_input = ui.number(label='Gelesen bis Seite', value=None, min=1) \
            .classes('w-full').props('outlined dense')
        
        # 3. Datums-Eingabe (Standard: Heute)
        heute_str = datetime.now().strftime('%Y-%m-%d')
        with ui.input(label='Datum', value=heute_str).classes('w-full').props('outlined dense') as datum_input:
            with datum_input.add_slot('append'):
                # Kleiner Kalender-Popup bei Klick auf das Icon
                ui.icon('access_time').classes('cursor-pointer').on('click', lambda: menu.open())
                with ui.menu() as menu:
                    ui.date().bind_value(datum_input)

        # Speicher-Logik
        # Speicher-Logik in layout.py
        async def schnell_log_speichern():
            b_id = buch_select.value
            neue_seite = seiten_input.value
            gewaehltes_datum = datum_input.value
            
            if not b_id:
                ui.notify('Bitte wähle ein Buch aus!', type='warning')
                return
            if not neue_seite:
                ui.notify('Bitte gib die aktuelle Seitenzahl ein!', type='warning')
                return

            # Wir holen uns kurz die Gesamtseiten aus der DB, um den Status-Wechsel zu prüfen
            with database.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT pages FROM books WHERE id = ?", (b_id,))
                row = cursor.fetchone()
                max_pages = row[0] if row and row[0] else 0

            erfolg, meldung = database.trage_lese_log_ein(
                aktiver_user_id, 
                b_id, 
                int(neue_seite), 
                gewaehltes_datum
            )
            
            if erfolg:
                ui.notify(f'Eintrag gesichert! +{meldung} Seiten.', type='positive')
                
                # --- FIX im Quick-Log der layout.py ---
                if max_pages > 0 and int(neue_seite) >= max_pages:
                    # Gewähltes Datum (gewaehltes_datum) an den Abschluss übergeben!
                    database.schliesse_aktiven_zyklus_ab(aktiver_user_id, b_id, end_datum=gewaehltes_datum)
                    
                    with database.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE user_books SET status = 'READ' WHERE user_id = ? AND book_id = ?", (aktiver_user_id, b_id))
                        conn.commit()
                    ui.notify('Buch erfolgreich beendet! 🎉', type='positive')

                log_dialog.close()
                ui.run_javascript('window.location.reload()')
            else:
                ui.notify(meldung, type='warning')

        # Buttons
        with ui.row().classes('w-full justify-end gap-2 mt-2'):
            ui.button(translations.t('cancel'), on_click=log_dialog.close).classes('text-slate-500').props('flat')
            ui.button(translations.t('save'), on_click=schnell_log_speichern).classes('bg-emerald-600 text-white px-4')

    log_dialog.open()


@contextmanager
def basis_layout(titel_key: str = None):
    global aktiver_user_id
    
    # 1. Benutzer aus der DB laden
    alle_user = database.lade_alle_user()
    # Erstellt ein Dictionary für das Dropdown: {1: 'Ich', 2: 'Meine Frau'}
    user_options = {u[0]: u[1] for u in alle_user}
    
    # Falls der Speicher ungültig ist, auf den ersten existierenden User zurückfallen
    if aktiver_user_id not in user_options and user_options:
        aktiver_user_id = list(user_options.keys())[0]

    # Seitentitel setzen
    titel_text = translations.t(titel_key) if titel_key in translations.TRANSLATIONS[translations.aktuelle_sprache] else (titel_key or "Booktracker")
    ui.page_title(titel_text)
    
    # Header-Navigation
    with ui.header().classes('bg-slate-800 text-white p-4 flex justify-between items-center shadow-md z-[100]'):
        with ui.row().classes('gap-6 font-medium items-center'):
            ui.link(translations.t('my_shelf'), '/').classes('text-white hover:text-slate-300 no-underline text-lg')
            ui.link(translations.t('authors'), '/authors').classes('text-white hover:text-slate-300 no-underline text-lg')
            ui.link(translations.t('stats'), '/statistics').classes('text-white hover:text-slate-300 no-underline text-lg')
            ui.link(translations.t('calendar'), '/calendar').classes('text-white hover:text-slate-300 no-underline text-lg')
            ui.link(translations.t('import'), '/import').classes('text-white hover:text-slate-300 no-underline text-lg')
        
        with ui.row().classes('items-center gap-4'):
            # SCHNELLZUGRIFFS-BUTTON (Blitzt auf, wenn Bücher aktiv gelesen werden)
            ui.button(
                icon='bookmark_add', 
                on_click=quick_log_modal
            ).props('round flat dense size=md') \
             .classes('text-emerald-400 hover:bg-slate-700') \
             .tooltip('Lese-Etappe schnellbuchen')

            # DYNAMISCHER PERSONENUMSCHALTER
            def user_wechseln(e):
                global aktiver_user_id
                aktiver_user_id = e.value
                ui.run_javascript('window.location.reload()')

            ui.select(
                options=user_options, 
                value=aktiver_user_id, 
                on_change=user_wechseln
            ).props('dark dense options-dense borderless').classes('w-36 text-white text-sm font-bold bg-slate-700 px-2 py-1 rounded')

            ui.separator().props('vertical').classes('bg-slate-600 h-6')

            # SPRACHUMSCHALTER
            def sprache_wechseln(e):
                translations.aktuelle_sprache = e.value
                ui.run_javascript('window.location.reload()')

            ui.select(
                options={'de': '🇩🇪 DE', 'en': '🇬🇧 EN'}, 
                value=translations.aktuelle_sprache, 
                on_change=sprache_wechseln
            ).props('dark dense options-dense borderless').classes('w-20 text-white text-sm')
        
    with ui.element('div').classes('w-full p-6 max-w-7xl mx-auto pt-5'):
        yield