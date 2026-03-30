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
    get_project_from_title,
)

logger = logging.getLogger(__name__)


def tracking_loop(config, shipper, metrics, hostname, max_iterations=None):
    iteration = 0
    while max_iterations is None or iteration < max_iterations:
        event = get_active_window()
        event.idle_seconds = get_idle_time()

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
