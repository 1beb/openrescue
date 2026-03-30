# OpenRescue MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a FOSS RescueTime alternative that tracks desktop activity and ships data to a centralized LGTM stack over Tailscale.

**Architecture:** A lightweight Python daemon runs on each Linux machine, polling the active window (title, app name, PID, CWD) and idle state every 5 seconds. It ships raw activity events to Loki and aggregated metrics to Mimir on a central server (server, SERVER_HOST). Grafana provides dashboards. The daemon is packaged as a .deb with a systemd user service.

**Tech Stack:** Python 3.11+, Docker Compose (Grafana/Loki/Mimir), systemd, fpm (.deb packaging), xdotool/python-xlib (X11), swaymsg (Wayland), prometheus-client, requests

---

### Task 1: Server - Docker Compose for LGTM Stack

**Files:**
- Create: `server/docker-compose.yml`
- Create: `server/config/grafana-datasources.yml`
- Create: `server/config/loki-config.yml`
- Create: `server/config/mimir-config.yml`

**Step 1: Create Loki config**

```yaml
# server/config/loki-config.yml
auth_enabled: false

server:
  http_listen_port: 3100

common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2020-10-24
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

limits_config:
  reject_old_samples: false
```

**Step 2: Create Mimir config**

```yaml
# server/config/mimir-config.yml
multitenancy_enabled: false

blocks_storage:
  backend: filesystem
  filesystem:
    dir: /data/blocks
  bucket_store:
    sync_dir: /data/tsdb-sync

compactor:
  data_dir: /data/compactor
  sharding_ring:
    kvstore:
      store: memberlist

store_gateway:
  sharding_ring:
    replication_factor: 1

ingester:
  ring:
    replication_factor: 1
    kvstore:
      store: memberlist

ruler_storage:
  backend: filesystem
  filesystem:
    dir: /data/rules
```

**Step 3: Create Grafana datasources provisioning**

```yaml
# server/config/grafana-datasources.yml
apiVersion: 1
datasources:
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    isDefault: false
  - name: Mimir
    type: prometheus
    access: proxy
    url: http://mimir:9009/prometheus
    isDefault: true
```

**Step 4: Create Docker Compose file**

```yaml
# server/docker-compose.yml
services:
  grafana:
    image: grafana/grafana:11.6.0
    ports:
      - "3000:3000"
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
      - GF_AUTH_DISABLE_LOGIN_FORM=true
    volumes:
      - grafana-data:/var/lib/grafana
      - ./config/grafana-datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml
    depends_on:
      - loki
      - mimir
    restart: unless-stopped

  loki:
    image: grafana/loki:3.4.2
    ports:
      - "3100:3100"
    command: -config.file=/etc/loki/config.yml
    volumes:
      - ./config/loki-config.yml:/etc/loki/config.yml
      - loki-data:/loki
    restart: unless-stopped

  mimir:
    image: grafana/mimir:2.15.0
    ports:
      - "9009:9009"
    command:
      - -config.file=/etc/mimir/config.yml
      - -target=all
      - -server.http-listen-port=9009
    volumes:
      - ./config/mimir-config.yml:/etc/mimir/config.yml
      - mimir-data:/data
    restart: unless-stopped

volumes:
  grafana-data:
  loki-data:
  mimir-data:
```

**Step 5: Deploy to server and verify**

```bash
scp -r server/ user@server:~/openrescue/
ssh user@server "cd ~/openrescue/server && docker compose up -d"
```

Verify:
```bash
ssh user@server "curl -s http://localhost:3100/ready"   # Loki
ssh user@server "curl -s http://localhost:9009/ready"   # Mimir
ssh user@server "curl -s -o /dev/null -w '%{http_code}' http://localhost:3000"  # Grafana
```

Expected: `ready`, `ready`, `200`

**Step 6: Commit**

```bash
git add server/
git commit -m "add LGTM stack docker compose for server"
```

---

### Task 2: Agent - Project Setup and Config

**Files:**
- Create: `agent/pyproject.toml`
- Create: `agent/src/openrescue/__init__.py`
- Create: `agent/src/openrescue/config.py`
- Create: `agent/tests/__init__.py`
- Create: `agent/tests/test_config.py`
- Create: `agent/config.example.yml`

**Step 1: Create pyproject.toml**

