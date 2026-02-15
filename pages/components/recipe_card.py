"""Recipe card display components for Streamlit pages."""

import streamlit as st
from meal_planner.models import Recipe
from pages.components.nutrition_display import render_nutrition_card


def render_recipe_summary(recipe: Recipe):
    """Compact recipe card for lists.

    Args:
        recipe: Recipe object to display
    """
    with st.container():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{recipe.title}**")
            meal_types_str = ', '.join([mt.capitalize() for mt in recipe.meal_types])
            cuisine_str = f" | {recipe.cuisine}" if recipe.cuisine else ""
            st.caption(f"{meal_types_str}{cuisine_str}")
        with col2:
            if recipe.nutrition:
                st.metric("Cal", f"{recipe.nutrition.calories:.0f}")


def render_recipe_detail(recipe: Recipe):
    """Full recipe detail view with ingredients, instructions, and nutrition.

    Args:
        recipe: Recipe object to display in detail
    """
    st.markdown(f"# {recipe.title}")

    # Metadata
    meta_parts = []
    if recipe.source:
        meta_parts.append(f"Source: {recipe.source.title()}")
    meta_parts.append(f"Servings: {recipe.servings}")
    if recipe.prep_time_minutes:
        meta_parts.append(f"Prep: {recipe.prep_time_minutes} min")
    if recipe.cook_time_minutes:
        meta_parts.append(f"Cook: {recipe.cook_time_minutes} min")

    st.caption(" | ".join(meta_parts))

    # Meal types
    if recipe.meal_types:
        meal_types_str = ', '.join([mt.capitalize() for mt in recipe.meal_types])
        st.info(f"**Meal Types:** {meal_types_str}")

    # Nutrition
    if recipe.nutrition:
        render_nutrition_card(recipe.nutrition, servings=1.0, title="Nutrition Per Serving")
        st.markdown("---")

    # Ingredients
    if recipe.ingredients:
        st.markdown("### Ingredients")
        for ing in recipe.ingredients:
            if ing.quantity and ing.unit:
                st.markdown(f"- {ing.quantity} {ing.unit} {ing.name}")
            else:
                st.markdown(f"- {ing.name}")
            if ing.notes:
                st.caption(f"  _{ing.notes}_")
        st.markdown("---")

    # Instructions
    if recipe.instructions:
        st.markdown("### Instructions")
        for i, step in enumerate(recipe.instructions, 1):
            st.markdown(f"**{i}.** {step}")
    else:
        st.info("No instructions available")
