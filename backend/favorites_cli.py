# How to use:
#   python backend/favorites_cli.py --list
#   python backend/favorites_cli.py --add-id 52795
#   python backend/favorites_cli.py --remove-id 52795
#   python backend/favorites_cli.py --find "handi"
#   python backend/favorites_cli.py --cook "handi"
#   python backend/favorites_cli.py --cook "handi" --ignore "salt" --ignore "chili powder"
# ------------------------------------------------------------

import json
import argparse
from typing import List
from pathlib import Path
from recipe_sources import (
    load_all_meals,
    index_meals_by_id,
    load_favorite_ids,
    save_favorite_ids,
)

BASE_DIR = Path(__file__).resolve().parent
INVENTORY_PATH = BASE_DIR / "inventory.json"

def find_by_name(meals, query: str) -> List[dict]:
    q = (query or "").lower()
    return [m for m in meals
            if q in (m.get("strMeal") or "").lower()]

def main():
    # Define CLI flags
    parser = argparse.ArgumentParser(description="Manage favorites by ID (no recipe duplication).")
    parser.add_argument("--list", action="store_true", help="List favorites (id + name)")
    parser.add_argument("--add-id", type=str, help="Favorite by idMeal (e.g., 52795)")
    parser.add_argument("--remove-id", type=str, help="Unfavorite by idMeal")
    parser.add_argument("--find", type=str, help='Search meals by name, e.g., "handi"')
    parser.add_argument("--add-first", action="store_true", help="With --find, favorite the first match")
    parser.add_argument("--cook", type=str, help="Removes corresponding items from inventory after cooking")
    parser.add_argument("--ignore", action="append", default=[], help="List ingridients to ignore removing from inventory after --cook")
    parser.add_argument("--shop-list", type=str, help="Given a recipe, returns a list of needed ingridients")

    args = parser.parse_args()

    meals = load_all_meals()# load API + custom meals
    by_id = index_meals_by_id(meals)# id -> meal dict
    favs = load_favorite_ids()# set of favorite IDs

    # List favorites
    if args.list:
        if not favs:
            print("(no favorites)")
        else:
            for fid in sorted(favs): 
                name = by_id.get(fid, {}).get("strMeal", "(not found)")
                print(f"★ {fid} — {name}")
        return 

    changed = False

    # Add favorite by explicit ID
    if args.add_id:
        fid = args.add_id.strip()
        if fid not in by_id:
            print(f"ID {fid} not found in available meals. Import API or add custom first.")
        else:
            favs.add(fid)
            print(f"[ok] Favorited {fid} — {by_id[fid].get('strMeal')}")
            changed = True

    # Remove favorite by ID
    if args.remove_id:  # if --remove-id provided
        rid = args.remove_id.strip()
        if rid in favs:
            favs.remove(rid)
            print(f"[ok] Unfavorited {rid}")
            changed = True
        else:
            print(f"ID {rid} is not in favorites.")

    # Find by name 
    if args.find: # if --find provided
        matches = find_by_name(meals, args.find)
        if not matches:
            print("No matches.")
        else:
            for i, m in enumerate(matches[:10], start=1):
                print(f"{i}. {m.get('idMeal')} — {m.get('strMeal')}")
            if args.add_first:
                fid = str(matches[0].get("idMeal") or "").strip()
                if fid:
                    favs.add(fid)
                    print(f"[ok] Favorited {fid} — {matches[0].get('strMeal')}")
                    changed = True

    if changed:  # if we changed favorites
        save_favorite_ids(favs) 
        print("[ok] Saved favorites.")


    if args.cook:
        match = find_by_name(meals, args.cook)
        print(args)
        if not match:
            print("No match.")
        else:
            with open("inventory.json", "r") as f:
                inv = json.load(f)
            for key in match[0].keys():
                if key.startswith("strIngredient") and match[0][key].lower() not in args.ignore:
                    if match[0][key].lower() in inv.keys():
                        inv.pop(match[0][key].lower())
                        # inv[match[0][key].lower()] = False # use whichever is more convenient, setting false or popping from inventory
                        
            
            with open("inventory.json", "w") as f2:
                json.dump(inv, f2, indent = 4)

    if args.shop_list: 
        match = find_by_name(meals, args.shop_list)
        # print("match: ", match)
        if not match:
            print("No match.")
        else: 
            shopping_list = {}
            with open("inventory.json", "r") as f:
                invList = json.load(f).keys()
                # print("invList: ", invList)
            for recipeKey in match[0].keys():
                
                if match[0][recipeKey]: 
                    recipeValue = match[0][recipeKey].lower()
                else:
                    continue

                if recipeKey.startswith("strIngredient") and recipeValue not in invList:
                    shopping_list[recipeValue] = match[0]["strMeasure" + f"{recipeKey[-1]}"]
                    # print("Key: ", recipeKey, "| Value: ", recipeValue, )
                
            print(shopping_list)




if __name__ == "__main__":
    main()