```toml
# agent/pyproject.toml
[project]
name = "openrescue"
version = "0.1.0"
description = "FOSS desktop activity tracker with LGTM backend"
requires-python = ">=3.11"
dependencies = [
    "requests>=2.31",
    "pyyaml>=6.0",
    "prometheus-client>=0.21",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-mock>=3.12",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/openrescue"]

[project.scripts]
openrescue = "openrescue.main:main"
```

**Step 2: Create example config**

```yaml
# agent/config.example.yml
server:
  loki_url: "http://server:3100"
  mimir_url: "http://server:9009"

tracking:
  poll_interval_seconds: 5
  idle_threshold_seconds: 300

projects:
  base_paths:
    - "~/projects"
    - "~/work"

categories:
  productive:
    - "code"
    - "terminal"
    - "github.com"
  neutral:
    - "slack"
    - "email"
  distracting:
    - "reddit.com"
    - "youtube.com"
    - "twitter.com"
```

**Step 3: Write failing test for config loading**

```python
# agent/tests/test_config.py
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
```

**Step 4: Run test to verify it fails**

```bash
cd agent && uv venv && uv pip install -e ".[dev]" && uv run pytest tests/test_config.py -v
```

Expected: FAIL (module not found)

**Step 5: Implement config module**

```python
# agent/src/openrescue/__init__.py
```

```python
# agent/src/openrescue/config.py
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
```

**Step 6: Run tests to verify they pass**

```bash
cd agent && uv run pytest tests/test_config.py -v
```

Expected: 2 passed

**Step 7: Commit**

```bash
git add agent/
git commit -m "add agent project setup and config module"
```

---

### Task 3: Agent - Window Tracker (X11)

**Files:**
- Create: `agent/src/openrescue/tracker.py`
- Create: `agent/tests/test_tracker.py`

**Step 1: Write failing tests for window tracking**

```python
# agent/tests/test_tracker.py
import os
from unittest.mock import patch, MagicMock
from openrescue.tracker import get_active_window_x11, get_project_from_cwd, ActivityEvent


def test_get_active_window_x11(mocker):
    mocker.patch(
        "openrescue.tracker._run_cmd",
        side_effect=lambda cmd: {
            "xdotool getactivewindow": "12345",
            "xdotool getactivewindow getwindowname": "main.py - openrescue - Visual Studio Code",
            "xdotool getactivewindow getwindowpid": "9876",
            "xprop -id 12345 WM_CLASS": 'WM_CLASS(STRING) = "code", "Code"',
        }[" ".join(cmd)],
    )
    mocker.patch("os.readlink", return_value="/home/b/projects/openrescue")

    event = get_active_window_x11()

    assert event.window_title == "main.py - openrescue - Visual Studio Code"
    assert event.app_name == "Code"
    assert event.pid == 9876
    assert event.cwd == "/home/b/projects/openrescue"


def test_get_project_from_cwd():
    assert get_project_from_cwd("/home/b/projects/openrescue", ["~/projects"]) == "openrescue"
    assert get_project_from_cwd("/home/b/projects/openrescue/src", ["~/projects"]) == "openrescue"
    assert get_project_from_cwd("/usr/bin", ["~/projects"]) is None
    assert get_project_from_cwd(None, ["~/projects"]) is None


def test_get_project_from_title():
    from openrescue.tracker import get_project_from_title

    assert get_project_from_title("main.py - openrescue - Visual Studio Code") == "openrescue"
    assert get_project_from_title("~/projects/myapp: bash") == "myapp"
    assert get_project_from_title("Google - Firefox") is None
```

**Step 2: Run tests to verify they fail**

```bash
cd agent && uv run pytest tests/test_tracker.py -v
```

Expected: FAIL (module not found)

**Step 3: Implement tracker module**

