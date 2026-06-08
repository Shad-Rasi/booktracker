import httpx
import os
import urllib.parse
import re  # Für die Textmustersuche

COVER_DIR = os.path.join('data', 'covers')
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

def daten_bereinigen(volume_info, isbn):
    """Interne Hilfsfunktion, um die Google-Daten für unsere DB-Struktur zu normieren."""
    autoren = volume_info.get("authors", [])
    image_links = volume_info.get("imageLinks", {})
    cover_url = image_links.get("thumbnail") or image_links.get("smallThumbnail", "")
    
    if cover_url and cover_url.startswith("http://"):
        cover_url = cover_url.replace("http://", "https://")

    return {
        'title': volume_info.get("title", ""),
        'subtitle': volume_info.get("subtitle", ""),
        'author': ", ".join(autoren) if autoren else "",
        'publisher': volume_info.get("publisher", ""),
        'published_date': volume_info.get("publishedDate", ""),
        'language': volume_info.get("language", "de"),
        'description': volume_info.get("description", ""),
        'pages': volume_info.get("pageCount", 0),
        'cover_url': cover_url
    }

async def isbn_suche_async(isbn_wert):
    """Asynchroner Abruf für den Massen-Import (blockiert den Server nicht)."""
    isbn_clean = isbn_wert.strip().replace("-", "")
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn_clean}"
    if GOOGLE_API_KEY:
        url += f"&key={GOOGLE_API_KEY}"
        
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=5.0)
            res_data = response.json()
            
            if "items" not in res_data:
                url_fallback = f"https://www.googleapis.com/books/v1/volumes?q={isbn_clean}"
                if GOOGLE_API_KEY:
                    url_fallback += f"&key={GOOGLE_API_KEY}"
                response = await client.get(url_fallback, timeout=5.0)
                res_data = response.json()
                
            if "items" in res_data:
                return daten_bereinigen(res_data["items"][0]["volumeInfo"], isbn_clean)
        except Exception as e:
            print(f"Async API-Fehler für ISBN {isbn_clean}: {str(e)}")
    return None

def isbn_suche_sync(isbn_wert):
    """Synchroner Abruf für das manuelle Formular (Direktanzeige im UI)."""
    isbn_clean = isbn_wert.strip().replace("-", "")
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn_clean}"
    if GOOGLE_API_KEY:
        url += f"&key={GOOGLE_API_KEY}"
        
    try:
        with httpx.Client() as client:
            response = client.get(url, timeout=5.0)
            res_data = response.json()
            
            if "items" not in res_data:
                url_fallback = f"https://www.googleapis.com/books/v1/volumes?q={isbn_clean}"
                if GOOGLE_API_KEY:
                    url_fallback += f"&key={GOOGLE_API_KEY}"
                response = client.get(url_fallback, timeout=5.0)
                res_data = response.json()
                
            if "items" in res_data:
                return daten_bereinigen(res_data["items"][0]["volumeInfo"], isbn_clean)
    except Exception as e:
        print(f"Sync API-Fehler für ISBN {isbn_clean}: {str(e)}")
    return None

