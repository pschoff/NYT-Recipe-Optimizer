"""Unit conversion utilities for imperial/metric conversion.

Display in imperial (lbs, feet/inches) for user-friendly forms.
Store in metric (kg, cm) in database for consistency with CLI.
"""

# Conversion constants
LBS_PER_KG = 2.20462
CM_PER_INCH = 2.54
INCHES_PER_FOOT = 12


def lbs_to_kg(lbs: float) -> float:
    """Convert pounds to kilograms."""
    return lbs / LBS_PER_KG


def kg_to_lbs(kg: float) -> float:
    """Convert kilograms to pounds."""
    return kg * LBS_PER_KG


def ft_in_to_cm(feet: int, inches: int) -> float:
    """Convert feet and inches to centimeters."""
    return (feet * INCHES_PER_FOOT + inches) * CM_PER_INCH


def cm_to_ft_in(cm: float) -> tuple:
    """Convert centimeters to (feet, inches)."""
    total_inches = cm / CM_PER_INCH
    feet = int(total_inches // INCHES_PER_FOOT)
    inches = int(round(total_inches % INCHES_PER_FOOT))
    if inches == 12:
        feet += 1
        inches = 0
    return feet, inches