```python
# agent/src/openrescue/tracker.py
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ActivityEvent:
    timestamp: float
    window_title: str
    app_name: str
    pid: int | None
    cwd: str | None
    project: str | None
    idle_seconds: float = 0.0


def _run_cmd(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, timeout=2).decode().strip()


def get_active_window_x11() -> ActivityEvent:
    try:
        wid = _run_cmd(["xdotool", "getactivewindow"])
        title = _run_cmd(["xdotool", "getactivewindow", "getwindowname"])
        pid_str = _run_cmd(["xdotool", "getactivewindow", "getwindowpid"])
        pid = int(pid_str) if pid_str else None

        xprop_out = _run_cmd(["xprop", "-id", wid, "WM_CLASS"])
        parts = xprop_out.split("=", 1)[-1].strip().replace('"', "").split(", ")
        app_name = parts[1] if len(parts) > 1 else parts[0]

        cwd = None
        if pid:
            try:
                cwd = os.readlink(f"/proc/{pid}/cwd")
            except OSError:
                pass

        return ActivityEvent(
            timestamp=time.time(),
            window_title=title,
            app_name=app_name,
            pid=pid,
            cwd=cwd,
            project=None,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        return ActivityEvent(
            timestamp=time.time(),
            window_title="unknown",
            app_name="unknown",
            pid=None,
            cwd=None,
            project=None,
        )


def get_project_from_cwd(cwd: str | None, base_paths: list[str]) -> str | None:
    if cwd is None:
        return None

    cwd_path = Path(cwd)
    for base in base_paths:
        expanded = Path(base).expanduser()
        try:
            rel = cwd_path.relative_to(expanded)
            parts = rel.parts
            if parts:
                return parts[0]
        except ValueError:
            continue
    return None


def get_project_from_title(title: str) -> str | None:
    # VS Code pattern: "file - project - Visual Studio Code"
    vscode_match = re.match(r".+ - (.+) - Visual Studio Code", title)
    if vscode_match:
        return vscode_match.group(1)

    # Terminal pattern: "~/projects/name: ..." or "/home/user/projects/name: ..."
    path_match = re.search(r"[~/]projects/([^/:\s]+)", title)
    if path_match:
        return path_match.group(1)

    return None


def get_idle_time_x11() -> float:
    try:
        ms = int(_run_cmd(["xprintidle"]))
        return ms / 1000.0
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        return 0.0
```

**Step 4: Run tests to verify they pass**

```bash
cd agent && uv run pytest tests/test_tracker.py -v
```

Expected: 3 passed

**Step 5: Commit**

```bash
git add agent/src/openrescue/tracker.py agent/tests/test_tracker.py
git commit -m "add window tracker with project detection"
```

---

### Task 4: Agent - Loki Shipper

**Files:**
- Create: `agent/src/openrescue/shipper.py`
- Create: `agent/tests/test_shipper.py`

**Step 1: Write failing test for Loki push**

```python
# agent/tests/test_shipper.py
import json
import time
from openrescue.shipper import LokiShipper
from openrescue.tracker import ActivityEvent


def test_loki_push_formats_correctly(mocker):
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.status_code = 204

    shipper = LokiShipper("http://localhost:3100")
    event = ActivityEvent(
        timestamp=1711700000.0,
        window_title="main.py - openrescue - VS Code",
        app_name="Code",
        pid=1234,
        cwd="/home/b/projects/openrescue",
        project="openrescue",
    )
    shipper.push_event(event, hostname="testhost")

    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[0][0] == "http://localhost:3100/loki/api/v1/push"

    payload = call_args[1]["json"]
    stream = payload["streams"][0]
    assert stream["stream"]["app"] == "Code"
    assert stream["stream"]["project"] == "openrescue"
    assert stream["stream"]["hostname"] == "testhost"


def test_loki_push_omits_none_project(mocker):
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.status_code = 204

    shipper = LokiShipper("http://localhost:3100")
    event = ActivityEvent(
        timestamp=1711700000.0,
        window_title="Google - Firefox",
        app_name="Firefox",
        pid=1234,
        cwd="/home/b",
        project=None,
    )
    shipper.push_event(event, hostname="testhost")

    payload = mock_post.call_args[1]["json"]
    stream = payload["streams"][0]
    assert "project" not in stream["stream"]
```

**Step 2: Run tests to verify they fail**

```bash
cd agent && uv run pytest tests/test_shipper.py -v
```

Expected: FAIL

**Step 3: Implement Loki shipper**

