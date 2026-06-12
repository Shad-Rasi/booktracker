import os
import base64
import asyncio
import weasyprint
import database
import translations
from translations import t

COVERS_DIR = os.path.join('data', 'covers')

def get_image_base64(path):
    try:
        with open(path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
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
        autor = b[2] if b[2] else t('unknown_author')
        rating = b[6] if b[6] else 0

        cover_base64 = None
        for ext in ['.jpg', '.jpeg', '.png', '.webp']:
            pfad = os.path.join(COVERS_DIR, f"{book_id}{ext}")
            if os.path.exists(pfad):
                cover_base64 = get_image_base64(pfad)
                break

        sterne_html = "★" * rating + "☆" * (5 - rating)

        if cover_base64:
            img_html = f'<img src="{cover_base64}" style="width:100px;height:145px;object-fit:cover;border-radius:4px;box-shadow:0 1px 3px rgba(0,0,0,.1);display:block;margin:0 auto 8px;" />'
        else:
            img_html = '<div style="width:100px;height:145px;background:#f1f5f9;border:1px solid #e2e8f0;border-radius:4px;display:flex;align-items:center;justify-content:center;margin:0 auto 8px;color:#94a3b8;font-size:10px;font-style:italic;">Kein Cover</div>'

        grid_items_html += f'''
        <div style="text-align:center;background:white;border:1px solid #f1f5f9;border-radius:12px;padding:12px;box-shadow:0 1px 2px rgba(0,0,0,.05);break-inside:avoid;">
            {img_html}
            <div style="font-size:10px;color:#f59e0b;">{sterne_html}</div>
        </div>
        '''

    # Balkenhöhe in Pixel (max. 80px)
    MAX_BAR_PX = 80
    max_wert = max(p_stats['werte_seiten']) if any(p_stats['werte_seiten']) else 1
    chart_bars_html = ""
    for zeitpunkt, seiten in zip(p_stats['x_achse_keys'], p_stats['werte_seiten']):
        bar_px = int((seiten / max_wert) * MAX_BAR_PX) if seiten > 0 else 0
        seiten_formatiert = f"{seiten:,}".replace(',', '.')

        chart_bars_html += f'''
        <div style="display:flex;flex-direction:column;align-items:center;flex:1;height:{MAX_BAR_PX + 36}px;justify-content:flex-end;">
            <div style="font-size:8px;font-weight:700;color:#059669;margin-bottom:4px;">{seiten_formatiert if seiten > 0 else ''}</div>
            <div style="width:28px;height:{bar_px}px;background:#10b981;border-radius:3px 3px 0 0;"></div>
            <div style="font-size:9px;color:#94a3b8;margin-top:6px;font-weight:500;">{zeitpunkt[:3]}</div>
        </div>
        '''

    books_section = (
        f'<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;">{grid_items_html}</div>'
        if highlights
        else f'<p style="font-size:14px;color:#94a3b8;font-style:italic;">{t("stats_no_data_year")}</p>'
    )

    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<style>
  @page {{ size: A4; margin: 15mm; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Helvetica, Arial, sans-serif; background: #f8fafc; color: #1e293b; padding: 8px; }}
</style>
</head>
<body>
  <!-- Header -->
  <div style="display:flex;justify-content:space-between;align-items:flex-end;border-bottom:1px solid #e2e8f0;padding-bottom:16px;margin-bottom:24px;">
    <div>
      <h1 style="font-size:28px;font-weight:800;color:#0f172a;letter-spacing:-0.02em;">{t('stats_title')}</h1>
      <p style="font-size:12px;color:#94a3b8;margin-top:4px;">{t('stats_sec_personal')} &nbsp;|&nbsp; {jahr}</p>
    </div>
    <div style="font-size:10px;color:#94a3b8;font-weight:600;text-align:right;">Stand: {aktuelles_datum}</div>
  </div>

  <!-- Stat-Cards -->
  <div style="display:flex;gap:16px;margin-bottom:24px;">
    <div style="flex:1;background:white;border:1px solid #e2e8f0;border-left:4px solid #f97316;border-radius:12px;padding:16px;box-shadow:0 1px 2px rgba(0,0,0,.05);">
      <div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">{t('stats_read_books_year')}</div>
      <div style="font-size:32px;font-weight:800;color:#1e293b;margin-top:4px;">{p_stats['buecher_gelesen_count']}</div>
    </div>
    <div style="flex:1;background:white;border:1px solid #e2e8f0;border-left:4px solid #10b981;border-radius:12px;padding:16px;box-shadow:0 1px 2px rgba(0,0,0,.05);">
      <div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;">{t('stats_total_pages_read')}</div>
      <div style="font-size:32px;font-weight:800;color:#1e293b;margin-top:4px;">{f"{p_stats['total_pages_read']:,}".replace(',', '.')}</div>
    </div>
  </div>

  <!-- Bücherliste -->
  <div style="margin-bottom:24px;">
    <div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;margin-bottom:16px;">Gelesene Bücher in diesem Zeitraum</div>
    {books_section}
  </div>

  <!-- Seitendiagramm -->
  <div>
    <div style="font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px;">{t('stats_total_pages_read')}</div>
    <div style="display:flex;align-items:flex-end;gap:4px;">
      {chart_bars_html}
    </div>
  </div>
</body>
</html>"""

async def export_personal_pdf(user_id, jahr):
    from statistics import berechne_grund_statistiken, berechne_zeitliche_statistiken

    global_stats = berechne_grund_statistiken(user_id)
    if not global_stats:
        raise ValueError("Keine Daten vorhanden.")

    p_stats = berechne_zeitliche_statistiken(global_stats['rohe_buecher'], jahr)

    highlights = [
        b for b in global_stats['rohe_buecher']
        if (b[5] or 'UNREAD') == 'READ' and b[12] and (jahr == 'ALL' or b[12].split('-')[0] == str(jahr))
    ]
    highlights.sort(key=lambda x: x[12] or "")

    html_content = generiere_html_template(jahr, p_stats, highlights)

    output_dir = os.path.join('data', 'exports')
    os.makedirs(output_dir, exist_ok=True)
    pdf_filename = f"Lesebericht_{jahr}.pdf" if jahr != 'ALL' else "Lesebericht_Gesamtzeitraum.pdf"
    output_path = os.path.join(output_dir, pdf_filename)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: weasyprint.HTML(string=html_content).write_pdf(output_path))

    return output_path
