# NYT Recipe Optimizer — Meal Planning Application

A personalized meal planning CLI that calculates macro targets based on your body metrics and fitness goals, then generates optimized weekly meal plans with tracking and analytics.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     CLI Interface                       │
│                   (meal_planner/cli.py)                  │
├──────────┬──────────┬───────────┬───────────┬───────────┤
│  Profile │  Macro   │   Meal    │  Weekly   │ Tracking  │
│ Manager  │Calculator│Recommender│  Planner  │ Analytics │
├──────────┴──────────┴───────────┴───────────┴───────────┤
│              Recipe Store (CRUD Layer)                   │
├─────────────────────────────────────────────────────────┤
│            SQLite Database (persistent)                  │
└─────────────────────────────────────────────────────────┘
```

**Components:**

| Module | Purpose |
|---|---|
| `models.py` | Dataclasses for Recipe, Nutrition, UserProfile, MealPlan, MealLog |
| `db.py` | SQLite schema, connection management, migrations |
| `recipe_store.py` | Recipe CRUD operations (save, query, search) |
| `recipe_sources.py` | Data sources: seed JSON, NYTimes Cooking scraper, Spoonacular API |
| `macro_calculator.py` | Mifflin-St Jeor BMR, TDEE, goal-based macro splits |
| `recommender.py` | Meal recommendation with scoring and variety constraints |
| `planner.py` | Weekly plan generation, persistence, regeneration |
| `tracker.py` | Meal logging, aggregated analytics (daily/weekly/monthly/yearly) |
| `cli.py` | Argparse CLI with subcommands |

**Technology Stack:** Python 3.9+, SQLite (via stdlib `sqlite3`), `dataclasses` for models. No heavy frameworks — lightweight and portable.

## Recipe Sources

The app supports multiple recipe sources:

1. **Seed data** — 30 curated recipes with full nutritional info, bundled as `data/seed_recipes.json`
2. **NYTimes Cooking** — Scrape recipes from any NYT Cooking article page (requires a NYTimes subscription). Extracts title, ingredients, instructions, and nutrition data via `recipe_scrapers`
3. **Spoonacular API** — Commercial recipe API with free tier (150 req/day). See `recipe_sources.py`
4. **TheMealDB** — Free open-source recipe database (CC licensed)

## Quick Start

```bash
# 1. Import the seed recipe database (30 recipes)
python -m meal_planner recipes import

# 2. Create your profile
python -m meal_planner profile create \
  --name "Alex" --age 28 --weight 75 --height 178 \
  --sex male --activity moderately_active --goal build_muscle

# 3. View your calculated macro targets
python -m meal_planner macros

# 4. Generate a weekly meal plan
python -m meal_planner plan generate

# 5. Log a consumed meal
python -m meal_planner log add --recipe-id 2 --meal breakfast --servings 1.5

# 6. View daily nutrition summary
python -m meal_planner track daily
```

## CLI Reference

### Profile Management

```bash
# Create profile
python -m meal_planner profile create \
  --name NAME --age AGE --weight WEIGHT_KG --height HEIGHT_CM \
  --sex {male,female} \
  --activity {sedentary,lightly_active,moderately_active,very_active,extra_active} \
  --goal {lose_fat,cut,maintain,build_muscle,recomp}

# View profile and macro targets
python -m meal_planner profile show

# Update profile
python -m meal_planner profile update --weight 78 --goal maintain
```

### Macro Targets

```bash
python -m meal_planner macros
# Output:
# BMR:      1780 kcal
# TDEE:     2759 kcal
# Target:   3035 kcal/day
# Protein:  228g (912 kcal)
# Carbs:    341g (1364 kcal)
# Fat:      84g (756 kcal)
```

### Recipe Management

```bash
python -m meal_planner recipes import          # Import bundled seed data
python -m meal_planner recipes list            # List all recipes
python -m meal_planner recipes search chicken  # Search by name
python -m meal_planner recipes show 5          # Show recipe details

