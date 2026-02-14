# ================= IMPORTY =================
import time
import os
import random
import urllib.parse
from datetime import datetime
from bs4 import BeautifulSoup
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

# Biblioteki sieciowe
import requests as req_olx
from curl_cffi import requests as req_vinted

# Biblioteka AI (Nowe SDK)
from google import genai
from google.genai import types

# Wczytuje dane z pliku .env
load_dotenv()

# Pobiera klucz i przypisuje do zmiennej
moje_api = os.getenv("MOJE_API_KEY")

print("Mój klucz to:", moje_api)

# ================= KONFIGURACJA KLUCZY I MODELI =================

# 👇 TUTAJ WKLEJ SWOJE KLUCZE (Im więcej, tym lepiej - np. 3-5 sztuk)
API_KEYS_POOL = []

# Modele do rotacji (od najlepszego)
MODELS_POOL = [
    "gemini-3-flash-preview",   # Najnowszy (Limit 20)
    "gemini-2.5-flash",         # Standard (Limit 20)
    "gemini-2.5-flash-lite",    # Wersja lekka (Limit 20)
]

# Konfiguracja Webhooków Discord
WEBHOOK_OLX = "https://discord.com/api/webhooks/1470037335520317513/V2my1EOXPSV6TMRK7y8CEFvg-YR-y3HJhHeyejzoguIDWX-_X2UgXCKYVnKhMNsrm4wX"
WEBHOOK_VINTED = WEBHOOK_OLX
PLIK_HISTORII = "historia_rotacja.txt"

# Prompt dla AI
SYSTEM_INSTRUCTION = """
Jesteś ekspertem resellu. Specjalizacja: Mangi, Warhammer i Maskotki (Jellycat).

Twoim zadaniem jest ocena okazji na podstawie zdjęcia, opisu i ceny.

ZASADY OCENY:
1. WARHAMMER:
   - Szukaj: Dużych zestawów, figurek w wypraskach (nieposklejane), "Pile of Shame" (niepomalowane).
   - Omijaj: Źle sklejone, "zalane" grubą warstwą farby figurki (chyba że cena jest śmiesznie niska).
   - Decyzja: Dużo plastiku za małą cenę -> WARTO.

2. JELLYCAT (Maskotki):
   - Szukaj: Charakterystycznych zwierząt (króliki, owoce, warzywa) z metkami.
   - Omijaj: Podróbki (krzywe szwy, dziwne oczy).
   - Cena < 30 zł za oryginał -> Zawsze WARTO.

3. MANGA:
   - Kompletne serie lub ciągi tomów w dobrej cenie. Jeśli uważasz że opłaca się kupić pod resell to WARTO

Odpowiedz w formacie:
DECYZJA: [WARTO / RYZYKO / NIE WARTO]
RYNEK: [Szacowana cena rynkowa]
POWÓD: [Krótka analiza]
"""

# --- LINKI DO OBSERWOWANIA ---
URLS_OLX = [
    "https://www.olx.pl/muzyka-edukacja/ksiazki/komiksy/q-manga-mangi/?search%5Bfilter_float_price%3Afrom%5D=100&search%5Border%5D=created_at%3Adesc"
]

URLS_VINTED = ["https://www.vinted.pl/catalog?search_text=manga&order=newest_first&currency=PLN&catalog[]=2312&price_from=100"]
# User-Agenty
OLX_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

# ================= MANAGER KLUCZY (ROTACJA) =================
class KeyManager:
    def __init__(self, keys, models):
        self.keys = keys
        self.models = models
        self.current_key_idx = 0
        self.current_model_idx = 0
        self._client = None
        self._refresh_client()

    def _refresh_client(self):
        """Tworzy klienta dla obecnego klucza"""
        current_key = self.keys[self.current_key_idx]
        self._client = genai.Client(api_key=current_key)
        print(f"🔑 Używam klucza nr {self.current_key_idx + 1} (końcówka: ...{current_key[-4:]}) | Model: {self.models[self.current_model_idx]}")

    def get_client_and_model(self):
        return self._client, self.models[self.current_model_idx]

    def rotate(self):
        """Zmienia konfigurację po błędzie"""
        print("   🔄 Rotacja! Przełączam na następną opcję...")
        
        # 1. Najpierw próbujemy zmienić model na tym samym kluczu
        self.current_model_idx += 1
        if self.current_model_idx >= len(self.models):
            # 2. Jeśli modele się skończyły, zmieniamy klucz
            self.current_model_idx = 0
            self.current_key_idx += 1
            
            # 3. Jeśli klucze się skończyły, wracamy do pierwszego
            if self.current_key_idx >= len(self.keys):
                self.current_key_idx = 0
                print("   ⚠️ Przelecieliśmy wszystkie klucze! Robię 60s pauzy...")
                time.sleep(60)
            
            self._refresh_client() # Nowy klucz = nowy klient
            return True
        
        print(f"   ➡️ Zmiana modelu na: {self.models[self.current_model_idx]}")
        return True

