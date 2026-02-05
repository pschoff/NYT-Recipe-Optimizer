"""Data models for the meal planning application."""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class Nutrition:
    """Nutritional information per serving."""
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float = 0.0
    sugar_g: float = 0.0
    sodium_mg: float = 0.0

    def scaled(self, servings: float) -> "Nutrition":
        """Return nutrition scaled by number of servings."""
        return Nutrition(
            calories=self.calories * servings,
            protein_g=self.protein_g * servings,
            carbs_g=self.carbs_g * servings,
            fat_g=self.fat_g * servings,
            fiber_g=self.fiber_g * servings,
            sugar_g=self.sugar_g * servings,
            sodium_mg=self.sodium_mg * servings,
        )

    def __add__(self, other: "Nutrition") -> "Nutrition":
        return Nutrition(
            calories=self.calories + other.calories,
            protein_g=self.protein_g + other.protein_g,
            carbs_g=self.carbs_g + other.carbs_g,
            fat_g=self.fat_g + other.fat_g,
            fiber_g=self.fiber_g + other.fiber_g,
            sugar_g=self.sugar_g + other.sugar_g,
            sodium_mg=self.sodium_mg + other.sodium_mg,
        )

    @staticmethod
    def zero() -> "Nutrition":
        return Nutrition(0, 0, 0, 0, 0, 0, 0)

    def macro_percentages(self) -> dict:
        """Return macro percentages based on caloric contribution."""
        if self.calories == 0:
            return {"protein": 0, "carbs": 0, "fat": 0}
        return {
            "protein": (self.protein_g * 4 / self.calories) * 100,
            "carbs": (self.carbs_g * 4 / self.calories) * 100,
            "fat": (self.fat_g * 9 / self.calories) * 100,
        }


@dataclass
class Ingredient:
    """A recipe ingredient."""
    name: str
    quantity: float
    unit: str
    notes: str = ""


@dataclass
class Recipe:
    """A complete recipe with metadata and nutrition."""
    id: Optional[int]
    title: str
    source: str  # e.g., "seed", "spoonacular", "edamam", "user"
    source_url: str = ""
    servings: int = 1
    prep_time_minutes: int = 0
    cook_time_minutes: int = 0
    meal_types: list = field(default_factory=list)  # ["breakfast", "lunch", "dinner"]
    cuisine: str = ""
    ingredients: list = field(default_factory=list)  # List[Ingredient]
    instructions: list = field(default_factory=list)  # List[str]
    nutrition: Optional[Nutrition] = None  # Per serving
    created_at: Optional[datetime] = None


@dataclass
class UserProfile:
    """User profile with physical attributes and goals."""
    id: Optional[int]
    name: str
    age: int
    weight_kg: float
    height_cm: float
    sex: str  # "male" or "female"
    activity_level: str  # sedentary, lightly_active, etc.
    goal: str  # lose_fat, cut, maintain, build_muscle, recomp
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class MacroTargets:
    """Daily macro targets calculated for a user."""
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    bmr: float
    tdee: float


@dataclass
class MealPlanEntry:
    """A single meal in a meal plan."""
    id: Optional[int]
    meal_plan_id: int
    day_of_week: int  # 0=Monday, 6=Sunday
    meal_type: str  # breakfast, lunch, dinner
    recipe_id: int
    servings: float = 1.0
    recipe: Optional[Recipe] = None  # Populated on load


@dataclass
class MealPlan:
    """A weekly meal plan."""
    id: Optional[int]
    user_id: int
    week_start_date: date
    entries: list = field(default_factory=list)  # List[MealPlanEntry]
    created_at: Optional[datetime] = None


@dataclass
class MealLog:
    """A logged/consumed meal."""
    id: Optional[int]
    user_id: int
    recipe_id: int
    meal_type: str
    servings: float
    logged_at: datetime
    recipe: Optional[Recipe] = None  # Populated on load


@dataclass
class NutritionSummary:
    """Aggregated nutrition for a time period."""
    period_label: str
    total_nutrition: Nutrition
    num_meals: int
    num_days: int
    target: Optional[MacroTargets] = None

    @property
    def daily_average(self) -> Nutrition:
        if self.num_days == 0:
            return Nutrition.zero()
        return self.total_nutrition.scaled(1.0 / self.num_days)

    def adherence_pct(self) -> Optional[dict]:
        """How close daily average is to targets (100% = perfect)."""
        if not self.target or self.num_days == 0:
            return None
        avg = self.daily_average
        t = self.target

        def pct(actual, target):
            if target == 0:
                return 100.0
            return max(0, 100 - abs(actual - target) / target * 100)

        return {
            "calories": round(pct(avg.calories, t.calories), 1),
            "protein": round(pct(avg.protein_g, t.protein_g), 1),
            "carbs": round(pct(avg.carbs_g, t.carbs_g), 1),
            "fat": round(pct(avg.fat_g, t.fat_g), 1),
        }
