from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from pathlib import Path
import json
import os
import shutil
from recipe_matcher import get_recipe_matches, INVENTORY_PATH

app = Flask(__name__, static_folder="static")

CORS(app)
 
STAR_INGREDIENTS = [
    "chicken",
    "beef",
    "pork",
    "salmon",
    "egg",
    "eggs",
    "onion",
    "celery",
]

INVENTORY_FILE = "inventory.json"
RECIPES_FILE = "recipes.json"
FAVORITES_FILE = "favorites.json"

def normalize_name(name: str) -> str:
    return (name or "").strip().lower()

def api_json(data: dict, status: int = 200):
    return jsonify(data), status

def load_data(file):
    if not os.path.exists(file):
        return []
    with open(file, "r") as f:
        return json.load(f)


def save_data(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)


@app.route("/")
def home():
    return send_from_directory(app.static_folder, "index.html")


# ---- Inventory ---- #

def load_inventory(path: Path) -> dict:
    if not path.exists():
        path.write_text("{}", encoding="utf-8")
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[warn] Could not parse inventory JSON: {e}")
        return {}
    fixed = {}
    for name, val in (raw or {}).items():
        if isinstance(val, dict):
            try:
                qty = float(val.get("quantity", 0) or 0)
            except (TypeError, ValueError):
                qty = 0.0
            unit = (val.get("unit") or "").strip()
        else:
            qty = 1.0 if val else 0.0
            unit = ""
        key = normalize_name(name)
        fixed[key] = {"quantity": qty, "unit": unit}
    return fixed


def save_inventory(data: dict):
    INVENTORY_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")

def _to_ui_shape(inv):
    out = {}
    for k, v in (inv or {}).items():
        if isinstance(v, dict):
            try:
                qty = float(v.get("quantity", 0) or 0)
            except (TypeError, ValueError):
                qty = 0.0
            unit = (v.get("unit") or "").strip()
        else:
            qty = 1.0 if v else 0.0
            unit = ""
        out[k] = {"quantity": qty, "unit": unit}
    return out


@app.route("/api/inventory", methods=["GET"])
def get_inventory():
    inv = load_inventory(INVENTORY_PATH)
    return jsonify(_to_ui_shape(inv))

@app.route("/api/inventory", methods=["POST"])
def add_inventory_item():
    data = request.json or {}
    raw_name = (data.get("name") or "").strip()
    name = normalize_name(raw_name)
    qty_raw = data.get("quantity", 0)
    unit = (data.get("unit") or "").strip()

    if not name:
        return jsonify({"error": "name required"}), 400

    try:
        qty = float(qty_raw)
    except (TypeError, ValueError):
        qty = 0.0

    if qty <= 0:
        qty = 1.0

    inv = load_inventory(INVENTORY_PATH)
    inv[name] = {"quantity": qty, "unit": unit}
    save_inventory(inv)

    return jsonify(
        {
            "message": "Item added/updated",
            "item": {"name": raw_name or name, "quantity": qty, "unit": unit},
        }
    ), 201


@app.route("/api/inventory/reset", methods=["POST"])
def reset_inventory():
    save_inventory({})
    return jsonify({"message": "Inventory reset"})


@app.route("/api/inventory/<name>", methods=["PUT"])
def update_inventory_item(name):
    key = normalize_name(name)
    inv = load_inventory(INVENTORY_PATH)
    if key not in inv:
        return jsonify({"error": "Not found"}), 404

    data = request.json or {}
    qty_raw = data.get("quantity", 0)
    unit = (data.get("unit") or "").strip()

    try:
        qty = float(qty_raw)
    except (TypeError, ValueError):
        qty = 0.0

    if qty <= 0:
        qty = 1.0

    inv[key] = {"quantity": qty, "unit": unit}
    save_inventory(inv)
    return jsonify({"message": "Updated", "item": {"quantity": qty, "unit": unit}})


