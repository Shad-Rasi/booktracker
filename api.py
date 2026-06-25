from fastapi import APIRouter, Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
import os
import database

router = APIRouter(prefix="/api/v1", tags=["Home Assistant"])

API_AKTIV = False

# =========================================================================
# API-KEY SCHUTZ FÜR AUTHELIA-BYPASS
# =========================================================================
# Definiert den Header-Namen. HA muss diesen mitschicken.
API_KEY_NAME = "X-Booktracker-Token"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Holt das erwartete Token aus den Umgebungsvariablen deines Containers
# Falls nicht gesetzt, ist das Standard-Passwort 'change_me_in_production'
EXPECTED_API_KEY = os.getenv("BOOKTRACKER_API_KEY", "")

async def get_api_key(api_key: str = Security(api_key_header)):
    # WENN ein Key im Container hinterlegt wurde, MUSS er matchen
    if EXPECTED_API_KEY:
        if api_key == EXPECTED_API_KEY:
            return api_key
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiger oder fehlender API-Key (X-Booktracker-Token)"
        )
    # WENN kein Key hinterlegt ist (lokales Heimnetz), einfach durchwinken
    return None
# =========================================================================


@router.get("/stats")
async def get_stats(api_key: str = Security(get_api_key)):
    """Holt die Buchstatistiken, wenn die API global aktiviert ist."""
    
    # HIER DIE PRÜFUNG: Wenn False, kommt keiner durch
    if not API_AKTIV:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API ist in den Einstellungen deaktiviert."
        )
    
    # 1. Alle registrierten User sauber aus der DB holen
    user_liste = database.lade_alle_user() 

    user_daten = {}
    gesamt_buecher_set = set()

    # 2. Schleife über jeden User, um den "Userteil" zu berechnen
    for u_id, u_name in user_liste:
        rows = database.lade_buecher_aus_db(u_id)
        
        reading_books = []
        read_books_count = 0
        last_finished_book = "Keines"
        beendete_buecher = []

        for r in rows:
            titel = r[1]
            status_wert = r[5]
            finished_at = r[12] # Index 12 aus deiner SQL-Query
            
            # Für die globale Zählung merken
            gesamt_buecher_set.add(r[0])
            
            if status_wert == 'READING':
                reading_books.append(titel)
            elif status_wert == 'READ':
                read_books_count += 1
                # Wir merken uns Titel und das echte Beendigungsdatum
                beendete_buecher.append({
                    "titel": titel,
                    "datum": finished_at if finished_at else "0000-00-00"
                })

        # Jetzt sortieren wir die Liste nach dem Datum (ältestes zuerst, neuestes ganz hinten)
        if beendete_buecher:
            beendete_buecher.sort(key=lambda x: x["datum"])
            last_finished_book = beendete_buecher[-1]["titel"]

        # Den Userteil für diesen spezifischen User befüllen
        user_daten[u_name.lower()] = {
            "currently_reading": reading_books,
            "books_read": read_books_count,
            "last_finished_book": last_finished_book
        }

    # 3. Das finale JSON-Format zusammenbauen
    return {
        "general": {
            "status": "online",
            "books_total": len(gesamt_buecher_set),
            "users_count": len(user_liste)
        },
        "users": user_daten
    }