from openrescue.categorizer import categorize
from openrescue.config import CategoriesConfig


def test_categorize_by_app_name():
    cats = CategoriesConfig(
        very_productive=[],
        productive=["code", "terminal"],
        distracting=["reddit.com"],
        very_distracting=[],
    )
    assert categorize("Code", "main.py - VS Code", cats) == "productive"
    assert categorize("Slack", "general - Slack", cats) == "uncategorized"


def test_categorize_by_title():
    cats = CategoriesConfig(
        very_productive=[],
        productive=[],
        distracting=["reddit.com", "youtube.com"],
        very_distracting=[],
    )
    assert categorize("Firefox", "r/linux - reddit.com - Firefox", cats) == "distracting"
    assert categorize("Firefox", "YouTube - Firefox", cats) == "distracting"


def test_categorize_unknown():
    cats = CategoriesConfig(very_productive=[], productive=["code"], distracting=[], very_distracting=[])
    assert categorize("SomeApp", "some title", cats) == "uncategorized"
