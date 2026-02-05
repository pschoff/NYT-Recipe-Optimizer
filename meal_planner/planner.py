"""Weekly meal plan generation and management."""

from datetime import date, datetime, timedelta
from typing import Optional

from meal_planner.db import get_connection, DB_PATH
from meal_planner.models import MacroTargets, MealPlan, MealPlanEntry
from meal_planner.recipe_store import get_all_recipes, get_recipe
from meal_planner.recommender import recommend_daily_meals


DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _get_recently_used_recipe_ids(
    user_id: int, before_date: date, window_days: int = 21, db_path: str = DB_PATH
) -> set:
    """Get recipe IDs used in recent meal plans (within variety window)."""
    cutoff = before_date - timedelta(days=window_days)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT DISTINCT mpe.recipe_id
               FROM meal_plan_entries mpe
               JOIN meal_plans mp ON mpe.meal_plan_id = mp.id
               WHERE mp.user_id = ? AND mp.week_start_date >= ?""",
            (user_id, cutoff.isoformat()),
        ).fetchall()
        return {row["recipe_id"] for row in rows}


def generate_weekly_plan(
    user_id: int,
    targets: MacroTargets,
    week_start: Optional[date] = None,
    db_path: str = DB_PATH,
) -> MealPlan:
    """Generate a 7-day meal plan optimized for macro targets.

    For each day:
    1. Gather recently used recipe IDs (previous plans within variety window)
    2. Also exclude recipes already selected earlier this week
    3. Run the recommendation algorithm
    4. Record selections
    """
    if week_start is None:
        today = date.today()
        # Start from next Monday
        week_start = today - timedelta(days=today.weekday())

    all_recipes = get_all_recipes(db_path)
    recently_used = _get_recently_used_recipe_ids(user_id, week_start, db_path=db_path)
    week_used = set()  # Track what we pick this week for added variety

    plan = MealPlan(
        id=None,
        user_id=user_id,
        week_start_date=week_start,
        entries=[],
        created_at=datetime.now(),
    )

    for day in range(7):
        exclusion_set = recently_used | week_used
        daily_meals = recommend_daily_meals(targets, all_recipes, exclusion_set)

        for meal_type, recipe, servings in daily_meals:
            entry = MealPlanEntry(
                id=None,
                meal_plan_id=0,  # Will be set on save
                day_of_week=day,
                meal_type=meal_type,
                recipe_id=recipe.id,
                servings=servings,
                recipe=recipe,
            )
            plan.entries.append(entry)
            week_used.add(recipe.id)

    return plan


def save_meal_plan(plan: MealPlan, db_path: str = DB_PATH) -> int:
    """Persist a meal plan to the database. Returns the plan ID."""
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            "INSERT INTO meal_plans (user_id, week_start_date) VALUES (?, ?)",
            (plan.user_id, plan.week_start_date.isoformat()),
        )
        plan_id = cursor.lastrowid

        for entry in plan.entries:
            conn.execute(
                """INSERT INTO meal_plan_entries
                   (meal_plan_id, day_of_week, meal_type, recipe_id, servings)
                   VALUES (?, ?, ?, ?, ?)""",
                (plan_id, entry.day_of_week, entry.meal_type, entry.recipe_id, entry.servings),
            )

        return plan_id


def load_meal_plan(
    user_id: int, week_start: date, db_path: str = DB_PATH
) -> Optional[MealPlan]:
    """Load a meal plan for a given week."""
    with get_connection(db_path) as conn:
        plan_row = conn.execute(
            "SELECT * FROM meal_plans WHERE user_id = ? AND week_start_date = ?",
            (user_id, week_start.isoformat()),
        ).fetchone()

        if not plan_row:
            return None

        entries_rows = conn.execute(
            """SELECT * FROM meal_plan_entries
               WHERE meal_plan_id = ?
               ORDER BY day_of_week, meal_type""",
            (plan_row["id"],),
        ).fetchall()

        entries = []
        for row in entries_rows:
            recipe = get_recipe(row["recipe_id"], db_path)
            entries.append(MealPlanEntry(
                id=row["id"],
                meal_plan_id=row["meal_plan_id"],
                day_of_week=row["day_of_week"],
                meal_type=row["meal_type"],
                recipe_id=row["recipe_id"],
                servings=row["servings"],
                recipe=recipe,
            ))

        return MealPlan(
            id=plan_row["id"],
            user_id=plan_row["user_id"],
            week_start_date=date.fromisoformat(plan_row["week_start_date"]),
            entries=entries,
            created_at=plan_row["created_at"],
        )


def regenerate_meal(
    plan_id: int,
    day_of_week: int,
    meal_type: str,
    targets: MacroTargets,
    db_path: str = DB_PATH,
) -> Optional[MealPlanEntry]:
    """Regenerate a single meal in an existing plan."""
    all_recipes = get_all_recipes(db_path)

    with get_connection(db_path) as conn:
        plan_row = conn.execute("SELECT * FROM meal_plans WHERE id = ?", (plan_id,)).fetchone()
        if not plan_row:
            return None

        # Get all recipe IDs in this plan to exclude
        used_rows = conn.execute(
            "SELECT recipe_id FROM meal_plan_entries WHERE meal_plan_id = ?",
            (plan_id,),
        ).fetchall()
        used_ids = {row["recipe_id"] for row in used_rows}

        # Also get recently used from other plans
        recently_used = _get_recently_used_recipe_ids(
            plan_row["user_id"],
            date.fromisoformat(plan_row["week_start_date"]),
            db_path=db_path,
        )
        exclusion = used_ids | recently_used

        # Recommend for just this meal type
        daily = recommend_daily_meals(targets, all_recipes, exclusion)
        new_meal = None
        for mt, recipe, servings in daily:
            if mt == meal_type:
                new_meal = (recipe, servings)
                break

        if not new_meal:
            return None

        recipe, servings = new_meal

        # Update the entry in the database
        conn.execute(
            """UPDATE meal_plan_entries
               SET recipe_id = ?, servings = ?
               WHERE meal_plan_id = ? AND day_of_week = ? AND meal_type = ?""",
            (recipe.id, servings, plan_id, day_of_week, meal_type),
        )

        return MealPlanEntry(
            id=None,
            meal_plan_id=plan_id,
            day_of_week=day_of_week,
            meal_type=meal_type,
            recipe_id=recipe.id,
            servings=servings,
            recipe=recipe,
        )


def format_meal_plan(plan: MealPlan) -> str:
    """Format a meal plan for display."""
    lines = [f"Meal Plan for week of {plan.week_start_date.isoformat()}", "=" * 50]

    for day in range(7):
        day_entries = [e for e in plan.entries if e.day_of_week == day]
        if not day_entries:
            continue

        lines.append(f"\n{DAY_NAMES[day]}:")
        lines.append("-" * 30)

        day_nutrition = None
        for entry in sorted(day_entries, key=lambda e: ["breakfast", "lunch", "dinner"].index(e.meal_type)):
            recipe_name = entry.recipe.title if entry.recipe else f"Recipe #{entry.recipe_id}"
            servings_str = f" ({entry.servings:.2g} servings)" if entry.servings != 1.0 else ""
            lines.append(f"  {entry.meal_type.capitalize():10s} {recipe_name}{servings_str}")

            if entry.recipe and entry.recipe.nutrition:
                n = entry.recipe.nutrition.scaled(entry.servings)
                lines.append(f"             {n.calories:.0f} cal | P:{n.protein_g:.0f}g C:{n.carbs_g:.0f}g F:{n.fat_g:.0f}g")
                if day_nutrition is None:
                    day_nutrition = n
                else:
                    day_nutrition = day_nutrition + n

        if day_nutrition:
            lines.append(f"  {'Daily Total':10s} {day_nutrition.calories:.0f} cal | "
                         f"P:{day_nutrition.protein_g:.0f}g C:{day_nutrition.carbs_g:.0f}g F:{day_nutrition.fat_g:.0f}g")

    return "\n".join(lines)
