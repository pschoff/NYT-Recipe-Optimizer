"""Streamlit frontend for the Meal Planning App.

Main entry point for the multi-page Streamlit application.
"""

import streamlit as st
from datetime import date, timedelta

from meal_planner.db import init_db
from meal_planner.cli import _load_user
from meal_planner.macro_calculator import calculate_macro_targets

st.set_page_config(
    page_title="Meal Planner",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize DB once per session
if 'db_initialized' not in st.session_state:
    init_db()
    st.session_state.db_initialized = True

# Initialize session state variables
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = None
if 'macro_targets' not in st.session_state:
    st.session_state.macro_targets = None
if 'current_week_start' not in st.session_state:
    today = date.today()
    # Get Monday of current week
    st.session_state.current_week_start = today - timedelta(days=today.weekday())

# Load user profile if it exists
if st.session_state.user_profile is None:
    user = _load_user()
    if user:
        st.session_state.user_profile = user
        st.session_state.macro_targets = calculate_macro_targets(user)

# Sidebar: Show current user info
with st.sidebar:
    st.markdown("## 🍽️ Meal Planner")
    st.markdown("---")

    if st.session_state.user_profile:
        user = st.session_state.user_profile
        st.success(f"👤 **{user.name}**")
        st.caption(f"Goal: {user.goal.replace('_', ' ').title()}")

        if st.session_state.macro_targets:
            targets = st.session_state.macro_targets
            st.metric("Daily Target", f"{targets.calories:.0f} cal")
            col1, col2, col3 = st.columns(3)
            col1.metric("P", f"{targets.protein_g:.0f}g")
            col2.metric("C", f"{targets.carbs_g:.0f}g")
            col3.metric("F", f"{targets.fat_g:.0f}g")
    else:
        st.warning("⚠️ No profile found")
        st.caption("Create one in the Profile page")

    st.markdown("---")
    st.markdown("### Navigation")
    st.markdown("Use the sidebar to navigate:")
    st.markdown("- 📋 **Profile** - Manage your profile")
    st.markdown("- 📚 **Recipes** - Browse recipes")
    st.markdown("- 📅 **Meal Plan** - Weekly plans")
    st.markdown("- 📊 **Tracking** - Log & track")

# Main home page
st.title("🍽️ Meal Planning App")

st.markdown("""
Welcome to your personalized meal planning assistant!

### Getting Started

1. **📋 Profile** - Create your profile to calculate your daily macro targets based on your:
   - Age, weight, height, sex
   - Activity level
   - Fitness goal (lose fat, build muscle, maintain, etc.)

2. **📚 Recipes** - Browse and search your recipe database:
   - Currently have **17 recipes** (16 NYTimes + 1 custom)
   - Search by name or filter by meal type
   - View detailed nutrition info, ingredients, and instructions

3. **📅 Meal Plan** - Generate optimized weekly meal plans:
   - Automatically allocates calories across breakfast, lunch, and dinner
   - Ensures variety (no recipe repeats within 21 days)
   - Regenerate individual meals with one click

4. **📊 Tracking** - Log meals and track your nutrition:
   - Log consumed meals with servings
   - View daily, weekly, monthly, and yearly summaries
   - See adherence to your macro targets with charts

### Quick Actions

""")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 👤 Your Profile")
    if st.session_state.user_profile:
        user = st.session_state.user_profile
        st.write(f"**Name:** {user.name}")
        st.write(f"**Age:** {user.age}")
        st.write(f"**Goal:** {user.goal.replace('_', ' ').title()}")

        if st.session_state.macro_targets:
            targets = st.session_state.macro_targets
            st.write(f"**Target Calories:** {targets.calories:.0f} kcal/day")
    else:
        st.info("No profile found. Go to the Profile page to create one!")

with col2:
    st.markdown("#### 📊 Quick Stats")
    # Show some quick stats
    from meal_planner.recipe_store import recipe_count
    from meal_planner.planner import load_meal_plan

    num_recipes = recipe_count()
    st.write(f"**Total Recipes:** {num_recipes}")

    if st.session_state.user_profile:
        user = st.session_state.user_profile
        plan = load_meal_plan(user.id, st.session_state.current_week_start)
        if plan:
            st.write(f"**Meal Plan:** ✓ Active for this week")
        else:
            st.write(f"**Meal Plan:** No plan for this week")
    else:
        st.write(f"**Meal Plan:** Create a profile first")

st.markdown("---")

st.markdown("""
### Tips

- 💡 Start by creating your profile in the **Profile** page
- 💡 Browse available recipes in the **Recipes** page
- 💡 Generate a meal plan in the **Meal Plan** page
- 💡 Log your meals in the **Tracking** page to monitor progress

### About This App

This meal planning application uses evidence-based nutrition science (Mifflin-St Jeor equation) to calculate your personalized macro targets. It then recommends meals that match your targets while ensuring variety and balance in your diet.

All data is stored locally in a SQLite database at `~/.meal_planner/meal_planner.db`.
""")
