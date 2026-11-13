"""Shared session-state setup for the Streamlit app and its pages."""

from datetime import date, timedelta

import streamlit as st

from meal_planner.cli import _load_user
from meal_planner.db import init_db
from meal_planner.macro_calculator import calculate_macro_targets


def init_session():
    """Initialize the DB and session state.

    Every page calls this, so a page opened directly (or refreshed) works
    without first visiting the home page.
    """
    if 'db_initialized' not in st.session_state:
        init_db()
        st.session_state.db_initialized = True

    if 'user_profile' not in st.session_state:
        st.session_state.user_profile = None
    if 'macro_targets' not in st.session_state:
        st.session_state.macro_targets = None
    if 'current_week_start' not in st.session_state:
        today = date.today()
        st.session_state.current_week_start = today - timedelta(days=today.weekday())

    if st.session_state.user_profile is None:
        user = _load_user()
        if user:
            st.session_state.user_profile = user
            st.session_state.macro_targets = calculate_macro_targets(user)