# Inicjalizacja managera
manager = KeyManager(API_KEYS_POOL, MODELS_POOL)

# ================= FUNKCJE POMOCNICZE =================
def wczytaj_historie():
    if not os.path.exists(PLIK_HISTORII): return set()
    with open(PLIK_HISTORII, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f)

def zapisz_link(link):
    with open(PLIK_HISTORII, "a", encoding="utf-8") as f:
        f.write(link + "\n")

def czy_swieze_ogloszenie(tekst_daty):
    if not tekst_daty: return False
    tekst_daty = tekst_daty.lower()
    swieze_slowa = ['dzisiaj', 'minut', 'godz', 'sekund', 'teraz', 'chwil']
    return any(slowo in tekst_daty for slowo in swieze_slowa)

# ================= SCRAPING DETALI =================
def pobierz_detale_olx(session, url):
    try:
        time.sleep(random.uniform(0.5, 1.0))
        resp = session.get(url, timeout=5)
        soup = BeautifulSoup(resp.text, 'html.parser')
        desc_div = soup.find('div', {'data-cy': 'ad_description'})
        return desc_div.text.strip() if desc_div else "Brak opisu"
    except: return "Brak opisu (błąd)"

def pobierz_detale_vinted(session, url):
    try:
        time.sleep(random.uniform(1.0, 2.0))
        resp = session.get(url, timeout=5)
        soup = BeautifulSoup(resp.text, 'html.parser')
        desc_div = soup.find('div', {'itemprop': 'description'})
        return desc_div.text.strip() if desc_div else "Brak opisu"
    except: return "Brak opisu (błąd)"

# ================= ANALIZA AI Z ROTACJĄ =================
def analiza_ai(tytul, cena, opis, img_url):
    """
    Analizuje ofertę. 
    Jak model rzuci błędem (429/503), zmienia klucz i NATYCHMIAST ponawia próbę dla tego samego ogłoszenia.
    """
    
    # Obliczamy ile mamy łącznie szans (liczba kluczy * liczba modeli) + mały zapas
    max_retries = len(API_KEYS_POOL) * len(MODELS_POOL) + 2
    
    # Przygotowanie danych (robimy to raz przed pętlą, żeby nie marnować czasu)
    prompt_text = f"Tytuł: {tytul}\nCena Kupna: {cena}\nOpis: {opis}\nWaluta: PLN."
    image_data = None
    
    # Pobieranie zdjęcia raz, trzymamy w pamięci
    if img_url and img_url.startswith('http'):
        try:
            img_resp = req_olx.get(img_url, timeout=5)
            if img_resp.status_code == 200:
                # Wczytujemy do RAM
                image_data = Image.open(BytesIO(img_resp.content))
        except: 
            pass

    # === PĘTLA UPORU ===
    for attempt in range(max_retries):
        client, model_id = manager.get_client_and_model()
        
        try:
            # Budujemy treść zapytania (tekst + zdjęcie jeśli jest)
            contents = [prompt_text]
            if image_data:
                contents.append(image_data)

            # Strzał do AI
            response = client.models.generate_content(
                model=model_id,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.1
                )
            )
            
            # Jak się uda, zwracamy wynik i kończymy funkcję (SUKCES)
            return response.text

        except Exception as e:
            error_msg = str(e)
            
            # Lista błędów, przy których WARTO próbować jeszcze raz na innym koncie
            retry_errors = ["429", "RESOURCE_EXHAUSTED", "404", "503", "UNAVAILABLE", "overloaded", "quota"]
            
            if any(x in error_msg for x in retry_errors):
                print(f"   ⚠️ Błąd {model_id} (Próba {attempt+1}/{max_retries})...")
                print("   🔄 Przełączam klucz/model i ponawiam TO SAMO ogłoszenie...")
                
                manager.rotate() # Zmieniamy klucz
                time.sleep(1)    # Krótki oddech (1s)
                continue         # <--- KLUCZOWE: Wracamy na początek pętli z TYM SAMYM ogłoszeniem!
            
            else:
                # Jeśli to inny błąd (np. zły format danych), nie ma sensu ponawiać
                return f"Błąd krytyczny AI: {e}"

    # Jeśli pętla się skończyła i żaden klucz nie zadziałał:
    return "Błąd: Wszystkie klucze/modele zawiodły."

