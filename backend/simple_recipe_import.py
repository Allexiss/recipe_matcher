# HOW TO RUN: python backend/simple_recipe_import.py "chicken"
# OUTPUT: backend/data/recipes.json   <-- raw API results
# ------------------------------------------------------------

import sys
import json
from pathlib import Path
import requests

OUT_PATH = Path(__file__).resolve().parent / "data" / "recipes.json"
BASE_URL = "https://www.themealdb.com/api/json/v1/1/search.php?s="

def main():
    if len(sys.argv) < 2:
        print('Usage: python backend/simple_recipe_import.py "chicken"')
        sys.exit(1)

    query = sys.argv[1]
    url = f"{BASE_URL}{query}"

    resp = requests.get(url, timeout=20)
    resp.raise_for_status()

    data = resp.json()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[ok] Saved {len(data.get('meals') or [])} recipes to {OUT_PATH}")

if __name__ == "__main__":
    main()

