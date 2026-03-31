# OpenRescue

Rescuetime is an excellent piece of software for habit/usage tracking, however, they unforunately stopped supportng Linux a few years ago. This is a FOSS alternative to RescueTime, specifically for Ubuntu on Wayland. It tracks activity and ships data to a centralized LGTM stack (Loki, Grafana, Mimir) over Tailscale.

Shamelessly, I'm using this software to get familiar with the LGTM stack but I think it's an excellent fit for this use case.

## How it works

A lightweight Python daemon runs on each Linux machine, detecting the focused window, its application name, PID, working directory, and project context. Instead of sending a row every few seconds, it aggregates activity into duration-based sessions and only ships an event when you switch windows or go idle.

Data flows to a central server running Grafana + Loki + Mimir via Docker Compose. Grafana provides dashboards for time-by-app, time-by-project, productivity scoring, and activity timelines.

## Architecture

```
[Agent .deb]  ---Tailscale--->  [Loki (logs)]     ---> [Grafana dashboards]
  per machine                   [Mimir (metrics)]
                                [Alloy (scraper)]
                                  on central server
```

## Requirements

### Agent (each tracked machine)

- Linux (X11 or GNOME Wayland)
- Python 3.11+
- xdotool, xprintidle (X11)
- python3-gi, gir1.2-atspi-2.0 (Wayland)
- For GNOME Wayland: the bundled `openrescue-focus` GNOME Shell extension

### Server (central collection)

- Docker and Docker Compose
- Reachable from agent machines (e.g. via Tailscale)

## Quick start

### 1. Deploy the server

Copy `server/` to your central machine and start the stack:

```bash
cd server
docker compose up -d
```

This starts Grafana (port 3000), Loki (port 3100), Mimir (port 9009), and Alloy (port 12345).

### 2. Install the agent

Build the .deb:

```bash
cd packaging
./build-deb.sh 0.3.0
```

Install on each machine:

```bash
sudo dpkg -i openrescue_0.3.0_amd64.deb
sudo apt-get install -f  # resolve deps
```

Edit the config to point at your server:

```bash
vim ~/.config/openrescue/config.yml
```

Start the service:

```bash
systemctl --user enable --now openrescue
```

### 3. GNOME Wayland setup

Copy the extension to your GNOME Shell extensions directory:

```bash
cp -r gnome-extension/openrescue-focus@openrescue \
  ~/.local/share/gnome-shell/extensions/
```

Log out and back in, then enable:

```bash
gnome-extensions enable openrescue-focus@openrescue
```

### 4. View dashboards

Open Grafana at `http://<server>:3000`. The OpenRescue dashboard is pre-provisioned.

## Configuration

The agent config lives at `~/.config/openrescue/config.yml`:

```yaml
server:
  loki_url: "http://<server-ip>:3100"
  mimir_url: "http://<server-ip>:9009"

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
```

## Project detection

OpenRescue detects which project you're working on via three methods (in priority order):

1. Process CWD - reads `/proc/<pid>/cwd` of the focused window
2. Child process walk - for terminals, walks child processes to find shells with CWDs under project base paths
3. Window title parsing - extracts project names from VS Code and terminal title patterns

## License

MIT