```python
# agent/src/openrescue/shipper.py
import json
import logging
import time

import requests

from openrescue.tracker import ActivityEvent

logger = logging.getLogger(__name__)


class LokiShipper:
    def __init__(self, loki_url: str):
        self.push_url = f"{loki_url}/loki/api/v1/push"

    def push_event(self, event: ActivityEvent, hostname: str) -> None:
        labels = {
            "job": "openrescue",
            "hostname": hostname,
            "app": event.app_name,
        }
        if event.project:
            labels["project"] = event.project

        log_line = json.dumps({
            "window_title": event.window_title,
            "pid": event.pid,
            "cwd": event.cwd,
            "idle_seconds": event.idle_seconds,
        })

        payload = {
            "streams": [{
                "stream": labels,
                "values": [[str(int(event.timestamp * 1e9)), log_line]],
            }]
        }

        try:
            resp = requests.post(self.push_url, json=payload, timeout=5)
            if resp.status_code not in (200, 204):
                logger.warning("Loki push failed: %s %s", resp.status_code, resp.text)
        except requests.RequestException as e:
            logger.warning("Loki push error: %s", e)
```

**Step 4: Run tests to verify they pass**

```bash
cd agent && uv run pytest tests/test_shipper.py -v
```

Expected: 2 passed

**Step 5: Commit**

```bash
git add agent/src/openrescue/shipper.py agent/tests/test_shipper.py
git commit -m "add Loki log shipper"
```

---

### Task 5: Agent - Metrics Exporter (Prometheus/Mimir)

**Files:**
- Create: `agent/src/openrescue/metrics.py`
- Create: `agent/tests/test_metrics.py`

**Step 1: Write failing test for metrics tracking**

```python
# agent/tests/test_metrics.py
from prometheus_client import CollectorRegistry
from openrescue.metrics import MetricsCollector


def test_record_activity_increments_counter():
    registry = CollectorRegistry()
    collector = MetricsCollector(registry=registry)

    collector.record_activity(app="Code", project="openrescue", category="productive", seconds=5.0)
    collector.record_activity(app="Code", project="openrescue", category="productive", seconds=5.0)

    samples = list(registry.get_all_sample_values("openrescue_active_seconds_total"))
    code_samples = [s for s in samples if s.labels.get("app") == "Code"]
    assert len(code_samples) == 1
    assert code_samples[0].value == 10.0


def test_record_idle():
    registry = CollectorRegistry()
    collector = MetricsCollector(registry=registry)

    collector.record_idle(seconds=120.0)

    samples = list(registry.get_all_sample_values("openrescue_idle_seconds"))
    assert len(samples) == 1
    assert samples[0].value == 120.0
```

**Step 2: Run tests to verify they fail**

```bash
cd agent && uv run pytest tests/test_metrics.py -v
```

Expected: FAIL

**Step 3: Implement metrics module**

```python
# agent/src/openrescue/metrics.py
from prometheus_client import CollectorRegistry, Counter, Gauge, start_http_server

REGISTRY = CollectorRegistry()


class MetricsCollector:
    def __init__(self, registry: CollectorRegistry | None = None):
        self.registry = registry or REGISTRY
        self.active_seconds = Counter(
            "openrescue_active_seconds_total",
            "Total active seconds per app/project/category",
            ["app", "project", "category"],
            registry=self.registry,
        )
        self.idle_seconds = Gauge(
            "openrescue_idle_seconds",
            "Current idle time in seconds",
            registry=self.registry,
        )

    def record_activity(self, app: str, project: str, category: str, seconds: float) -> None:
        self.active_seconds.labels(app=app, project=project, category=category).inc(seconds)

    def record_idle(self, seconds: float) -> None:
        self.idle_seconds.set(seconds)

    def start_server(self, port: int = 8000) -> None:
        start_http_server(port, registry=self.registry)
```

**Step 4: Run tests to verify they pass**

```bash
cd agent && uv run pytest tests/test_metrics.py -v
```

Expected: 2 passed

**Step 5: Commit**

```bash
git add agent/src/openrescue/metrics.py agent/tests/test_metrics.py
git commit -m "add prometheus metrics collector"
```

---

### Task 6: Agent - Categorizer

**Files:**
- Create: `agent/src/openrescue/categorizer.py`
- Create: `agent/tests/test_categorizer.py`

**Step 1: Write failing test for categorization**

```python
# agent/tests/test_categorizer.py
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
```

**Step 2: Run tests to verify they fail**

```bash
cd agent && uv run pytest tests/test_categorizer.py -v
```

Expected: FAIL

**Step 3: Implement categorizer**

