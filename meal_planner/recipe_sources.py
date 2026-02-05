"""Recipe data sources.

Available sources:
1. **Seed Data**: 30 curated recipes bundled as data/seed_recipes.json
2. **NYTimes Cooking**: Scrape recipes from NYT Cooking article pages
   (requires a NYTimes subscription for full access)
3. **Spoonacular API**: Commercial recipe API with free tier (150 req/day)
4. **TheMealDB API**: Free open recipe database (CC licensed)
"""

import json
import os
import time
from typing import Optional
from urllib.request import urlopen

from meal_planner.config import SEED_DATA_PATH
from meal_planner.models import Recipe, Nutrition, Ingredient
from meal_planner.recipe_store import save_recipe, recipe_count, search_recipes


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


def _discover_nyt_recipe_urls(article_url: str) -> set:
    """Crawl a NYTimes Cooking article page and extract recipe URLs.

    Based on the original Scraper.py logic.
    """
    import requests
    from bs4 import BeautifulSoup

    response = requests.get(article_url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    recipe_links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/recipes/" in href:
            if href.startswith("https://"):
                full_url = href
            else:
                full_url = "https://cooking.nytimes.com" + href
            recipe_links.add(full_url)

    return recipe_links


def _scrape_nyt_recipe(url: str) -> Optional[Recipe]:
    """Scrape a single NYTimes Cooking recipe page.

    Uses the recipe_scrapers library to extract structured data.
    Returns a Recipe object or None if scraping fails.
    """
    from recipe_scrapers import scrape_html

    try:
        html = urlopen(url).read().decode("utf-8")
        scraper = scrape_html(html, org_url=url)
    except Exception as e:
        print(f"  Failed to fetch {url}: {e}")
        return None

    # Extract nutrition
    nutrition = None
    try:
        nutrients = scraper.nutrients()
        nutrition = Nutrition(
            calories=float(nutrients.get("calories", 0)),
            protein_g=float(str(nutrients.get("proteinContent", "0")).split()[0]),
            carbs_g=float(str(nutrients.get("carbohydrateContent", "0")).split()[0]),
            fat_g=float(str(nutrients.get("fatContent", "0")).split()[0]),
            fiber_g=float(str(nutrients.get("fiberContent", "0")).split()[0]) if "fiberContent" in nutrients else 0,
            sugar_g=float(str(nutrients.get("sugarContent", "0")).split()[0]) if "sugarContent" in nutrients else 0,
            sodium_mg=float(str(nutrients.get("sodiumContent", "0")).split()[0]) if "sodiumContent" in nutrients else 0,
        )
    except Exception:
        pass  # Some recipes don't have nutrition data

    # Extract title
    try:
        title = scraper.title()
    except Exception:
        title = url.split("/")[-1].replace("-", " ").title()

    # Extract ingredients
    ingredients = []
    try:
        for ing_str in scraper.ingredients():
            ingredients.append(Ingredient(name=ing_str, quantity=0, unit=""))
    except Exception:
        pass

    # Extract instructions
    instructions = []
    try:
        raw = scraper.instructions()
        instructions = [s.strip() for s in raw.split("\n") if s.strip()]
    except Exception:
        pass

    # Extract other metadata
    servings = 1
    try:
        servings = int(scraper.yields().split()[0])
    except Exception:
        pass

    prep_time = 0
    try:
        prep_time = int(scraper.prep_time())
    except Exception:
        pass

    cook_time = 0
    try:
        cook_time = int(scraper.cook_time())
    except Exception:
        pass

    # NYT doesn't tag meal types, so default to lunch+dinner
    meal_types = ["lunch", "dinner"]

    return Recipe(
        id=None,
        title=title,
        source="nytimes",
        source_url=url,
        servings=servings,
        prep_time_minutes=prep_time,
        cook_time_minutes=cook_time,
        meal_types=meal_types,
        cuisine="",
        ingredients=ingredients,
        instructions=instructions,
        nutrition=nutrition,
    )


def scrape_nyt_article(
    article_url: str = "https://cooking.nytimes.com/article/cheap-healthy-dinner-ideas",
    db_path: Optional[str] = None,
    delay: float = 1.0,
) -> int:
    """Scrape recipes from a NYTimes Cooking article and import them.

    Discovers recipe links on the article page, then scrapes each recipe
    individually. Skips recipes already in the database (by title match).
    Adds a delay between requests to be respectful.

    Returns the number of newly imported recipes.
    """
    kwargs = {"db_path": db_path} if db_path else {}

    print(f"Discovering recipe URLs from {article_url}...")
    urls = _discover_nyt_recipe_urls(article_url)
    print(f"Found {len(urls)} recipe links.")

    imported = 0
    for i, url in enumerate(sorted(urls), 1):
        print(f"  [{i}/{len(urls)}] Scraping {url}...")
        recipe = _scrape_nyt_recipe(url)
        if not recipe:
            continue

        # Skip if a recipe with this title already exists
        existing = search_recipes(recipe.title, **kwargs)
        if any(r.title.lower() == recipe.title.lower() for r in existing):
            print(f"    Skipped (already exists): {recipe.title}")
            continue

        save_recipe(recipe, **kwargs)
        imported += 1
        cal_str = f"{recipe.nutrition.calories:.0f} cal" if recipe.nutrition else "no nutrition"
        print(f"    Imported: {recipe.title} ({cal_str})")

        if delay > 0 and i < len(urls):
            time.sleep(delay)

    return imported


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
