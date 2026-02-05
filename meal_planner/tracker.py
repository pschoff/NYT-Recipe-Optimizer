"""Meal tracking and nutritional analytics.

Tracks consumed meals and provides aggregated nutritional data at
multiple time granularities: daily, weekly, monthly, yearly.
"""

from datetime import date, datetime, timedelta
from typing import Optional

from meal_planner.db import get_connection, DB_PATH
from meal_planner.models import MacroTargets, MealLog, Nutrition, NutritionSummary
from meal_planner.recipe_store import get_recipe


def log_meal(
    user_id: int,
    recipe_id: int,
    meal_type: str,
    servings: float = 1.0,
    logged_at: Optional[datetime] = None,
    db_path: str = DB_PATH,
) -> int:
    """Log a consumed meal. Returns the log entry ID."""
    if logged_at is None:
        logged_at = datetime.now()

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """INSERT INTO meal_log (user_id, recipe_id, meal_type, servings, logged_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, recipe_id, meal_type, servings, logged_at.isoformat()),
        )
        return cursor.lastrowid


def get_meal_logs(
    user_id: int,
    start_date: date,
    end_date: date,
    db_path: str = DB_PATH,
) -> list:
    """Get all meal log entries within a date range."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """SELECT * FROM meal_log
               WHERE user_id = ? AND date(logged_at) >= ? AND date(logged_at) <= ?
               ORDER BY logged_at""",
            (user_id, start_date.isoformat(), end_date.isoformat()),
        ).fetchall()

        logs = []
        for row in rows:
            recipe = get_recipe(row["recipe_id"], db_path)
            logs.append(MealLog(
                id=row["id"],
                user_id=row["user_id"],
                recipe_id=row["recipe_id"],
                meal_type=row["meal_type"],
                servings=row["servings"],
                logged_at=datetime.fromisoformat(row["logged_at"]),
                recipe=recipe,
            ))
        return logs


def _aggregate_nutrition(logs: list) -> Nutrition:
    """Sum up nutrition across all meal logs."""
    total = Nutrition.zero()
    for log in logs:
        if log.recipe and log.recipe.nutrition:
            total = total + log.recipe.nutrition.scaled(log.servings)
    return total


def _count_unique_days(logs: list) -> int:
    """Count unique days in a set of logs."""
    days = {log.logged_at.date() for log in logs}
    return len(days)


def daily_summary(
    user_id: int,
    target_date: date,
    targets: Optional[MacroTargets] = None,
    db_path: str = DB_PATH,
) -> NutritionSummary:
    """Get nutrition summary for a single day."""
    logs = get_meal_logs(user_id, target_date, target_date, db_path)
    return NutritionSummary(
        period_label=target_date.isoformat(),
        total_nutrition=_aggregate_nutrition(logs),
        num_meals=len(logs),
        num_days=1 if logs else 0,
        target=targets,
    )


def weekly_summary(
    user_id: int,
    week_start: date,
    targets: Optional[MacroTargets] = None,
    db_path: str = DB_PATH,
) -> NutritionSummary:
    """Get nutrition summary for a week (Mon-Sun)."""
    # Adjust to Monday
    adjusted = week_start - timedelta(days=week_start.weekday())
    week_end = adjusted + timedelta(days=6)
    logs = get_meal_logs(user_id, adjusted, week_end, db_path)

    return NutritionSummary(
        period_label=f"Week of {adjusted.isoformat()}",
        total_nutrition=_aggregate_nutrition(logs),
        num_meals=len(logs),
        num_days=_count_unique_days(logs),
        target=targets,
    )


def monthly_summary(
    user_id: int,
    year: int,
    month: int,
    targets: Optional[MacroTargets] = None,
    db_path: str = DB_PATH,
) -> NutritionSummary:
    """Get nutrition summary for a month."""
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)

    logs = get_meal_logs(user_id, start, end, db_path)
    return NutritionSummary(
        period_label=f"{year}-{month:02d}",
        total_nutrition=_aggregate_nutrition(logs),
        num_meals=len(logs),
        num_days=_count_unique_days(logs),
        target=targets,
    )


def yearly_summary(
    user_id: int,
    year: int,
    targets: Optional[MacroTargets] = None,
    db_path: str = DB_PATH,
) -> NutritionSummary:
    """Get nutrition summary for a year."""
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    logs = get_meal_logs(user_id, start, end, db_path)

    return NutritionSummary(
        period_label=str(year),
        total_nutrition=_aggregate_nutrition(logs),
        num_meals=len(logs),
        num_days=_count_unique_days(logs),
        target=targets,
    )


def format_summary(summary: NutritionSummary) -> str:
    """Format a nutrition summary for display."""
    lines = [
        f"Nutrition Summary: {summary.period_label}",
        "=" * 45,
        f"Meals logged: {summary.num_meals} across {summary.num_days} day(s)",
    ]

    if summary.num_days > 0:
        total = summary.total_nutrition
        avg = summary.daily_average
        pcts = total.macro_percentages()

        lines.append(f"\nTotal:")
        lines.append(f"  Calories: {total.calories:.0f} kcal")
        lines.append(f"  Protein:  {total.protein_g:.0f}g ({pcts['protein']:.1f}%)")
        lines.append(f"  Carbs:    {total.carbs_g:.0f}g ({pcts['carbs']:.1f}%)")
        lines.append(f"  Fat:      {total.fat_g:.0f}g ({pcts['fat']:.1f}%)")

        if summary.num_days > 1:
            avg_pcts = avg.macro_percentages()
            lines.append(f"\nDaily Average:")
            lines.append(f"  Calories: {avg.calories:.0f} kcal")
            lines.append(f"  Protein:  {avg.protein_g:.0f}g ({avg_pcts['protein']:.1f}%)")
            lines.append(f"  Carbs:    {avg.carbs_g:.0f}g ({avg_pcts['carbs']:.1f}%)")
            lines.append(f"  Fat:      {avg.fat_g:.0f}g ({avg_pcts['fat']:.1f}%)")

        adherence = summary.adherence_pct()
        if adherence:
            lines.append(f"\nTarget Adherence (daily avg vs target):")
            lines.append(f"  Calories: {adherence['calories']}%")
            lines.append(f"  Protein:  {adherence['protein']}%")
            lines.append(f"  Carbs:    {adherence['carbs']}%")
            lines.append(f"  Fat:      {adherence['fat']}%")
    else:
        lines.append("\nNo meals logged for this period.")

    return "\n".join(lines)