```python
# agent/src/openrescue/categorizer.py
from openrescue.config import CategoriesConfig


def categorize(app_name: str, window_title: str, categories: CategoriesConfig) -> str:
    searchable = f"{app_name} {window_title}".lower()

    for keyword in categories.productive:
        if keyword.lower() in searchable:
            return "productive"

    for keyword in categories.distracting:
        if keyword.lower() in searchable:
            return "distracting"

    for keyword in categories.neutral:
        if keyword.lower() in searchable:
            return "neutral"

    return "uncategorized"
```

**Step 4: Run tests to verify they pass**

```bash
cd agent && uv run pytest tests/test_categorizer.py -v
```

Expected: 3 passed

**Step 5: Commit**

```bash
git add agent/src/openrescue/categorizer.py agent/tests/test_categorizer.py
git commit -m "add activity categorizer"
```

---

### Task 7: Agent - Main Loop

**Files:**
- Create: `agent/src/openrescue/main.py`
- Create: `agent/tests/test_main.py`

**Step 1: Write failing test for main loop**

```python
# agent/tests/test_main.py
import time
from unittest.mock import MagicMock, patch
from openrescue.main import tracking_loop
from openrescue.config import Config, ServerConfig, TrackingConfig, ProjectsConfig, CategoriesConfig
from openrescue.tracker import ActivityEvent


def test_tracking_loop_single_iteration(mocker):
    config = Config(
        server=ServerConfig(loki_url="http://localhost:3100", mimir_url="http://localhost:9009"),
        tracking=TrackingConfig(poll_interval_seconds=5),
        projects=ProjectsConfig(base_paths=["~/projects"]),
        categories=CategoriesConfig(productive=["code"], neutral=[], distracting=[]),
    )

    mock_event = ActivityEvent(
        timestamp=time.time(),
        window_title="main.py - openrescue - Visual Studio Code",
        app_name="Code",
        pid=1234,
        cwd="/home/b/projects/openrescue",
        project=None,
    )

    mock_get_window = mocker.patch("openrescue.main.get_active_window_x11", return_value=mock_event)
    mock_get_idle = mocker.patch("openrescue.main.get_idle_time_x11", return_value=10.0)
    mock_shipper = MagicMock()
    mock_metrics = MagicMock()

    tracking_loop(config, mock_shipper, mock_metrics, hostname="test", max_iterations=1)

    mock_shipper.push_event.assert_called_once()
    pushed_event = mock_shipper.push_event.call_args[0][0]
    assert pushed_event.project == "openrescue"
    assert pushed_event.idle_seconds == 10.0
    mock_metrics.record_activity.assert_called_once()
```

**Step 2: Run tests to verify they fail**

```bash
cd agent && uv run pytest tests/test_main.py -v
```

Expected: FAIL

**Step 3: Implement main loop**

```python
# agent/src/openrescue/main.py
import argparse
import logging
import platform
import time
from pathlib import Path

from openrescue.categorizer import categorize
from openrescue.config import load_config
from openrescue.metrics import MetricsCollector
from openrescue.shipper import LokiShipper
from openrescue.tracker import (
    get_active_window_x11,
    get_idle_time_x11,
    get_project_from_cwd,
    get_project_from_title,
)

logger = logging.getLogger(__name__)


def tracking_loop(config, shipper, metrics, hostname, max_iterations=None):
    iteration = 0
    while max_iterations is None or iteration < max_iterations:
        event = get_active_window_x11()
        event.idle_seconds = get_idle_time_x11()

        project = get_project_from_cwd(event.cwd, config.projects.base_paths)
        if project is None:
            project = get_project_from_title(event.window_title)
        event.project = project

        category = categorize(event.app_name, event.window_title, config.categories)

        if event.idle_seconds < config.tracking.idle_threshold_seconds:
            shipper.push_event(event, hostname=hostname)
            metrics.record_activity(
                app=event.app_name,
                project=event.project or "unknown",
                category=category,
                seconds=config.tracking.poll_interval_seconds,
            )

        metrics.record_idle(event.idle_seconds)

        iteration += 1
        if max_iterations is None or iteration < max_iterations:
            time.sleep(config.tracking.poll_interval_seconds)


def main():
    parser = argparse.ArgumentParser(description="OpenRescue activity tracker")
    parser.add_argument(
        "-c", "--config",
        default=Path.home() / ".config" / "openrescue" / "config.yml",
        type=Path,
        help="Path to config file",
    )
    parser.add_argument(
        "--metrics-port",
        default=8000,
        type=int,
        help="Port for Prometheus metrics endpoint",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    config = load_config(args.config)
    shipper = LokiShipper(config.server.loki_url)
    metrics = MetricsCollector()
    metrics.start_server(args.metrics_port)
    hostname = platform.node()

    logger.info("OpenRescue started on %s, shipping to %s", hostname, config.server.loki_url)
    tracking_loop(config, shipper, metrics, hostname)


if __name__ == "__main__":
    main()
```

