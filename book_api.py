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

    return bild_urls[:8]

async def hole_autoren_metadaten_async(autoren_name, isbn_liste=None):
    """
    Sucht vorrangig bei isbn.de nach der ersten Biografie und prüft Cover-Bilder.
    Nutzt Open Library STRENG NUR ALS FALLBACK für fehlende Infos/Bilder.
    """
    if not autoren_name or autoren_name.lower() == "unbekannter autor":
        return None
        
    sauberer_name = autoren_name.split(',')[0].split('(')[0].strip()
    
    final_data = {
        'bio': '',
        'birth_date': '',
        'death_date': '',
        'image_url': None
    }
    
    # === SPUND 1: REIN IN DEN ISBN.DE SCRAPER ===
    isbn_de_ergebnis = await scrape_autor_details_isbn_de_async(sauberer_name, isbn_liste)
    if isbn_de_ergebnis:
        final_data['bio'] = isbn_de_ergebnis.get('bio', '')
        final_data['birth_date'] = isbn_de_ergebnis.get('birth_date', '')
        final_data['image_url'] = isbn_de_ergebnis.get('image_url', None)

    # === SPUND 2: OPEN LIBRARY ALS BACKUP / ERGÄNZUNG ===
    # WICHTIG: Open Library darf die Bio NUR ergänzen, wenn isbn.de absolut NICHTS geliefert hat!
    import urllib.parse
    import httpx
    
    search_url = f"https://openlibrary.org/search/authors.json?q={urllib.parse.quote_plus(sauberer_name)}"
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=8.0) as client:
        try:
            response = await client.get(search_url)
            if response.status_code == 200:
                data = response.json()
                docs = data.get("docs", [])
                
                if docs:
                    author_key = docs[0].get("key")
                    if author_key:
                        detail_url = f"https://openlibrary.org/authors/{author_key}.json"
                        detail_res = await client.get(detail_url)
                        
                        if detail_res.status_code == 200:
                            detail_data = detail_res.json()
                            
                            # Lebensdaten und Bild-Fallback (das ist okay, da isbn.de das seltener hat)
                            if not final_data['birth_date'] and detail_data.get('birth_date'):
                                final_data['birth_date'] = detail_data['birth_date']
                                
                            if detail_data.get('death_date'):
                                final_data['death_date'] = detail_data['death_date']
                                
                            if not final_data['image_url']:
                                photos = detail_data.get("photos", [])
                                if photos and photos[0] > 0:
                                    final_data['image_url'] = f"https://covers.openlibrary.org/b/id/{photos[0]}-L.jpg"
                            
                            # STRENGER SCHUTZ FÜR DIE BIOGRAFIE:
                            # Nur wenn isbn.de keine Bio gefunden hat, laden wir die von Open Library
                            if not final_data['bio'].strip():
                                bio_raw = detail_data.get("bio", "")
                                ol_bio = bio_raw.get("value", "") if isinstance(bio_raw, dict) else bio_raw
                                final_data['bio'] = ol_bio
                                
        except Exception as e:
            print(f"Fehler beim OpenLibrary-Fallback für {autoren_name}: {e}")

    if not final_data['bio'] and not final_data['image_url']:
        return None
        
    return final_data

