"""Chart components using Plotly for data visualization."""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from meal_planner.models import MacroTargets


def create_macro_pie_chart(targets: MacroTargets):
    """Create pie chart of macro calorie distribution.

    Args:
        targets: MacroTargets object with protein, carbs, fat in grams

    Returns:
        Plotly figure
    """
    labels = ['Protein', 'Carbs', 'Fat']
    values = [
        targets.protein_g * 4,  # 4 cal/g
        targets.carbs_g * 4,    # 4 cal/g
        targets.fat_g * 9       # 9 cal/g
    ]

    fig = px.pie(
        names=labels,
        values=values,
        title="Macro Calorie Distribution",
        color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#FFE66D']
    )

    fig.update_traces(textposition='inside', textinfo='percent+label')

    return fig


def create_adherence_gauge(actual: float, target: float, label: str):
    """Create gauge chart for single macro adherence.

    Args:
        actual: Actual value consumed
        target: Target value
        label: Metric label (e.g., "Calories", "Protein")

    Returns:
        Plotly figure
    """
    # Calculate adherence percentage
    if target > 0:
        pct = max(0, 100 - abs(actual - target) / target * 100)
    else:
        pct = 100

    # Determine color
    if pct > 90:
        color = "darkgreen"
    elif pct > 70:
        color = "orange"
    else:
        color = "red"

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=pct,
        title={'text': f"{label} Adherence"},
        delta={'reference': 100, 'suffix': '%'},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 70], 'color': "lightgray"},
                {'range': [70, 90], 'color': "lightyellow"},
                {'range': [90, 100], 'color': "lightgreen"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 100
            }
        }
    ))

    return fig


def create_daily_calories_trend(meal_logs: list):
    """Create line chart of daily calories over time.

    Args:
        meal_logs: List of MealLog objects with logged_at and recipe

    Returns:
        Plotly figure
    """
    # Group by date, sum calories
    data = {}
    for log in meal_logs:
        date_key = log.logged_at.date()
        if log.recipe and log.recipe.nutrition:
            cal = log.recipe.nutrition.calories * log.servings
            data[date_key] = data.get(date_key, 0) + cal

    if not data:
        # Return empty chart if no data
        fig = go.Figure()
        fig.add_annotation(
            text="No meal logs found",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig

    df = pd.DataFrame(list(data.items()), columns=['Date', 'Calories'])
    df = df.sort_values('Date')

    fig = px.line(
        df,
        x='Date',
        y='Calories',
        title='Daily Calorie Intake',
        markers=True
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Calories (kcal)",
        hovermode='x unified'
    )

    return fig


def create_macro_stacked_bar(meal_logs: list, targets: MacroTargets = None):
    """Create stacked bar chart of protein/carbs/fat per day.

    Args:
        meal_logs: List of MealLog objects
        targets: Optional MacroTargets for reference lines

    Returns:
        Plotly figure
    """
    # Group by date, sum macros
    data = {}
    for log in meal_logs:
        date_key = log.logged_at.date()
        if log.recipe and log.recipe.nutrition:
            n = log.recipe.nutrition.scaled(log.servings)
            if date_key not in data:
                data[date_key] = {'protein': 0, 'carbs': 0, 'fat': 0}
            data[date_key]['protein'] += n.protein_g
            data[date_key]['carbs'] += n.carbs_g
            data[date_key]['fat'] += n.fat_g

    if not data:
        # Return empty chart if no data
        fig = go.Figure()
        fig.add_annotation(
            text="No meal logs found",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
        return fig

    df = pd.DataFrame.from_dict(data, orient='index').reset_index()
    df.columns = ['Date', 'Protein', 'Carbs', 'Fat']
    df = df.sort_values('Date')

    fig = px.bar(
        df,
        x='Date',
        y=['Protein', 'Carbs', 'Fat'],
        title='Daily Macro Breakdown',
        barmode='stack',
        color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#FFE66D']
    )

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Grams",
        hovermode='x unified',
        legend_title="Macros"
    )

    # Add target reference lines if provided
    if targets:
        fig.add_hline(
            y=targets.protein_g,
            line_dash="dash",
            annotation_text="Protein Target",
            line_color="red"
        )

    return fig