**Step 4: Run tests to verify they pass**

```bash
cd agent && uv run pytest tests/test_main.py -v
```

Expected: 1 passed

**Step 5: Run all tests**

```bash
cd agent && uv run pytest -v
```

Expected: all passed

**Step 6: Commit**

```bash
git add agent/src/openrescue/main.py agent/tests/test_main.py
git commit -m "add main tracking loop"
```

---

### Task 8: Agent - Mimir Scrape Config

To get metrics from the agent into Mimir, add a Grafana Alloy container to the server compose that scrapes the agent's `/metrics` endpoint.

**Files:**
- Modify: `server/docker-compose.yml`
- Create: `server/config/alloy-config.alloy`

**Step 1: Create Alloy config**

```hcl
// server/config/alloy-config.alloy
prometheus.scrape "openrescue_agents" {
  targets = [
    {"__address__" = "AGENT_HOST_1:8000", "hostname" = "host1"},
    {"__address__" = "AGENT_HOST_2:8000", "hostname" = "host2"},
    {"__address__" = "AGENT_HOST_3:8000", "hostname" = "host3"},
    {"__address__" = "AGENT_HOST_4:8000", "hostname" = "host4"},
  ]
  scrape_interval = "15s"
  forward_to = [prometheus.remote_write.mimir.receiver]
}

prometheus.remote_write "mimir" {
  endpoint {
    url = "http://mimir:9009/api/v1/push"
  }
}
```

**Step 2: Add Alloy to docker-compose.yml**

Add this service to `server/docker-compose.yml`:

```yaml
  alloy:
    image: grafana/alloy:latest
    ports:
      - "12345:12345"
    volumes:
      - ./config/alloy-config.alloy:/etc/alloy/config.alloy
    command:
      - run
      - /etc/alloy/config.alloy
      - --server.http.listen-addr=0.0.0.0:12345
    depends_on:
      - mimir
    restart: unless-stopped
```

**Step 3: Redeploy**

```bash
scp -r server/ user@server:~/openrescue/
ssh user@server "cd ~/openrescue/server && docker compose up -d"
```

**Step 4: Commit**

```bash
git add server/
git commit -m "add Grafana Alloy for metrics scraping"
```

---

### Task 9: Packaging - .deb with systemd User Service

**Files:**
- Create: `packaging/openrescue.service`
- Create: `packaging/postinst.sh`
- Create: `packaging/prerm.sh`
- Create: `packaging/build-deb.sh`

**Step 1: Create systemd user service file**

```ini
# packaging/openrescue.service
[Unit]
Description=OpenRescue Activity Tracker
After=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/lib/openrescue/venv/bin/openrescue -c %h/.config/openrescue/config.yml
Restart=on-failure
RestartSec=10
Environment=DISPLAY=:0

[Install]
WantedBy=default.target
```

Note: This is a user service (installed to `/usr/lib/systemd/user/`) so it runs in the user's graphical session and has access to X11/Wayland.

**Step 2: Create postinst script**

```bash
#!/bin/bash
# packaging/postinst.sh
set -e

CONFIG_DIR="$HOME/.config/openrescue"
if [ ! -f "$CONFIG_DIR/config.yml" ]; then
    mkdir -p "$CONFIG_DIR"
    cp /usr/lib/openrescue/config.example.yml "$CONFIG_DIR/config.yml"
    echo "Default config created at $CONFIG_DIR/config.yml — edit server URLs before starting."
fi

echo ""
echo "To enable OpenRescue:"
echo "  1. Edit ~/.config/openrescue/config.yml"
echo "  2. systemctl --user enable --now openrescue"
echo ""
```

**Step 3: Create prerm script**

```bash
#!/bin/bash
# packaging/prerm.sh
set -e
systemctl --user stop openrescue || true
systemctl --user disable openrescue || true
```

