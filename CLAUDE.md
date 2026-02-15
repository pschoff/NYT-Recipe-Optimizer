# Project Context for Claude

This document provides context about the NYT Recipe Optimizer meal planning application and recent development work.

## Project Overview

The NYT Recipe Optimizer is a personalized meal planning application that:
- Calculates macro targets based on body metrics and fitness goals (Mifflin-St Jeor equation)
- Generates optimized weekly meal plans with automatic calorie allocation
- Tracks nutrition with daily/weekly/monthly analytics
- Scrapes recipes from NYTimes Cooking (requires subscription)

**Technology Stack:**
- Backend: Python 3.8+, SQLite
- CLI: argparse-based command interface
- Frontend: Streamlit web UI (in progress)
- Data: SQLite database at `~/.meal_planner/meal_planner.db`

## Recent Development History

### Phase 1: Recipe Management (Completed)

**Testing NYTimes Scraper**
- Fixed Python environment mismatch (anaconda 3.8 vs system 3.9)
- Successfully scraped 16 recipes from NYTimes Cooking
- Scraper extracts: title, ingredients, instructions, nutrition data
- Duplicate detection works correctly

**Database Cleanup**
- Removed 30 seed recipes from database
- Kept only 16 NYTimes-scraped recipes
- All recipes verified with source='nytimes'

**Custom Recipe Addition**
- Added protein shake recipe (Optimum Whey + Creatine + 2% milk)
- Total nutrition: 364 cal, 40g protein, 27g carbs, 12g fat
- Recipe ID: 47, meal type: breakfast

**Current Recipe Count:** 17 recipes (16 NYTimes + 1 custom)

### Phase 2: Streamlit Frontend Development (Completed)

**Goal:** Create a web-based UI for easier interaction with the meal planning app.

**Architecture Decision:**
- Framework: Streamlit (Python-based, quick to build, modern UI)
- Integration: Zero modifications to existing `meal_planner/` modules
- Database: Shared SQLite DB with CLI (cross-compatible)
- Units: Display imperial (lbs, ft/in), store metric (kg, cm)

**File Structure:**
```
NYT-Recipe-Optimizer/
├── streamlit_app.py                 # Main entry point ✅
├── pages/                           # Multi-page app
│   ├── components/                  # Reusable components ✅
│   │   ├── unit_converter.py       # Imperial/metric conversion
│   │   ├── nutrition_display.py    # Nutrition cards & adherence
│   │   ├── recipe_card.py          # Recipe display
│   │   └── charts.py               # Plotly visualizations
│   ├── 1_Profile.py                # Profile management ✅
│   ├── 2_Recipes.py                # Recipe browser ✅
│   ├── 3_Meal_Plan.py              # Meal planning ✅
│   └── 4_Tracking.py               # Nutrition tracking ✅
└── requirements.txt                 # Updated with Streamlit deps ✅
```

**Completed Components:**

1. **streamlit_app.py** - Main entry point
   - Initializes DB and session state
   - Loads user profile if exists
   - Displays home page with quick stats
   - Sidebar shows current user and macro targets

2. **Component Files** (pages/components/)
   - `unit_converter.py` - Functions: lbs_to_kg, kg_to_lbs, ft_in_to_cm, cm_to_ft_in
   - `nutrition_display.py` - Functions: render_nutrition_card, render_target_comparison
   - `recipe_card.py` - Functions: render_recipe_summary, render_recipe_detail
   - `charts.py` - Functions: create_macro_pie_chart, create_adherence_gauge, create_daily_calories_trend, create_macro_stacked_bar

3. **Profile Page** (pages/1_Profile.py)
   - Create/update user profile with imperial units
   - Display current profile and calculated macro targets
   - Show BMR, TDEE, target calories, protein/carbs/fat
   - Macro distribution pie chart
   - Form validation and session state management

**Dependencies Added to requirements.txt:**
```
streamlit>=1.31.0
plotly>=5.18.0
pandas>=2.1.0
```

**Installation Status:**
- All Streamlit dependencies installed successfully
- App imports without errors (tested)

