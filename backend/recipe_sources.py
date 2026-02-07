# Load/merge recipes from:
#   - API
#   - Custom: custom_recipes.json
# Favorites are stored separately as a list of IDs in:
# ------------------------------------------------------------

import json 
from pathlib import Path 
from typing import List, Dict, Any, Set 

BASE_DIR = Path(__file__).resolve().parent

API_RECIPES_PATH     = BASE_DIR / "data" / "recipes.json"
CUSTOM_RECIPES_PATH  = BASE_DIR / "data" / "custom_recipes.json"
FAVORITES_IDS_PATH   = BASE_DIR / "data" / "favorites.json"

def _load_meals_themealdb_wrapper(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    meals = data.get("meals") or []
    return [m for m in meals if isinstance(m, dict)]

def _load_meals_plain_list(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    return [m for m in data if isinstance(m, dict)]

def load_all_meals() -> List[Dict[str, Any]]:
    api_meals    = _load_meals_themealdb_wrapper(API_RECIPES_PATH)
    custom_meals = _load_meals_plain_list(CUSTOM_RECIPES_PATH)
    # show custom first, then API
    return list(custom_meals) + list(api_meals)

def index_meals_by_id(meals: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for m in meals:
        id_ = str(m.get("idMeal") or "").strip()
        if id_:
            out[id_] = m
    return out

def load_favorite_ids() -> Set[str]:
    if not FAVORITES_IDS_PATH.exists():
        return set()
    try:
        data = json.loads(FAVORITES_IDS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return set()
    if isinstance(data, list):
        return {str(x).strip() for x in data if str(x).strip()}
    return set()

def save_favorite_ids(ids: Set[str]) -> None:
    FAVORITES_IDS_PATH.write_text(
        json.dumps(sorted(ids), indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

def get_favorite_meals(meals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ids = load_favorite_ids()
    if not ids:
        return []
    by_id = index_meals_by_id(meals)
    return [by_id[i] for i in ids if i in by_id]
