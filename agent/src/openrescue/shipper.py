import json
import logging

import requests

from openrescue.tracker import ActivityEvent

logger = logging.getLogger(__name__)


class LokiShipper:
    def __init__(self, loki_url: str):
        self.push_url = f"{loki_url}/loki/api/v1/push"

    def push_session(self, event: ActivityEvent, hostname: str, duration: float) -> None:
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
            "duration_seconds": round(duration, 1),
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

    def push_from_buffer(self, record: dict) -> bool:
        labels = {
            "job": "openrescue",
            "hostname": record["hostname"],
            "app": record["app_name"],
        }
        if record.get("project"):
            labels["project"] = record["project"]

        log_line = json.dumps({
            "window_title": record["window_title"],
            "pid": record["pid"],
            "cwd": record["cwd"],
            "duration_seconds": round(record["duration"], 1),
        })

        payload = {
            "streams": [{
                "stream": labels,
                "values": [[str(int(record["timestamp"] * 1e9)), log_line]],
            }]
        }

        try:
            resp = requests.post(self.push_url, json=payload, timeout=5)
            if resp.status_code in (200, 204):
                return True
            logger.warning("Loki push failed: %s %s", resp.status_code, resp.text)
            return False
        except requests.RequestException as e:
            logger.warning("Loki push error: %s", e)
            return False
