# WEEK 2 GOAL:
# Reads recipes from recipes.json
# Read a local pantry
# Tell us which recipes "cookable" if you have every ingredient OR "nearly cookable" if missing <= K ingredients
#
# HOW TO RUN: 
    # python backend/recipe_matcher.py
    # python backend/recipe_matcher.py --max-missing "#"      <- it should be a number and remove the quotes. this is used if you are missing a lot but still want to see what you can make
# OUTPUT: Fully cookable recipes OR  Nearly cookable recipes (with the missing ingredients listed)
# ------------------------------------------------------------

import json
from pathlib import Path
import argparse# lets us read command-line
import re
from typing import Dict, List, Tuple
from recipe_sources import load_all_meals  #New -> loads favorites + custom + API recipes

# Build the paths relative to THIS file, so it works no matter where you run it
BASE_DIR = Path(__file__).resolve().parent
RECIPES_PATH = BASE_DIR / "data" / "recipes.json"
INVENTORY_PATH = BASE_DIR / "inventory.json"


# Using regular expressions to filter
def normalize_name(name: str) -> str:
    if not name:
        return ""
    s = name.lower().strip()
    # Remove punctuation characters using regex (keep letters, digits, spaces)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    # Collapse multiple spaces to one
    s = re.sub(r"\s+", " ", s).strip()
    return s

# TheMealDB parsing
#TheMealDB stores ingredient names in fields strIngredient1..strIngredient20.
#This function pulls TheMealDB stores ingredient names out and returns a cleaned list of names
def extract_ingredients_from_meal(meal: Dict) -> List[str]:
    if "ingredients" in meal:
        return [normalize_name(i) for i in meal["ingredients"]]
    names: List[str] = []
    for i in range(1, 21):
        raw = meal.get(f"strIngredient{i}") or ""
        cleaned = normalize_name(raw)
        if cleaned:
            names.append(cleaned)
    return names

# Return a list of 'meal' dicts from json file. If the file is missing or empty, return [].
def load_themealdb_recipes(path: Path) -> List[Dict]:
    if not path.exists():
        print(f"[warn] {path} not found. Run script to get data")
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))# parse JSON file
    except Exception as e:
        print(f"[warn] Could not parse recipes JSON: {e}")
        return []
    meals = data.get("meals") or []
    return [m for m in meals if isinstance(m, dict)]


def load_inventory(path: Path) -> dict:
    if not path.exists():
        # Create starter inventory with proper dict structure
        default = {
            "salt": {"quantity": 1, "unit": "tsp"},
            "pepper": {"quantity": 1, "unit": "tsp"}
        }
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        print(f"[info] Created starter inventory at {path}. Edit it to match your pantry.")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[warn] Could not parse inventory JSON: {e}")
        return {}
    return raw  # raw is a dict with "quantity"/"unit"

# Matching
# Compare a recipe's ingredient list against the inventory.
    # Returns missing count and the list
def score_recipe(ingredient_names: List[str], inventory: Dict[str, bool]):
    missing = []
    for ing in ingredient_names:
        if not inventory.get(ing, False):
            # print(f"[missing] {ing}")
            missing.append(ing)
    return len(missing), missing

#Split the list of recipes into two groups: cookable or near
def partition_recipes(meals: List[Dict], inventory: Dict[str, bool], max_missing: int):
    cookable = []
    near = []
    for meal in meals:
        name = meal.get("strMeal") or "(unnamed)"
        # extract normalized ingredient names for this meal
        ing_names = extract_ingredients_from_meal(meal)

        missing_count, missing_list = score_recipe(ing_names, inventory)

        if missing_count == 0:
            cookable.append((name, missing_count, missing_list))
        elif 0 < missing_count <= max_missing:
            near.append((name, missing_count, missing_list))
    # Simple sort to make output stable: fewest missing first, then name
    cookable.sort(key=lambda t: t[0].lower())
    near.sort(key=lambda t: (t[1], t[0].lower()))
    return cookable, near


# Command-line interface entry point: missing ingredients
def main():
    parser = argparse.ArgumentParser(description="Week 2: match recipes to inventory.")
    parser.add_argument("--max-missing", type=int, default=2, help="Max missing ingredients for 'near' bucket (default 2)")
    parser.add_argument("--top", type=int, default=15, help="How many items to show per bucket (default 15)")
    args = parser.parse_args()

    # Load data files (recipes + inventory)
    meals = load_all_meals()   # new <-- now includes API + favorites + custom in one list
    if not meals:
        print("No recipes loaded. Generate API data or add custom/favorites.")
        return
    inventory = load_inventory(INVENTORY_PATH)

    # If there are no recipes, run script to get TheMealDB
    if not meals:
        print("[warn] No recipes loaded. Run: python backend/simple_recipe_import.py \"chicken\"")
        return

    # Partition recipes by availability
    cookable, near = partition_recipes(meals, inventory, args.max_missing)

    print("\n================ COOKABLE RECIPES ================\n")
    if not cookable:
        print("(none)")
    else:
        for name, _, _ in cookable[:args.top]:
            print(f" {name}")

    print("\n============= NEARLY COOKABLE (missing ≤", args.max_missing, ") =============\n", sep="")
    if not near:
        print("(none)")
    else:
        for name, miss_cnt, miss_list in near[:args.top]:
            # join missing items as a comma-separated string
            missing_str = ", ".join(miss_list) if miss_list else "-"
            print(f"!!! {name}   — missing {miss_cnt}: {missing_str}")

    print("\n[ok] Matching complete.")

def get_recipe_matches(inventory: dict, max_missing=5, top=15):
    meals = load_all_meals()

    inventory_flags = {}
    for k, v in inventory.items():
        name = normalize_name(k)
        if isinstance(v, dict):
            qty = float(v.get("quantity", 0) or 0)
            have_it = qty > 0
        else:
            have_it = bool(v)
        inventory_flags[name] = have_it

    cookable, near = partition_recipes(meals, inventory_flags, max_missing)

    # Convert output format
    def meal_dict(recipe_tuple):
        name, _, missing = recipe_tuple
        meal = next((m for m in meals if m.get("title") == name or m.get("strMeal") == name), {})

        # Build ingredients list
        ingredients = []
        for i in range(1, 21):
            ing = meal.get(f"strIngredient{i}")
            measure = meal.get(f"strMeasure{i}")
            if ing and ing.strip():
                ingredients.append({"name": ing.strip(), "measure": measure.strip() if measure else ""})

        instructions = meal.get("strInstructions", "")

        image = meal.get("image") or meal.get("strMealThumb") or ""

        return {"title": name, "image": image, "missing": missing, "ingredients": ingredients, "instructions": instructions}


    return {
        "cookable": [meal_dict(r) for r in cookable[:top]],
        "near": [meal_dict(r) for r in near[:top]],
    }

# Run main() when executed as a script
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-missing", type=int, default=2)
    parser.add_argument("--top", type=int, default=15)
    args = parser.parse_args()

    inventory = load_inventory(INVENTORY_PATH)
    matches = get_recipe_matches(inventory, args.max_missing, args.top)
    print(matches)
