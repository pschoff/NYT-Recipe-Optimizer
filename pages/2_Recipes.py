"""Recipe Browser Page.

Search, filter, and view recipe details.
"""

import streamlit as st
import pandas as pd
from meal_planner.recipe_store import get_all_recipes, search_recipes, recipe_count
from meal_planner.recipe_sources import export_recipes_csv, import_recipes_csv
from pages.components.recipe_card import render_recipe_detail

st.set_page_config(page_title="Recipes | Meal Planner", page_icon="📚", layout="wide")
st.title("📚 Recipe Browser")

# Load all recipes
all_recipes = get_all_recipes()
total_count = len(all_recipes)

if total_count == 0:
    st.warning("⚠️ No recipes found in the database.")
    st.info("Import recipes using the button below or run: `python -m meal_planner recipes import`")

    if st.button("📥 Import Seed Recipes"):
        from meal_planner.recipe_sources import import_seed_recipes
        count = import_seed_recipes()
        st.success(f"✅ Imported {count} seed recipes!")
        st.rerun()
    st.stop()

# Search and filter controls
st.markdown("### Search & Filter")

col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    search_query = st.text_input(
        "🔍 Search recipes by name",
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
        "⏱️ Max time (min)",
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

# Recipe table
st.markdown("### Recipes")

if len(filtered_recipes) == 0:
    st.info("No recipes match your filters. Try adjusting your search or filters.")
else:
    # Create DataFrame for display
    recipe_data = []
    for recipe in filtered_recipes:
        total_time = recipe.prep_time_minutes + recipe.cook_time_minutes
        recipe_data.append({
            "ID": recipe.id,
            "Title": recipe.title,
            "Time (min)": total_time if total_time > 0 else "N/A",
            "Calories": f"{recipe.nutrition.calories:.0f}" if recipe.nutrition else "N/A",
            "Protein (g)": f"{recipe.nutrition.protein_g:.0f}" if recipe.nutrition else "N/A",
            "Carbs (g)": f"{recipe.nutrition.carbs_g:.0f}" if recipe.nutrition else "N/A",
            "Fat (g)": f"{recipe.nutrition.fat_g:.0f}" if recipe.nutrition else "N/A",
            "Meal Types": ", ".join([mt.capitalize() for mt in recipe.meal_types]),
            "Source": recipe.source.title()
        })

    df = pd.DataFrame(recipe_data)

    # Display table
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.NumberColumn("ID", width="small"),
            "Title": st.column_config.TextColumn("Title", width="large"),
            "Time (min)": st.column_config.TextColumn("Time", width="small"),
            "Calories": st.column_config.TextColumn("Calories", width="small"),
            "Protein (g)": st.column_config.TextColumn("Protein", width="small"),
            "Carbs (g)": st.column_config.TextColumn("Carbs", width="small"),
            "Fat (g)": st.column_config.TextColumn("Fat", width="small"),
            "Meal Types": st.column_config.TextColumn("Meal Types", width="medium"),
            "Source": st.column_config.TextColumn("Source", width="small")
        }
    )

    st.divider()

    # Recipe detail viewer
    st.markdown("### Recipe Details")

    # Recipe selector
    recipe_options = {f"{r.id} - {r.title}": r for r in filtered_recipes}
    selected_recipe_key = st.selectbox(
        "Select a recipe to view details",
        options=list(recipe_options.keys()),
        help="Choose a recipe to see full details"
    )

    if selected_recipe_key:
        selected_recipe = recipe_options[selected_recipe_key]

        with st.container():
            render_recipe_detail(selected_recipe)

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

    if st.button("📤 Export to CSV", use_container_width=True):
        try:
            count = export_recipes_csv(export_filename)
            st.success(f"✅ Exported {count} recipes to {export_filename}")
        except Exception as e:
            st.error(f"❌ Export failed: {e}")

with col2:
    st.markdown("#### Import Recipes")
    import_file = st.file_uploader(
        "Upload CSV file",
        type=["csv"],
        help="Upload a CSV file with recipes to import"
    )

    if import_file is not None:
        if st.button("📥 Import from CSV", use_container_width=True):
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

                st.success(f"✅ Imported {count} new recipes!")
                st.info("Refresh the page to see the new recipes.")

            except Exception as e:
                st.error(f"❌ Import failed: {e}")

st.markdown("---")
st.caption("💡 **Tip:** Export your recipes to CSV to back them up or share them with others. You can re-import them later if needed.")
