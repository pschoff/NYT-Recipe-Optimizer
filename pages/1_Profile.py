"""Profile Management Page.

Create and update user profile with macro target calculation.
"""

import streamlit as st
from meal_planner.cli import _load_user, _save_user, _update_user
from meal_planner.macro_calculator import calculate_macro_targets
from meal_planner.models import UserProfile
from meal_planner.config import ACTIVITY_MULTIPLIERS, GOAL_CALORIE_ADJUSTMENTS
from pages.components.unit_converter import lbs_to_kg, kg_to_lbs, ft_in_to_cm, cm_to_ft_in
from pages.components.charts import create_macro_pie_chart

st.set_page_config(page_title="Profile | Meal Planner", page_icon="📋", layout="wide")
st.title("📋 Profile Management")

# Load current user
user = _load_user()

# Display current profile if exists
if user:
    st.markdown("### Current Profile")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Name", user.name)
        st.metric("Age", f"{user.age} years")
    with col2:
        lbs = kg_to_lbs(user.weight_kg)
        st.metric("Weight", f"{lbs:.1f} lbs")
        ft, inches = cm_to_ft_in(user.height_cm)
        st.metric("Height", f"{ft}'{inches}\"")
    with col3:
        st.metric("Sex", user.sex.capitalize())
        st.metric("Activity", user.activity_level.replace('_', ' ').title())
        st.metric("Goal", user.goal.replace('_', ' ').title())

    # Calculate and show macro targets
    targets = calculate_macro_targets(user)

    st.markdown("### Daily Macro Targets")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("BMR", f"{targets.bmr:.0f} kcal")
    col2.metric("TDEE", f"{targets.tdee:.0f} kcal")
    col3.metric("Target", f"{targets.calories:.0f} kcal")
    col4.metric("Protein", f"{targets.protein_g:.0f}g")
    col5.metric("Carbs", f"{targets.carbs_g:.0f}g")
    col6.metric("Fat", f"{targets.fat_g:.0f}g")

    # Show macro pie chart
    st.markdown("### Macro Distribution")
    fig = create_macro_pie_chart(targets)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("### Update Profile")
else:
    st.info("No profile found. Create your profile below to get started!")

# Profile form (for create or update)
st.markdown("### Profile Form")

with st.form("profile_form"):
    st.markdown("Enter your information below:")

    name = st.text_input("Name*", value=user.name if user else "", help="Your full name")

    col1, col2 = st.columns(2)
    with col1:
        age = st.number_input(
            "Age*",
            min_value=13,
            max_value=120,
            value=user.age if user else 25,
            help="Must be 13 or older"
        )
    with col2:
        sex = st.selectbox(
            "Sex*",
            ["male", "female"],
            index=0 if not user or user.sex == "male" else 1
        )

    st.markdown("#### Body Measurements")
    col1, col2 = st.columns(2)
    with col1:
        default_lbs = kg_to_lbs(user.weight_kg) if user else 165.0
        weight_lbs = st.number_input(
            "Weight (lbs)*",
            min_value=50.0,
            max_value=500.0,
            value=default_lbs,
            step=0.5,
            help="Your current weight in pounds"
        )

    with col2:
        if user:
            default_ft, default_in = cm_to_ft_in(user.height_cm)
        else:
            default_ft, default_in = 5, 10

        ft_col, in_col = st.columns(2)
        with ft_col:
            feet = st.number_input("Feet*", min_value=3, max_value=8, value=default_ft)
        with in_col:
            inches = st.number_input("Inches*", min_value=0, max_value=11, value=default_in)

    st.markdown("#### Activity & Goals")
    col1, col2 = st.columns(2)

    with col1:
        activity = st.selectbox(
            "Activity Level*",
            list(ACTIVITY_MULTIPLIERS.keys()),
            index=list(ACTIVITY_MULTIPLIERS.keys()).index(user.activity_level) if user else 2,
            help="Your typical daily activity level"
        )

        # Show activity descriptions
        activity_descriptions = {
            "sedentary": "Little or no exercise",
            "lightly_active": "Light exercise 1-3 days/week",
            "moderately_active": "Moderate exercise 3-5 days/week",
            "very_active": "Hard exercise 6-7 days/week",
            "extra_active": "Very hard exercise & physical job"
        }
        st.caption(activity_descriptions.get(activity, ""))

    with col2:
        goal = st.selectbox(
            "Goal*",
            list(GOAL_CALORIE_ADJUSTMENTS.keys()),
            index=list(GOAL_CALORIE_ADJUSTMENTS.keys()).index(user.goal) if user else 3,
            help="Your fitness goal"
        )

        # Show goal descriptions
        goal_descriptions = {
            "lose_fat": "20% calorie deficit",
            "cut": "25% calorie deficit",
            "maintain": "Maintain current weight",
            "build_muscle": "10% calorie surplus",
            "recomp": "Body recomposition"
        }
        st.caption(goal_descriptions.get(goal, ""))

    st.markdown("---")
    submitted = st.form_submit_button(
        "💾 Save Profile" if not user else "💾 Update Profile",
        use_container_width=True
    )

    if submitted:
        # Validation
        if not name or not name.strip():
            st.error("⚠️ Name is required")
        elif age < 13:
            st.error("⚠️ Age must be 13 or older")
        elif weight_lbs < 50 or weight_lbs > 500:
            st.error("⚠️ Weight must be between 50 and 500 lbs")
        else:
            # Convert to metric
            weight_kg = lbs_to_kg(weight_lbs)
            height_cm = ft_in_to_cm(feet, inches)

            # Create profile object
            profile = UserProfile(
                id=user.id if user else None,
                name=name.strip(),
                age=age,
                weight_kg=weight_kg,
                height_cm=height_cm,
                sex=sex,
                activity_level=activity,
                goal=goal
            )

            try:
                if user:
                    # Update existing
                    _update_user(profile)
                    st.success("✅ Profile updated successfully!")
                else:
                    # Create new
                    user_id = _save_user(profile)
                    st.success(f"✅ Profile created successfully! (ID: {user_id})")

                # Update session state
                st.session_state.user_profile = profile
                st.session_state.macro_targets = calculate_macro_targets(profile)

                # Rerun to show updated profile
                st.rerun()

            except Exception as e:
                st.error(f"❌ Error saving profile: {e}")

st.markdown("---")
st.caption("💡 **Tip:** Your macro targets are calculated using the Mifflin-St Jeor equation, which is evidence-based and widely used in nutrition science.")
