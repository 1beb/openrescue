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


def _get_children(pid: int) -> list[int]:
    """Get direct child PIDs of a process."""
    children = []
    try:
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            try:
                with open(f"/proc/{entry}/stat") as f:
                    stat = f.read()
                ppid = int(stat.split(")")[1].split()[1])
                if ppid == pid:
                    children.append(int(entry))
            except (OSError, ValueError, IndexError):
                pass
    except OSError:
        pass
    return children


def _walk_for_project(pid: int, base_paths: list[str]) -> tuple[str | None, str | None]:
    """BFS from pid, return (project, cwd) of the most recently spawned match."""
    to_visit = [pid]
    visited = set()
    best = None
    best_cwd = None
    best_pid = -1

    while to_visit:
        current = to_visit.pop(0)
        if current in visited:
            continue
        visited.add(current)

        try:
            cwd = os.readlink(f"/proc/{current}/cwd")
            project = get_project_from_cwd(cwd, base_paths)
            if project and current > best_pid:
                best = project
                best_cwd = cwd
                best_pid = current
        except OSError:
            pass

        to_visit.extend(_get_children(current))

    return best, best_cwd


def get_project_from_pid(pid: int | None, base_paths: list[str]) -> tuple[str | None, str | None]:
    """Find the project for a focused window PID by walking child processes.
    For terminal emulators with multiple tabs, uses the foreground process group
    of each tab's shell to find the active process tree.
    Returns (project_name, cwd) or (None, None)."""
    if pid is None:
        return None, None

    # Find immediate children (e.g. ptyxis-agent, then bash shells)
    # Walk down to find shell processes with a tpgid that points to a project-aware process
    shells = []
    to_check = [pid]
    visited = set()

    # Find all bash/zsh/fish shells in the first 3 levels
    for _ in range(3):
        next_level = []
        for p in to_check:
            if p in visited:
                continue
            visited.add(p)
            for child in _get_children(p):
                try:
                    with open(f"/proc/{child}/comm") as f:
                        comm = f.read().strip()
                    if comm in ("bash", "zsh", "fish", "sh"):
                        shells.append(child)
                    next_level.append(child)
                except OSError:
                    next_level.append(child)
        to_check = next_level

    if shells:
        # For each shell, get its foreground process group leader (tpgid),
        # walk from there to find a project, and use the max child starttime
        # as a proxy for "most recently active tab"
        best = None
        best_cwd = None
        best_starttime = -1
        for shell_pid in shells:
            try:
                with open(f"/proc/{shell_pid}/stat") as f:
                    stat = f.read()
                tpgid = int(stat.split(")")[1].split()[5])
                if tpgid <= 0:
                    continue
                project, cwd = _walk_for_project(tpgid, base_paths)
                if not project:
                    continue
                # Find max starttime (field 22) among descendants
                max_start = 0
                to_visit = [tpgid]
                seen = set()
                while to_visit:
                    p = to_visit.pop(0)
                    if p in seen:
                        continue
                    seen.add(p)
                    try:
                        with open(f"/proc/{p}/stat") as f:
                            s = f.read()
                        starttime = int(s.split(")")[1].split()[19])
                        if starttime > max_start:
                            max_start = starttime
                    except (OSError, ValueError, IndexError):
                        pass
                    to_visit.extend(_get_children(p))
                if max_start > best_starttime:
                    best = project
                    best_cwd = cwd
                    best_starttime = max_start
            except (OSError, ValueError, IndexError):
                pass

        if best:
            return best, best_cwd

    # Fallback: simple walk from PID
    return _walk_for_project(pid, base_paths)


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
