import os
import random
from nicegui import ui
import database
import layout
from layout import basis_layout 
import translations
from translations import t

# Globale Variable für den Suchtext im RAM
genre_suchtext = ""

@ui.page('/genres')
def genres_uebersicht():
    """Zeigt das saubere Genre-Grid mit Live-Suche ohne Fallbacks und ohne Formatzeile."""
    global genre_suchtext
    genre_suchtext = ""  # Bei jedem Laden der Seite die Suche zurücksetzen
    
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    is_dark = user_ui['dark_mode']
    
    bg_card = 'bg-slate-800 border-slate-700 hover:border-slate-500' if is_dark else 'bg-white border-slate-200 hover:border-slate-400'
    text_title = 'text-slate-100' if is_dark else 'text-slate-800'
    text_sub = 'text-slate-400' if is_dark else 'text-slate-500'

    # REPARIERT: Nutzt jetzt den Key 'manage_genres' für den Browsertab
    with basis_layout('manage_genres'):
        # --- HEADER ---
        ui.label(t('manage_genres')).classes(f'text-2xl font-black mb-1 {text_title}')
        ui.label(t('genre_subtitle') if 'genre_subtitle' in translations.TRANSLATIONS[translations.aktuelle_sprache] else "Stöbere in den verschiedenen Kategorien deiner Bibliothek.").classes(f'text-sm {text_sub} mb-6')

        # Alle globalen Genres vorab aus der DB laden
        alle_genres = database.lade_alle_genres(layout.aktiver_user_id)
        
        if not alle_genres:
            with ui.card().classes('w-full p-8 text-center border bg-slate-50 dark:bg-slate-900/40'):
                ui.label(t('no_genres_hint')).classes('text-slate-400 italic')
            return

        # =========================================================================
        # Einmaliger Cover-Cache für DIESEN Seitenaufruf
        # =========================================================================
        sitzung_cover_cache = {}
        genre_buch_counts = {}

        for g_id, g_name in alle_genres:
            buecher_in_genre = hole_buecher_nach_genre(layout.aktiver_user_id, g_name)
            genre_buch_counts[g_name] = len(buecher_in_genre)
            
            cover_url = "/covers/placeholder.jpg"
            if buecher_in_genre:
                zufaelliges_buch = random.choice(buecher_in_genre)
                cover_url = database.hole_cover_url(zufaelliges_buch[0])
            
            sitzung_cover_cache[g_name] = cover_url

        # --- SUCHFUNKTION ---
        with ui.card().classes('w-full p-4 bg-slate-100 dark:bg-slate-800 shadow-sm border border-slate-200 dark:border-slate-700 mb-6'):
            suchfeld = ui.input(
                placeholder=t('search'), 
                value=genre_suchtext, 
                on_change=lambda e: filter_genres_live(e.value)
            ).classes('w-full px-1').props(f'clearable icon=search outlined {"dark" if is_dark else ""}')

        # --- REFRESHABLE GRID ---
        @ui.refreshable
        def grid_rendern():
            global genre_suchtext
            such_begriff = genre_suchtext.lower().strip()
            
            # Genres basierend auf der Suche filtern
            gefilterte_genres = [
                (g_id, g_name) for g_id, g_name in alle_genres 
                if not such_begriff or such_begriff in g_name.lower()
            ]

            if not gefilterte_genres:
                with ui.card().classes('w-full p-8 text-center bg-slate-50 dark:bg-slate-900/20 col-span-full border border-dashed'):
                    ui.label(t('empty_shelf')).classes('text-slate-400 italic')
                return

            with ui.grid().classes('w-full grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-6'):
                for g_id, g_name in gefilterte_genres:
                    anzahl = genre_buch_counts.get(g_name, 0)
                    cover_url = sitzung_cover_cache.get(g_name, "/covers/placeholder.jpg")

                    with ui.card().classes(f'p-2 cursor-pointer hover:shadow-md transition-all h-full flex flex-col justify-between overflow-hidden border {bg_card}') \
                            .on('click', lambda _, name=g_name: ui.navigate.to(f'/genres/{name}')):
                        
                        with ui.element('div').classes('w-full flex flex-col gap-2'):
                            with ui.element('div').classes('relative w-full aspect-[2/3] rounded shadow-sm bg-slate-200 dark:bg-slate-900 flex items-center justify-center overflow-hidden'):
                                if cover_url != "/covers/placeholder.jpg":
                                    ui.image(cover_url).classes('w-full h-full object-cover')
                                else:
                                    with ui.element('div').classes('flex flex-col items-center text-slate-400 dark:text-slate-600 gap-1'):
                                        ui.icon('local_offer', size='md')
                            
                            with ui.element('div').classes('px-1 flex flex-col gap-0.5'):
                                ui.label(g_name).classes(f'font-bold text-xs md:text-sm line-clamp-2 leading-tight {text_title}')
                        
                        with ui.row().classes('w-full justify-between items-center mt-2 px-1 pt-1 border-t border-slate-200/10'):
                            text_buecher = t('book') if anzahl == 1 else t('books_count')
                            ui.badge(f"{anzahl} {text_buecher}", color='blue').classes('text-[9px] px-1.5 py-0.5')

        def filter_genres_live(wert):
            global genre_suchtext
            genre_suchtext = wert if wert else ""
            grid_rendern.refresh()

        grid_rendern()


