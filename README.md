![CI Pipeline](https://github.com/Kofek/Vinted-OLX-Scraper/actions/workflows/ci.yml/badge.svg)



![Podgląd strony MagicScraper](docs/my-bots.png)





Projekt automatyzuje proces monitorowania popularnych serwisow ogloszeniowych. Bot w czasie rzeczywistym analizuje ceny rynkowe i powiadamia o ofertach ponizej sredniej wartosci.

Bot jest gotowy do uruchomienia i dziala. Strona webowa jest nadal w procesie tworzenia.



Konfiguracja botow (URL-e, webhook, prompt, pauza/wznow) jest w **Postgres** — przez UI albo API `/api/bots`.

Scraper (`python bot.py`) czyta wlaczone boty z bazy. Globalny status procesu scrapera trzyma tabela **`scraper_worker`**.



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



W pliku `backend/.env` ustaw co najmniej:



```env

DATABASE_URL=postgresql://USER:PASSWORD@HOST/neondb?sslmode=require

GEMINI_API_KEYS=twoj_klucz_1,twoj_klucz_2

```



`DATABASE_URL` — connection string z Neon (lub innego Postgresa).  

`GEMINI_API_KEYS` — klucze Google AI, rozdzielone przecinkami.



3) Migracje bazy (z katalogu `backend`, aktywne venv):



```powershell

cd backend

python -m venv .venv

.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

alembic upgrade head

```



Opcjonalnie import przykladowych botow z JSON:



```powershell

python scripts/import_bots_json_to_postgres.py

```



4) Uruchom backend (FastAPI):



```powershell

python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000

```



Sprawdz polaczenie z baza: `GET http://127.0.0.1:8000/api/db-health`  

Podsumowanie scrapera i botow: `GET http://127.0.0.1:8000/api/status`



5) Uruchom frontend (w nowym terminalu):



```powershell

cd frontend

npm install

npm run dev

```



6) Uruchom scraper (w nowym terminalu):



```powershell

cd backend

.\.venv\Scripts\Activate.ps1

python bot.py

```



Jak bot powinien wyglądac po poprawnym uruchomieniu? Zaglądnij do `backend/data_example`.



## Prawa autorskie

Copyright (c) 2026 [Kacper Kośniowski]. 

Wszelkie prawa zastrzeżone.



Ten kod źródłowy został udostępniony wyłącznie w celach demonstracyjnych (do wglądu w ramach mojego portfolio/CV). 

Kopiowanie, modyfikowanie, dystrybucja oraz wykorzystywanie tego kodu w celach komercyjnych lub prywatnych bez mojej wyraźnej zgody jest zabronione.