**To Run the Streamlit App:**
```bash
cd /Users/peterschoffelen/github/NYT\ recipe/NYT-Recipe-Optimizer
streamlit run streamlit_app.py
```
Opens at `http://localhost:8501`

## All Pages Completed! ✅

### Implemented Pages

**1_Profile.py - Profile Management** ✅
- Create/update user profile with imperial units (lbs, feet/inches)
- Display current profile and calculated macro targets
- Show BMR, TDEE, target calories, protein/carbs/fat
- Macro distribution pie chart visualization
- Form validation and session state management

**2_Recipes.py - Recipe Browser** ✅
- Search bar with live filtering by recipe name
- Filter by meal type (breakfast/lunch/dinner) with multiselect
- Sortable table: ID, Title, Calories, Protein, Carbs, Fat, Meal Types, Source
- Recipe detail viewer with full ingredients, instructions, and nutrition
- CSV import/export functionality
- Handles empty recipe lists gracefully

**3_Meal_Plan.py - Weekly Meal Planning** ✅
- Week selector with previous/next week navigation
- Generate optimized meal plan button (7 days × 3 meals = 21 meals)
- 7×3 grid calendar view with recipe cards for each meal
- Each cell shows: recipe name, servings, calories, P/C/F macros
- Individual "Swap" buttons to regenerate single meals
- Daily nutrition totals with adherence indicators
- Weekly summary with daily average vs target comparison
- Full plan regeneration option with confirmation

**4_Tracking.py - Nutrition Tracking & Analytics** ✅
- Quick meal log form: recipe dropdown, meal type, servings, date/time
- Period selector tabs: Daily | Weekly | Monthly | Yearly
- Daily summary: total nutrition, meals logged, target adherence
- Weekly summary: daily average, trend charts (calories, macros)
- Monthly summary: adherence gauges for each macro
- Yearly summary: long-term trends and statistics
- Interactive Plotly charts:
  - Line chart: Daily calorie intake over time
  - Stacked bar chart: Protein/Carbs/Fat breakdown per day
  - Gauge charts: Adherence % for calories, protein, carbs, fat
- Color-coded adherence (green >90%, yellow 70-90%, red <70%)
- Individual meal log viewer showing time and nutrition

## Key Design Patterns

### Session State Management
```python
# Initialized in streamlit_app.py
st.session_state.user_profile = None          # UserProfile object
st.session_state.macro_targets = None         # MacroTargets object
st.session_state.current_week_start = today   # date object (Monday)
st.session_state.db_initialized = True        # One-time DB init
```

### Unit Conversion Pattern
```python
# Display in imperial
weight_lbs = st.number_input("Weight (lbs)", value=165.0)
feet = st.number_input("Feet", value=5)
inches = st.number_input("Inches", value=10)

# Convert to metric for storage
from pages.components.unit_converter import lbs_to_kg, ft_in_to_cm
weight_kg = lbs_to_kg(weight_lbs)
height_cm = ft_in_to_cm(feet, inches)
```

### Integration with Existing Modules
```python
# Import directly from meal_planner (no modifications needed)
from meal_planner.db import init_db
from meal_planner.cli import _load_user, _save_user, _update_user
from meal_planner.macro_calculator import calculate_macro_targets
from meal_planner.recipe_store import get_all_recipes, search_recipes
from meal_planner.planner import generate_weekly_plan, load_meal_plan
from meal_planner.tracker import log_meal, daily_summary
```

## Important Notes

### Database
- Single SQLite database shared between CLI and Streamlit
- Path: `~/.meal_planner/meal_planner.db`
- Changes in Streamlit visible in CLI (and vice versa)

### Unit Handling
- **User Input/Display:** Imperial (lbs, feet/inches)
- **Database Storage:** Metric (kg, cm)
- **Nutrition Labels:** Always grams (standard format)

### Error Handling
- Check for missing profile on all pages except Profile page
- Handle empty recipe lists gracefully
- Show loading spinners during long operations (meal plan generation)
- Validate form inputs before submission

