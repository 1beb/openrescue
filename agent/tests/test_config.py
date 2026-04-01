import tempfile
from pathlib import Path

import yaml

from openrescue.config import load_config, Config


def test_load_config_from_file():
    raw = {
        "server": {
            "loki_url": "http://localhost:3100",
            "mimir_url": "http://localhost:9009",
        },
        "tracking": {
            "poll_interval_seconds": 5,
            "idle_threshold_seconds": 300,
        },
        "projects": {
            "base_paths": ["~/projects"],
        },
        "categories": {
            "very_productive": ["neovim"],
            "productive": ["code"],
            "distracting": ["slack"],
            "very_distracting": ["reddit.com"],
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(raw, f)
        path = f.name

    config = load_config(Path(path))

    assert config.server.loki_url == "http://localhost:3100"
    assert config.tracking.poll_interval_seconds == 5
    assert "~/projects" in config.projects.base_paths
    assert "neovim" in config.categories.very_productive


def test_load_config_defaults():
    raw = {"server": {"loki_url": "http://localhost:3100", "mimir_url": "http://localhost:9009"}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(raw, f)
        path = f.name

    config = load_config(Path(path))

    assert config.tracking.poll_interval_seconds == 5
    assert config.tracking.idle_threshold_seconds == 300
    assert len(config.categories.very_productive) > 0


def test_load_config_five_level_categories():
    raw = {
        "server": {"loki_url": "http://localhost:3100", "mimir_url": "http://localhost:9009"},
        "categories": {
            "very_productive": ["code", "neovim"],
            "productive": ["github.com"],
            "distracting": ["slack"],
            "very_distracting": ["reddit.com"],
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(raw, f)
        path = f.name

    config = load_config(Path(path))

    assert config.categories.very_productive == ["code", "neovim"]
    assert config.categories.productive == ["github.com"]
    assert config.categories.distracting == ["slack"]
    assert config.categories.very_distracting == ["reddit.com"]


def test_default_categories_loaded_when_no_user_categories():
    raw = {"server": {"loki_url": "http://localhost:3100", "mimir_url": "http://localhost:9009"}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(raw, f)
        path = f.name

    config = load_config(Path(path))

    # Should have defaults loaded, not empty lists
    assert len(config.categories.very_productive) > 0
    assert len(config.categories.very_distracting) > 0


def test_user_categories_override_defaults():
    raw = {
        "server": {"loki_url": "http://localhost:3100", "mimir_url": "http://localhost:9009"},
        "categories": {
            "very_productive": ["my-custom-app"],
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(raw, f)
        path = f.name

    config = load_config(Path(path))

    # User-specified categories replace defaults for that level
    assert config.categories.very_productive == ["my-custom-app"]
    # Other levels still get defaults
    assert len(config.categories.very_distracting) > 0
