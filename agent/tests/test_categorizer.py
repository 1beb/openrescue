from openrescue.categorizer import categorize
from openrescue.config import CategoriesConfig


def _make_cats(**kwargs):
    defaults = dict(very_productive=[], productive=[], distracting=[], very_distracting=[])
    defaults.update(kwargs)
    return CategoriesConfig(**defaults)


def test_very_productive_match():
    cats = _make_cats(very_productive=["code", "terminal"])
    assert categorize("Code", "main.py - VS Code", cats) == "very_productive"


def test_productive_match():
    cats = _make_cats(productive=["github.com"])
    assert categorize("Firefox", "Issues - github.com", cats) == "productive"


def test_distracting_match():
    cats = _make_cats(distracting=["slack"])
    assert categorize("Slack", "general - Slack", cats) == "distracting"


def test_very_distracting_match():
    cats = _make_cats(very_distracting=["reddit.com", "youtube.com"])
    assert categorize("Firefox", "r/linux - reddit.com", cats) == "very_distracting"
    assert categorize("Firefox", "YouTube - Firefox", cats) == "very_distracting"


def test_priority_order():
    """very_productive wins over productive wins over distracting wins over very_distracting."""
    cats = _make_cats(
        very_productive=["code"],
        productive=["code"],
        distracting=["code"],
        very_distracting=["code"],
    )
    assert categorize("Code", "test", cats) == "very_productive"


def test_uncategorized_fallback():
    cats = _make_cats(very_productive=["code"])
    assert categorize("SomeApp", "some title", cats) == "uncategorized"


def test_domain_name_matching():
    cats = _make_cats(very_distracting=["youtube.com"])
    assert categorize("Firefox", "YouTube - Firefox", cats) == "very_distracting"
