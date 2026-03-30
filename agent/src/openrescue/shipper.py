import json
import logging

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
