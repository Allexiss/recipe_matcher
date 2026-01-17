# Bulk-import recipes from TheMealDB by ingredient, category (meal type), or cuisine (area), then merge them into backend/data/recipes.json
# ------------------------------------------------------------
from __future__ import annotations
import json
import sys
from pathlib import Path
import requests
import argparse

 
FILTER_BY_ING = "https://www.themealdb.com/api/json/v1/1/filter.php?i="
FILTER_BY_CAT = "https://www.themealdb.com/api/json/v1/1/filter.php?c="
FILTER_BY_AREA = "https://www.themealdb.com/api/json/v1/1/filter.php?a="
LOOKUP_BY_ID = "https://www.themealdb.com/api/json/v1/1/lookup.php?i="

OUT_PATH = Path(__file__).resolve().parent / "data" / "recipes.json"

def get_json(url: str) -> dict:
    #GET a URL and return JSON
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    data = resp.json() or {}
    return data

def ensure_store() -> dict:
    #Read existing recipes.json
    if OUT_PATH.exists():
        try:
            return json.loads(OUT_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"meals": []}
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    return {"meals": []}

def index_by_id(meals: list[dict]) -> dict[str, dict]:
    #Return { idMeal: meal_object }
    out = {}
    for m in meals or []:
        mid = (m.get("idMeal") or "").strip()
        if mid:
            out[mid] = m
    return out

def fetch_ids_from_filter(mode: str, value: str) -> list[str]:
    # Ask TheMealDB for a list of meal IDs matching the filter

    if mode == "ingredient":
        url = FILTER_BY_ING + value
    elif mode == "category":
        url = FILTER_BY_CAT + value
    elif mode == "cuisine":
        url = FILTER_BY_AREA + value
    else:
        return []

    data = get_json(url)
    meals = data.get("meals") or []
    ids = []
    for m in meals:
        mid = (m.get("idMeal") or "").strip()
        if mid:
            ids.append(mid)
    return ids

def fetch_full_meal(mid: str) -> dict | None:
    #Fetch the full meal object for a given idMeal
    data = get_json(LOOKUP_BY_ID + mid)
    meals = data.get("meals") or []
    return meals[0] if meals else None

def merge_and_save(existing: dict, new_meals: list[dict]) -> None:
    
    #Merge new meals, store by idMeal
    index = index_by_id(existing.get("meals") or [])
    for m in new_meals:
        mid = (m.get("idMeal") or "").strip()
        if mid:
            index[mid] = m

    merged_list = list(index.values())
    merged = {"meals": merged_list}
    OUT_PATH.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

def main():
    parser = argparse.ArgumentParser(description="Bulk import recipes by ingredient/category/cuisine.")
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument("--ingredient", help="Filter by main ingredient")
    group.add_argument("--category",   help="Filter by meal category")
    group.add_argument("--cuisine",    help="Filter by area/cuisine")

    args = parser.parse_args()
    if args.ingredient:
        mode, value = "ingredient", args.ingredient.strip()
    elif args.category:
        mode, value = "category", args.category.strip()
    else:
        mode, value = "cuisine", args.cuisine.strip()

    print(f"[info] Fetching list for {mode}='{value}' ...")

    ids = fetch_ids_from_filter(mode, value)
    if not ids:
        print("[warn] No results from filter. Nothing to import.")
        sys.exit(0)

    new_meals = []
    for mid in ids:
        meal = fetch_full_meal(mid)
        if meal:
            new_meals.append(meal)

    store = ensure_store()
    merge_and_save(store, new_meals)

    print(f"[ok] Imported {len(new_meals)} meal(s) for {mode}='{value}'.")
    print(f"[ok] Written to {OUT_PATH}")

if __name__ == "__main__":
    main()
