"""Streamlit frontend for the Meal Planning App.

Main entry point for the multi-page Streamlit application.
"""

import random
from html import escape

import streamlit as st
from datetime import date

from meal_planner.planner import load_meal_plan, DAY_NAMES
from meal_planner.recipe_store import get_all_recipes
from pages.components.session import init_session
from pages.components.theme import apply_theme, masthead, recipe_card, stat

st.set_page_config(
    page_title="Meal Planner",
    layout="wide",
    initial_sidebar_state="expanded"
)
apply_theme()

init_session()

# Sidebar: current profile and targets
with st.sidebar:
    if st.session_state.user_profile:
        user = st.session_state.user_profile
        st.markdown(f"**{user.name}**")
        st.caption(f"Goal: {user.goal.replace('_', ' ').title()}")

        if st.session_state.macro_targets:
            targets = st.session_state.macro_targets
            st.metric("Daily Target", f"{targets.calories:.0f} cal")
            col1, col2, col3 = st.columns(3)
            col1.metric("Protein", f"{targets.protein_g:.0f}g")
            col2.metric("Carbs", f"{targets.carbs_g:.0f}g")
            col3.metric("Fat", f"{targets.fat_g:.0f}g")
    else:
        st.caption("No profile yet. Create one on the Profile page.")

# Front page
masthead("The Meal Planner", "Recipes, portioned to your numbers")

user = st.session_state.user_profile
targets = st.session_state.macro_targets
recipes = get_all_recipes()
week_start = st.session_state.current_week_start
plan = load_meal_plan(user.id, week_start) if user else None

if not recipes:
    st.info("The recipe box is empty. Import recipes on the Recipes page to get started.")
    st.page_link("pages/2_Recipes.py", label="Go to Recipes →")
    st.stop()

# Featured recipes: a stable pick for the week, so the page doesn't reshuffle on every rerun
rng = random.Random(week_start.toordinal())
featured = rng.sample(recipes, min(7, len(recipes)))

lead, side = st.columns([3, 2], gap="large")

with lead:
    recipe_card(featured[0], hero=True)
    st.page_link("pages/2_Recipes.py", label="Browse all recipes →")

with side:
    today_idx = date.today().weekday()
    st.markdown('<div class="ed-kicker">On the table today</div>', unsafe_allow_html=True)
    todays = sorted(
        (e for e in plan.entries if e.day_of_week == today_idx and e.recipe),
        key=lambda e: ["breakfast", "lunch", "dinner"].index(e.meal_type),
    ) if plan else []
    if todays:
        for entry in todays:
            st.markdown(
                f'<div class="ed-card" style="min-height:0"><div class="ed-meta">{entry.meal_type.upper()}</div>'
                f'<div class="ed-card-title" style="font-size:1.1rem">{escape(entry.recipe.title)}</div></div>',
                unsafe_allow_html=True,
            )
        st.page_link("pages/3_Meal_Plan.py", label=f"See all of {DAY_NAMES[today_idx]} and the week →")
    elif user:
        st.write("No plan for this week yet.")
        st.page_link("pages/3_Meal_Plan.py", label="Generate this week's plan →")
    else:
        st.write("Create a profile to get daily targets and a weekly plan built around them.")
        st.page_link("pages/1_Profile.py", label="Create your profile →")

st.markdown("### This Week's Picks")
cols = st.columns(3, gap="large")
for i, recipe in enumerate(featured[1:]):
    with cols[i % 3]:
        recipe_card(recipe)

st.markdown("### By the Numbers")
c1, c2, c3, c4 = st.columns(4, gap="large")
with c1:
    stat(str(len(recipes)), "Recipes in the box")
with c2:
    stat(f"{targets.calories:.0f}" if targets else "—", "Daily calorie target")
with c3:
    stat(f"{targets.protein_g:.0f}g" if targets else "—", "Daily protein target")
with c4:
    stat(str(len(plan.entries)) if plan else "0", "Meals planned this week")

st.markdown("### How It Works")
h1, h2, h3 = st.columns(3, gap="large")
with h1:
    st.markdown("#### 1. Set your targets")
    st.write("Enter age, weight, height, activity level and goal. Daily calories and macros follow from the Mifflin-St Jeor equation.")
    st.page_link("pages/1_Profile.py", label="Profile →")
with h2:
    st.markdown("#### 2. Plan the week")
    st.write("Each day's breakfast, lunch and dinner are chosen and portioned to match your targets, with no repeats inside three weeks.")
    st.page_link("pages/3_Meal_Plan.py", label="Meal Plan →")
with h3:
    st.markdown("#### 3. Log what you eat")
    st.write("Record meals and compare days, weeks and months against your targets.")
    st.page_link("pages/4_Tracking.py", label="Tracking →")

st.divider()
st.caption("All data is stored locally in a SQLite database at ~/.meal_planner/meal_planner.db")
