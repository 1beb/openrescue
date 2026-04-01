from dataclasses import dataclass, field
from importlib.resources import files
from pathlib import Path

import yaml


@dataclass
class ServerConfig:
    loki_url: str
    mimir_url: str


@dataclass
class TrackingConfig:
    poll_interval_seconds: int = 5
    idle_threshold_seconds: int = 300


@dataclass
class ProjectsConfig:
    base_paths: list[str] = field(default_factory=list)


@dataclass
class CategoriesConfig:
    very_productive: list[str] = field(default_factory=list)
    productive: list[str] = field(default_factory=list)
    distracting: list[str] = field(default_factory=list)
    very_distracting: list[str] = field(default_factory=list)


@dataclass
class Config:
    server: ServerConfig
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    projects: ProjectsConfig = field(default_factory=ProjectsConfig)
    categories: CategoriesConfig = field(default_factory=CategoriesConfig)


def _load_default_categories() -> dict:
    default_path = files("openrescue").joinpath("default_categories.yml")
    with open(str(default_path)) as f:
        return yaml.safe_load(f)


def load_config(path: Path) -> Config:
    with open(path) as f:
        raw = yaml.safe_load(f)

    server = ServerConfig(**raw["server"])
    tracking = TrackingConfig(**raw.get("tracking", {}))
    projects = ProjectsConfig(**raw.get("projects", {}))

    defaults = _load_default_categories()
    user_cats = raw.get("categories", {})
    merged = {
        "very_productive": user_cats.get("very_productive", defaults.get("very_productive", [])),
        "productive": user_cats.get("productive", defaults.get("productive", [])),
        "distracting": user_cats.get("distracting", defaults.get("distracting", [])),
        "very_distracting": user_cats.get("very_distracting", defaults.get("very_distracting", [])),
    }
    categories = CategoriesConfig(**merged)

    return Config(server=server, tracking=tracking, projects=projects, categories=categories)
