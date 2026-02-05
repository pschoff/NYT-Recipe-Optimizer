"""Tests for data models."""

import unittest

from meal_planner.models import MacroTargets, Nutrition, NutritionSummary


class TestNutrition(unittest.TestCase):
    def test_scaled(self):
        n = Nutrition(400, 30, 50, 15)
        s = n.scaled(2.0)
        self.assertEqual(s.calories, 800)
        self.assertEqual(s.protein_g, 60)
        self.assertEqual(s.carbs_g, 100)
        self.assertEqual(s.fat_g, 30)

    def test_add(self):
        a = Nutrition(300, 20, 40, 10)
        b = Nutrition(500, 35, 60, 20)
        result = a + b
        self.assertEqual(result.calories, 800)
        self.assertEqual(result.protein_g, 55)
        self.assertEqual(result.carbs_g, 100)
        self.assertEqual(result.fat_g, 30)

    def test_zero(self):
        z = Nutrition.zero()
        self.assertEqual(z.calories, 0)
        self.assertEqual(z.protein_g, 0)

    def test_macro_percentages(self):
        # 30g protein * 4 = 120 cal, 50g carbs * 4 = 200 cal, 15g fat * 9 = 135 cal
        # Total from macros = 455, but we use the calorie field
        n = Nutrition(455, 30, 50, 15)
        pcts = n.macro_percentages()
        self.assertAlmostEqual(pcts["protein"], 120 / 455 * 100, places=1)
        self.assertAlmostEqual(pcts["carbs"], 200 / 455 * 100, places=1)
        self.assertAlmostEqual(pcts["fat"], 135 / 455 * 100, places=1)

    def test_macro_percentages_zero_calories(self):
        n = Nutrition(0, 0, 0, 0)
        pcts = n.macro_percentages()
        self.assertEqual(pcts["protein"], 0)


class TestNutritionSummary(unittest.TestCase):
    def test_daily_average(self):
        total = Nutrition(3000, 225, 300, 100)
        summary = NutritionSummary("test", total, num_meals=9, num_days=3)
        avg = summary.daily_average
        self.assertEqual(avg.calories, 1000)
        self.assertEqual(avg.protein_g, 75)

    def test_adherence(self):
        total = Nutrition(2000, 150, 200, 70)
        target = MacroTargets(2000, 150, 200, 70, 1600, 2000)
        summary = NutritionSummary("test", total, num_meals=3, num_days=1, target=target)
        adherence = summary.adherence_pct()
        self.assertEqual(adherence["calories"], 100.0)
        self.assertEqual(adherence["protein"], 100.0)

    def test_adherence_no_target(self):
        total = Nutrition(2000, 150, 200, 70)
        summary = NutritionSummary("test", total, num_meals=3, num_days=1)
        self.assertIsNone(summary.adherence_pct())


if __name__ == "__main__":
    unittest.main()
