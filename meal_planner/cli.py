"""Command-line interface for the meal planning application."""

import argparse
import os
import sys
from datetime import date, datetime

from meal_planner.config import ACTIVITY_MULTIPLIERS, GOAL_CALORIE_ADJUSTMENTS
from meal_planner.db import init_db, get_connection, DB_PATH
from meal_planner.macro_calculator import calculate_macro_targets, format_targets
from meal_planner.models import UserProfile
from meal_planner.planner import (
    DAY_NAMES,
    format_meal_plan,
    generate_weekly_plan,
    load_meal_plan,
    regenerate_meal,
    save_meal_plan,
)
from meal_planner.recipe_sources import (
    export_recipes_csv,
    import_recipes_csv,
    import_seed_recipes,
    scrape_nyt_article,
)
from meal_planner.recipe_store import get_all_recipes, get_recipe, search_recipes
from meal_planner.tracker import (
    daily_summary,
    format_summary,
    log_meal,
    monthly_summary,
    weekly_summary,
    yearly_summary,
)


# --- Unit conversions (imperial input, metric internal) ---

LBS_PER_KG = 2.20462
CM_PER_INCH = 2.54
INCHES_PER_FOOT = 12


def _lbs_to_kg(lbs: float) -> float:
    return lbs / LBS_PER_KG


def _kg_to_lbs(kg: float) -> float:
    return kg * LBS_PER_KG


def _ft_in_to_cm(feet: int, inches: int) -> float:
    return (feet * INCHES_PER_FOOT + inches) * CM_PER_INCH


def _cm_to_ft_in(cm: float) -> tuple:
    total_inches = cm / CM_PER_INCH
    feet = int(total_inches // INCHES_PER_FOOT)
    inches = int(round(total_inches % INCHES_PER_FOOT))
    if inches == 12:
        feet += 1
        inches = 0
    return feet, inches


# --- User profile helpers ---

def _save_user(profile: UserProfile) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO users (name, age, weight_kg, height_cm, sex, activity_level, goal)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (profile.name, profile.age, profile.weight_kg, profile.height_cm,
             profile.sex, profile.activity_level, profile.goal),
        )
        return cursor.lastrowid


