"""Recipe Browser Page.

Search, filter, and view recipe details.
"""

import streamlit as st
from meal_planner.recipe_store import get_all_recipes, search_recipes, recipe_count
from meal_planner.recipe_sources import export_recipes_csv, import_recipes_csv
from pages.components.recipe_card import render_recipe_detail

from pages.components.session import init_session
from pages.components.theme import apply_theme, page_header, recipe_card

PAGE_SIZE = 12

st.set_page_config(page_title="Recipes | Meal Planner", layout="wide")
apply_theme()
init_session()
page_header('Recipes', 'Recipe Box', 'Search the collection, filter by meal or time, and open any recipe for ingredients, steps and nutrition.')

# Load all recipes
all_recipes = get_all_recipes()
total_count = len(all_recipes)

if total_count == 0:
    st.warning("No recipes found in the database.")
    st.info("Import recipes using the button below or run: `python -m meal_planner recipes import`")

    if st.button("Import Seed Recipes"):
        from meal_planner.recipe_sources import import_seed_recipes
        count = import_seed_recipes()
        st.success(f"Imported {count} seed recipes!")
        st.rerun()
    st.stop()

# Recipe detail view (opened from a card)
selected_id = st.session_state.get("selected_recipe_id")
selected_recipe = next((r for r in all_recipes if r.id == selected_id), None)

if selected_recipe:
    if st.button("← Back to all recipes"):
        st.session_state.selected_recipe_id = None
        st.rerun()
    render_recipe_detail(selected_recipe)
    st.stop()
# Search and filter controls
st.markdown("### Search & Filter")

col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    search_query = st.text_input(
        "Search recipes by name",
        placeholder="e.g., chicken, soup, salad...",
        help="Search is case-insensitive"
    )

with col2:
    meal_type_filter = st.multiselect(
        "Filter by meal type",
        options=["breakfast", "lunch", "dinner"],
        default=[],
        help="Select one or more meal types"
    )

with col3:
    max_time = st.number_input(
        "Max time (min)",
        min_value=0,
        max_value=300,
        value=0,
        step=5,
        help="Total cooking time (0 = no limit)"
    )

# Apply filters
filtered_recipes = all_recipes

# Search filter
if search_query:
    filtered_recipes = [
        r for r in filtered_recipes
        if search_query.lower() in r.title.lower()
    ]

# Meal type filter
if meal_type_filter:
    filtered_recipes = [
        r for r in filtered_recipes
        if any(mt in r.meal_types for mt in meal_type_filter)
    ]

# Cooking time filter
if max_time > 0:
    filtered_recipes = [
        r for r in filtered_recipes
        if (r.prep_time_minutes + r.cook_time_minutes) <= max_time
    ]

# Display count
st.caption(f"Showing {len(filtered_recipes)} of {total_count} recipes")

st.divider()

if len(filtered_recipes) == 0:
    st.info("No recipes match your filters. Try adjusting your search or filters.")
else:
    # Card grid, paged
    total_pages = (len(filtered_recipes) - 1) // PAGE_SIZE + 1
    page = min(st.session_state.get("recipe_page", 0), total_pages - 1)
    page_recipes = filtered_recipes[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    for row_start in range(0, len(page_recipes), 3):
        cols = st.columns(3, gap="large")
        for col, recipe in zip(cols, page_recipes[row_start:row_start + 3]):
            with col:
                recipe_card(recipe)
                if st.button("View recipe", key=f"view_{recipe.id}"):
                    st.session_state.selected_recipe_id = recipe.id
                    st.rerun()

    if total_pages > 1:
        st.divider()
        prev_col, mid_col, next_col = st.columns([1, 2, 1])
        with prev_col:
            if st.button("← Previous", disabled=page == 0, use_container_width=True):
                st.session_state.recipe_page = page - 1
                st.rerun()
        with mid_col:
            st.markdown(
                f'<div class="ed-meta" style="text-align:center;padding-top:0.6rem">PAGE {page + 1} OF {total_pages}</div>',
                unsafe_allow_html=True,
            )
        with next_col:
            if st.button("Next →", disabled=page >= total_pages - 1, use_container_width=True):
                st.session_state.recipe_page = page + 1
                st.rerun()

# CSV Import/Export section
st.divider()
st.markdown("### Import / Export")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Export Recipes")
    export_filename = st.text_input(
        "Export filename",
        value="my_recipes.csv",
        help="File will be saved in the current directory"
    )

    if st.button("Export to CSV", use_container_width=True):
        try:
            count = export_recipes_csv(export_filename)
            st.success(f"Exported {count} recipes to {export_filename}")
        except Exception as e:
            st.error(f"Export failed: {e}")

with col2:
    st.markdown("#### Import Recipes")
    import_file = st.file_uploader(
        "Upload CSV file",
        type=["csv"],
        help="Upload a CSV file with recipes to import"
    )

    if import_file is not None:
        if st.button("Import from CSV", use_container_width=True):
            try:
                # Save uploaded file temporarily
                import tempfile
                import os

                with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
                    tmp_file.write(import_file.getvalue())
                    tmp_path = tmp_file.name

                # Import recipes
                count = import_recipes_csv(tmp_path)

                # Clean up temp file
                os.unlink(tmp_path)

                st.success(f"Imported {count} new recipes!")
                st.info("Refresh the page to see the new recipes.")

            except Exception as e:
                st.error(f"Import failed: {e}")

st.markdown("---")
st.caption("**Tip:** Export your recipes to CSV to back them up or share them with others. You can re-import them later if needed.")