**Step 4: Create build script**

```bash
#!/bin/bash
# packaging/build-deb.sh
set -e

VERSION="${1:-0.1.0}"
BUILD_DIR="$(mktemp -d)"
trap "rm -rf $BUILD_DIR" EXIT

# Create venv with dependencies
python3 -m venv "$BUILD_DIR/usr/lib/openrescue/venv"
"$BUILD_DIR/usr/lib/openrescue/venv/bin/pip" install ../agent/

# Copy example config
cp ../agent/config.example.yml "$BUILD_DIR/usr/lib/openrescue/config.example.yml"

# Install systemd user service
mkdir -p "$BUILD_DIR/usr/lib/systemd/user"
cp openrescue.service "$BUILD_DIR/usr/lib/systemd/user/"

# Build .deb
fpm -s dir -t deb \
    --name openrescue \
    --version "$VERSION" \
    --description "FOSS desktop activity tracker" \
    --url "https://github.com/b/openrescue" \
    --license "MIT" \
    --depends python3 \
    --depends xdotool \
    --depends xprintidle \
    --after-install postinst.sh \
    --before-remove prerm.sh \
    -C "$BUILD_DIR" \
    .

echo "Built: openrescue_${VERSION}_amd64.deb"
```

**Step 5: Make build script executable and commit**

```bash
chmod +x packaging/build-deb.sh packaging/postinst.sh packaging/prerm.sh
git add packaging/
git commit -m "add deb packaging with systemd user service"
```

---

### Task 10: Grafana - Provisioned Dashboards

**Files:**
- Create: `server/config/grafana-dashboards.yml`
- Create: `server/dashboards/activity-overview.json`
- Modify: `server/docker-compose.yml` (add dashboard volume mount)

**Step 1: Create dashboard provisioning config**

```yaml
# server/config/grafana-dashboards.yml
apiVersion: 1
providers:
  - name: OpenRescue
    folder: OpenRescue
    type: file
    options:
      path: /var/lib/grafana/dashboards
```

**Step 2: Create activity overview dashboard JSON**

Create `server/dashboards/activity-overview.json` with panels for:
- Time by application (Mimir: `sum by (app) (rate(openrescue_active_seconds_total[1h]))`)
- Time by project (Mimir: `sum by (project) (rate(openrescue_active_seconds_total[1h]))`)
- Time by category (Mimir: `sum by (category) (rate(openrescue_active_seconds_total[1h]))`)
- Activity timeline (Loki: `{job="openrescue"} | json`)
- Current idle time (Mimir: `openrescue_idle_seconds`)
- Daily productivity score (Mimir: derived from category ratios)

The full JSON is too large for this plan — generate it during implementation using Grafana's API or UI, then export.

**Step 3: Update docker-compose.yml grafana volumes**

Add to grafana service volumes:
```yaml
      - ./config/grafana-dashboards.yml:/etc/grafana/provisioning/dashboards/dashboards.yml
      - ./dashboards:/var/lib/grafana/dashboards
```

**Step 4: Redeploy and verify dashboards load**

```bash
scp -r server/ user@server:~/openrescue/
ssh user@server "cd ~/openrescue/server && docker compose up -d"
```

Open `http://server:3000` and verify the OpenRescue dashboard folder appears.

**Step 5: Commit**

```bash
git add server/
git commit -m "add provisioned Grafana dashboards"
```

---

### Task 11: End-to-End Test

**Step 1: Build and install the .deb locally**

```bash
cd packaging && ./build-deb.sh 0.1.0
sudo dpkg -i openrescue_0.1.0_amd64.deb
```

**Step 2: Configure and start**

```bash
vim ~/.config/openrescue/config.yml  # set loki_url and mimir_url to server
systemctl --user enable --now openrescue
```

**Step 3: Verify data flow**

```bash
# Check agent is running
systemctl --user status openrescue

# Check logs shipping to Loki
ssh user@server 'curl -s "http://localhost:3100/loki/api/v1/query?query={job=\"openrescue\"}&limit=5"' | python3 -m json.tool

# Check metrics endpoint
curl -s http://localhost:8000/metrics | grep openrescue

# Check Grafana dashboards at http://server:3000
```

**Step 4: Commit any fixes**

```bash
git add -A && git commit -m "fix: e2e issues"
```
