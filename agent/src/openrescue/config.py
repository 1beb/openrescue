from dataclasses import dataclass, field
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
    productive: list[str] = field(default_factory=list)
    neutral: list[str] = field(default_factory=list)
    distracting: list[str] = field(default_factory=list)


@dataclass
class Config:
    server: ServerConfig
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    projects: ProjectsConfig = field(default_factory=ProjectsConfig)
    categories: CategoriesConfig = field(default_factory=CategoriesConfig)


def load_config(path: Path) -> Config:
    with open(path) as f:
        raw = yaml.safe_load(f)

    server = ServerConfig(**raw["server"])
    tracking = TrackingConfig(**raw.get("tracking", {}))
    projects = ProjectsConfig(**raw.get("projects", {}))
    categories = CategoriesConfig(**raw.get("categories", {}))

    return Config(server=server, tracking=tracking, projects=projects, categories=categories)
