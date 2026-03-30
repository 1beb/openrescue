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


def get_project_from_pid(pid: int | None, base_paths: list[str]) -> str | None:
    """Walk child processes of pid to find one with a CWD under a project base path."""
    if pid is None:
        return None

    # BFS through child processes
    to_visit = [pid]
    visited = set()
    best = None

    while to_visit:
        current = to_visit.pop(0)
        if current in visited:
            continue
        visited.add(current)

        try:
            cwd = os.readlink(f"/proc/{current}/cwd")
            project = get_project_from_cwd(cwd, base_paths)
            if project:
                best = project
        except OSError:
            pass

        # Find children
        try:
            for entry in os.listdir("/proc"):
                if not entry.isdigit():
                    continue
                try:
                    with open(f"/proc/{entry}/stat") as f:
                        stat = f.read()
                    ppid = int(stat.split(")")[1].split()[1])
                    if ppid == current:
                        to_visit.append(int(entry))
                except (OSError, ValueError, IndexError):
                    pass
        except OSError:
            pass

    return best


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


def get_active_window_gnome_wayland() -> ActivityEvent:
    # Use OpenRescue GNOME Shell extension for accurate focus tracking
    try:
        import json as _json
        result = _run_cmd([
            "gdbus", "call", "--session",
            "--dest", "org.gnome.Shell",
            "--object-path", "/org/openrescue/FocusTracker",
            "--method", "org.openrescue.FocusTracker.GetFocusedWindow",
        ])
        # Output: ('{"title":"...","app":"...","pid":123}',)
        json_str = result.strip("()',\n ")
        data = _json.loads(json_str)

        app_name = data.get("app", "unknown")
        title = data.get("title", "unknown")
        pid = data.get("pid") or None

        cwd = None
        if pid and pid > 0:
            try:
                cwd = os.readlink(f"/proc/{pid}/cwd")
            except OSError:
                pass

        return ActivityEvent(
            timestamp=time.time(),
            window_title=title,
            app_name=app_name,
            pid=pid if pid and pid > 0 else None,
            cwd=cwd,
            project=None,
        )
    except Exception:
        pass

    return ActivityEvent(
        timestamp=time.time(),
        window_title="unknown",
        app_name="unknown",
        pid=None,
        cwd=None,
        project=None,
    )


def get_idle_time_gnome_wayland() -> float:
    try:
        result = _run_cmd([
            "gdbus", "call", "--session",
            "--dest", "org.gnome.Mutter.IdleMonitor",
            "--object-path", "/org/gnome/Mutter/IdleMonitor/Core",
            "--method", "org.gnome.Mutter.IdleMonitor.GetIdletime",
        ])
        # Output: (uint64 1234,)
        ms = int(result.strip("(,)").split()[-1].rstrip(","))
        return ms / 1000.0
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        return 0.0


def detect_session_type() -> str:
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session == "wayland":
        desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
        if "gnome" in desktop:
            return "gnome-wayland"
        return "wayland-unknown"
    return "x11"


def get_active_window() -> ActivityEvent:
    session = detect_session_type()
    if session == "gnome-wayland":
        return get_active_window_gnome_wayland()
    return get_active_window_x11()


def get_idle_time() -> float:
    session = detect_session_type()
    if session == "gnome-wayland":
        return get_idle_time_gnome_wayland()
    return get_idle_time_x11()


def get_idle_time_x11() -> float:
    try:
        ms = int(_run_cmd(["xprintidle"]))
        return ms / 1000.0
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError):
        return 0.0
