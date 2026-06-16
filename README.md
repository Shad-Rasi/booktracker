<p align="center">
  <a href="https://booktracker.de" target="_blank">
    <img src="static/app-icon.png" alt="Booktracker Logo" width="120" height="120" style="border-radius: 20px;">
  </a>
</p>

# 📚 Booktracker

A sleek, privacy-first, self-hosted tracker for your physical book library. Keep track of your reading progress, automatically fetch beautiful cover art, and generate elegant PDF reading reports.

🌍 **[Visit the Official Homepage](https://booktracker.de)**

![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python&logoColor=white)
![NiceGUI](https://img.shields.io/badge/UI-NiceGUI-green?style=for-the-badge)
![Docker](https://img.shields.io/badge/Docker-shadrasi%2Fbooktracker-emerald?style=for-the-badge&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-zinc?style=for-the-badge)

---

## ✨ Features

- **📶 True Self-Hosted Privacy:** No tracking, no forced cloud connection. Your data stays in your local SQLite database.
- **🔒 No Built-in Login:** Designed to run securely in your home network or behind your favorite reverse proxy (like Traefik/Authelia, Nginx, or VPN Tunnels).
- **📚 Smart Metadata Fetching:** Type an ISBN. Booktracker automatically pulls covers and rich details from **OpenLibrary**, **isbn.de** (excellent for German books), and **Google Books**.
- **⚡ PWA Ready:** Install Booktracker directly onto your smartphone's home screen. It works and feels like a native mobile app.
- **📊 Reading Progress Tracking:** Log your daily reading stats, visualize your habits with clean charts, and track multiple reading cycles (including re-reads!).
- **🖨️ PDF Report Export:** Generate and download beautiful PDF statistics of your reading year.
- **🌍 Multi-Language & Multi-User:** Full English and German UI support out of the box.

---

## Quick Start with Docker Hub (Recommended)

Create a `docker-compose.yml` file:

```yaml
services:
  booktracker:
    image: shadrasi/booktracker:latest
    container_name: booktracker
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - TZ=Europe/Berlin
      - STORAGE_SECRET=change_me_to_a_long_random_string
      - GOOGLE_API_KEY=optional_google_books_key
    volumes:
      - ./data:/app/data

```

Run the container:

```bash
docker compose up -d

```

Open `http://YOUR_SERVER_IP:8080` in your browser and start tracking!

---

## Development & Building from Source

If you want to modify the code or build the image yourself:

**1. Clone the repository**

```bash
git clone https://github.com/Shad-Rasi/booktracker.git
cd booktracker

```

**2. Set up your environment**

```bash
cp .env.example .env
# Edit .env and fill in your STORAGE_SECRET and keys

```

**3. Run in Development Mode (Live Reload)**

```bash
docker compose -f docker-compose.dev.yml up

```

Or run locally without Docker:

```bash
pip install -r requirements.txt
python main.py

```

---

## ⚙️ Configuration

All configuration is handled via environment variables (or your `.env` file):

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `STORAGE_SECRET` | **Yes** | *None* | A long random string used to encrypt session data securely. |
| `GOOGLE_API_KEY` | No | *None* | Optional Google Books API key for higher rate limits during lookups. |
| `TZ` | No | `UTC` | Timezone for accurate reading logs (e.g., `Europe/Berlin`). |
| `PORT` | No | `8080` | The internal port NiceGUI listens on. |

---

## 🧰 Tech Stack

* **Frontend/Backend:** [NiceGUI](https://nicegui.io/) (Python-based Web UI Framework)
* **PDF Engine:** [WeasyPrint](https://weasyprint.org/) (Flawless HTML-to-PDF compilation)
* **Database:** SQLite (Lightweight, zero-administration, deeply embedded)

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

