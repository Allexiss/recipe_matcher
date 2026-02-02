from __future__ import annotations

from typing import Dict


# SYNONYMS maps variant -> canonical name.
# Ex: both "bell pepper" and "bell peppers" become "pepper"
SYNONYMS: Dict[str, str] = {
    # peppers
    "bell pepper": "pepper",
    "bell peppers": "pepper",
    "red pepper": "pepper",
    "green pepper": "pepper",
    # other
    "yoghurt": "yogurt",
    # chilli/chili variants
    "green chilli": "chilli",
    "green chili": "chilli",
    "chilli powder": "chili powder",
    # oils
    "vegetable oil": "oil",
    "olive oil": "oil",
    # stock/broth
    "chicken stock": "chicken broth",
    "stock": "broth",
    # onion
    "spring onion": "green onion",
    "spring onions": "green onion",
    "tomatoes": "tomato",
    "potatoes": "potato",
    "onions": "onion",
    "peppers": "pepper",
    # we can add more
}


def to_canonical(name: str) -> str:
    return SYNONYMS.get(name, name)
