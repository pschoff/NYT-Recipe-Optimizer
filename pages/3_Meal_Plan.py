"""Weekly Meal Planning Page.

Generate and view optimized weekly meal plans.
"""

import streamlit as st
from datetime import date, timedelta
from meal_planner.planner import (
    generate_weekly_plan, load_meal_plan, save_meal_plan,
    regenerate_meal, DAY_NAMES
)
from meal_planner.models import Nutrition
from meal_planner.recipe_store import recipe_count
from pages.components.nutrition_display import render_nutrition_card

st.set_page_config(page_title="Meal Plan | Meal Planner", page_icon="📅", layout="wide")
st.title("📅 Weekly Meal Planner")

# Check if user profile exists
if not st.session_state.user_profile:
    st.warning("⚠️ No profile found. Please create a profile first in the Profile page.")
    st.stop()

user = st.session_state.user_profile
targets = st.session_state.macro_targets

# Check if recipes exist
num_recipes = recipe_count()
if num_recipes == 0:
    st.error("❌ No recipes found. Please add recipes first in the Recipes page.")
    st.stop()

st.info(f"👤 Planning for: **{user.name}** | 🎯 Target: **{targets.calories:.0f} cal/day**")

# Week selector
st.markdown("### Select Week")

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    # Default to current week Monday
    if 'selected_week_start' not in st.session_state:
        today = date.today()
        st.session_state.selected_week_start = today - timedelta(days=today.weekday())

    selected_date = st.date_input(
        "Week starting (Monday)",
        value=st.session_state.selected_week_start,
        help="Select any date - the week will start on the Monday of that week"
    )

    # Adjust to Monday
    week_start = selected_date - timedelta(days=selected_date.weekday())
    st.session_state.selected_week_start = week_start

    week_end = week_start + timedelta(days=6)
    st.caption(f"Week: {week_start.strftime('%b %d')} - {week_end.strftime('%b %d, %Y')}")

with col2:
    if st.button("⬅️ Previous Week", use_container_width=True):
        st.session_state.selected_week_start -= timedelta(days=7)
        st.rerun()

with col3:
    if st.button("Next Week ➡️", use_container_width=True):
        st.session_state.selected_week_start += timedelta(days=7)
        st.rerun()

st.divider()

# Load or generate meal plan
plan = load_meal_plan(user.id, week_start)

if not plan:
    st.info("📋 No meal plan exists for this week yet.")

    if st.button("✨ Generate Meal Plan", type="primary", use_container_width=True):
        with st.spinner("🔄 Generating optimized meal plan..."):
            try:
                plan = generate_weekly_plan(user.id, targets, week_start)
                plan_id = save_meal_plan(plan)
                plan.id = plan_id
                st.success("✅ Meal plan generated successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to generate meal plan: {e}")
                st.stop()