async def google_bildsuche_async(titel, autor, isbn=""):
    """
    Sucht Cover-Bilder über die freie Open Library API.
    Der Funktionsname bleibt gleich, damit in der book.py nichts geändert werden muss.
    """
    bild_urls = []
    isbn_clean = isbn.strip().replace("-", "") if isbn else ""
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        # Strategie 1: Wenn eine ISBN vorhanden ist, versuchen wir den Direktlink
        if isbn_clean:
            # Open Library bietet Cover in den Größen S, M, L an. Wir nehmen 'L' für große Auflösung.
            direkt_url = f"https://covers.openlibrary.org/b/isbn/{isbn_clean}-L.jpg"
            
            try:
                # Wir prüfen kurz, ob Open Library das Cover wirklich hat.
                # Wenn sie es nicht haben, geben sie ein 1x1 Pixel großes Blindgänger-Bild zurück.
                check_res = await client.get(direkt_url, timeout=3.0)
                if check_res.status_code == 200 and len(check_res.content) > 1000:
                    bild_urls.append(direkt_url)
            except Exception as e:
                print(f"ISBN-Cover-Check fehlgeschlagen: {e}")

        # Strategie 2: Titelsuche über die Open Library API (als Ergänzung oder falls ISBN fehlschlägt)
        try:
            suchbegriff = f"{titel} {autor}".strip()
            search_url = f"https://openlibrary.org/search.json?q={urllib.parse.quote_plus(suchbegriff)}&limit=5"
            
            response = await client.get(search_url, timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                docs = data.get("docs", [])
                
                for doc in docs:
                    # Open Library speichert interne Cover-IDs im Feld 'cover_i'
                    cover_id = doc.get("cover_i")
                    if cover_id:
                        url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
                        if url not in bild_urls:
                            bild_urls.append(url)
                            
                    # Falls das Buch ISBNs hinterlegt hat, ziehen wir uns die auch noch als Cover-Quelle
                    isbn_list = doc.get("isbn", [])
                    for i in isbn_list[:2]:  # Max 2 zusätzliche ISBNs prüfen
                        url = f"https://covers.openlibrary.org/b/isbn/{i}-L.jpg"
                        if url not in bild_urls:
                            # Wir fügen sie hinzu; der Download-Mechanismus filtert später kaputte Bilder
                            bild_urls.append(url)
                            
                    if len(bild_urls) >= 8:
                        break
                        
        except Exception as e:
            print(f"Fehler bei OpenLibrary Titelsuche für {titel}: {e}")

    # Falls gar nichts gefunden wurde, setzen wir als allerletzten Strohhalm 
    # die Standard-Such-URL von Google Books als Bild ein (manchmal klappt es)
    if not bild_urls and isbn_clean:
        bild_urls.append(f"https://books.google.com/books/content?id=&printsec=frontcover&img=1&zoom=1&source=gbs_api&isbn={isbn_clean}")

    print(f"Cover-Suche erfolgreich! {len(bild_urls)} Bilder für '{titel}' bereitgestellt.")
    return bild_urls[:8]

async def hole_autoren_metadaten_async(autoren_name):
    """
    Sucht einen Autoren bei Open Library und gibt Bio, Lebensdaten 
    und die URL zum Profilbild zurück.
    """
    if not autoren_name or autoren_name.lower() == "unbekannter autor":
        return None
        
    # Open Library reagiert allergisch auf Zusätze wie "(Hrsg.)" oder Kommata.
    # Wir nehmen den reinen Namen für die Suche.
    sauberer_name = autoren_name.split(',')[0].split('(')[0].strip()
    search_url = f"https://openlibrary.org/search/authors.json?q={urllib.parse.quote_plus(sauberer_name)}"
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=8.0) as client:
        try:
            # 1. Schritt: ID des Autors suchen
            response = await client.get(search_url)
            if response.status_code != 200:
                return None
                
            data = response.json()
            docs = data.get("docs", [])
            if not docs:
                return None
                
            # Wir nehmen den ersten, relevantesten Treffer
            author_key = docs[0].get("key") # Liefert z.B. "OL26320A"
            if not author_key:
                return None
                
            # 2. Schritt: Detail-Daten mit der ID abfragen
            detail_url = f"https://openlibrary.org/authors/{author_key}.json"
            detail_res = await client.get(detail_url)
            if detail_res.status_code != 200:
                return None
                
            detail_data = detail_res.json()
            
            # Biografie extrahieren (kann ein String oder ein Dict sein)
            bio_raw = detail_data.get("bio", "")
            bio = bio_raw.get("value", "") if isinstance(bio_raw, dict) else bio_raw
            
            # Lebensdaten extrahieren
            birth_date = detail_data.get("birth_date", "")
            death_date = detail_data.get("death_date", "")
            
            # Bild-URL generieren (falls ein Foto hinterlegt ist)
            # Open Library nutzt IDs aus dem 'photos'-Array
            photos = detail_data.get("photos", [])
            image_url = ""
            if photos and photos[0] > 0:
                image_url = f"https://covers.openlibrary.org/b/id/{photos[0]}-L.jpg"
                
            return {
                'bio': bio,
                'birth_date': birth_date,
                'death_date': death_date,
                'image_url': image_url
            }
            
        except Exception as e:
            print(f"Fehler beim Abruf der Autoren-API für {autoren_name}: {e}")
            return None