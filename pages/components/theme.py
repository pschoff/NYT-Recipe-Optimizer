"""Editorial (newspaper food section) look for the Streamlit front end.

Call ``apply_theme()`` right after ``st.set_page_config`` on every page, and
use ``page_header`` in place of ``st.title``. Base colors live in
``.streamlit/config.toml``; everything else is the CSS below.
"""

from datetime import date
from html import escape

import streamlit as st

from meal_planner.models import Recipe

ACCENT = "#c8322b"
INK = "#121212"
MUTED = "#6b6b6b"
RULE = "#dfdfdf"
CHART_COLORS = ["#c8322b", "#2f5d50", "#d9a441"]  # protein, carbs, fat

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,700;0,800;1,500&family=Libre+Franklin:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap');

:root {
  --accent: #c8322b; --ink: #121212; --muted: #6b6b6b; --rule: #dfdfdf;
  --display: 'Playfair Display', 'Times New Roman', Georgia, serif;
  --serif: 'Source Serif 4', Georgia, 'Times New Roman', serif;
  --sans: 'Libre Franklin', 'Helvetica Neue', Helvetica, Arial, sans-serif;
}

.stApp, .stApp p, .stApp li { font-family: var(--serif); color: var(--ink); }
.block-container { max-width: 1180px; padding-top: 2.2rem; }
header[data-testid="stHeader"] { background: transparent; }

h1, h2, h3, h4 { font-family: var(--display) !important; color: var(--ink); letter-spacing: -0.01em; }
h1 { font-weight: 800 !important; }
h3 { font-weight: 700 !important; border-top: 1px solid var(--ink); padding-top: 0.7rem !important; margin-top: 1.2rem; }
h4 { font-weight: 700 !important; }

/* Small-caps sans labels: captions, widget labels, metric labels */
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p,
[data-testid="stWidgetLabel"] p, [data-testid="stMetricLabel"] p {
  font-family: var(--sans) !important; font-size: 0.72rem !important;
  letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted) !important;
}
[data-testid="stMetricValue"] { font-family: var(--display); font-weight: 700; font-size: 1.7rem; }
[data-testid="stMetricDelta"] { font-family: var(--sans); font-size: 0.72rem; }

