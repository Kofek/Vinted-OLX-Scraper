Projekt automatyzuje proces monitorowania popularnych serwisow ogloszeniowych. Bot w czasie rzeczywistym analizuje ceny rynkowe i powiadamia o ofertach ponizej sredniej wartosci.
Bot jest gotowy do uruchomienia i dziala. Strona webowa jest nadal w procesie tworzenia.

Quick start (PowerShell, localhost)

1) Sklonuj repozytorium:

```powershell
git clone https://github.com/Kofek/Vinted-OLX-Scraper
cd Vinted-OLX-Scraper
```

2) Skopiuj pliki env:

```powershell
Copy-Item frontend/.env.example frontend/.env
Copy-Item backend/.env.example backend/.env
```

W pliku `backend/.env` wpisz swoje wlasne klucze Gemini od Google AI:

```env
GEMINI_API_KEYS=twoj_klucz_1,twoj_klucz_2
```

2.1) Skopiuj config bota:

```powershell
Copy-Item backend/config_example.json backend/config.json
```

W pliku `backend/config.json` dodaj swoj webhook w polu `webhook` dla kazdej kategorii.

3) Uruchom backend (FastAPI):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

4) Uruchom frontend (w nowym terminalu):

```powershell
cd frontend
npm install
npm run dev
```

5) Uruchom bota (w nowym terminalu):

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python bot.py
```