czy_pierwsze_uruchomienie = True

# ================= LOGIKA OLX =================
# ================= POPRAWIONA FUNKCJA OLX =================
# ================= FILTRACJA OLX (TYLKO "WARTO") =================
# ================= FILTRACJA OLX (TYLKO "WARTO") =================
def sprawdz_olx(historia):
    print("🔵 [OLX] Skanuję...")
    session = req_olx.Session()
    session.headers.update({"User-Agent": random.choice(OLX_AGENTS)})

    for url in URLS_OLX:
        try:
            resp = session.get(url, timeout=10)
            if resp.status_code != 200: continue
            soup = BeautifulSoup(resp.text, 'html.parser')
            cards = soup.find_all('div', {'data-cy': 'l-card'})

            for card in cards[:15]:
                try:
                    a_tag = card.find('a')
                    if not a_tag: continue
                    href = a_tag['href']
                    link = "https://www.olx.pl" + href if href.startswith('/') else href
                    link = link.split("#")[0]

                    if link in historia: continue

                    date_loc = "Brak danych"
                    date_tag = card.find('p', {'data-testid': 'location-date'})
                    if date_tag: date_loc = date_tag.text.strip()

                    if not czy_pierwsze_uruchomienie and not czy_swieze_ogloszenie(date_loc):
                        continue

                    title = card.find('h6').text.strip() if card.find('h6') else (card.find('h4').text.strip() if card.find('h4') else "Bez tytułu")
                    price = card.find('p', {'data-testid': 'ad-price'}).text.strip() if card.find('p', {'data-testid': 'ad-price'}) else "???"
                    img = card.find('img').get('src') if card.find('img') else ""

                    historia.add(link)
                    zapisz_link(link)
                    print(f"   --> OLX [NOWE]: {price} | {title[:30]}")

                    if not czy_pierwsze_uruchomienie:
                        pelny_opis = pobierz_detale_olx(session, link)
                        werdykt_ai = analiza_ai(title, price, pelny_opis, img)
                        werdykt_upper = werdykt_ai.upper()

                        # === OSTRY FILTR: TYLKO "WARTO" ===
                        # 1. Odrzucamy "NIE WARTO"
                        if "NIE WARTO" in werdykt_upper:
                            print(f"      🗑️ Odrzucone (Nie warto): {title[:20]}...")
                            continue
                        
                        # 2. Odrzucamy "RYZYKO" (Tego chciałeś)
                        if "RYZYKO" in werdykt_upper:
                            print(f"      🗑️ Odrzucone (Ryzyko): {title[:20]}...")
                            continue

                        # 3. Dla pewności: sprawdzamy czy w ogóle jest słowo "WARTO"
                        if "WARTO" not in werdykt_upper:
                            print(f"      ❓ AI bredzi (brak decyzji): {title[:20]}...")
                            continue

                        # Jeśli kod doszedł tutaj, to znaczy że jest to PEWNIAK
                        color = 5763719 # Zielony

                        teraz = datetime.now().strftime("%H:%M")
                        payload = {
                            "embeds": [{
                                "title": f"💎 {title}", # Dodaję diamencik do tytułu
                                "url": link, 
                                "color": color,
                                "description": f"**Cena:** `{price}`\n**Lokalizacja:** {date_loc}\n\n🤖 **Gemini:**\n{werdykt_ai}",
                                "thumbnail": {"url": img},
                                "footer": {"text": f"OLX Bot (Pewniaki) • {teraz}"}
                            }]
                        }
                        
                        print("      ✅ WYSYŁAM POWIADOMIENIE (PEWNIAK)!")
                        req_olx.post(WEBHOOK_OLX, json=payload)
                        time.sleep(2)

                except Exception as e: 
                    print(f"⚠️ Błąd OLX: {e}")
                    continue
            time.sleep(random.uniform(2, 4))
        except Exception as e: print(f"❌ Błąd OLX URL: {e}")
    return historia

