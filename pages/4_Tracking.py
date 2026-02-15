"""Nutrition Tracking & Analytics Page.

Log meals and track nutrition with detailed analytics.
"""

import streamlit as st
from datetime import date, datetime, timedelta
from meal_planner.tracker import (
    log_meal, daily_summary, weekly_summary,
    monthly_summary, yearly_summary, get_meal_logs
)
from meal_planner.recipe_store import get_all_recipes
from pages.components.nutrition_display import render_nutrition_card, render_target_comparison
from pages.components.charts import (
    create_daily_calories_trend, create_macro_stacked_bar, create_adherence_gauge
)

st.set_page_config(page_title="Tracking | Meal Planner", page_icon="📊", layout="wide")
st.title("📊 Nutrition Tracking & Analytics")

# Check if user profile exists
if not st.session_state.user_profile:
    st.warning("⚠️ No profile found. Please create a profile first in the Profile page.")
    st.stop()

user = st.session_state.user_profile
targets = st.session_state.macro_targets

st.info(f"👤 Tracking for: **{user.name}** | 🎯 Target: **{targets.calories:.0f} cal/day**")

# Meal Logging Section
st.markdown("### Log a Meal")

with st.form("log_meal_form"):
    col1, col2, col3, col4 = st.columns([3, 2, 1, 2])

    # Load recipes for dropdown
    all_recipes = get_all_recipes()
    recipe_options = {f"{r.id} - {r.title}": r for r in all_recipes}

    with col1:
        if len(recipe_options) == 0:
            st.error("No recipes found. Add recipes first.")
            st.stop()

        selected_recipe_key = st.selectbox(
            "Recipe",
            options=list(recipe_options.keys()),
            help="Select the recipe you consumed"
        )

    with col2:
        meal_type = st.selectbox(
            "Meal Type",
            options=["breakfast", "lunch", "dinner"],
            help="When did you eat this?"
        )

    with col3:
        servings = st.number_input(
            "Servings",
            min_value=0.25,
            max_value=10.0,
            value=1.0,
            step=0.25,
            help="How many servings?"
        )

    with col4:
        log_date = st.date_input(
            "Date",
            value=date.today(),
            help="When did you eat this?"
        )
        log_time = st.time_input(
            "Time",
            value=datetime.now().time(),
            help="What time?"
        )

    submitted = st.form_submit_button("📝 Log Meal", use_container_width=True)

    if submitted:
        selected_recipe = recipe_options[selected_recipe_key]

        # Combine date and time
        logged_at = datetime.combine(log_date, log_time)

        try:
            log_id = log_meal(
                user_id=user.id,
                recipe_id=selected_recipe.id,
                meal_type=meal_type,
                servings=servings,
                logged_at=logged_at
            )

            # Show confirmation with nutrition info
            if selected_recipe.nutrition:
                nutrition = selected_recipe.nutrition.scaled(servings)
                st.success(f"✅ Logged: {selected_recipe.title} ({nutrition.calories:.0f} cal)")
            else:
                st.success(f"✅ Logged: {selected_recipe.title}")

            # Clear form by rerunning
            st.rerun()

        except Exception as e:
            st.error(f"❌ Failed to log meal: {e}")

st.divider()

# Analytics Section
st.markdown("### Analytics")

# Period selector
period_tab1, period_tab2, period_tab3, period_tab4 = st.tabs([
    "📅 Daily", "📆 Weekly", "📊 Monthly", "📈 Yearly"
])

# Daily Tab
with period_tab1:
    st.markdown("#### Daily Summary")

    selected_date = st.date_input(
        "Select date",
        value=date.today(),
        key="daily_date"
    )

    summary = daily_summary(user.id, selected_date, targets)

    if summary.num_meals == 0:
        st.info(f"No meals logged for {selected_date.strftime('%B %d, %Y')}")
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"##### {selected_date.strftime('%B %d, %Y')}")
            st.metric("Meals Logged", summary.num_meals)
            render_nutrition_card(
                summary.total_nutrition,
                servings=1.0,
                title="Total Nutrition"
            )

        with col2:
            st.markdown("##### Target Adherence")
            render_target_comparison(summary.total_nutrition, targets)

        # Show individual meals
        st.markdown("##### Meals Logged")
        meal_logs = get_meal_logs(
            user.id,
            selected_date,
            selected_date + timedelta(days=1)
        )

        for log in meal_logs:
            if log.recipe:
                nutrition = log.recipe.nutrition.scaled(log.servings) if log.recipe.nutrition else None
                with st.expander(
                    f"{log.meal_type.capitalize()}: {log.recipe.title} "
                    f"({nutrition.calories:.0f} cal)" if nutrition else log.recipe.title
                ):
                    st.caption(f"Time: {log.logged_at.strftime('%I:%M %p')}")
                    st.caption(f"Servings: {log.servings:.2g}")
                    if nutrition:
                        st.caption(f"P: {nutrition.protein_g:.0f}g | C: {nutrition.carbs_g:.0f}g | F: {nutrition.fat_g:.0f}g")

