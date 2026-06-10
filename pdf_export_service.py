import os
import asyncio
import base64
from playwright.async_api import async_playwright
import database
import translations
from translations import t

COVERS_DIR = os.path.join('data', 'covers')

def get_image_base64(path):
    """Konvertiert ein lokales Bild in einen Base64-String für das PDF."""
    try:
        with open(path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            # Dateiendung ermitteln für den richtigen MIME-Type
            ext = os.path.splitext(path)[1].replace('.', '')
            if ext == 'jpg': ext = 'jpeg'
            return f"data:image/{ext};base64,{encoded_string}"
    except Exception:
        return None

def generiere_html_template(jahr, p_stats, highlights):
    from datetime import datetime
    aktuelles_datum = datetime.now().strftime("%d.%m.%Y")
    
    grid_items_html = ""
    for b in highlights:
        book_id = b[0]
        titel = b[1]
        autor = b[2] if b[2] else t('unknown_author')
        rating = b[6] if b[6] else 0
        
        # Lokales Cover suchen und in Base64 umwandeln
        cover_base64 = None
        for ext in ['.jpg', '.jpeg', '.png', '.webp']:
            pfad = os.path.join(COVERS_DIR, f"{book_id}{ext}")
            if os.path.exists(pfad):
                cover_base64 = get_image_base64(pfad)
                break
        
        sterne_html = "★" * rating + "☆" * (5 - rating)
        
        # Im img-tag nutzen wir jetzt den Base64-String statt file://
        if cover_base64:
            img_html = f'<img src="{cover_base64}" class="w-[100px] h-[145px] object-cover rounded shadow-sm mx-auto mb-2" />'
        else:
            img_html = f'''
            <div class="w-[100px] h-[145px] bg-slate-100 border border-slate-200 rounded mx-auto mb-2 flex flex-col items-center justify-center text-center p-2 text-slate-400">
                <span class="text-[10px] italic">Kein Cover</span>
            </div>
            '''
            
        grid_items_html += f'''
        <div class="text-center break-inside-avoid p-3 bg-white rounded-xl border border-slate-100 shadow-sm">
            {img_html}
            <div class="text-[10px] text-amber-500 tracking-wider">{sterne_html}</div>
        </div>
        '''

    # Balken für das Diagramm per Flexbox & Tailwind generieren
    max_wert = max(p_stats['werte_seiten']) if any(p_stats['werte_seiten']) else 1
    chart_bars_html = ""
    for zeitpunkt, seiten in zip(p_stats['x_achse_keys'], p_stats['werte_seiten']):
        bar_height_pct = (seiten / max_wert) * 100 if seiten > 0 else 0
        
        # Tausender-Trennzeichen formatieren
        seiten_formatiert = f"{seiten:,}".replace(',', '.')
        
        chart_bars_html += f'''
        <div class="flex flex-col items-center flex-1 h-full justify-end">
            <div class="text-[9px] font-bold text-emerald-600 mb-1">
                {seiten_formatiert if seiten > 0 else ''}
            </div>
            <div style="height: {bar_height_pct}%; min-height: {2 if seiten > 0 else 0}px;" class="w-8 bg-emerald-500 rounded-t"></div>
            <div class="text-[10px] text-slate-400 mt-2 font-medium">{zeitpunkt[:3]}</div>
        </div>
        '''

    # Das finale HTML-Template inklusive Tailwind CDN und Druck-Layout-Parametern
    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @page {{
            size: A4;
            margin: 15mm 15mm 15mm 15mm;
        }}
        body {{
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
        }}
        .break-inside-avoid {{
            break-inside: avoid;
        }}
    </style>
</head>
<body class="bg-slate-50 text-slate-800 p-2">
    <div class="border-b border-slate-200 pb-4 mb-6 flex justify-between items-end">
        <div>
            <h1 class="text-3xl font-bold text-slate-900 tracking-tight">{t('stats_title')}</h1>
            <p class="text-sm text-slate-500 mt-1">{t('stats_sec_personal')}  |  Zeitraum: {jahr}</p>
        </div>
        <div class="text-right text-xs text-slate-400 font-medium">
            Stand: {aktuelles_datum}
        </div>
    </div>

    <div class="grid grid-cols-2 gap-4 mb-6">
        <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm border-l-4 border-l-orange-500">
            <div class="text-xs font-bold text-slate-400 uppercase tracking-wider">{t('stats_read_books_year')}</div>
            <div class="text-3xl font-extrabold text-slate-800 mt-1">{p_stats['buecher_gelesen_count']}</div>
        </div>
        <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm border-l-4 border-l-emerald-500">
            <div class="text-xs font-bold text-slate-400 uppercase tracking-wider">{t('stats_total_pages_read')}</div>
            <div class="text-3xl font-extrabold text-slate-800 mt-1">{f"{p_stats['total_pages_read']:,}".replace(',', '.')}</div>
        </div>
    </div>

    <div>
        <h2 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Gelesene Bücher in diesem Zeitraum</h2>
        {"<p class='text-sm text-slate-400 italic'>" + t('stats_no_data_year') + "</p>" if not highlights else '<div class="grid grid-cols-5 gap-3">' + grid_items_html + '</div>'}
    </div>
</body>
</html>"""
    return html

async def export_personal_pdf(user_id, jahr):
    """
    Sammelt die Daten und rendert das PDF asynchron via Playwright (Chromium).
    Da Playwright nativ asynchron läuft, blockiert es NiceGUI nicht.
    """
    from statistics import berechne_grund_statistiken, berechne_zeitliche_statistiken
    
    global_stats = berechne_grund_statistiken(user_id)
    if not global_stats:
        raise ValueError("Keine Daten vorhanden.")
        
    p_stats = berechne_zeitliche_statistiken(global_stats['rohe_buecher'], jahr)
    
    highlights = []
    for b in global_stats['rohe_buecher']:
        status = b[5] or 'UNREAD'
        finished_at = b[12]
        if status == 'READ' and finished_at:
            b_jahr = finished_at.split('-')[0]
            if jahr == 'ALL' or b_jahr == str(jahr):
                highlights.append(b)
                
    highlights.sort(key=lambda x: x[12] or "")

    # HTML Code generieren
    html_content = generiere_html_template(jahr, p_stats, highlights)

    output_dir = os.path.join('data', 'exports')
    os.makedirs(output_dir, exist_ok=True)
    pdf_filename = f"Lesebericht_{jahr}.pdf" if jahr != 'ALL' else "Lesebericht_Gesamtzeitraum.pdf"
    output_path = os.path.join(output_dir, pdf_filename)

    # Playwright anwerfen
    async with async_playwright() as p:
        # Startet den schlanken Chromium Headless Browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # HTML Inhalt in die Page injizieren
        await page.set_content(html_content)
        
        # Wichtig: Warten, bis Tailwind via CDN geladen wurde und das Netzwerk ruhig ist
        await page.wait_for_load_state("networkidle")
        
        # Drucken als hochauflösendes A4-PDF
        await page.pdf(
            path=output_path,
            format="A4",
            print_background=True,  # Zwingend notwendig, damit Tailwind-Farben gedruckt werden
            margin={"top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"}
        )
        await browser.close()
        
    return output_path