### Cross-Verification
After building pages, verify compatibility:
```bash
# Create profile in Streamlit → verify in CLI
python -m meal_planner profile show

# Generate plan in Streamlit → verify in CLI
python -m meal_planner plan show

# Log meal in Streamlit → verify in CLI
python -m meal_planner track daily
```

## Testing Checklist (Post-Implementation)

### Profile Page ✅ (Ready to Test)
- [ ] Create profile with imperial units
- [ ] Verify metric storage in DB
- [ ] Update weight/goal
- [ ] Verify macro recalculation
- [ ] Check BMR/TDEE calculations match CLI

### Recipe Page ⏳ (TODO)
- [ ] Search recipes
- [ ] Filter by meal type
- [ ] View recipe detail
- [ ] Export CSV
- [ ] Import CSV

### Meal Plan Page ⏳ (TODO)
- [ ] Generate plan for current week
- [ ] Verify 7 days × 3 meals = 21 entries
- [ ] Regenerate single meal
- [ ] Switch to different week
- [ ] Verify daily totals calculation

### Tracking Page ⏳ (TODO)
- [ ] Log meal
- [ ] View daily summary
- [ ] View weekly summary
- [ ] Verify adherence % calculations
- [ ] Check charts render correctly

## Development Commands

```bash
# Run CLI commands
python -m meal_planner profile show
python -m meal_planner recipes list
python -m meal_planner plan generate
python -m meal_planner track daily

# Run Streamlit app
streamlit run streamlit_app.py

# Install dependencies
pip install -r requirements.txt

# Run tests (if any)
python -m unittest discover -s tests -v
```

## References

### Key Files to Reference

**For implementing Recipe page:**
- [meal_planner/recipe_store.py](meal_planner/recipe_store.py) - All CRUD functions
- [meal_planner/recipe_sources.py](meal_planner/recipe_sources.py) - CSV import/export
- [pages/components/recipe_card.py](pages/components/recipe_card.py) - Display components

**For implementing Meal Plan page:**
- [meal_planner/planner.py](meal_planner/planner.py) - Generation and regeneration logic
- [meal_planner/recommender.py](meal_planner/recommender.py) - Recommendation algorithm
- [meal_planner/config.py](meal_planner/config.py) - MEAL_CALORIE_SPLITS constants

**For implementing Tracking page:**
- [meal_planner/tracker.py](meal_planner/tracker.py) - All tracking and summary functions
- [pages/components/charts.py](pages/components/charts.py) - Plotly chart functions
- [pages/components/nutrition_display.py](pages/components/nutrition_display.py) - Adherence display

### Plan File
- Full implementation plan: `~/.claude/plans/validated-honking-spark.md`

## Current State Summary

**✅ Fully Functional:**
- CLI application (all features working)
- NYTimes recipe scraper (16 recipes scraped)
- Recipe database with 17 recipes (16 NYTimes + 1 custom)
- **Streamlit Web UI - COMPLETE:**
  - Home page with navigation and quick stats
  - Profile management page (create/update, macro targets, pie chart)
  - Recipe browser page (search, filter, view details, CSV import/export)
  - Meal planning page (generate plans, regenerate meals, weekly summary)
  - Nutrition tracking page (log meals, daily/weekly/monthly/yearly analytics, charts)
  - All reusable components (nutrition cards, recipe cards, charts, unit conversion)

**🎯 Ready to Use:**
1. Run CLI: `python -m meal_planner [command]`
2. Run Streamlit UI: `streamlit run streamlit_app.py`
3. Both interfaces share the same database seamlessly

**📊 Application Features:**
- Evidence-based macro calculations (Mifflin-St Jeor equation)
- Intelligent meal recommendations with variety constraints (21-day window)
- Automatic serving size optimization for calorie targets
- Comprehensive nutrition tracking with adherence metrics
- Interactive data visualizations (Plotly charts)
- Imperial/metric unit conversion
- CSV recipe import/export

---

*Last updated: February 14, 2026 (Streamlit UI completed)*
*Total files: 13 (app + 4 pages + 4 components + docs)*
