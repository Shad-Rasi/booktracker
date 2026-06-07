from contextlib import contextmanager
from nicegui import ui
import database
import translations

# Sitzungsspeicher für den aktuell ausgewählten User (Standard: ID 1)
aktiver_user_id = 1

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
            ui.link(translations.t('add_book'), '/add').classes('text-white hover:text-slate-300 no-underline text-lg')
        
        with ui.row().classes('items-center gap-4'):
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