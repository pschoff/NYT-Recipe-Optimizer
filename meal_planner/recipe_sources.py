"""Recipe data sources.

Available sources:
1. **Seed Data**: 30 curated recipes bundled as data/seed_recipes.json
2. **NYTimes Cooking**: Scrape recipes from NYT Cooking article pages
   (requires a NYTimes subscription for full access)
3. **CSV import/export**: Save scraped recipes to CSV so you don't have to re-scrape
"""

import csv
import json
import os
import time
from typing import Optional
from urllib.request import urlopen

from meal_planner.config import SEED_DATA_PATH
from meal_planner.models import Recipe, Nutrition, Ingredient
from meal_planner.recipe_store import get_all_recipes, save_recipe, recipe_count, search_recipes


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


CSV_COLUMNS = [
    "title", "source", "source_url", "servings", "prep_time_minutes",
    "cook_time_minutes", "meal_types", "cuisine", "ingredients",
    "instructions", "calories", "protein_g", "carbs_g", "fat_g",
    "fiber_g", "sugar_g", "sodium_mg",
]


def export_recipes_csv(file_path: str, db_path: Optional[str] = None) -> int:
    """Export all recipes from the database to a CSV file.

    Returns the number of recipes exported.
    """
    kwargs = {"db_path": db_path} if db_path else {}
    recipes = get_all_recipes(**kwargs)

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()

        for r in recipes:
            row = {
                "title": r.title,
                "source": r.source,
                "source_url": r.source_url,
                "servings": r.servings,
                "prep_time_minutes": r.prep_time_minutes,
                "cook_time_minutes": r.cook_time_minutes,
                "meal_types": ",".join(r.meal_types),
                "cuisine": r.cuisine,
                "ingredients": json.dumps([
                    {"name": i.name, "quantity": i.quantity, "unit": i.unit, "notes": i.notes}
                    for i in r.ingredients
                ]),
                "instructions": json.dumps(r.instructions),
                "calories": r.nutrition.calories if r.nutrition else "",
                "protein_g": r.nutrition.protein_g if r.nutrition else "",
                "carbs_g": r.nutrition.carbs_g if r.nutrition else "",
                "fat_g": r.nutrition.fat_g if r.nutrition else "",
                "fiber_g": r.nutrition.fiber_g if r.nutrition else "",
                "sugar_g": r.nutrition.sugar_g if r.nutrition else "",
                "sodium_mg": r.nutrition.sodium_mg if r.nutrition else "",
            }
            writer.writerow(row)

    return len(recipes)


def import_recipes_csv(file_path: str, db_path: Optional[str] = None) -> int:
    """Import recipes from a CSV file into the database.

    Skips recipes whose title already exists in the database.
    Returns the number of newly imported recipes.
    """
    kwargs = {"db_path": db_path} if db_path else {}

    with open(file_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        imported = 0

        for row in reader:
            title = row.get("title", "").strip()
            if not title:
                continue

            # Skip duplicates
            existing = search_recipes(title, **kwargs)
            if any(r.title.lower() == title.lower() for r in existing):
                continue

            # Parse nutrition
            nutrition = None
            cal = row.get("calories", "").strip()
            if cal:
                nutrition = Nutrition(
                    calories=float(cal),
                    protein_g=float(row.get("protein_g", 0) or 0),
                    carbs_g=float(row.get("carbs_g", 0) or 0),
                    fat_g=float(row.get("fat_g", 0) or 0),
                    fiber_g=float(row.get("fiber_g", 0) or 0),
                    sugar_g=float(row.get("sugar_g", 0) or 0),
                    sodium_mg=float(row.get("sodium_mg", 0) or 0),
                )

            # Parse ingredients (JSON string or empty)
            ingredients = []
            ing_raw = row.get("ingredients", "").strip()
            if ing_raw:
                try:
                    for ing in json.loads(ing_raw):
                        ingredients.append(Ingredient(
                            name=ing.get("name", ""),
                            quantity=ing.get("quantity", 0),
                            unit=ing.get("unit", ""),
                            notes=ing.get("notes", ""),
                        ))
                except (json.JSONDecodeError, TypeError):
                    pass

            # Parse instructions (JSON string or empty)
            instructions = []
            inst_raw = row.get("instructions", "").strip()
            if inst_raw:
                try:
                    instructions = json.loads(inst_raw)
                except (json.JSONDecodeError, TypeError):
                    pass

            meal_types = [m.strip() for m in row.get("meal_types", "").split(",") if m.strip()]

            recipe = Recipe(
                id=None,
                title=title,
                source=row.get("source", "csv"),
                source_url=row.get("source_url", ""),
                servings=int(row.get("servings", 1) or 1),
                prep_time_minutes=int(row.get("prep_time_minutes", 0) or 0),
                cook_time_minutes=int(row.get("cook_time_minutes", 0) or 0),
                meal_types=meal_types,
                cuisine=row.get("cuisine", ""),
                ingredients=ingredients,
                instructions=instructions,
                nutrition=nutrition,
            )

            save_recipe(recipe, **kwargs)
            imported += 1

    return imported


