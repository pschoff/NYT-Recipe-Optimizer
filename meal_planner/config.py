"""Application configuration and constants."""

import os

# Database
DB_DIR = os.path.join(os.path.expanduser("~"), ".meal_planner")
DB_PATH = os.path.join(DB_DIR, "meal_planner.db")

# Seed data
SEED_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "seed_recipes.json")

# Meal planning constraints
VARIETY_WINDOW_DAYS = 21  # No recipe repeats within this many days
MEALS_PER_DAY = 3
DAYS_PER_WEEK = 7

# Meal calorie distribution (fraction of daily calories)
MEAL_CALORIE_SPLITS = {
    "breakfast": 0.25,
    "lunch": 0.35,
    "dinner": 0.40,
}

# Activity level multipliers for TDEE calculation
ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "lightly_active": 1.375,
    "moderately_active": 1.55,
    "very_active": 1.725,
    "extra_active": 1.9,
}

# Goal-based calorie adjustments (multiplier on TDEE)
GOAL_CALORIE_ADJUSTMENTS = {
    "lose_fat": 0.80,
    "cut": 0.75,
    "maintain": 1.0,
    "build_muscle": 1.10,
    "recomp": 1.0,
}

# Goal-based macro splits (protein%, carbs%, fat%)
GOAL_MACRO_SPLITS = {
    "lose_fat": {"protein": 0.40, "carbs": 0.30, "fat": 0.30},
    "cut": {"protein": 0.40, "carbs": 0.25, "fat": 0.35},
    "maintain": {"protein": 0.30, "carbs": 0.40, "fat": 0.30},
    "build_muscle": {"protein": 0.30, "carbs": 0.45, "fat": 0.25},
    "recomp": {"protein": 0.35, "carbs": 0.35, "fat": 0.30},
}

# Scoring weights for meal recommendation
MACRO_SCORE_WEIGHTS = {
    "calories": 1.0,
    "protein": 1.5,  # Protein adherence weighted higher
    "carbs": 1.0,
    "fat": 1.0,
}

# Macro calorie multipliers (calories per gram)
CALORIES_PER_GRAM = {
    "protein": 4,
    "carbs": 4,
    "fat": 9,
}
