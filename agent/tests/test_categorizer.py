from openrescue.categorizer import categorize
from openrescue.config import CategoriesConfig


def test_categorize_by_app_name():
    cats = CategoriesConfig(
        productive=["code", "terminal"],
        neutral=["slack"],
        distracting=["reddit.com"],
    )
    assert categorize("Code", "main.py - VS Code", cats) == "productive"
    assert categorize("Slack", "general - Slack", cats) == "neutral"


def test_categorize_by_title():
    cats = CategoriesConfig(
        productive=[],
        neutral=[],
        distracting=["reddit.com", "youtube.com"],
    )
    assert categorize("Firefox", "r/linux - reddit.com - Firefox", cats) == "distracting"
    assert categorize("Firefox", "YouTube - Firefox", cats) == "distracting"


def test_categorize_unknown():
    cats = CategoriesConfig(productive=["code"], neutral=[], distracting=[])
    assert categorize("SomeApp", "some title", cats) == "uncategorized"
