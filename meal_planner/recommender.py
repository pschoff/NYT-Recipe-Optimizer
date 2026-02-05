"""Meal recommendation engine.

Selects daily meals (breakfast, lunch, dinner) optimized for macro targets
while ensuring variety (no recipe repeats within a configurable window).

Algorithm overview:
1. For each meal slot, calculate the per-meal calorie/macro budget
2. Score candidate recipes by how closely they match the meal budget
3. Apply variety constraint: exclude recently used recipes (21-day window)
4. Greedy selection: pick best breakfast, then best lunch given remaining
   budget, then best dinner for remaining budget
5. Optional: adjust servings to fine-tune macro adherence
"""

import random
from typing import Optional

from meal_planner.config import (
    MACRO_SCORE_WEIGHTS,
    MEAL_CALORIE_SPLITS,
    VARIETY_WINDOW_DAYS,
    MEALS_PER_DAY,
)
from meal_planner.models import MacroTargets, Nutrition, Recipe


def _recipe_score(recipe: Recipe, target_nutrition: Nutrition, servings: float = 1.0) -> float:
    """Score a recipe against target nutrition. Higher = better match.

    Uses weighted normalized absolute deviation:
    score = 1 / (1 + sum(weight_i * |actual_i - target_i| / target_i))
    """
    if not recipe.nutrition:
        return 0.0

    actual = recipe.nutrition.scaled(servings)
    weights = MACRO_SCORE_WEIGHTS

    deviations = 0.0
    if target_nutrition.calories > 0:
        deviations += weights["calories"] * abs(actual.calories - target_nutrition.calories) / target_nutrition.calories
    if target_nutrition.protein_g > 0:
        deviations += weights["protein"] * abs(actual.protein_g - target_nutrition.protein_g) / target_nutrition.protein_g
    if target_nutrition.carbs_g > 0:
        deviations += weights["carbs"] * abs(actual.carbs_g - target_nutrition.carbs_g) / target_nutrition.carbs_g
    if target_nutrition.fat_g > 0:
        deviations += weights["fat"] * abs(actual.fat_g - target_nutrition.fat_g) / target_nutrition.fat_g

    return 1.0 / (1.0 + deviations)


def _meal_target(targets: MacroTargets, meal_type: str) -> Nutrition:
    """Calculate the nutrition target for a specific meal type."""
    fraction = MEAL_CALORIE_SPLITS.get(meal_type, 1.0 / MEALS_PER_DAY)
    return Nutrition(
        calories=targets.calories * fraction,
        protein_g=targets.protein_g * fraction,
        carbs_g=targets.carbs_g * fraction,
        fat_g=targets.fat_g * fraction,
    )


def _optimal_servings(recipe: Recipe, target: Nutrition) -> float:
    """Calculate the optimal serving size to best match target calories."""
    if not recipe.nutrition or recipe.nutrition.calories == 0:
        return 1.0
    raw = target.calories / recipe.nutrition.calories
    # Clamp to reasonable range (0.5 to 2.0 servings)
    return max(0.5, min(2.0, round(raw * 4) / 4))  # Round to nearest 0.25


def recommend_daily_meals(
    targets: MacroTargets,
    all_recipes: list,
    recently_used_ids: Optional[set] = None,
    variety_window: int = VARIETY_WINDOW_DAYS,
) -> list:
    """Recommend breakfast, lunch, and dinner for a single day.

    Returns a list of (meal_type, recipe, servings) tuples.

    Algorithm:
    1. Filter recipes by meal type and variety constraint
    2. For breakfast: score all breakfast recipes against breakfast target
    3. For lunch: score against lunch target, adjusted by breakfast remainder
    4. For dinner: score against remaining daily budget
    5. Select best candidates with some randomization for variety
    """
    if recently_used_ids is None:
        recently_used_ids = set()

    # Filter out recipes without nutrition data
    available = [r for r in all_recipes if r.nutrition is not None]

    meal_order = ["breakfast", "lunch", "dinner"]
    selected = []
    used_today = set()
    consumed = Nutrition.zero()

    for meal_type in meal_order:
        # Get candidates: matching meal type, not recently used, not used today
        candidates = [
            r for r in available
            if meal_type in r.meal_types
            and r.id not in recently_used_ids
            and r.id not in used_today
        ]

        # If too few candidates, relax variety constraint
        if len(candidates) < 3:
            candidates = [
                r for r in available
                if meal_type in r.meal_types
                and r.id not in used_today
            ]

        if not candidates:
            # Last resort: any recipe not used today
            candidates = [r for r in available if r.id not in used_today]

        if not candidates:
            continue

        # Calculate remaining budget for this meal
        remaining = Nutrition(
            calories=max(0, targets.calories - consumed.calories),
            protein_g=max(0, targets.protein_g - consumed.protein_g),
            carbs_g=max(0, targets.carbs_g - consumed.carbs_g),
            fat_g=max(0, targets.fat_g - consumed.fat_g),
        )

        # For breakfast/lunch, use the predefined split; for dinner, use remainder
        if meal_type == "dinner":
            meal_target = remaining
        else:
            meal_target = _meal_target(targets, meal_type)

        # Score and sort candidates
        scored = []
        for recipe in candidates:
            servings = _optimal_servings(recipe, meal_target)
            score = _recipe_score(recipe, meal_target, servings)
            scored.append((score, recipe, servings))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Pick from top candidates with slight randomization
        top_n = min(5, len(scored))
        idx = random.randint(0, top_n - 1) if top_n > 1 else 0
        best_score, best_recipe, best_servings = scored[idx]

        selected.append((meal_type, best_recipe, best_servings))
        used_today.add(best_recipe.id)
        consumed = consumed + best_recipe.nutrition.scaled(best_servings)

    return selected


def score_daily_plan(
    meals: list,
    targets: MacroTargets,
) -> dict:
    """Score a full day's meals against targets. Returns deviation info."""
    total = Nutrition.zero()
    for meal_type, recipe, servings in meals:
        if recipe.nutrition:
            total = total + recipe.nutrition.scaled(servings)

    def deviation(actual, target):
        if target == 0:
            return 0
        return round((actual - target) / target * 100, 1)

    return {
        "total_nutrition": total,
        "deviation": {
            "calories": deviation(total.calories, targets.calories),
            "protein": deviation(total.protein_g, targets.protein_g),
            "carbs": deviation(total.carbs_g, targets.carbs_g),
            "fat": deviation(total.fat_g, targets.fat_g),
        },
    }
