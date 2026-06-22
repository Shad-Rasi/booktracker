# logger.py
from datetime import datetime
import translations
from translations import t

# Das ist jetzt der EINZIGE Puffer im gesamten System
UI_LOG_BUFFER = ["[System] Booktracker Log-Schnittstelle initialisiert..."]

def ui_log_lang(translation_key, **kwargs):
    """
    Schreibt eine übersetzte Zeile in das Docker-Terminal UND in den UI-Puffer.
    Nutzt .format() für übergebene Variablen.
    """
    try:
        # Text übersetzen und Variablen einsetzen
        rohtext = t(translation_key)
        # Falls die Übersetzung fehlschlägt und nur der Key zurückkommt
        if rohtext == translation_key:
            nachricht = f"[Log-System] {translation_key} {str(kwargs)}"
        else:
            nachricht = rohtext.format(**kwargs)
    except Exception as e:
        nachricht = f"[Log-Fehler] {translation_key}: {str(e)}"

    # Ab ins Docker-Terminal
    print(nachricht, flush=True)
    
    # Ab in den Web-Puffer
    zeit = datetime.now().strftime('%X')
    UI_LOG_BUFFER.append(f"[{zeit}] {nachricht}")
    
    if len(UI_LOG_BUFFER) > 100:
        UI_LOG_BUFFER.pop(0)