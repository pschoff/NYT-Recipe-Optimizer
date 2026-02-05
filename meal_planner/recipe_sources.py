"""Recipe data sources - legal alternatives to scraping NYTimes.

LEGAL & ETHICAL NOTE:
---------------------
Scraping NYTimes Cooking violates their Terms of Service, which explicitly
prohibit automated data collection. Instead, this module provides compliant
alternatives:

1. **Seed Data**: A curated set of original recipes with nutritional info,
   bundled with the application. No copyright concerns.

2. **Spoonacular API**: A commercial recipe API with a free tier (150 requests/day).
   Requires an API key from https://spoonacular.com/food-api

3. **TheMealDB API**: A free, open recipe database at https://www.themealdb.com/api.php
   Provides recipes under a Creative Commons license.

4. **Edamam API**: Another commercial option with nutrition analysis.
   https://developer.edamam.com/

5. **User-submitted recipes**: Users can add their own recipes manually.

The original Scraper.py is preserved for reference but should not be used
for production data collection from NYTimes.
"""

import json
import os
from typing import Optional

from meal_planner.config import SEED_DATA_PATH
from meal_planner.models import Recipe, Nutrition, Ingredient
from meal_planner.recipe_store import save_recipe, recipe_count


def load_seed_recipes(seed_path: str = SEED_DATA_PATH) -> list:
    """Load recipes from the bundled seed JSON file."""
    if not os.path.exists(seed_path):
        raise FileNotFoundError(f"Seed data not found at {seed_path}")

    with open(seed_path, "r") as f:
        data = json.load(f)

    recipes = []
    for item in data:
        nutrition = Nutrition(
            calories=item["nutrition"]["calories"],
            protein_g=item["nutrition"]["protein_g"],
            carbs_g=item["nutrition"]["carbs_g"],
            fat_g=item["nutrition"]["fat_g"],
            fiber_g=item["nutrition"].get("fiber_g", 0),
            sugar_g=item["nutrition"].get("sugar_g", 0),
            sodium_mg=item["nutrition"].get("sodium_mg", 0),
        )

        ingredients = [
            Ingredient(
                name=ing["name"],
                quantity=ing.get("quantity", 0),
                unit=ing.get("unit", ""),
                notes=ing.get("notes", ""),
            )
            for ing in item.get("ingredients", [])
        ]

        recipe = Recipe(
            id=None,
            title=item["title"],
            source="seed",
            source_url=item.get("source_url", ""),
            servings=item.get("servings", 1),
            prep_time_minutes=item.get("prep_time_minutes", 0),
            cook_time_minutes=item.get("cook_time_minutes", 0),
            meal_types=item.get("meal_types", []),
            cuisine=item.get("cuisine", ""),
            ingredients=ingredients,
            instructions=item.get("instructions", []),
            nutrition=nutrition,
        )
        recipes.append(recipe)

    return recipes


def import_seed_recipes(db_path: Optional[str] = None) -> int:
    """Import seed recipes into the database. Returns count of imported recipes."""
    kwargs = {"db_path": db_path} if db_path else {}
    if recipe_count(**kwargs) > 0:
        return 0  # Already seeded

    recipes = load_seed_recipes()
    count = 0
    for recipe in recipes:
        save_recipe(recipe, **kwargs)
        count += 1
    return count


def fetch_from_spoonacular(api_key: str, query: str = "", number: int = 10) -> list:
    """Fetch recipes from the Spoonacular API.

    Requires a free API key from https://spoonacular.com/food-api

    This is a template implementation. Users should sign up for an API key
    and configure it in their environment.
    """
    try:
        import requests
    except ImportError:
        print("requests library required. Install with: pip install requests")
        return []

    base_url = "https://api.spoonacular.com/recipes/complexSearch"
    params = {
        "apiKey": api_key,
        "query": query,
        "number": number,
        "addRecipeNutrition": True,
        "fillIngredients": True,
    }

    resp = requests.get(base_url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    recipes = []
    for item in data.get("results", []):
        nutrients = {n["name"].lower(): n["amount"] for n in item.get("nutrition", {}).get("nutrients", [])}

        nutrition = Nutrition(
            calories=nutrients.get("calories", 0),
            protein_g=nutrients.get("protein", 0),
            carbs_g=nutrients.get("carbohydrates", 0),
            fat_g=nutrients.get("fat", 0),
            fiber_g=nutrients.get("fiber", 0),
            sugar_g=nutrients.get("sugar", 0),
            sodium_mg=nutrients.get("sodium", 0),
        )

        ingredients = [
            Ingredient(
                name=ing.get("name", ""),
                quantity=ing.get("amount", 0),
                unit=ing.get("unit", ""),
            )
            for ing in item.get("extendedIngredients", [])
        ]

        # Determine meal types from dish types
        dish_types = [d.lower() for d in item.get("dishTypes", [])]
        meal_types = []
        if any(t in dish_types for t in ["breakfast", "morning meal"]):
            meal_types.append("breakfast")
        if any(t in dish_types for t in ["lunch", "main course", "salad", "soup"]):
            meal_types.append("lunch")
        if any(t in dish_types for t in ["dinner", "main course", "main dish"]):
            meal_types.append("dinner")
        if not meal_types:
            meal_types = ["lunch", "dinner"]

        recipe = Recipe(
            id=None,
            title=item.get("title", ""),
            source="spoonacular",
            source_url=item.get("sourceUrl", ""),
            servings=item.get("servings", 1),
            prep_time_minutes=item.get("preparationMinutes", 0),
            cook_time_minutes=item.get("cookingMinutes", 0),
            meal_types=meal_types,
            cuisine=", ".join(item.get("cuisines", [])),
            ingredients=ingredients,
            instructions=item.get("instructions", "").split("\n") if item.get("instructions") else [],
            nutrition=nutrition,
        )
        recipes.append(recipe)

    return recipes
