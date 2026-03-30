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
    get_active_window,
    get_idle_time,
    get_project_from_cwd,
    get_project_from_pid,
    get_project_from_title,
)

logger = logging.getLogger(__name__)


def _normalize_title(title: str) -> str:
    """Strip leading spinner/status characters that change frequently."""
    import re
    # Strip leading unicode spinners, braille patterns, emoji, whitespace
    return re.sub(r'^[\s\u2800-\u28FF\u2700-\u27BF✳⠀-⣿]+', '', title).strip()


def _session_key(event):
    """Return a hashable key representing the current window session."""
    return (event.app_name, _normalize_title(event.window_title), event.project)


def _flush_session(session_event, session_polls, poll_interval, shipper, metrics, config, hostname):
    duration = session_polls * poll_interval
    if duration <= 0:
        return
    category = categorize(session_event.app_name, session_event.window_title, config.categories)
    shipper.push_session(session_event, hostname=hostname, duration=duration)
    metrics.record_activity(
        app=session_event.app_name,
        project=session_event.project or "unknown",
        category=category,
        seconds=duration,
    )


def tracking_loop(config, shipper, metrics, hostname, max_iterations=None):
    current_session = None  # (app_name, window_title, project)
    session_event = None
    session_polls = 0
    was_idle = False
    poll_interval = config.tracking.poll_interval_seconds

    iteration = 0
    while max_iterations is None or iteration < max_iterations:
        event = get_active_window()
        event.idle_seconds = get_idle_time()

        project = get_project_from_cwd(event.cwd, config.projects.base_paths)
        if project is None:
            project, child_cwd = get_project_from_pid(event.pid, config.projects.base_paths)
            if child_cwd:
                event.cwd = child_cwd
        if project is None:
            project = get_project_from_title(event.window_title)
        event.project = project

        is_idle = event.idle_seconds >= config.tracking.idle_threshold_seconds
        key = _session_key(event)

        # Flush previous session if window changed or transitioned to idle
        if current_session is not None and (key != current_session or (is_idle and not was_idle)):
            if not was_idle:
                _flush_session(session_event, session_polls, poll_interval, shipper, metrics, config, hostname)
            current_session = None

        # Start new session if not idle
        if current_session is None and not is_idle:
            current_session = key
            session_event = event
            session_polls = 0

        if current_session is not None:
            session_polls += 1

        was_idle = is_idle
        metrics.record_idle(event.idle_seconds)

        iteration += 1
        if max_iterations is None or iteration < max_iterations:
            time.sleep(poll_interval)

    # Flush final session
    if current_session is not None and not was_idle:
        _flush_session(session_event, session_polls, poll_interval, shipper, metrics, config, hostname)


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
