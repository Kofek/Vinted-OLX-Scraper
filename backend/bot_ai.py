import time
from io import BytesIO

import requests as req_olx
from PIL import Image
from google import genai
from google.genai import types

API_KEYS_POOL = []
MODELS_POOL = []
manager = None


class KeyManager:
    def __init__(self, keys, models):
        self.keys = keys
        self.models = models
        self.current_key_idx = 0
        self.current_model_idx = 0
        self._client = None
        self._refresh_client()

    def _refresh_client(self):
        current_key = self.keys[self.current_key_idx]
        self._client = genai.Client(api_key=current_key)
        print(f"🔄 Switched to Key #{self.current_key_idx + 1} | Model: {self.models[self.current_model_idx]}")

    def get_client_and_model(self):
        return self._client, self.models[self.current_model_idx]

    def rotate(self):
        print("🔄 Rotation! Switching models/keys...")

        self.current_model_idx += 1

        if self.current_model_idx >= len(self.models):
            self.current_model_idx = 0
            self.current_key_idx += 1

            if self.current_key_idx >= len(self.keys):
                self.current_key_idx = 0
                self.current_model_idx = 0
                print("⚠️ All keys and models exhausted! Cooling down for 60s...")
                time.sleep(60)

        self._refresh_client()
        return True

def init_ai(api_keys_pool, models_pool):
    global API_KEYS_POOL, MODELS_POOL, manager
    API_KEYS_POOL = api_keys_pool
    MODELS_POOL = models_pool
    manager = KeyManager(API_KEYS_POOL, MODELS_POOL)

def analyze_ai(title, price, description, img_url, system_instruction):
    if manager is None:
        return "AI Error: manager not initialized. Call init_ai() first."

    max_retries = len(API_KEYS_POOL) * len(MODELS_POOL) + 2
    prompt_text = f"Tytuł: {title}\nCena Kupna: {price}\nOpis: {description}\nWaluta: PLN."
    image_data = None

    if img_url and img_url.startswith('http'):
        try:
            img_resp = req_olx.get(img_url, timeout=5)
            if img_resp.status_code == 200:
                with BytesIO(img_resp.content) as img_buffer:
                    with Image.open(img_buffer) as img:
                        image_data = img.copy()
        except Exception as e:
            print(f"AI Image Fetch Error: {e}")

    for attempt in range(max_retries):
        client, model_id = manager.get_client_and_model()
        try:
            contents = [prompt_text]
            if image_data:
                contents.append(image_data)

            response = client.models.generate_content(
                model=model_id,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1
                )
            )
            return response.text

        except Exception as e:
            error_msg = str(e)
            retry_errors = ["429", "RESOURCE_EXHAUSTED", "404", "503", "UNAVAILABLE", "overloaded", "quota"]

            if any(x in error_msg for x in retry_errors):
                manager.rotate()
                time.sleep(1)
                continue
            else:
                return f"AI Error: {e}"

    return "Error: All keys/models failed."