# Scrape recipes from NYTimes Cooking (requires subscription)
python -m meal_planner recipes scrape-nyt
python -m meal_planner recipes scrape-nyt --url "https://cooking.nytimes.com/article/easy-pasta-recipes"
```

### Meal Planning

```bash
python -m meal_planner plan generate             # Generate for current week
python -m meal_planner plan generate --week 2026-02-09  # Specific week
python -m meal_planner plan show                 # View current plan
python -m meal_planner plan regenerate --day Monday --meal lunch  # Swap one meal
```

### Meal Logging & Tracking

```bash
python -m meal_planner log add --recipe-id 11 --meal lunch --servings 1.0

python -m meal_planner track daily                    # Today
python -m meal_planner track daily --date 2026-02-05  # Specific date
python -m meal_planner track weekly                   # Current week
python -m meal_planner track monthly --date 2026-02   # Specific month
python -m meal_planner track yearly --date 2026       # Full year
```

## Data Models

### Recipe
```
recipes (id, title, source, source_url, servings, prep_time_minutes,
         cook_time_minutes, meal_types, cuisine, ingredients[JSON],
         instructions[JSON])
recipe_nutrition (recipe_id, calories, protein_g, carbs_g, fat_g,
                  fiber_g, sugar_g, sodium_mg)
```

### User
```
users (id, name, age, weight_kg, height_cm, sex, activity_level, goal)
```

### Meal Plan
```
meal_plans (id, user_id, week_start_date)
meal_plan_entries (id, meal_plan_id, day_of_week, meal_type, recipe_id, servings)
```

### Tracking
```
meal_log (id, user_id, recipe_id, meal_type, servings, logged_at)
```

## Key Algorithms

### Macro Calculation (Mifflin-St Jeor)

```
BMR (male)   = 10 × weight(kg) + 6.25 × height(cm) − 5 × age + 5
BMR (female) = 10 × weight(kg) + 6.25 × height(cm) − 5 × age − 161

TDEE = BMR × activity_multiplier
Target calories = TDEE × goal_adjustment
```

**Activity multipliers:** Sedentary (1.2), Lightly Active (1.375), Moderately Active (1.55), Very Active (1.725), Extra Active (1.9)

**Goal adjustments & macro splits:**

| Goal | Calorie Adj. | Protein | Carbs | Fat |
|---|---|---|---|---|
| Lose Fat | ×0.80 | 40% | 30% | 30% |
| Cut | ×0.75 | 40% | 25% | 35% |
| Maintain | ×1.00 | 30% | 40% | 30% |
| Build Muscle | ×1.10 | 30% | 45% | 25% |
| Recomp | ×1.00 | 35% | 35% | 30% |

### Meal Recommendation Algorithm

1. **Budget allocation**: Breakfast 25%, Lunch 35%, Dinner 40% of daily calories
2. **Candidate scoring**: `score = 1 / (1 + Σ(weight_i × |actual_i − target_i| / target_i))` for calories, protein (×1.5 weight), carbs, fat
3. **Greedy construction**: Select breakfast → adjust remaining budget → select lunch → remaining → select dinner
4. **Variety constraint**: 21-day exclusion window (no recipe repeats)
5. **Serving optimization**: Auto-adjust servings (0.5×–2.0×) to match calorie targets
6. **Randomization**: Picks from top-5 candidates to avoid monotonous plans

## Running Tests

```bash
python -m unittest discover -s tests -v
```

## Project Structure

```
NYT-Recipe-Optimizer/
├── README.md
├── requirements.txt
├── Scraper.py                  # Original standalone scraper
├── data/
│   └── seed_recipes.json       # 30 curated recipes with nutrition data
├── meal_planner/
│   ├── __init__.py
│   ├── __main__.py             # python -m meal_planner entry point
│   ├── cli.py                  # CLI argument parsing and commands
│   ├── config.py               # Constants and configuration
│   ├── db.py                   # SQLite database layer
│   ├── macro_calculator.py     # BMR/TDEE/macro target calculations
│   ├── models.py               # Data models (dataclasses)
│   ├── planner.py              # Weekly meal plan generation
│   ├── recipe_sources.py       # Recipe data sources (seed, NYT scraper, APIs)
│   ├── recipe_store.py         # Recipe CRUD operations
│   ├── recommender.py          # Meal recommendation engine
│   └── tracker.py              # Meal logging and analytics
└── tests/
    ├── __init__.py
    ├── test_macro_calculator.py
    ├── test_meal_recommender.py
    ├── test_models.py
    └── test_tracker.py
```
