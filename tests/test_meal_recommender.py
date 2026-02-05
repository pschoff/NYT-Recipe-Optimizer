"""Tests for the meal recommendation engine."""

import unittest

from meal_planner.models import MacroTargets, Nutrition, Recipe
from meal_planner.recommender import (
    _meal_target,
    _optimal_servings,
    _recipe_score,
    recommend_daily_meals,
    score_daily_plan,
)


def _make_recipe(id, title, cal, protein, carbs, fat, meal_types):
    return Recipe(
        id=id, title=title, source="test", meal_types=meal_types,
        nutrition=Nutrition(cal, protein, carbs, fat),
    )


SAMPLE_RECIPES = [
    _make_recipe(1, "Oatmeal", 310, 9, 55, 6, ["breakfast"]),
    _make_recipe(2, "Yogurt Parfait", 280, 24, 38, 4, ["breakfast"]),
    _make_recipe(3, "Eggs + Toast", 420, 26, 30, 22, ["breakfast"]),
    _make_recipe(4, "Chicken Salad", 420, 42, 15, 22, ["lunch"]),
    _make_recipe(5, "Turkey Wrap", 390, 32, 30, 17, ["lunch"]),
    _make_recipe(6, "Lentil Soup", 340, 22, 52, 5, ["lunch"]),
    _make_recipe(7, "Salmon + Veggies", 450, 40, 15, 26, ["dinner"]),
    _make_recipe(8, "Chicken Stir-Fry", 460, 42, 40, 14, ["dinner"]),
    _make_recipe(9, "Beef Tacos", 470, 38, 35, 20, ["dinner"]),
    _make_recipe(10, "Tofu Stir-Fry", 420, 28, 40, 18, ["dinner"]),
]

TARGETS = MacroTargets(
    calories=2200, protein_g=165, carbs_g=220, fat_g=73, bmr=1700, tdee=2200,
)


class TestRecipeScoring(unittest.TestCase):
    def test_perfect_match_scores_highest(self):
        # A recipe that perfectly matches the target should score 1.0
        target = Nutrition(400, 30, 50, 15)
        perfect = Recipe(
            id=99, title="Perfect", source="test", meal_types=["lunch"],
            nutrition=Nutrition(400, 30, 50, 15),
        )
        score = _recipe_score(perfect, target)
        self.assertAlmostEqual(score, 1.0)

    def test_no_nutrition_scores_zero(self):
        target = Nutrition(400, 30, 50, 15)
        recipe = Recipe(id=99, title="No Nutr", source="test", meal_types=["lunch"])
        self.assertEqual(_recipe_score(recipe, target), 0.0)

    def test_closer_recipe_scores_higher(self):
        target = Nutrition(400, 30, 50, 15)
        close = _make_recipe(99, "Close", 410, 28, 48, 16, ["lunch"])
        far = _make_recipe(100, "Far", 600, 10, 80, 30, ["lunch"])
        self.assertGreater(_recipe_score(close, target), _recipe_score(far, target))

    def test_servings_scaling(self):
        target = Nutrition(800, 60, 100, 30)
        recipe = _make_recipe(99, "Half", 400, 30, 50, 15, ["lunch"])
        score_1x = _recipe_score(recipe, target, servings=1.0)
        score_2x = _recipe_score(recipe, target, servings=2.0)
        self.assertGreater(score_2x, score_1x)


class TestMealTarget(unittest.TestCase):
    def test_breakfast_fraction(self):
        target = _meal_target(TARGETS, "breakfast")
        # Breakfast = 25% of daily
        self.assertAlmostEqual(target.calories, 2200 * 0.25)
        self.assertAlmostEqual(target.protein_g, 165 * 0.25)

    def test_dinner_fraction(self):
        target = _meal_target(TARGETS, "dinner")
        self.assertAlmostEqual(target.calories, 2200 * 0.40)


class TestOptimalServings(unittest.TestCase):
    def test_optimal_servings_scales_to_target(self):
        recipe = _make_recipe(1, "Test", 400, 30, 50, 15, ["lunch"])
        target = Nutrition(800, 60, 100, 30)
        servings = _optimal_servings(recipe, target)
        self.assertEqual(servings, 2.0)

    def test_clamped_to_minimum(self):
        recipe = _make_recipe(1, "Big", 2000, 100, 200, 80, ["dinner"])
        target = Nutrition(400, 30, 50, 15)
        servings = _optimal_servings(recipe, target)
        self.assertEqual(servings, 0.5)

    def test_clamped_to_maximum(self):
        recipe = _make_recipe(1, "Tiny", 100, 5, 15, 2, ["lunch"])
        target = Nutrition(800, 60, 100, 30)
        servings = _optimal_servings(recipe, target)
        self.assertEqual(servings, 2.0)


class TestDailyRecommendation(unittest.TestCase):
    def test_returns_three_meals(self):
        meals = recommend_daily_meals(TARGETS, SAMPLE_RECIPES)
        self.assertEqual(len(meals), 3)
        types = {m[0] for m in meals}
        self.assertEqual(types, {"breakfast", "lunch", "dinner"})

    def test_no_duplicate_recipes_in_day(self):
        meals = recommend_daily_meals(TARGETS, SAMPLE_RECIPES)
        ids = [m[1].id for m in meals]
        self.assertEqual(len(ids), len(set(ids)))

    def test_variety_constraint_excludes_recipes(self):
        excluded = {1, 2, 3}  # Exclude all breakfast options
        meals = recommend_daily_meals(TARGETS, SAMPLE_RECIPES, recently_used_ids=excluded)
        # Should still find 3 meals (will relax constraints if needed)
        self.assertEqual(len(meals), 3)

    def test_empty_recipe_list(self):
        meals = recommend_daily_meals(TARGETS, [])
        self.assertEqual(len(meals), 0)


class TestDailyPlanScoring(unittest.TestCase):
    def test_score_returns_deviation(self):
        meals = [
            ("breakfast", SAMPLE_RECIPES[0], 1.0),
            ("lunch", SAMPLE_RECIPES[3], 1.0),
            ("dinner", SAMPLE_RECIPES[6], 1.0),
        ]
        result = score_daily_plan(meals, TARGETS)
        self.assertIn("total_nutrition", result)
        self.assertIn("deviation", result)
        self.assertIn("calories", result["deviation"])


if __name__ == "__main__":
    unittest.main()
