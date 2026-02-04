# backend/inventory_cli.py
import json
from pathlib import Path
import argparse
import re
import subprocess
from typing import Dict, List

INVENTORY_PATH = Path(__file__).resolve().parent / "/api/inventory.json"

def normalize(name: str) -> str:
    s = (name or "").lower().strip()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def load_inventory() -> Dict[str, bool]:
    if not INVENTORY_PATH.exists():
        return {}
    try:
        return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_inventory(inv: Dict[str, bool]) -> None:
    INVENTORY_PATH.write_text(json.dumps(inv, indent=2, ensure_ascii=False), encoding="utf-8")

def add_have(inv: Dict[str, bool], items: List[str]) -> None:
    for raw in items:
        n = normalize(raw)
        if n:
            inv[n] = True

def add_missing(inv: Dict[str, bool], items: List[str]) -> None:
    for raw in items:
        n = normalize(raw)
        if n:
            inv[n] = False

def remove(inv: Dict[str, bool], items: List[str]) -> None:
    for raw in items:
        n = normalize(raw)
        if n in inv:
            del inv[n]

def parse_csv(s: str | None) -> List[str]:
    if not s:
        return []
    return [p.strip() for p in s.split(",") if p.strip()]

def main():
    parser = argparse.ArgumentParser(description="Manage backend/inventory.json")
    parser.add_argument("--have", type=str, help='Comma-separated items you HAVE, e.g., "chicken,onion"')
    parser.add_argument("--missing", type=str, help='Comma-separated items you do NOT have, e.g., "tomato"')
    parser.add_argument("--remove", type=str, help='Comma-separated items to delete from pantry')
    parser.add_argument("--reset", action="store_true", help="Clear inventory (set to empty {})")
    parser.add_argument("--list", action="store_true", help="Print current inventory and exit")
    parser.add_argument("--run", action="store_true", help="Run the recipe matcher after updating inventory")
    parser.add_argument("--max-missing", type=int, default=2, help="Threshold for 'nearly cookable' when using --run")
    args = parser.parse_args()

    inv = load_inventory()

    if args.reset:
        inv = {}

    have_items = parse_csv(args.have)
    if have_items:
        add_have(inv, have_items)

    missing_items = parse_csv(args.missing)
    if missing_items:
        add_missing(inv, missing_items)

    remove_items = parse_csv(args.remove)
    if remove_items:
        remove(inv, remove_items)

    if args.list and not (args.reset or have_items or missing_items or remove_items):
        print(json.dumps(inv, indent=2, ensure_ascii=False))
        return

    if args.reset or have_items or missing_items or remove_items:
        save_inventory(inv)
        print(f"[ok] Saved {INVENTORY_PATH}")

    if args.run:
        cmd = ["python", str(Path(__file__).resolve().parent / "recipe_matcher.py"),
               "--max-missing", str(args.max_missing)]
        print(f"[info] Running: {' '.join(cmd)}")
        subprocess.run(cmd, check=False)

if __name__ == "__main__":
    main()
