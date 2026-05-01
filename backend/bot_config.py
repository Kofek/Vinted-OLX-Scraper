import json
import os
from pathlib import Path


def validate_config(base_dir: Path):
    API_KEYS_RAW = os.getenv("GEMINI_API_KEYS", "")
    MODELS_POOL_RAW = os.getenv("MODELS_POOL", "")

    API_KEYS = [key.strip() for key in API_KEYS_RAW.split(",") if key.strip()]
    MODELS_POOL = [model.strip() for model in MODELS_POOL_RAW.split(",") if model.strip()]

    errors = []
    if not API_KEYS: errors.append("❌ Missing GEMINI_API_KEYS in .env")
    if not MODELS_POOL: errors.append("❌ Missing MODELS_POOL in .env")

    categories = []
    config_path = base_dir / "config.json"
    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            config_data = json.load(config_file)
            categories_raw = config_data.get("categories", [])

            if not categories_raw:
                errors.append("❌ No categories found in config.json")

            for idx, cat in enumerate(categories_raw):
                required_fields = ["name", "history_file", "prompt_file", "webhook"]
                for field in required_fields:
                    if field not in cat:
                        errors.append(
                            f"❌ Category at index {idx} [{cat.get('name', 'Unknown')}] is missing field: '{field}'"
                        )

                # Ładowanie promptu z pliku .txt do pamięci
                prompt_path = cat.get("prompt_file")
                if prompt_path:
                    prompt_path_abs = base_dir / prompt_path
                    try:
                        with prompt_path_abs.open("r", encoding="utf-8") as prompt_file:
                            cat["system_instruction"] = prompt_file.read()
                    except FileNotFoundError:
                        errors.append(f"❌ Prompt file not found: {prompt_path}")

                history_file_raw = cat.get("history_file")
                if history_file_raw:
                    cat["history_file"] = str((base_dir / history_file_raw).resolve())

                categories.append(cat)

    except FileNotFoundError:
        errors.append("❌ config.json file not found!")
    except json.JSONDecodeError:
        errors.append("❌ Syntax error in config.json! Check commas and quotes.")

    if errors:
        print("\n" + "!" * 40)
        print("CRITICAL CONFIGURATION ERRORS:")
        for error in errors:
            print(error)
        print("!" * 40 + "\n")
        exit(1)

    # --- 4. SUCCESS REPORT ---
    print("-" * 35)
    print(f"✅ CONFIGURATION VALIDATED")
    print(f"🔑 API Keys:    {len(API_KEYS)}")
    print(f"🧠 AI Models:   {len(MODELS_POOL)}")
    print(f"📂 Categories:  {len(categories)}")
    print("-" * 35)

    return API_KEYS, MODELS_POOL, categories
