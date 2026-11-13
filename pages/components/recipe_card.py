"""Recipe card display components for Streamlit pages."""

from html import escape

import streamlit as st
from meal_planner.models import Recipe
from pages.components.nutrition_display import render_nutrition_card
from pages.components.theme import page_header, recipe_kicker


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
    page_header(recipe_kicker(recipe), recipe.title)

    meta_parts = [f"Yield: <b>{recipe.servings} servings</b>"]
    if recipe.prep_time_minutes:
        meta_parts.append(f"Prep: <b>{recipe.prep_time_minutes} min</b>")
    if recipe.cook_time_minutes:
        meta_parts.append(f"Cook: <b>{recipe.cook_time_minutes} min</b>")
    if recipe.source:
        meta_parts.append(f"Source: <b>{escape(recipe.source.title())}</b>")
    st.markdown(f'<div class="ed-meta">{" &nbsp;·&nbsp; ".join(meta_parts)}</div>', unsafe_allow_html=True)

    if recipe.source_url:
        st.markdown(f"[View the original recipe]({recipe.source_url})")

    if recipe.nutrition:
        render_nutrition_card(recipe.nutrition, servings=1.0, title="Nutrition Per Serving")

    left, right = st.columns([2, 3], gap="large")

    with left:
        st.markdown("### Ingredients")
        if recipe.ingredients:
            items = []
            for ing in recipe.ingredients:
                text = f"{ing.quantity} {ing.unit} {ing.name}" if ing.quantity and ing.unit else ing.name
                if ing.notes:
                    text += f" ({ing.notes})"
                items.append(f"<li>{escape(text)}</li>")
            st.markdown(f'<ul class="ed-ingredients">{"".join(items)}</ul>', unsafe_allow_html=True)
        else:
            st.caption("No ingredients listed")

    with right:
        st.markdown("### Preparation")
        if recipe.instructions:
            steps = "".join(
                f'<div class="ed-step"><div class="ed-step-n">Step {i}</div><p>{escape(step)}</p></div>'
                for i, step in enumerate(recipe.instructions, 1)
            )
            st.markdown(steps, unsafe_allow_html=True)
        else:
            st.caption("No instructions available")
