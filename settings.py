import csv
import io
import asyncio
from nicegui import ui, context
import database
import layout
from layout import basis_layout
from translations import t

@ui.page('/settings')
def einstellungen_seite():
    # 1. Darkmode-Zustand des Users ermitteln
    user_ui = database.lade_user_settings(layout.aktiver_user_id)
    is_dark = user_ui['dark_mode']
    
    # Props und Style-Zuweisungen generieren
    dark_prop = 'dark' if is_dark else ''
    select_prop = 'dark popup-content-class="dark"' if is_dark else ''
    style_modal = 'background-color: #1e293b; color: #f8fafc;' if is_dark else ''
    
    # Adaptive CSS-Klassen für Container und Texte
    bg_card = 'bg-slate-800 border-slate-700 text-slate-100' if is_dark else 'bg-slate-50 border-slate-200 text-slate-700'
    bg_pill = 'bg-slate-900 text-slate-200' if is_dark else 'bg-slate-200 text-slate-700'
    text_main = 'text-slate-100' if is_dark else 'text-slate-700'
    text_sub = 'text-slate-400' if is_dark else 'text-slate-500'

    with basis_layout('settings'):
        ui.label(t('settings_title')).classes(f'text-2xl font-bold mb-2 {text_main}')
        ui.label(t('settings_subtitle')).classes(f'text-sm mb-6 {text_sub}')
        
        with ui.element('div').classes('w-full max-w-4xl flex flex-col gap-8'):
            
            # ==========================================
            # SEKTION 1: BENUTZERVERWALTUNG
            # ==========================================
            with ui.card().classes(f'w-full p-6 border shadow-sm {bg_card}'):
                ui.label(t('user_management')).classes(f'text-lg font-bold {text_main} mb-2')
                
                with ui.row().classes('w-full items-center gap-4 no-wrap mb-4'):
                    neuer_user_input = ui.input(label=t('new_username')).classes('flex-1 dark:bg-slate-900').props(f'outlined {dark_prop}')
                    
                    async def user_speichern():
                        name = neuer_user_input.value.strip()
                        if not name:
                            ui.notify(t('error_empty_name'), type='warning')
                            return
                        if database.speichere_user_in_db(name):
                            ui.notify(f'{t("user")} "{name}" {t("notify_user_added")}', type='positive')
                            neuer_user_input.value = ''
                            user_liste_refresh.refresh()
                        else:
                            ui.notify(t('error_user_exists'), type='negative')
                            
                    ui.button(icon='person_add', on_click=user_speichern).classes('bg-slate-700 text-white p-3 rounded')
                
                ui.separator().classes('my-4 dark:bg-slate-700')
                ui.label(t('existing_users')).classes(f'text-sm font-bold mb-2 {text_sub}')
                
                @ui.refreshable
                def user_liste_refresh():
                    user_liste = database.lade_alle_user()
                    with ui.element('div').classes('flex flex-wrap gap-2'):
                        for u_id, u_name in user_liste:
                            with ui.element('div').classes(f'flex items-center rounded-full pl-3 pr-1 py-1 gap-2 shadow-sm {bg_pill}'):
                                ui.label(u_name).classes('text-sm font-medium')
                                
                                if u_id == layout.aktiver_user_id:
                                    ui.badge(t('active'), color='blue').classes('text-[10px]')
                                else:
                                    async def user_loeschen_klick(id_zu_loeschen=u_id, name_zu_loeschen=u_name):
                                        with ui.dialog() as dialog, ui.card().classes('p-4 w-full max-w-sm flex flex-col gap-4').style(style_modal):
                                            ui.label(f'{t("confirm_delete_user_text")} "{name_zu_loeschen}"?').classes('text-sm text-slate-600 dark:text-slate-300 mb-4')
                                            with ui.row().classes('w-full justify-end gap-2'):
                                                ui.button(t('cancel'), on_click=dialog.close).classes('text-slate-500').props('flat')
                                                
                                                async def definitiv_loeschen():
                                                    if database.loesche_user_aus_db(id_zu_loeschen):
                                                        ui.notify(f'"{name_zu_loeschen}" {t("notify_user_deleted")}', type='info')
                                                        user_liste_refresh.refresh()
                                                    dialog.close()
                                                    
                                                ui.button(t('delete'), on_click=definitiv_loeschen).classes('bg-red-500 text-white')
                                        dialog.open()
                                    
                                    ui.button(icon='close', on_click=user_loeschen_klick).props('round dense flat size=sm').classes('text-red-500 hover:bg-red-900/30')
                user_liste_refresh()

            # ==========================================
            # SEKTION 2: REGAL- / STANDORTVERWALTUNG
            # ==========================================
            with ui.card().classes(f'w-full p-6 border shadow-sm {bg_card}'):
                ui.label(t('manage_locations')).classes(f'text-lg font-bold {text_main} mb-2')
                
                with ui.row().classes('w-full items-center gap-4 no-wrap mb-4'):
                    neues_regal_input = ui.input(label=t('location_name')).classes('flex-1 dark:bg-slate-900').props(f'outlined {dark_prop}')
                    
                    async def regal_speichern():
                        name = neues_regal_input.value.strip()
                        if not name:
                            ui.notify(t('error_empty_name'), type='warning')
                            return
                        if database.speichere_regal_in_db(name):
                            ui.notify(f'"{name}" {t("notify_location_added")}', type='positive')
                            neues_regal_input.value = ''
                            regal_liste_refresh.refresh()
                        else:
                            ui.notify(t('error_location_exists'), type='negative')
                            
                    ui.button(icon='add', on_click=regal_speichern).classes('bg-slate-700 text-white p-3 rounded')

                ui.separator().classes('my-4 dark:bg-slate-700')
                ui.label(t('existing_locations')).classes(f'text-sm font-bold mb-2 {text_sub}')
                
                @ui.refreshable
                def regal_liste_refresh():
                    regale = database.lade_alle_regale()
                    with ui.element('div').classes('flex flex-wrap gap-2'):
                        for r_id, r_name in regale:
                            with ui.element('div').classes(f'flex items-center rounded-full pl-3 pr-1 py-1 gap-2 shadow-sm {bg_pill}'):
                                ui.label(r_name).classes('text-sm font-medium')
                                
                                async def regal_loeschen_klick(id_zu_loeschen=r_id, name_zu_loeschen=r_name):
                                    with ui.dialog() as dialog, ui.card().classes('p-4 w-full max-w-sm flex flex-col gap-4').style(style_modal):
                                        ui.label(f'"{name_zu_loeschen}" {t("confirm_delete_location_text")}').classes('text-sm text-slate-600 dark:text-slate-300 mb-4')
                                        with ui.row().classes('w-full justify-end gap-2'):
                                            ui.button(t('cancel'), on_click=dialog.close).classes('text-slate-500').props('flat')
                                            
                                            async def definitiv_loeschen():
                                                if database.loesche_regal_aus_db(id_zu_loeschen):
                                                    ui.notify(f'"{name_zu_loeschen}" {t("notify_location_deleted")}', type='info')
                                                    regal_liste_refresh.refresh()
                                                dialog.close()
                                                
                                            ui.button(t('delete'), on_click=definitiv_loeschen).classes('bg-red-500 text-white')
                                    dialog.open()
                                ui.button(icon='close', on_click=regal_loeschen_klick).props('round dense flat size=sm').classes('text-red-500 hover:bg-red-900/30')
                regal_liste_refresh()

            # ==========================================
            # SEKTION 3: UI & DARSTELLUNGS-EINSTELLUNGEN
            # ==========================================
            with ui.card().classes(f'w-full p-6 border shadow-sm {bg_card}'):
                ui.label(t('ui_design_title')).classes(f'text-lg font-bold {text_main} mb-2')
                ui.label(t('ui_design_subtitle')).classes(f'text-xs {text_sub} -mt-2 mb-4')
                
                current_settings = database.lade_user_settings(layout.aktiver_user_id)
                
                async def ui_einstellungen_speichern():
                    database.speichere_user_settings(layout.aktiver_user_id, ansicht_select.value, dark_switch.value)
                    if dark_switch.value:
                        ui.dark_mode().enable()
                    else:
                        ui.dark_mode().disable()
                    ui.notify(t('notify_saved'), type='positive', duration=1)
                    await asyncio.sleep(0.2)
                    ui.navigate.to('/settings')

                with ui.row().classes('w-full items-center justify-between gap-4 flex-wrap'):
                    view_opts = {
                        'PAGINATED': f"📄 {t('view_paginated')}", 
                        'INFINITE': f"📜 {t('view_infinite')}"
                    }
                    ansicht_select = ui.select(
                        options=view_opts, 
                        value=current_settings['view_mode'],
                        label=t('shelf_view_mode'),
                        on_change=ui_einstellungen_speichern
                    ).classes('w-64 dark:bg-slate-900 px-2 rounded').props(f'outlined dense {select_prop}')
                    
                    dark_switch = ui.switch(
                        t('activate_darkmode'), 
                        value=current_settings['dark_mode'],
                        on_change=ui_einstellungen_speichern
                    ).classes(f'font-medium {text_main}')