async def scrape_autor_details_isbn_de_async(sauberer_name, isbn_liste=None):
    """Scrapt die ERSTE Biografie von isbn.de und filtert das störende HTML-Modal heraus."""
    name_url_format = sauberer_name.replace(" ", "+")
    url = f"https://www.isbn.de/person/{name_url_format}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    from bs4 import BeautifulSoup
    import re
    import httpx
    
    res_daten = {'bio': '', 'birth_date': '', 'image_url': None}
    
    async with httpx.AsyncClient(timeout=5.0, headers=headers, follow_redirects=True) as client:
        try:
            response = await client.get(url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                article = soup.find('article', id='content')
                
                if article:
                    # STRENG NUR DAS ERSTE h2 ANFASSEN (Verhindert Dubletten)
                    # --- TEXT-EXTRAKTION (BASIEREND AUF DER ECHTEN HTML-STRUKTUR) ---
                    erstes_h2 = article.find('h2')
                    if erstes_h2:
                        # Wir gehen alle nachfolgenden Geschwisterelemente des h2 durch
                        for sibling in erstes_h2.find_next_siblings():
                            # Wenn wir auf das nächste h2 stoßen, stoppen wir (Ende des ersten Verlagsblocks)
                            if sibling.name == 'h2':
                                break
                            
                            # Wir suchen nach einem div, das den Text enthält
                            if sibling.name == 'div':
                                # Wenn es der Bild-Container mit dem Modal ist, ignorieren wir ihn
                                if sibling.find('div', id='myModal') or sibling.get('style') == 'float:right;':
                                    continue
                                
                                # Das hier ist das saubere Text-Div!
                                text = sibling.get_text(strip=True)
                                if text and not text.startswith("Hinweis:"):
                                    res_daten['bio'] = text
                                    break # Text gefunden, Schleife beenden

                    # Geburtsdaten-Extraktion aus der bereinigten Biografie
                    if res_daten['bio']:
                        jahr_match = re.search(r'(\d{4})\s+geborene', res_daten['bio'])
                        datum_match = re.search(r'am\s+(\d{1,2}\.\s*[a-zA-ZüäöÖÄÜß]+|\d{2}\.\d{2}\.)\s*(\d{4})', res_daten['bio'])
                        if datum_match:
                            res_daten['birth_date'] = f"{datum_match.group(1)} {datum_match.group(2)}".strip()
                        elif jahr_match:
                            res_daten['birth_date'] = jahr_match.group(1)
        except Exception as e:
            print(f"Fehler beim Scrapen von isbn.de Person: {e}")

        # --- BILD-VERARBEITUNG BLEIBT EXAKT WIE SIE WAR ---
        if isbn_liste and isinstance(isbn_liste, list):
            for isbn in isbn_liste:
                isbn_clean = str(isbn).strip().replace("-", "")
                if len(isbn_clean) != 13:
                    continue
                
                test_bild_url = f"https://lesen.isbn.de/{isbn_clean}_autorenbild-01.jpg"
                
                try:
                    img_check = await client.head(test_bild_url, timeout=2.5)
                    if img_check.status_code == 200:
                        res_daten['image_url'] = test_bild_url
                        break
                except Exception:
                    pass

    return res_daten if (res_daten['bio'] or res_daten['image_url']) else None


async def scrape_buch_details_isbn_de_async(isbn_wert):
    """Scrapt Buchinformationen inklusive Reihen-Details direkt von isbn.de."""
    if not isbn_wert:
        return None
        
    isbn_clean = str(isbn_wert).strip().replace("-", "")
    url = f"https://www.isbn.de/buch/{isbn_clean}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    from bs4 import BeautifulSoup
    import json
    import re
    
    async with httpx.AsyncClient(timeout=6.0, headers=headers, follow_redirects=True) as client:
        try:
            response = await client.get(url)
            if response.status_code != 200:
                return None
                
            soup = BeautifulSoup(response.text, 'html.parser')
            data = {}
            
            # 1. JSON-LD für Basisdaten auslesen (Jetzt MIT Titel und Autor!)
            script_tag = soup.find('script', type='application/ld+json')
            if script_tag:
                try:
                    json_data = json.loads(script_tag.string)
                    
                    # NEU: Titel und Autor direkt aus dem Schema-Strukturen ziehen
                    data['title'] = json_data.get('name', '')
                    
                    autoren_liste = json_data.get('author', [])
                    if isinstance(autoren_liste, list) and autoren_liste:
                        # Extrahiert die Namen aller gelisteten Autoren und fügt sie mit Komma zusammen
                        data['author'] = ", ".join([a.get('name', '') for a in autoren_liste if isinstance(a, dict)])
                    elif isinstance(autoren_liste, dict):
                        data['author'] = autoren_liste.get('name', '')
                    else:
                        data['author'] = ""
                        
                    data['description'] = json_data.get('description', '')
                    data['publisher'] = json_data.get('publisher', {}).get('name', '') if isinstance(json_data.get('publisher'), dict) else json_data.get('publisher', '')
                    data['published_date'] = json_data.get('datePublished', '')
                    data['pages'] = int(json_data.get('numberOfPages', 1))
                except Exception as json_err:
                    print(f"JSON-LD Fehler: {json_err}")

            # 2. PRÄZISER HTML-SCAN FÜR DIE REIHE
            # Wir suchen in der Infotabelle gezielt nach dem Kästchen, das "Reihe" enthält
            infotab = soup.find('div', class_='infotab')
            if infotab:
                for row_div in infotab.find_all('div', recursive=False):
                    row_text = row_div.get_text()
                    
                    if 'Reihe' in row_text:
                        reihen_link = row_div.find('a')
                        if reihen_link:
                            # Reihen-Name extrahieren (z.B. "Die Buchhändlerinnen von Frankfurt")
                            data['series_name'] = reihen_link.get_text(strip=True)
                            
                            # Bandnummer am Ende des gesamten Texts extrahieren
                            voller_text = row_div.get_text(strip=True)
                            nummer_match = re.search(r'(\d+)\s*$', voller_text)
                            data['series_number'] = int(nummer_match.group(1)) if nummer_match else 0
                            break

            # Fallback für Seiten/Verlag, falls JSON-LD mal lückenhaft sein sollte
            for li in soup.find_all('li'):
                text = li.get_text()
                if 'Seiten' in text and 'pages' not in data:
                    seiten_match = re.search(r'(\d+)\s*Seiten', text)
                    if seiten_match: data['pages'] = int(seiten_match.group(1))
                elif 'Verlag:' in text and not data.get('publisher'):
                    data['publisher'] = text.replace('Verlag:', '').strip()
                elif 'Erschienen:' in text and not data.get('published_date'):
                    datum_match = re.search(r'\d{2}\.\d{2}\.\d{4}', text)
                    if datum_match:
                        tag, monat, jahr = datum_match.group(0).split('.')
                        data['published_date'] = f"{jahr}-{monat}-{tag}"

            return data if data else None
            
        except Exception as e:
            print(f"Schwerer Fehler beim Scraping von isbn.de: {e}")
            return None