# ================= LOGIKA VINTED =================
# ================= POPRAWIONA LOGIKA VINTED =================
# ================= LOGIKA VINTED (STARA WERSJA + UPDATE) =================
# ================= FILTRACJA VINTED (TYLKO "WARTO") =================
# ================= FILTRACJA VINTED (TYLKO "WARTO") =================
def sprawdz_vinted(historia):
    print("🔴 [VINTED] Skanuję...")
    session = req_vinted.Session(impersonate="chrome124")
    session.headers.update({
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.vinted.pl/"
    })

    try:
        if 'access_token_web' not in session.cookies: 
            session.get("https://www.vinted.pl/", timeout=10)
    except: pass

    for url in URLS_VINTED:
        try:
            resp = session.get(url, timeout=10)
            if resp.status_code != 200: 
                print(f"⚠️ Vinted BŁĄD: {resp.status_code}")
                continue
                
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.find_all('div', {'data-testid': 'grid-item'})

            if len(items) == 0: print("⚠️ Vinted: Pusta lista (Captcha?)")

            for item in items[:15]:
                try:
                    a_tag = item.find('a')
                    if not a_tag: continue
                    link = a_tag.get('href')
                    if not link.startswith("http"): link = "https://www.vinted.pl" + link
                    if link in historia: continue

                    price = "???"
                    for s in item.stripped_strings:
                        if "zł" in s: price = s; break
                    
                    owner = item.find('div', {'data-testid': 'box-user-login'}).text.strip() if item.find('div', {'data-testid': 'box-user-login'}) else "Ukryty"
                    img_tag = item.find('img')
                    img = img_tag.get('src') if img_tag else ""
                    title = img_tag.get('alt')[:60] if img_tag and img_tag.get('alt') else "Przedmiot Vinted"

                    historia.add(link)
                    zapisz_link(link)
                    print(f"    --> VINTED [NOWE]: {price} | {title}")

                    if not czy_pierwsze_uruchomienie:
                        pelny_opis = pobierz_detale_vinted(session, link)
                        werdykt_ai = analiza_ai(title, price, pelny_opis, img)
                        werdykt_upper = werdykt_ai.upper()

                        # === OSTRY FILTR ===
                        if "NIE WARTO" in werdykt_upper:
                            print(f"      🗑️ Odrzucone (Nie warto): {title[:20]}...")
                            continue
                        
                        if "RYZYKO" in werdykt_upper:
                            print(f"      🗑️ Odrzucone (Ryzyko): {title[:20]}...")
                            continue

                        if "WARTO" not in werdykt_upper:
                            print(f"      ❓ AI bredzi: {title[:20]}...")
                            continue
                        
                        # Tylko PEWNIAKI przechodzą dalej
                        color = 5763719

                        payload = {
                            "embeds": [{
                                "title": f"💎 {title}", 
                                "url": link, 
                                "color": color,
                                "description": f"**Cena:** `{price}`\n**Sprzedawca:** {owner}\n\n🤖 **Gemini:**\n{werdykt_ai}",
                                "thumbnail": {"url": img},
                                "footer": {"text": f"Vinted Bot (Pewniaki) • {datetime.now().strftime('%H:%M:%S')}"}
                            }]
                        }
                        print("      ✅ WYSYŁAM POWIADOMIENIE (PEWNIAK)!")
                        req_olx.post(WEBHOOK_VINTED, json=payload)
                        time.sleep(3)
                except Exception: continue
            time.sleep(random.uniform(5, 10)) # Zwiększyłem lekko czas dla Vinted, bo jest więcej kategorii
        except Exception as e: print(f"❌ Błąd Vinted: {e}")
    return historia

# ================= START =================
def main():
    global czy_pierwsze_uruchomienie
    print("🚀 MEGA BOT (OLX + VINTED + MULTI-KEY) STARTUJE...")
    historia = wczytaj_historie()

    while True:
        historia = sprawdz_olx(historia)
        time.sleep(5)
        historia = sprawdz_vinted(historia)

        if czy_pierwsze_uruchomienie:
            print("✅ Baza załadowana. Czekam na nowości.")
            czy_pierwsze_uruchomienie = False

        wait = random.uniform(30, 60)
        print(f"💤 Czekam {int(wait)}s...\n")
        time.sleep(wait)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("🛑 Zatrzymano.")