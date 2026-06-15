# Booktracker

A self-hosted tracker for your physical book library — including reading stats, cover art, and PDF reports.

![Python](https://img.shields.io/badge/Python-3.11-blue) ![NiceGUI](https://img.shields.io/badge/UI-NiceGUI-green) ![Docker](https://img.shields.io/badge/Docker-ready-blue)

## Features

- Track your physical book collection with status (reading, read, given away)
- Automatic book metadata & cover lookup via Google Books and OpenLibrary and isbn.de (good resource for german books)
- Personal reading statistics with charts
- PDF reading report export
- Multiple users
- Genres and shelf management
- English and German UI

## Quick Start (Docker)

**1. Clone the repository**
```bash
git clone https://github.com/your-username/booktracker.git
cd booktracker
```

**2. Set up your environment**
```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
GOOGLE_API_KEY=your_key_here
STORAGE_SECRET=some_long_random_string
TZ=Europe/Berlin
```

A Google Books API key is **optional** — book search also works via OpenLibrary without one. With a key you get higher rate limits. Get one at [Google Cloud Console](https://console.cloud.google.com/apis/library/books.googleapis.com).

**3. Build and run**
```bash
docker compose up -d
```

Open [http://localhost:8080](http://localhost:8080) in your browser.

Data is persisted in a local `data/` folder (SQLite database + cover images).

## Development Setup

```bash
# Run with code live-reload and local code mount
docker compose -f docker-compose.dev.yml up
```

Or run locally without Docker:
```bash
pip install -r requirements.txt
cp .env.example .env  # fill in values
python main.py
```

## Configuration

All configuration is done via the `.env` file:

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_API_KEY` | No | Google Books API key for book metadata lookup |
| `STORAGE_SECRET` | Yes | Random string to encrypt session data |
| `TZ` | No | Timezone (default: UTC) |
| `PORT` | No | Port to listen on (default: 8080) |

## Tech Stack

- [NiceGUI](https://nicegui.io/) — Python web UI framework
- [WeasyPrint](https://weasyprint.org/) — PDF generation
- SQLite — local database, no server needed
- Google Books API / OpenLibrary — book metadata

## License

MIT
