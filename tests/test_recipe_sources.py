"""Tests for NYT recipe URL discovery and pagination (no network)."""

import unittest
from unittest.mock import patch

from meal_planner.recipe_sources import _discover_nyt_recipe_urls, _nyt_page_url

TOPIC = "https://cooking.nytimes.com/topics/dinner-recipes"


class FakeResponse:
    def __init__(self, text="", status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code != 200:
            raise RuntimeError(f"HTTP {self.status_code}")


def page_html(*slugs):
    return "".join(f'<a href="/recipes/{s}?foo=1">x</a>' for s in slugs) + '<a href="/about">a</a>'


def fake_get(pages):
    """pages maps page number -> FakeResponse; records requested URLs."""
    calls = []

    def get(url, **kwargs):
        calls.append(url)
        page = int(url.split("page=")[1]) if "page=" in url else 1
        return pages.get(page, FakeResponse(status_code=404))

    return get, calls


class TestNytPagination(unittest.TestCase):
    def test_page_url(self):
        self.assertEqual(_nyt_page_url(TOPIC, 1), TOPIC)
        self.assertEqual(_nyt_page_url(TOPIC, 3), TOPIC + "?page=3")
        self.assertEqual(_nyt_page_url(TOPIC + "?q=a&page=2", 4), TOPIC + "?q=a&page=4")

    def test_single_page_by_default(self):
        get, calls = fake_get({1: FakeResponse(page_html("1-a", "2-b", "1-a"))})
        with patch("requests.get", get):
            urls = _discover_nyt_recipe_urls(TOPIC)
        self.assertEqual(urls, [
            "https://cooking.nytimes.com/recipes/1-a",
            "https://cooking.nytimes.com/recipes/2-b",
        ])
        self.assertEqual(calls, [TOPIC])

    def test_follows_pages_until_no_new_links(self):
        get, calls = fake_get({
            1: FakeResponse(page_html("1-a", "2-b")),
            2: FakeResponse(page_html("2-b", "3-c")),
            3: FakeResponse(page_html("3-c")),  # repeats: end of listing
            4: FakeResponse(page_html("4-d")),
        })
        with patch("requests.get", get):
            urls = _discover_nyt_recipe_urls(TOPIC, max_pages=10, delay=0)
        self.assertEqual([u.rsplit("/", 1)[1] for u in urls], ["1-a", "2-b", "3-c"])
        self.assertEqual(calls, [TOPIC, TOPIC + "?page=2", TOPIC + "?page=3"])

    def test_stops_on_http_error_and_respects_max_pages(self):
        get, calls = fake_get({1: FakeResponse(page_html("1-a")), 2: FakeResponse(page_html("2-b"))})
        with patch("requests.get", get):
            self.assertEqual(len(_discover_nyt_recipe_urls(TOPIC, max_pages=10, delay=0)), 2)
            self.assertEqual(len(calls), 3)  # page 3 returned 404
            self.assertEqual(len(_discover_nyt_recipe_urls(TOPIC, max_pages=1, delay=0)), 1)

    def test_starts_from_page_in_url(self):
        get, calls = fake_get({2: FakeResponse(page_html("2-b")), 3: FakeResponse(page_html("3-c"))})
        with patch("requests.get", get):
            urls = _discover_nyt_recipe_urls(TOPIC + "?page=2", max_pages=2, delay=0)
        self.assertEqual(len(urls), 2)
        self.assertEqual(calls, [TOPIC + "?page=2", TOPIC + "?page=3"])

    def test_first_page_failure_raises(self):
        get, _ = fake_get({})
        with patch("requests.get", get):
            with self.assertRaises(RuntimeError):
                _discover_nyt_recipe_urls(TOPIC, max_pages=3, delay=0)


if __name__ == "__main__":
    unittest.main()
