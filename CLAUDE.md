# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A personal meal planner: it calculates macro targets from body metrics (Mifflin-St Jeor), builds weekly meal plans from a recipe database (mostly scraped from NYTimes Cooking), and tracks logged meals against those targets. There are two front ends, an argparse CLI and a Streamlit multi-page app. Both sit on the same `meal_planner/` package and the same SQLite database.

## Commands

```bash
pip install -r requirements.txt

# Tests (stdlib unittest, no pytest config)
python -m unittest discover -s tests -v
python -m unittest tests.test_tracker                              # one module
python -m unittest tests.test_tracker.TestTracker.test_daily_summary  # one test

# CLI (entry point: meal_planner/__main__.py -> cli.main)
python -m meal_planner recipes import        # load data/seed_recipes.json into the DB
python -m meal_planner profile show
python -m meal_planner plan generate [--week YYYY-MM-DD]
python -m meal_planner plan regenerate --day Monday --meal lunch
python -m meal_planner track daily|weekly|monthly|yearly [--date ...]
python -m meal_planner recipes scrape-nyt [--url <NYT Cooking article URL>]
python -m meal_planner recipes export file.csv / import-csv file.csv

# Web UI (http://localhost:8501)
streamlit run streamlit_app.py
```

The README has the full CLI reference. There is no linter or formatter configured.

## Architecture

**Layering.** `config.py` (constants) → `db.py` (schema and `get_connection` context manager) → `recipe_store.py` (recipe CRUD) → domain modules (`macro_calculator`, `recommender`, `planner`, `tracker`) → front ends (`cli.py`, `streamlit_app.py` and `pages/`). Models are plain dataclasses in `models.py`.

**Database.** SQLite at `~/.meal_planner/meal_planner.db`. This path is outside the repo, and `*.db` is gitignored. The schema is in `db.py` as `CREATE TABLE IF NOT EXISTS`, and there is no migration framework, so a schema change means editing `SCHEMA_SQL` and handling existing DBs by hand. Nutrition lives in a separate `recipe_nutrition` table keyed by `recipe_id`. `ingredients` and `instructions` are JSON text columns, and `meal_types` is a comma-separated string that `recipe_store._row_to_recipe` parses.

**`db_path` threading.** Every store, planner, and tracker function takes `db_path: str = DB_PATH`. Tests use this to run against a `tempfile.mkstemp` DB (see `tests/test_tracker.py`), so keep the parameter on any new DB-touching function. The user helpers in `cli.py` (`_save_user`, `_load_user`, `_update_user`) do **not** take `db_path` and always hit the real DB.

**Single-user assumption.** `_load_user(user_id=1)` is used everywhere, in the CLI and in Streamlit. Streamlit imports these private `_`-prefixed helpers straight from `meal_planner.cli`, so renaming them breaks the UI.

**Plan generation flow.** `planner.generate_weekly_plan` loads all recipes, collects recipe IDs used in the previous `VARIETY_WINDOW_DAYS` (21) from stored plans, and calls `recommender.recommend_daily_meals` once per day. The recommender is pure: it takes targets and a recipe list and never touches the DB, so it is the easiest part to unit-test. It fills breakfast, then lunch, then dinner, using `MEAL_CALORIE_SPLITS` and carrying the leftover budget forward. Each candidate is scored by weighted relative macro error (`MACRO_SCORE_WEIGHTS`, where protein counts 1.5x), servings are adjusted to hit the calorie target, and the pick is random among the top candidates. Because of that randomness, tests check properties of a plan, not exact recipes. All tuning constants are in `config.py`.

**Units.** Storage and all domain math are metric (kg, cm). Both front ends take and show imperial units. The CLI has its own converters in `cli.py`, and Streamlit uses `pages/components/unit_converter.py`. These are duplicate implementations, so change both together.

**Streamlit.** `streamlit_app.py` initializes the DB and `st.session_state` (`user_profile`, `macro_targets`, `current_week_start` as a Monday). The pages in `pages/N_Name.py` rely on that state and must handle a missing profile. Shared rendering and Plotly charts are in `pages/components/`. The UI was built so that it needed no changes to `meal_planner/`, and new logic should go in the package rather than in pages.

**Recipe sources** (`recipe_sources.py`): seed JSON (`data/seed_recipes.json`), the NYT scraper (it finds `/recipes/` links on an NYT Cooking article page, then parses each recipe with `recipe_scrapers`; full recipes need an NYT subscription), and CSV import/export. `data/current_recipes.csv` is an export of the curated collection, and re-importing it is how you rebuild the DB without scraping again. `Scraper.py` at the repo root is the original standalone prototype and is not used by the app.