@app.route("/api/inventory/<name>", methods=["DELETE"])
def delete_inventory_item(name):
    key = normalize_name(name)
    inv = load_inventory(INVENTORY_PATH)
    if key not in inv:
        return jsonify({"error": "Not found"}), 404
    removed = inv.pop(key)
    save_inventory(inv)
    return jsonify({"message": "Deleted", "item": removed})


@app.route("/api/inventory/recipes")
def api_inventory_recipes():
    raw = load_inventory(INVENTORY_PATH)
    inventory = _to_bool_inv(raw)
    matches = get_recipe_matches(inventory)

    cookable = matches.get("cookable", [])
    near = matches.get("near", [])

    search = (request.args.get("search") or "").strip().lower()

    if search:
        main = search
    else:
        main = infer_main_ingredient(raw)

    def recipe_has_main(recipe, main_term):
        if not main_term:
            return False
        title = (recipe.get("title") or "").lower()
        if main_term in title:
            return True
        ings = recipe.get("ingredients") or []
        for ing in ings:
            name = (ing.get("name") or "").lower()
            if main_term in name:
                return True
        return False

    if main:
        combined = cookable + near
        combined = [r for r in combined if recipe_has_main(r, main)]
    else:
        combined = cookable

    return jsonify({"recipes": combined})



# ---- Recipes ---- #

@app.route("/api/recipes", methods=["GET"])
def get_recipes():
    return jsonify(load_data(RECIPES_FILE))

@app.route("/api/recipes/match")
def api_match_recipes():
    raw = load_inventory(INVENTORY_PATH)
    inventory = _to_bool_inv(raw)
    matches = get_recipe_matches(inventory, max_missing=3, top=50)
    recipes = matches["cookable"] + matches["near"]

    search = request.args.get("search", "").lower()
    if search:
        recipes = [r for r in recipes if search in r["title"].lower()]

    return jsonify({"recipes": recipes})


# ---- Favorites ---- #

@app.route("/api/favorites", methods=["GET"])
def get_favorites():
    favorites = load_data(FAVORITES_FILE)
    return jsonify(favorites)


@app.route("/api/favorites", methods=["POST"])
def add_favorite():
    data = request.json
    favorites = load_data(FAVORITES_FILE)

    if data not in favorites:
        favorites.append(data)
        save_data(FAVORITES_FILE, favorites)

    return jsonify({"message": "Added to favorites"}), 201


@app.route("/api/favorites", methods=["DELETE"])
def delete_favorite():
    data = request.get_json()
    title_to_remove = data.get("title")

    if not title_to_remove:
        return jsonify({"error": "Title required"}), 400

    favorites = load_data(FAVORITES_FILE)
    favorites = [f for f in favorites if f.get("title") != title_to_remove]
    save_data(FAVORITES_FILE, favorites)

    return jsonify({"message": "Favorite removed"})


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

def _to_bool_inv(inv):
    out = {}
    for k, v in (inv or {}).items():
        if isinstance(v, dict):
            try:
                qty = float(v.get("quantity", 0) or 0)
            except (TypeError, ValueError):
                qty = 0.0
            has = qty > 0
        else:
            has = bool(v)
        if not k:
            continue
        base = str(k).strip()
        variants = {
            base,
            base.lower(),
            base.upper(),
            base[:1].upper() + base[1:].lower(),
        }
        for name in variants:
            if has:
                out[name] = True
            else:
                out.setdefault(name, False)
    return out

def infer_main_ingredient(inv: dict):
    names = {normalize_name(k) for k in (inv or {}).keys()}
    for star in STAR_INGREDIENTS:
        if star in names:
            return star
    return None

@app.route("/api/inventory/main", methods=["GET"])
def get_main_ingredient():
    raw = load_inventory(INVENTORY_PATH)
    main = infer_main_ingredient(raw)
    return jsonify({"main": main})



if __name__ == "__main__":
    app.run()