@ui.page('/genres/{genre_name}')
def genre_detailseite(genre_name: str):
    """Detailseite, die alle Bücher eines spezifischen Genres anzeigt."""
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    is_dark = user_ui['dark_mode']
    
    bg_buch_karte = 'bg-slate-800 border-slate-700' if is_dark else 'bg-white border-slate-100'
    text_main = 'text-slate-100' if is_dark else 'text-slate-700'
    text_sub = 'text-slate-400' if is_dark else 'text-slate-500'

    # REPARIERT: Übergibt den reinen Genrenamen (z.B. "Fantasy") direkt starr an den Browsertab
    with basis_layout(genre_name):
        ui.button(t('back'), icon='arrow_back', on_click=lambda: ui.navigate.to('/genres')) \
            .props('flat dense').classes('text-slate-500 dark:text-slate-400 mb-4')
            
        genre_buecher = hole_buecher_nach_genre(layout.aktiver_user_id, genre_name)
        genre_buecher.sort(key=lambda x: (x[1] or "").lower())

        with ui.row().classes('items-center gap-2 mb-6'):
            ui.icon('local_offer', size='md').classes('text-blue-500 dark:text-blue-400')
            ui.label(genre_name).classes(f'text-3xl font-black {text_main}')
        
        if not genre_buecher:
            with ui.card().classes('w-full p-8 text-center border bg-slate-50 dark:bg-slate-900/40'):
                ui.label(t('empty_shelf')).classes('text-slate-400 italic')
            return

        with ui.grid().classes('w-full grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-6'):
            for b in genre_buecher:
                b_id, b_title, b_author = b[0], b[1], b[3]
                b_pages = b[14]
                
                b_status = b[20] or 'UNREAD'
                b_rating = b[21]
                b_ownership = b[23] or 'OWNED'
                
                if b_ownership == 'GIVEN_AWAY':
                    card_style = 'border: 1px dashed #ef4444;'
                    cover_classes = 'w-full h-full object-cover opacity-40 grayscale transition-all'
                else:
                    card_style = ''
                    cover_classes = 'w-full h-full object-cover transition-all'
                
                with ui.card().classes(f'p-2 cursor-pointer hover:shadow-md transition-shadow border {bg_buch_karte}') \
                        .style(card_style).on('click', lambda _, current_book_id=b_id: ui.navigate.to(f'/book/{current_book_id}')):
                    
                    with ui.element('div').classes('w-full flex flex-col justify-between h-full'):
                        with ui.element('div').classes('w-full flex flex-col gap-2'):
                            cover_pfad = database.hole_cover_url(b_id)
                            
                            with ui.element('div').classes('relative w-full aspect-[2/3] rounded shadow-sm bg-slate-200 dark:bg-slate-900 flex items-center justify-center overflow-hidden'):
                                if cover_pfad != "/covers/placeholder.jpg":
                                    ui.image(cover_pfad).classes(cover_classes)
                                else:
                                    ui.icon('book', size='sm').classes('text-slate-400' + (' opacity-40' if b_ownership == 'GIVEN_AWAY' else ''))
                                    
                            with ui.column().classes('px-1 gap-0.5 flex-1 justify-between min-h-[96px]'):
                                with ui.element('div').classes('w-full'):
                                    ui.label(b_title).classes(f'font-bold text-xs md:text-sm line-clamp-2 leading-tight {text_main}')
                                    ui.label(b_author if b_author else t('unknown_author')).classes(f'text-[11px] {text_sub} line-clamp-1 mt-0.5')
                                
                                with ui.element('div').classes('w-full flex flex-col gap-0.5 mt-auto'):
                                    with ui.row().classes('items-center gap-0.5 my-0.5'):
                                        b_rating_val = b_rating if b_rating is not None else 0
                                        if b_rating_val > 0:
                                            for star_idx in range(1, 6):
                                                star_icon = 'star' if star_idx <= b_rating_val else 'star_border'
                                                ui.icon(star_icon, size='14px').classes('text-amber-500')
                                        else:
                                            ui.label(t('none')).classes('text-[11px] text-slate-400 italic')
                                    
                                    with ui.row().classes('w-full items-center justify-between no-wrap'):
                                        ui.label(f"{b_pages or '?'} {t('pages_short')}").classes(f'text-[10px] {text_sub}')
                                        
                                        if b_ownership == 'GIVEN_AWAY':
                                            ui.label(t('ownership_given_away_short') if 'ownership_given_away_short' in translations.TRANSLATIONS[translations.aktuelle_sprache] else 'Weg').classes('text-[9px] text-red-500 dark:text-red-400 font-bold tracking-wide uppercase')
                        
                        with ui.row().classes('w-full mt-2 pt-1 px-1 border-t border-slate-200/10'):
                            badge_color = 'teal' if b_status == 'READ' else ('orange' if b_status == 'READING' else 'slate')
                            ui.badge(t(b_status.lower()), color=badge_color).classes('text-[9px] px-1.5 py-0.5')


def hole_buecher_nach_genre(user_id, genre_name):
    """Hilfsfunktion: Holt alle Bücher eines bestimmten Genres mit bereinigtem Join-Schema."""
    with database.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                b.id, b.title, b.subtitle, b.author, b.translator, b.narrator, b.illustrator, 
                b.editor, b.isbn_13, b.isbn_10, b.publisher, b.published_date, b.language, 
                b.description, b.pages, b.special, b.is_series, b.series_name, b.series_number, b.location_id,
                ub.status, ub.rating, b.format, b.ownership, b.quantity, l.name
            FROM books b
            JOIN book_genres bg ON b.id = bg.book_id
            JOIN genres g ON bg.genre_id = g.id
            JOIN user_books ub ON b.id = ub.book_id
            LEFT JOIN locations l ON b.location_id = l.id
            WHERE ub.user_id = ? AND g.name = ?
        """, (user_id, genre_name))
        return cursor.fetchall()