"""Recipe persistence layer - CRUD operations for recipes."""

import json
from typing import Optional

from meal_planner.db import get_connection, DB_PATH
from meal_planner.models import Recipe, Nutrition, Ingredient


def _row_to_recipe(row, nutrition_row=None) -> Recipe:
    """Convert a database row to a Recipe object."""
    nutrition = None
    if nutrition_row:
        nutrition = Nutrition(
            calories=nutrition_row["calories"],
            protein_g=nutrition_row["protein_g"],
            carbs_g=nutrition_row["carbs_g"],
            fat_g=nutrition_row["fat_g"],
            fiber_g=nutrition_row["fiber_g"],
            sugar_g=nutrition_row["sugar_g"],
            sodium_mg=nutrition_row["sodium_mg"],
        )

    ingredients_raw = json.loads(row["ingredients"]) if row["ingredients"] else []
    ingredients = [
        Ingredient(
            name=ing.get("name", ""),
            quantity=ing.get("quantity", 0),
            unit=ing.get("unit", ""),
            notes=ing.get("notes", ""),
        )
        for ing in ingredients_raw
    ]

    instructions = json.loads(row["instructions"]) if row["instructions"] else []
    meal_types = [m.strip() for m in row["meal_types"].split(",") if m.strip()]

    return Recipe(
        id=row["id"],
        title=row["title"],
        source=row["source"],
        source_url=row["source_url"],
        servings=row["servings"],
        prep_time_minutes=row["prep_time_minutes"],
        cook_time_minutes=row["cook_time_minutes"],
        meal_types=meal_types,
        cuisine=row["cuisine"],
        ingredients=ingredients,
        instructions=instructions,
        nutrition=nutrition,
        created_at=row["created_at"],
    )


def save_recipe(recipe: Recipe, db_path: str = DB_PATH) -> int:
    """Save a recipe to the database. Returns the recipe ID."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO recipes (title, source, source_url, servings,
               prep_time_minutes, cook_time_minutes, meal_types, cuisine,
               ingredients, instructions)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                recipe.title,
                recipe.source,
                recipe.source_url,
                recipe.servings,
                recipe.prep_time_minutes,
                recipe.cook_time_minutes,
                ",".join(recipe.meal_types),
                recipe.cuisine,
                json.dumps([
                    {"name": i.name, "quantity": i.quantity, "unit": i.unit, "notes": i.notes}
                    for i in recipe.ingredients
                ]),
                json.dumps(recipe.instructions),
            ),
        )
        recipe_id = cursor.lastrowid

        if recipe.nutrition:
            n = recipe.nutrition
            conn.execute(
                """INSERT INTO recipe_nutrition
                   (recipe_id, calories, protein_g, carbs_g, fat_g, fiber_g, sugar_g, sodium_mg)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (recipe_id, n.calories, n.protein_g, n.carbs_g, n.fat_g,
                 n.fiber_g, n.sugar_g, n.sodium_mg),
            )

        return recipe_id


def get_recipe(recipe_id: int, db_path: str = DB_PATH) -> Optional[Recipe]:
    """Load a single recipe by ID."""
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
        if not row:
            return None
        nutr_row = conn.execute(
            "SELECT * FROM recipe_nutrition WHERE recipe_id = ?", (recipe_id,)
        ).fetchone()
        return _row_to_recipe(row, nutr_row)


def get_all_recipes(db_path: str = DB_PATH) -> list:
    """Load all recipes with nutrition data."""
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM recipes ORDER BY title").fetchall()
        recipes = []
        for row in rows:
            nutr_row = conn.execute(
                "SELECT * FROM recipe_nutrition WHERE recipe_id = ?", (row["id"],)
            ).fetchone()
            recipes.append(_row_to_recipe(row, nutr_row))
        return recipes


def get_recipes_by_meal_type(meal_type: str, db_path: str = DB_PATH) -> list:
    """Get recipes that match a given meal type."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM recipes WHERE meal_types LIKE ? ORDER BY title",
            (f"%{meal_type}%",),
        ).fetchall()
        recipes = []
        for row in rows:
            nutr_row = conn.execute(
                "SELECT * FROM recipe_nutrition WHERE recipe_id = ?", (row["id"],)
            ).fetchone()
            recipes.append(_row_to_recipe(row, nutr_row))
        return recipes


def get_recipes_with_nutrition(db_path: str = DB_PATH) -> list:
    """Get all recipes that have nutrition data."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT r.* FROM recipes r
               INNER JOIN recipe_nutrition rn ON r.id = rn.recipe_id
               ORDER BY r.title""",
        ).fetchall()
        recipes = []
        for row in rows:
            nutr_row = conn.execute(
                "SELECT * FROM recipe_nutrition WHERE recipe_id = ?", (row["id"],)
            ).fetchone()
            recipes.append(_row_to_recipe(row, nutr_row))
        return recipes


def recipe_count(db_path: str = DB_PATH) -> int:
    """Return total number of recipes in the database."""
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) as cnt FROM recipes").fetchone()
        return row["cnt"]


def delete_recipe(recipe_id: int, db_path: str = DB_PATH) -> bool:
    """Delete a recipe by ID. Returns True if deleted."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
        return cursor.rowcount > 0


def search_recipes(query: str, db_path: str = DB_PATH) -> list:
    """Search recipes by title (case-insensitive)."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM recipes WHERE LOWER(title) LIKE ? ORDER BY title",
            (f"%{query.lower()}%",),
        ).fetchall()
        recipes = []
        for row in rows:
            nutr_row = conn.execute(
                "SELECT * FROM recipe_nutrition WHERE recipe_id = ?", (row["id"],)
            ).fetchone()
            recipes.append(_row_to_recipe(row, nutr_row))
        return recipes