/* Buttons: flat, squared, sans */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  font-family: var(--sans); font-size: 0.74rem; font-weight: 600;
  letter-spacing: 0.08em; text-transform: uppercase;
  border-radius: 3px; border: 1px solid var(--ink); background: #fff; color: var(--ink);
  box-shadow: none;
}
.stButton > button p, .stFormSubmitButton > button p { font-family: var(--sans); font-size: 0.74rem; color: inherit; }
.stButton > button:hover, .stFormSubmitButton > button:hover { background: var(--ink); color: #fff; border-color: var(--ink); }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
  background: var(--accent); border-color: var(--accent); color: #fff;
}
.stButton > button[kind="primary"]:hover { background: #a82822; border-color: #a82822; }

/* Inputs */
.stTextInput input, .stNumberInput input, .stDateInput input,
[data-baseweb="select"] > div { border-radius: 3px !important; font-family: var(--sans); }

/* Alerts: quiet notes with a side rule instead of colored boxes */
[data-testid="stAlert"] { border-radius: 0; background: #faf8f5; border-left: 3px solid var(--ink); }
[data-testid="stAlert"] p { font-family: var(--sans); font-size: 0.86rem; }

hr { border-color: var(--rule) !important; margin: 1.2rem 0 !important; }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 0 !important; }
.stTabs [data-baseweb="tab"] p { font-family: var(--sans); font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; }
.stApp a { color: var(--ink); text-decoration-color: var(--accent); text-underline-offset: 3px; }

/* Sidebar */
[data-testid="stSidebar"] { background: #f7f5f2; border-right: 1px solid var(--rule); }
[data-testid="stSidebarNav"] a span, [data-testid="stSidebarNav"] a span p,
[data-testid="stSidebarNav"] li:first-child a::after {
  font-family: var(--sans); font-size: 0.8rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase;
}

/* The entry script is listed as "streamlit app"; show it as "Home" */
[data-testid="stSidebarNav"] li:first-child a span { display: none; }
[data-testid="stSidebarNav"] li:first-child a::after { content: "Home"; color: var(--ink); }

/* Masthead and page headers */
.ed-masthead { text-align: center; border-bottom: 3px double var(--ink); padding-bottom: 0.9rem; margin-bottom: 1.6rem; }
.ed-masthead .ed-date { font-family: var(--sans); font-size: 0.7rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); }
.ed-masthead .ed-name { font-family: var(--display); font-weight: 800; font-size: 3.2rem; line-height: 1.1; margin: 0.2rem 0; }
.ed-masthead .ed-tag { font-family: var(--serif); font-style: italic; color: var(--muted); font-size: 1rem; }
.ed-kicker { font-family: var(--sans); font-size: 0.72rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: var(--accent); }
.ed-header { border-bottom: 1px solid var(--ink); padding-bottom: 0.9rem; margin-bottom: 1.4rem; }
.ed-header .ed-title { font-family: var(--display); font-weight: 800; font-size: 2.6rem; line-height: 1.12; margin: 0.25rem 0 0.3rem; }
.ed-dek { font-family: var(--serif); font-size: 1.1rem; color: #333; line-height: 1.45; }

/* Recipe cards */
.ed-card { border-top: 1px solid var(--ink); padding: 0.75rem 0 0.4rem; min-height: 8.2rem; }
.ed-card .ed-card-title { font-family: var(--display); font-weight: 700; font-size: 1.28rem; line-height: 1.2; margin: 0.3rem 0 0.45rem; }
.ed-card.ed-hero { border-top: 3px solid var(--ink); }
.ed-card.ed-hero .ed-card-title { font-size: 2.3rem; font-weight: 800; }
.ed-meta { font-family: var(--sans); font-size: 0.74rem; color: var(--muted); letter-spacing: 0.02em; }
.ed-meta b { color: var(--ink); font-weight: 600; }

/* Recipe detail */
.ed-ingredients { list-style: none; padding: 0 !important; margin: 0 !important; }
.ed-ingredients li { margin: 0 !important; padding: 0.5rem 0; border-bottom: 1px solid var(--rule); font-size: 0.98rem; }
.ed-step { margin-bottom: 1.3rem; }
.ed-step .ed-step-n { font-family: var(--sans); font-weight: 700; font-size: 0.8rem; letter-spacing: 0.06em; text-transform: uppercase; }
.ed-step p { margin: 0.25rem 0 0; font-size: 1.04rem; line-height: 1.6; }
.ed-stat { border-top: 1px solid var(--ink); padding-top: 0.5rem; }
.ed-stat .ed-stat-n { font-family: var(--display); font-weight: 800; font-size: 2.4rem; line-height: 1.15; margin-bottom: 0.2rem; }
</style>
"""


def apply_theme():
    """Inject the editorial stylesheet. Call once per page render."""
    st.markdown(_CSS, unsafe_allow_html=True)


def masthead(name: str = "The Meal Planner", tagline: str = ""):
    """Front-page masthead with today's date."""
    today = date.today().strftime("%A, %B %-d, %Y")
    tag = f'<div class="ed-tag">{escape(tagline)}</div>' if tagline else ""
    st.markdown(
        f'<div class="ed-masthead"><div class="ed-date">{today}</div>'
        f'<div class="ed-name">{escape(name)}</div>{tag}</div>',
        unsafe_allow_html=True,
    )


def page_header(kicker: str, title: str, dek: str = ""):
    """Section kicker, headline and optional standfirst, replacing st.title."""
    dek_html = f'<div class="ed-dek">{escape(dek)}</div>' if dek else ""
    st.markdown(
        f'<div class="ed-header"><div class="ed-kicker">{escape(kicker)}</div>'
        f'<div class="ed-title">{escape(title)}</div>{dek_html}</div>',
        unsafe_allow_html=True,
    )


def recipe_kicker(recipe: Recipe) -> str:
    """Short label for a recipe: cuisine if known, otherwise its meal types."""
    if recipe.cuisine:
        return recipe.cuisine
    return " · ".join(mt.capitalize() for mt in recipe.meal_types) or "Recipe"


def recipe_meta(recipe: Recipe) -> str:
    """One-line 'time · calories · protein' summary as HTML."""
    parts = []
    total = (recipe.prep_time_minutes or 0) + (recipe.cook_time_minutes or 0)
    if total:
        hours, mins = divmod(total, 60)
        time_str = f"{hours} hr {mins} min" if hours and mins else f"{hours} hr" if hours else f"{mins} min"
        parts.append(f"<b>{time_str}</b>")
    if recipe.nutrition:
        parts.append(f"<b>{recipe.nutrition.calories:.0f}</b> cal")
        parts.append(f"<b>{recipe.nutrition.protein_g:.0f}g</b> protein")
    return " &nbsp;·&nbsp; ".join(parts)


def recipe_card(recipe: Recipe, hero: bool = False):
    """Typographic recipe card: kicker, headline, meta line."""
    cls = "ed-card ed-hero" if hero else "ed-card"
    st.markdown(
        f'<div class="{cls}"><div class="ed-kicker">{escape(recipe_kicker(recipe))}</div>'
        f'<div class="ed-card-title">{escape(recipe.title)}</div>'
        f'<div class="ed-meta">{recipe_meta(recipe)}</div></div>',
        unsafe_allow_html=True,
    )


def stat(value: str, label: str):
    """Large number over a small-caps label."""
    st.markdown(
        f'<div class="ed-stat"><div class="ed-stat-n">{escape(value)}</div>'
        f'<div class="ed-meta">{escape(label.upper())}</div></div>',
        unsafe_allow_html=True,
    )
