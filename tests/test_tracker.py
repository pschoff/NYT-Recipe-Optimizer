"""Tests for the tracking and analytics module."""

import os
import tempfile
import unittest
from datetime import date, datetime

from meal_planner.db import init_db
from meal_planner.models import Nutrition, Recipe
from meal_planner.recipe_store import save_recipe
from meal_planner.tracker import (
    daily_summary,
    log_meal,
    monthly_summary,
    weekly_summary,
    yearly_summary,
)


class TestTracker(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        init_db(self.db_path)

        # Create a test user
        from meal_planner.db import get_connection
        with get_connection(self.db_path) as conn:
            conn.execute(
                """INSERT INTO users (name, age, weight_kg, height_cm, sex, activity_level, goal)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("Test User", 30, 80, 180, "male", "moderately_active", "maintain"),
            )

        # Create test recipes
        self.recipe1_id = save_recipe(Recipe(
            id=None, title="Test Breakfast", source="test",
            meal_types=["breakfast"],
            nutrition=Nutrition(300, 20, 40, 8),
        ), self.db_path)

        self.recipe2_id = save_recipe(Recipe(
            id=None, title="Test Lunch", source="test",
            meal_types=["lunch"],
            nutrition=Nutrition(500, 35, 50, 20),
        ), self.db_path)

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_log_meal(self):
        log_id = log_meal(1, self.recipe1_id, "breakfast", 1.0,
                          datetime(2026, 2, 5, 8, 0), self.db_path)
        self.assertIsNotNone(log_id)
        self.assertGreater(log_id, 0)

    def test_daily_summary(self):
        log_meal(1, self.recipe1_id, "breakfast", 1.0,
                 datetime(2026, 2, 5, 8, 0), self.db_path)
        log_meal(1, self.recipe2_id, "lunch", 1.0,
                 datetime(2026, 2, 5, 12, 0), self.db_path)

        summary = daily_summary(1, date(2026, 2, 5), db_path=self.db_path)
        self.assertEqual(summary.num_meals, 2)
        self.assertEqual(summary.num_days, 1)
        self.assertAlmostEqual(summary.total_nutrition.calories, 800)
        self.assertAlmostEqual(summary.total_nutrition.protein_g, 55)

    def test_daily_summary_empty(self):
        summary = daily_summary(1, date(2026, 2, 10), db_path=self.db_path)
        self.assertEqual(summary.num_meals, 0)

    def test_weekly_summary(self):
        # Log meals on Monday and Wednesday
        log_meal(1, self.recipe1_id, "breakfast", 1.0,
                 datetime(2026, 2, 2, 8, 0), self.db_path)  # Monday
        log_meal(1, self.recipe2_id, "lunch", 1.0,
                 datetime(2026, 2, 4, 12, 0), self.db_path)  # Wednesday

        summary = weekly_summary(1, date(2026, 2, 2), db_path=self.db_path)
        self.assertEqual(summary.num_meals, 2)
        self.assertEqual(summary.num_days, 2)

    def test_monthly_summary(self):
        log_meal(1, self.recipe1_id, "breakfast", 1.0,
                 datetime(2026, 2, 5, 8, 0), self.db_path)

        summary = monthly_summary(1, 2026, 2, db_path=self.db_path)
        self.assertEqual(summary.num_meals, 1)

    def test_yearly_summary(self):
        log_meal(1, self.recipe1_id, "breakfast", 1.0,
                 datetime(2026, 2, 5, 8, 0), self.db_path)

        summary = yearly_summary(1, 2026, db_path=self.db_path)
        self.assertEqual(summary.num_meals, 1)

    def test_serving_scaling(self):
        log_meal(1, self.recipe1_id, "breakfast", 2.0,
                 datetime(2026, 2, 5, 8, 0), self.db_path)

        summary = daily_summary(1, date(2026, 2, 5), db_path=self.db_path)
        self.assertAlmostEqual(summary.total_nutrition.calories, 600)  # 300 * 2
        self.assertAlmostEqual(summary.total_nutrition.protein_g, 40)  # 20 * 2


if __name__ == "__main__":
    unittest.main()
