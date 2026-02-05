"""Macro calculation engine using evidence-based formulas.

Uses:
- Mifflin-St Jeor equation for Basal Metabolic Rate (BMR)
- Activity multipliers for Total Daily Energy Expenditure (TDEE)
- Goal-specific calorie adjustments and macro splits

References:
- Mifflin MD, St Jeor ST, et al. (1990). "A new predictive equation for
  resting energy expenditure in healthy individuals." Am J Clin Nutr.
- ISSN Position Stand on Diets and Body Composition (2017).
"""

from meal_planner.config import (
    ACTIVITY_MULTIPLIERS,
    CALORIES_PER_GRAM,
    GOAL_CALORIE_ADJUSTMENTS,
    GOAL_MACRO_SPLITS,
)
from meal_planner.models import MacroTargets, UserProfile


def calculate_bmr(profile: UserProfile) -> float:
    """Calculate Basal Metabolic Rate using the Mifflin-St Jeor equation.

    Male:   BMR = 10 × weight(kg) + 6.25 × height(cm) − 5 × age(y) + 5
    Female: BMR = 10 × weight(kg) + 6.25 × height(cm) − 5 × age(y) − 161
    """
    bmr = 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age
    if profile.sex == "male":
        bmr += 5
    else:
        bmr -= 161
    return bmr


def calculate_tdee(bmr: float, activity_level: str) -> float:
    """Calculate Total Daily Energy Expenditure.

    TDEE = BMR × activity multiplier
    """
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.2)
    return bmr * multiplier


def calculate_macro_targets(profile: UserProfile) -> MacroTargets:
    """Calculate personalized daily macro targets for a user.

    Steps:
    1. Calculate BMR via Mifflin-St Jeor
    2. Multiply by activity factor to get TDEE
    3. Apply goal-based calorie adjustment
    4. Split calories into macros based on goal
    5. Convert calories to grams using 4/4/9 cal/g for protein/carbs/fat
    """
    bmr = calculate_bmr(profile)
    tdee = calculate_tdee(bmr, profile.activity_level)

    # Adjust calories for goal
    calorie_adjustment = GOAL_CALORIE_ADJUSTMENTS.get(profile.goal, 1.0)
    target_calories = tdee * calorie_adjustment

    # Get macro split for goal
    splits = GOAL_MACRO_SPLITS.get(profile.goal, GOAL_MACRO_SPLITS["maintain"])

    # Convert percentages to grams
    protein_calories = target_calories * splits["protein"]
    carbs_calories = target_calories * splits["carbs"]
    fat_calories = target_calories * splits["fat"]

    return MacroTargets(
        calories=round(target_calories),
        protein_g=round(protein_calories / CALORIES_PER_GRAM["protein"]),
        carbs_g=round(carbs_calories / CALORIES_PER_GRAM["carbs"]),
        fat_g=round(fat_calories / CALORIES_PER_GRAM["fat"]),
        bmr=round(bmr),
        tdee=round(tdee),
    )


def format_targets(targets: MacroTargets) -> str:
    """Format macro targets for display."""
    lines = [
        f"BMR:      {targets.bmr} kcal",
        f"TDEE:     {targets.tdee} kcal",
        f"Target:   {targets.calories} kcal/day",
        f"Protein:  {targets.protein_g}g ({targets.protein_g * 4} kcal)",
        f"Carbs:    {targets.carbs_g}g ({targets.carbs_g * 4} kcal)",
        f"Fat:      {targets.fat_g}g ({targets.fat_g * 9} kcal)",
    ]
    return "\n".join(lines)