# Weekly Tab
with period_tab2:
    st.markdown("#### Weekly Summary")

    week_date = st.date_input(
        "Select week (any day in the week)",
        value=date.today(),
        key="weekly_date"
    )

    week_start = week_date - timedelta(days=week_date.weekday())

    summary = weekly_summary(user.id, week_start, targets)

    if summary.num_meals == 0:
        st.info(f"No meals logged for week of {week_start.strftime('%B %d, %Y')}")
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"##### Week of {week_start.strftime('%B %d, %Y')}")
            st.metric("Meals Logged", summary.num_meals)
            st.metric("Days with Logs", summary.num_days)

            render_nutrition_card(
                summary.daily_average,
                servings=1.0,
                title="Daily Average"
            )

        with col2:
            st.markdown("##### Target Adherence (Avg)")
            render_target_comparison(summary.daily_average, targets)

        # Charts
        st.markdown("##### Weekly Trends")

        meal_logs = get_meal_logs(
            user.id,
            week_start,
            week_start + timedelta(days=7)
        )

        col_a, col_b = st.columns(2)

        with col_a:
            fig = create_daily_calories_trend(meal_logs)
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            fig = create_macro_stacked_bar(meal_logs, targets)
            st.plotly_chart(fig, use_container_width=True)

# Monthly Tab
with period_tab3:
    st.markdown("#### Monthly Summary")

    col1, col2 = st.columns(2)

    with col1:
        month_year = st.date_input(
            "Select month",
            value=date.today(),
            key="monthly_date"
        )

    year = month_year.year
    month = month_year.month

    summary = monthly_summary(user.id, year, month, targets)

    if summary.num_meals == 0:
        st.info(f"No meals logged for {month_year.strftime('%B %Y')}")
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"##### {month_year.strftime('%B %Y')}")
            st.metric("Meals Logged", summary.num_meals)
            st.metric("Days with Logs", summary.num_days)

            render_nutrition_card(
                summary.daily_average,
                servings=1.0,
                title="Daily Average"
            )

        with col2:
            st.markdown("##### Target Adherence (Avg)")
            render_target_comparison(summary.daily_average, targets)

        # Adherence gauges
        st.markdown("##### Monthly Adherence Breakdown")

        col_a, col_b, col_c, col_d = st.columns(4)

        with col_a:
            fig = create_adherence_gauge(
                summary.daily_average.calories,
                targets.calories,
                "Calories"
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            fig = create_adherence_gauge(
                summary.daily_average.protein_g,
                targets.protein_g,
                "Protein"
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_c:
            fig = create_adherence_gauge(
                summary.daily_average.carbs_g,
                targets.carbs_g,
                "Carbs"
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_d:
            fig = create_adherence_gauge(
                summary.daily_average.fat_g,
                targets.fat_g,
                "Fat"
            )
            st.plotly_chart(fig, use_container_width=True)

# Yearly Tab
with period_tab4:
    st.markdown("#### Yearly Summary")

    selected_year = st.number_input(
        "Select year",
        min_value=2020,
        max_value=2030,
        value=date.today().year,
        key="yearly_year"
    )

    summary = yearly_summary(user.id, selected_year, targets)

    if summary.num_meals == 0:
        st.info(f"No meals logged for {selected_year}")
    else:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"##### Year {selected_year}")
            st.metric("Meals Logged", summary.num_meals)
            st.metric("Days with Logs", summary.num_days)

            render_nutrition_card(
                summary.daily_average,
                servings=1.0,
                title="Daily Average"
            )

        with col2:
            st.markdown("##### Target Adherence (Avg)")
            render_target_comparison(summary.daily_average, targets)

        # Long-term trends
        st.markdown("##### Yearly Trends")

        # Get all logs for the year
        start_date = date(selected_year, 1, 1)
        end_date = date(selected_year, 12, 31)
        meal_logs = get_meal_logs(user.id, start_date, end_date)

        col_a, col_b = st.columns(2)

        with col_a:
            fig = create_daily_calories_trend(meal_logs)
            st.plotly_chart(fig, use_container_width=True)

        with col_b:
            fig = create_macro_stacked_bar(meal_logs, targets)
            st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.caption("💡 **Tip:** Log your meals daily to track adherence to your macro targets and see progress over time.")
