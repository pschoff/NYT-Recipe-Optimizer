"""Tests for the macro calculation engine."""

import unittest

from meal_planner.macro_calculator import calculate_bmr, calculate_macro_targets, calculate_tdee
from meal_planner.models import UserProfile


class TestBMR(unittest.TestCase):
    def test_bmr_male(self):
        profile = UserProfile(
            id=None, name="Test", age=30, weight_kg=80,
            height_cm=180, sex="male", activity_level="sedentary", goal="maintain",
        )
        bmr = calculate_bmr(profile)
        # 10*80 + 6.25*180 - 5*30 + 5 = 800 + 1125 - 150 + 5 = 1780
        self.assertEqual(bmr, 1780)

    def test_bmr_female(self):
        profile = UserProfile(
            id=None, name="Test", age=25, weight_kg=60,
            height_cm=165, sex="female", activity_level="sedentary", goal="maintain",
        )
        bmr = calculate_bmr(profile)
        # 10*60 + 6.25*165 - 5*25 - 161 = 600 + 1031.25 - 125 - 161 = 1345.25
        self.assertAlmostEqual(bmr, 1345.25)

    def test_bmr_increases_with_weight(self):
        base = UserProfile(
            id=None, name="T", age=30, weight_kg=70,
            height_cm=175, sex="male", activity_level="sedentary", goal="maintain",
        )
        heavier = UserProfile(
            id=None, name="T", age=30, weight_kg=90,
            height_cm=175, sex="male", activity_level="sedentary", goal="maintain",
        )
        self.assertGreater(calculate_bmr(heavier), calculate_bmr(base))


class TestTDEE(unittest.TestCase):
    def test_sedentary(self):
        self.assertAlmostEqual(calculate_tdee(1780, "sedentary"), 1780 * 1.2)

    def test_very_active(self):
        self.assertAlmostEqual(calculate_tdee(1780, "very_active"), 1780 * 1.725)

    def test_unknown_defaults_to_sedentary(self):
        self.assertAlmostEqual(calculate_tdee(1780, "unknown"), 1780 * 1.2)


class TestMacroTargets(unittest.TestCase):
    def test_build_muscle_surplus(self):
        profile = UserProfile(
            id=None, name="Test", age=30, weight_kg=80,
            height_cm=180, sex="male", activity_level="moderately_active",
            goal="build_muscle",
        )
        targets = calculate_macro_targets(profile)
        # TDEE = 1780 * 1.55 = 2759, target = 2759 * 1.10 = 3034.9
        self.assertAlmostEqual(targets.calories, 3035, delta=1)
        # Protein: 30% of 3035 / 4 = 228g
        self.assertAlmostEqual(targets.protein_g, 228, delta=1)

    def test_lose_fat_deficit(self):
        profile = UserProfile(
            id=None, name="Test", age=30, weight_kg=80,
            height_cm=180, sex="male", activity_level="moderately_active",
            goal="lose_fat",
        )
        targets = calculate_macro_targets(profile)
        # TDEE = 2759, target = 2759 * 0.80 = 2207.2
        self.assertAlmostEqual(targets.calories, 2207, delta=1)
        # Protein: 40% of 2207 / 4 = 221g
        self.assertAlmostEqual(targets.protein_g, 221, delta=1)

    def test_macros_sum_to_total_calories(self):
        profile = UserProfile(
            id=None, name="Test", age=25, weight_kg=65,
            height_cm=170, sex="female", activity_level="lightly_active",
            goal="maintain",
        )
        targets = calculate_macro_targets(profile)
        macro_calories = targets.protein_g * 4 + targets.carbs_g * 4 + targets.fat_g * 9
        # Allow small rounding error
        self.assertAlmostEqual(macro_calories, targets.calories, delta=15)


class TestMacroTargetsAllGoals(unittest.TestCase):
    def test_all_goals_produce_valid_targets(self):
        goals = ["lose_fat", "cut", "maintain", "build_muscle", "recomp"]
        for goal in goals:
            profile = UserProfile(
                id=None, name="Test", age=30, weight_kg=75,
                height_cm=175, sex="male", activity_level="moderately_active",
                goal=goal,
            )
            targets = calculate_macro_targets(profile)
            self.assertGreater(targets.calories, 0, f"Failed for goal={goal}")
            self.assertGreater(targets.protein_g, 0, f"Failed for goal={goal}")
            self.assertGreater(targets.carbs_g, 0, f"Failed for goal={goal}")
            self.assertGreater(targets.fat_g, 0, f"Failed for goal={goal}")


if __name__ == "__main__":
    unittest.main()
