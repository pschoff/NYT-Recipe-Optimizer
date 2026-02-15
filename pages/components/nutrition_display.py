"""Nutrition display components for Streamlit pages."""

import streamlit as st
from meal_planner.models import Nutrition, MacroTargets


def render_nutrition_card(nutrition: Nutrition, servings: float = 1.0, title: str = "Nutrition Facts"):
    """Render a nutrition label-style card with metrics.

    Args:
        nutrition: Nutrition object
        servings: Serving multiplier (default 1.0)
        title: Card title (default "Nutrition Facts")
    """
    scaled = nutrition.scaled(servings)

    st.markdown(f"### {title}")
    cols = st.columns(4)
    cols[0].metric("Calories", f"{scaled.calories:.0f}")
    cols[1].metric("Protein", f"{scaled.protein_g:.0f}g")
    cols[2].metric("Carbs", f"{scaled.carbs_g:.0f}g")
    cols[3].metric("Fat", f"{scaled.fat_g:.0f}g")

    # Show macro percentages
    pcts = scaled.macro_percentages()
    st.caption(
        f"Macros: {pcts['protein']:.0f}% protein | "
        f"{pcts['carbs']:.0f}% carbs | "
        f"{pcts['fat']:.0f}% fat"
    )

    # Show fiber if available
    if scaled.fiber_g > 0:
        st.caption(f"Fiber: {scaled.fiber_g:.0f}g")


def render_target_comparison(actual: Nutrition, target: MacroTargets):
    """Render actual vs target nutrition with progress bars and adherence %.

    Args:
        actual: Actual nutrition consumed
        target: Target macro goals

    Color coding:
        - Green: >90% adherence
        - Orange: 70-90% adherence
        - Red: <70% adherence
    """
    st.markdown("### Target Adherence")

    def adherence_pct(actual_val: float, target_val: float) -> float:
        """Calculate adherence percentage (100% = perfect match)."""
        if target_val == 0:
            return 100.0
        deviation = abs(actual_val - target_val) / target_val
        return max(0, 100 - deviation * 100)

    def get_color(pct: float) -> str:
        """Get color based on adherence percentage."""
        if pct > 90:
            return "green"
        elif pct > 70:
            return "orange"
        else:
            return "red"

    metrics = [
        ("Calories", actual.calories, target.calories),
        ("Protein", actual.protein_g, target.protein_g),
        ("Carbs", actual.carbs_g, target.carbs_g),
        ("Fat", actual.fat_g, target.fat_g),
    ]

    for label, actual_val, target_val in metrics:
        pct = adherence_pct(actual_val, target_val)
        color = get_color(pct)

        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.metric(label, f"{actual_val:.0f}", delta=f"Target: {target_val:.0f}")
        with col2:
            st.progress(min(pct / 100, 1.0))
        with col3:
            # Color-coded adherence text
            if color == "green":
                st.success(f"{pct:.0f}%")
            elif color == "orange":
                st.warning(f"{pct:.0f}%")
            else:
                st.error(f"{pct:.0f}%")
