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
            "productive": ["code"],
            "neutral": ["slack"],
            "distracting": ["reddit.com"],
        },
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(raw, f)
        path = f.name

    config = load_config(Path(path))

    assert config.server.loki_url == "http://localhost:3100"
    assert config.tracking.poll_interval_seconds == 5
    assert "~/projects" in config.projects.base_paths
    assert "code" in config.categories.productive


def test_load_config_defaults():
    raw = {"server": {"loki_url": "http://localhost:3100", "mimir_url": "http://localhost:9009"}}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(raw, f)
        path = f.name

    config = load_config(Path(path))

    assert config.tracking.poll_interval_seconds == 5
    assert config.tracking.idle_threshold_seconds == 300
    assert config.categories.productive == []