def _update_user(profile: UserProfile) -> None:
    with get_connection() as conn:
        conn.execute(
            """UPDATE users SET name=?, age=?, weight_kg=?, height_cm=?, sex=?,
               activity_level=?, goal=?, updated_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (profile.name, profile.age, profile.weight_kg, profile.height_cm,
             profile.sex, profile.activity_level, profile.goal, profile.id),
        )


def _load_user(user_id: int = 1) -> UserProfile:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            return None
        return UserProfile(
            id=row["id"], name=row["name"], age=row["age"],
            weight_kg=row["weight_kg"], height_cm=row["height_cm"],
            sex=row["sex"], activity_level=row["activity_level"],
            goal=row["goal"], created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def _get_active_user() -> UserProfile:
    user = _load_user()
    if not user:
        print("No user profile found. Create one first:")
        print("  python -m meal_planner profile create")
        sys.exit(1)
    return user


# --- Command handlers ---

def cmd_profile_create(args):
    activity_levels = list(ACTIVITY_MULTIPLIERS.keys())
    goals = list(GOAL_CALORIE_ADJUSTMENTS.keys())

    weight_kg = _lbs_to_kg(args.weight)
    height_cm = _ft_in_to_cm(args.feet, args.inches)

    profile = UserProfile(
        id=None,
        name=args.name,
        age=args.age,
        weight_kg=weight_kg,
        height_cm=height_cm,
        sex=args.sex,
        activity_level=args.activity,
        goal=args.goal,
    )

    if profile.activity_level not in activity_levels:
        print(f"Invalid activity level. Choose from: {', '.join(activity_levels)}")
        sys.exit(1)
    if profile.goal not in goals:
        print(f"Invalid goal. Choose from: {', '.join(goals)}")
        sys.exit(1)

    user_id = _save_user(profile)
    print(f"Profile created (ID: {user_id})")

    targets = calculate_macro_targets(profile)
    print(f"\nYour daily targets:")
    print(format_targets(targets))


def cmd_profile_show(args):
    user = _get_active_user()
    lbs = _kg_to_lbs(user.weight_kg)
    ft, inches = _cm_to_ft_in(user.height_cm)
    print(f"Name:     {user.name}")
    print(f"Age:      {user.age}")
    print(f"Weight:   {lbs:.0f} lbs")
    print(f"Height:   {ft}'{inches}\"")
    print(f"Sex:      {user.sex}")
    print(f"Activity: {user.activity_level}")
    print(f"Goal:     {user.goal}")

    targets = calculate_macro_targets(user)
    print(f"\nDaily Targets:")
    print(format_targets(targets))


def cmd_profile_update(args):
    user = _get_active_user()
    if args.age is not None:
        user.age = args.age
    if args.weight is not None:
        user.weight_kg = _lbs_to_kg(args.weight)
    if args.feet is not None or args.inches is not None:
        ft, inches = _cm_to_ft_in(user.height_cm)
        if args.feet is not None:
            ft = args.feet
        if args.inches is not None:
            inches = args.inches
        user.height_cm = _ft_in_to_cm(ft, inches)
    if args.activity is not None:
        user.activity_level = args.activity
    if args.goal is not None:
        user.goal = args.goal

    _update_user(user)
    print("Profile updated.")
    targets = calculate_macro_targets(user)
    print(f"\nUpdated daily targets:")
    print(format_targets(targets))


def cmd_macros(args):
    user = _get_active_user()
    targets = calculate_macro_targets(user)
    print(format_targets(targets))


def cmd_recipes_list(args):
    recipes = get_all_recipes()
    if not recipes:
        print("No recipes found. Import seed data:")
        print("  python -m meal_planner recipes import")
        return

    print(f"{'ID':>4}  {'Title':<45}  {'Cal':>5}  {'P(g)':>5}  {'C(g)':>5}  {'F(g)':>5}  {'Types'}")
    print("-" * 95)
    for r in recipes:
        cal = f"{r.nutrition.calories:.0f}" if r.nutrition else "N/A"
        prot = f"{r.nutrition.protein_g:.0f}" if r.nutrition else "N/A"
        carb = f"{r.nutrition.carbs_g:.0f}" if r.nutrition else "N/A"
        fat = f"{r.nutrition.fat_g:.0f}" if r.nutrition else "N/A"
        types = ", ".join(r.meal_types)
        print(f"{r.id:>4}  {r.title:<45}  {cal:>5}  {prot:>5}  {carb:>5}  {fat:>5}  {types}")


def cmd_recipes_search(args):
    results = search_recipes(args.query)
    if not results:
        print(f"No recipes found matching '{args.query}'")
        return
    for r in results:
        cal = f"{r.nutrition.calories:.0f}" if r.nutrition else "N/A"
        print(f"  [{r.id}] {r.title} ({cal} cal)")


def cmd_recipes_show(args):
    recipe = get_recipe(args.recipe_id)
    if not recipe:
        print(f"Recipe {args.recipe_id} not found.")
        return

    print(f"Title:    {recipe.title}")
    print(f"Cuisine:  {recipe.cuisine}")
    print(f"Types:    {', '.join(recipe.meal_types)}")
    print(f"Servings: {recipe.servings}")
    print(f"Prep:     {recipe.prep_time_minutes} min")
    print(f"Cook:     {recipe.cook_time_minutes} min")

    if recipe.ingredients:
        print(f"\nIngredients:")
        for ing in recipe.ingredients:
            notes = f" ({ing.notes})" if ing.notes else ""
            print(f"  - {ing.quantity} {ing.unit} {ing.name}{notes}")

    if recipe.instructions:
        print(f"\nInstructions:")
        for i, step in enumerate(recipe.instructions, 1):
            print(f"  {i}. {step}")

    if recipe.nutrition:
        n = recipe.nutrition
        print(f"\nNutrition (per serving):")
        print(f"  Calories: {n.calories:.0f}")
        print(f"  Protein:  {n.protein_g:.0f}g")
        print(f"  Carbs:    {n.carbs_g:.0f}g")
        print(f"  Fat:      {n.fat_g:.0f}g")
        print(f"  Fiber:    {n.fiber_g:.0f}g")


def cmd_recipes_import(args):
    count = import_seed_recipes()
    if count == 0:
        print("Recipes already imported (database not empty).")
    else:
        print(f"Imported {count} seed recipes.")


def cmd_recipes_scrape_nyt(args):
    url = args.url
    count = scrape_nyt_article(url)
    if count == 0:
        print("No new recipes imported (all already in database, or none found).")
    else:
        print(f"\nImported {count} new recipes from NYTimes Cooking.")


def cmd_recipes_export(args):
    path = args.file
    count = export_recipes_csv(path)
    print(f"Exported {count} recipes to {path}")


def cmd_recipes_import_csv(args):
    path = args.file
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
    count = import_recipes_csv(path)
    if count == 0:
        print("No new recipes imported (all already in database, or file empty).")
    else:
        print(f"Imported {count} new recipes from {path}")


def cmd_plan_generate(args):
    user = _get_active_user()
    targets = calculate_macro_targets(user)

    week_start = None
    if args.week:
        week_start = date.fromisoformat(args.week)

    plan = generate_weekly_plan(user.id, targets, week_start)
    plan_id = save_meal_plan(plan)
    plan.id = plan_id

    print(format_meal_plan(plan))
    print(f"\nPlan saved (ID: {plan_id})")


def cmd_plan_show(args):
    user = _get_active_user()

    if args.week:
        week_start = date.fromisoformat(args.week)
    else:
        today = date.today()
        week_start = today - __import__("datetime").timedelta(days=today.weekday())

    plan = load_meal_plan(user.id, week_start)
    if not plan:
        print(f"No meal plan found for week of {week_start.isoformat()}")
        print("Generate one with: python -m meal_planner plan generate")
        return

    print(format_meal_plan(plan))


def cmd_plan_regenerate(args):
    user = _get_active_user()
    targets = calculate_macro_targets(user)

    if args.week:
        week_start = date.fromisoformat(args.week)
    else:
        today = date.today()
        week_start = today - __import__("datetime").timedelta(days=today.weekday())

    plan = load_meal_plan(user.id, week_start)
    if not plan:
        print("No existing plan found for that week.")
        return

    day_map = {name.lower(): i for i, name in enumerate(DAY_NAMES)}
    day_idx = day_map.get(args.day.lower())
    if day_idx is None:
        print(f"Invalid day. Choose from: {', '.join(DAY_NAMES)}")
        return

    meal_type = args.meal.lower()
    if meal_type not in ("breakfast", "lunch", "dinner"):
        print("Invalid meal type. Choose from: breakfast, lunch, dinner")
        return

    entry = regenerate_meal(plan.id, day_idx, meal_type, targets)
    if entry:
        name = entry.recipe.title if entry.recipe else f"Recipe #{entry.recipe_id}"
        print(f"Regenerated {DAY_NAMES[day_idx]} {meal_type}: {name} ({entry.servings:.2g} servings)")
    else:
        print("Could not find a suitable replacement.")


def cmd_log_add(args):
    user = _get_active_user()
    recipe = get_recipe(args.recipe_id)
    if not recipe:
        print(f"Recipe {args.recipe_id} not found.")
        return

    logged_at = datetime.now()
    if args.date:
        logged_at = datetime.fromisoformat(args.date)

    log_id = log_meal(user.id, args.recipe_id, args.meal, args.servings, logged_at)
    print(f"Logged: {recipe.title} for {args.meal} ({args.servings} servings) [#{log_id}]")


def cmd_track(args):
    user = _get_active_user()
    targets = calculate_macro_targets(user)

    if args.period == "daily":
        target_date = date.fromisoformat(args.date) if args.date else date.today()
        summary = daily_summary(user.id, target_date, targets)
    elif args.period == "weekly":
        if args.date:
            week_start = date.fromisoformat(args.date)
        else:
            today = date.today()
            week_start = today - __import__("datetime").timedelta(days=today.weekday())
        summary = weekly_summary(user.id, week_start, targets)
    elif args.period == "monthly":
        if args.date:
            d = date.fromisoformat(args.date + "-01") if len(args.date) == 7 else date.fromisoformat(args.date)
        else:
            d = date.today()
        summary = monthly_summary(user.id, d.year, d.month, targets)
    elif args.period == "yearly":
        year = int(args.date) if args.date else date.today().year
        summary = yearly_summary(user.id, year, targets)
    else:
        print(f"Unknown period: {args.period}")
        return

    print(format_summary(summary))


# --- Argument parser ---

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="meal_planner",
        description="NYT Recipe Optimizer - Personalized Meal Planning",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- profile ---
    profile_parser = subparsers.add_parser("profile", help="Manage user profile")
    profile_sub = profile_parser.add_subparsers(dest="subcommand")

    create_p = profile_sub.add_parser("create", help="Create a new profile")
    create_p.add_argument("--name", required=True)
    create_p.add_argument("--age", type=int, required=True)
    create_p.add_argument("--weight", type=float, required=True, help="Weight in lbs")
    create_p.add_argument("--feet", type=int, required=True, help="Height (feet)")
    create_p.add_argument("--inches", type=int, required=True, help="Height (inches)")
    create_p.add_argument("--sex", choices=["male", "female"], required=True)
    create_p.add_argument("--activity", required=True,
                          choices=list(ACTIVITY_MULTIPLIERS.keys()),
                          help="Activity level")
    create_p.add_argument("--goal", required=True,
                          choices=list(GOAL_CALORIE_ADJUSTMENTS.keys()),
                          help="Fitness goal")
    create_p.set_defaults(func=cmd_profile_create)

    show_p = profile_sub.add_parser("show", help="Show current profile")
    show_p.set_defaults(func=cmd_profile_show)

    update_p = profile_sub.add_parser("update", help="Update profile")
    update_p.add_argument("--age", type=int)
    update_p.add_argument("--weight", type=float, help="Weight in lbs")
    update_p.add_argument("--feet", type=int, help="Height (feet)")
    update_p.add_argument("--inches", type=int, help="Height (inches)")
    update_p.add_argument("--activity", choices=list(ACTIVITY_MULTIPLIERS.keys()))
    update_p.add_argument("--goal", choices=list(GOAL_CALORIE_ADJUSTMENTS.keys()))
    update_p.set_defaults(func=cmd_profile_update)

    # --- macros ---
    macros_p = subparsers.add_parser("macros", help="Show daily macro targets")
    macros_p.set_defaults(func=cmd_macros)

    # --- recipes ---
    recipes_parser = subparsers.add_parser("recipes", help="Manage recipes")
    recipes_sub = recipes_parser.add_subparsers(dest="subcommand")

    list_p = recipes_sub.add_parser("list", help="List all recipes")
    list_p.set_defaults(func=cmd_recipes_list)

    search_p = recipes_sub.add_parser("search", help="Search recipes")
    search_p.add_argument("query", help="Search term")
    search_p.set_defaults(func=cmd_recipes_search)

    show_rp = recipes_sub.add_parser("show", help="Show recipe details")
    show_rp.add_argument("recipe_id", type=int, help="Recipe ID")
    show_rp.set_defaults(func=cmd_recipes_show)

    import_p = recipes_sub.add_parser("import", help="Import seed recipes")
    import_p.set_defaults(func=cmd_recipes_import)

    nyt_p = recipes_sub.add_parser("scrape-nyt", help="Scrape recipes from a NYTimes Cooking article")
    nyt_p.add_argument("--url", default="https://cooking.nytimes.com/article/cheap-healthy-dinner-ideas",
                       help="NYTimes Cooking article URL to scrape (default: cheap healthy dinners)")
    nyt_p.set_defaults(func=cmd_recipes_scrape_nyt)

    export_p = recipes_sub.add_parser("export", help="Export all recipes to a CSV file")
    export_p.add_argument("file", help="Output CSV file path (e.g. recipes.csv)")
    export_p.set_defaults(func=cmd_recipes_export)

    import_csv_p = recipes_sub.add_parser("import-csv", help="Import recipes from a CSV file")
    import_csv_p.add_argument("file", help="CSV file to import")
    import_csv_p.set_defaults(func=cmd_recipes_import_csv)

    # --- plan ---
    plan_parser = subparsers.add_parser("plan", help="Meal planning")
    plan_sub = plan_parser.add_subparsers(dest="subcommand")

    gen_p = plan_sub.add_parser("generate", help="Generate a weekly meal plan")
    gen_p.add_argument("--week", help="Week start date (YYYY-MM-DD), default: current week")
    gen_p.set_defaults(func=cmd_plan_generate)

    show_pp = plan_sub.add_parser("show", help="Show current meal plan")
    show_pp.add_argument("--week", help="Week start date (YYYY-MM-DD)")
    show_pp.set_defaults(func=cmd_plan_show)

    regen_p = plan_sub.add_parser("regenerate", help="Regenerate a specific meal")
    regen_p.add_argument("--week", help="Week start date (YYYY-MM-DD)")
    regen_p.add_argument("--day", required=True, help="Day of week (e.g., Monday)")
    regen_p.add_argument("--meal", required=True, choices=["breakfast", "lunch", "dinner"])
    regen_p.set_defaults(func=cmd_plan_regenerate)

    # --- log ---
    log_parser = subparsers.add_parser("log", help="Log consumed meals")
    log_sub = log_parser.add_subparsers(dest="subcommand")

    add_p = log_sub.add_parser("add", help="Log a meal")
    add_p.add_argument("--recipe-id", type=int, required=True, help="Recipe ID")
    add_p.add_argument("--meal", required=True, choices=["breakfast", "lunch", "dinner"])
    add_p.add_argument("--servings", type=float, default=1.0)
    add_p.add_argument("--date", help="Date/time (YYYY-MM-DD or ISO format)")
    add_p.set_defaults(func=cmd_log_add)

    # --- track ---
    track_p = subparsers.add_parser("track", help="View nutrition analytics")
    track_p.add_argument("period", choices=["daily", "weekly", "monthly", "yearly"])
    track_p.add_argument("--date", help="Date or period identifier")
    track_p.set_defaults(func=cmd_track)

    return parser


def main():
    init_db()
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if hasattr(args, "func"):
        args.func(args)
    elif args.command in ("profile", "recipes", "plan", "log"):
        # Subcommand not specified
        sub = parser._subparsers._group_actions[0].choices[args.command]
        sub.print_help()
    else:
        parser.print_help()