else:
    st.success(f"✅ Meal plan loaded for week of {week_start.strftime('%b %d, %Y')}")

    # Display meal plan grid
    st.markdown("### Weekly Meal Plan")

    for day in range(7):
        day_date = week_start + timedelta(days=day)
        day_entries = [e for e in plan.entries if e.day_of_week == day]

        # Day header
        st.markdown(f"#### {DAY_NAMES[day]} - {day_date.strftime('%b %d')}")

        # Create columns for each meal
        cols = st.columns([3, 3, 3, 2])

        day_nutrition = Nutrition(calories=0, protein_g=0, carbs_g=0, fat_g=0)

        # Breakfast, Lunch, Dinner
        for i, meal_type in enumerate(['breakfast', 'lunch', 'dinner']):
            entry = next((e for e in day_entries if e.meal_type == meal_type), None)

            with cols[i]:
                st.markdown(f"**{meal_type.capitalize()}**")

                if entry and entry.recipe:
                    recipe = entry.recipe
                    nutrition = recipe.nutrition.scaled(entry.servings) if recipe.nutrition else None

                    if nutrition:
                        day_nutrition = day_nutrition + nutrition

                    # Display recipe info
                    with st.container():
                        st.markdown(f"**{recipe.title}**")
                        st.caption(f"Servings: {entry.servings:.2g}")

                        if nutrition:
                            col_a, col_b = st.columns(2)
                            col_a.metric("Cal", f"{nutrition.calories:.0f}")
                            col_b.metric("P", f"{nutrition.protein_g:.0f}g")

                            col_c, col_d = st.columns(2)
                            col_c.metric("C", f"{nutrition.carbs_g:.0f}g")
                            col_d.metric("F", f"{nutrition.fat_g:.0f}g")
                        else:
                            st.caption("_No nutrition data_")

                        # Regenerate button
                        if st.button(
                            "🔄 Swap",
                            key=f"regen_{day}_{meal_type}",
                            use_container_width=True
                        ):
                            with st.spinner("Finding new recipe..."):
                                try:
                                    new_entry = regenerate_meal(plan.id, day, meal_type, targets)
                                    if new_entry:
                                        st.success("✅ Meal updated!")
                                        st.rerun()
                                    else:
                                        st.error("❌ Could not find replacement recipe")
                                except Exception as e:
                                    st.error(f"❌ Failed to regenerate: {e}")
                else:
                    st.info("No meal assigned")

        # Daily totals
        with cols[3]:
            st.markdown("**Daily Total**")
            st.metric("Calories", f"{day_nutrition.calories:.0f}")
            st.caption(f"P: {day_nutrition.protein_g:.0f}g")
            st.caption(f"C: {day_nutrition.carbs_g:.0f}g")
            st.caption(f"F: {day_nutrition.fat_g:.0f}g")

            # Adherence indicator
            cal_pct = (day_nutrition.calories / targets.calories * 100) if targets.calories > 0 else 0
            if 90 <= cal_pct <= 110:
                st.success(f"{cal_pct:.0f}% of target")
            elif 80 <= cal_pct <= 120:
                st.warning(f"{cal_pct:.0f}% of target")
            else:
                st.error(f"{cal_pct:.0f}% of target")

        st.divider()

    # Weekly summary
    st.markdown("### Weekly Summary")

    # Calculate weekly totals
    weekly_nutrition = Nutrition(calories=0, protein_g=0, carbs_g=0, fat_g=0)
    meal_count = 0

    for entry in plan.entries:
        if entry.recipe and entry.recipe.nutrition:
            nutrition = entry.recipe.nutrition.scaled(entry.servings)
            weekly_nutrition = weekly_nutrition + nutrition
            meal_count += 1

    # Calculate daily average
    daily_avg = Nutrition(
        calories=weekly_nutrition.calories / 7,
        protein_g=weekly_nutrition.protein_g / 7,
        carbs_g=weekly_nutrition.carbs_g / 7,
        fat_g=weekly_nutrition.fat_g / 7
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Daily Average")
        render_nutrition_card(daily_avg, servings=1.0, title="Average per Day")

    with col2:
        st.markdown("#### vs Target")

        def adherence_pct(actual, target):
            if target == 0:
                return 100
            return max(0, 100 - abs(actual - target) / target * 100)

        metrics = [
            ("Calories", daily_avg.calories, targets.calories),
            ("Protein", daily_avg.protein_g, targets.protein_g),
            ("Carbs", daily_avg.carbs_g, targets.carbs_g),
            ("Fat", daily_avg.fat_g, targets.fat_g),
        ]

        for label, actual, target in metrics:
            pct = adherence_pct(actual, target)
            col_a, col_b, col_c = st.columns([2, 2, 1])

            with col_a:
                st.metric(label, f"{actual:.0f}")
            with col_b:
                st.caption(f"Target: {target:.0f}")
            with col_c:
                if pct > 90:
                    st.success(f"{pct:.0f}%")
                elif pct > 70:
                    st.warning(f"{pct:.0f}%")
                else:
                    st.error(f"{pct:.0f}%")

    # Regenerate entire plan button
    st.divider()

    if st.button("🔄 Regenerate Entire Plan", type="secondary"):
        if st.session_state.get('confirm_regenerate'):
            with st.spinner("Generating new meal plan..."):
                try:
                    # Delete old plan and generate new one
                    new_plan = generate_weekly_plan(user.id, targets, week_start)
                    plan_id = save_meal_plan(new_plan)
                    st.success("✅ New meal plan generated!")
                    st.session_state.confirm_regenerate = False
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to regenerate: {e}")
        else:
            st.warning("⚠️ This will replace your entire meal plan. Click again to confirm.")
            st.session_state.confirm_regenerate = True

st.markdown("---")
st.caption("💡 **Tip:** Use the 'Swap' buttons to replace individual meals, or regenerate the entire week for a fresh plan.")
