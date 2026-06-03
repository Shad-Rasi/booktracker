# Wir starten mit einem schlanken Python-Image
FROM python:3.11-slim

# Arbeitsverzeichnis im Container festlegen
WORKDIR /app

# System-Abhängigkeiten installieren (wichtig für spätere Erweiterungen)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# requirements kopieren und installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Den restlichen Code der App in den Container kopieren
COPY . .

# Port für die NiceGUI-Oberfläche freigeben
EXPOSE 8080

# Befehl zum Starten der App (wir nennen unsere Hauptdatei später main.py)
CMD ["python", "main.py"]