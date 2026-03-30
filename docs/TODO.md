# TODO

## Metrics port

Change default metrics port from 8000 to 8005 to avoid conflicts with common dev servers. Update in:
- `agent/src/openrescue/main.py` (argparse default)
- `agent/config.example.yml` (document the port)
- `server/config/alloy-config.alloy` (scrape targets)
- `packaging/openrescue.service` (if port is hardcoded)

## Ptyxis window title disambiguation

The "Window Titles - Ptyxis" pie chart shows duplicate entries because all Claude Code sessions have similar titles (just the conversation name). Need to enrich the title with project context so they don't overlap. Options:
- Prepend the detected project name to the window title in the log line: "openrescue: Claude Code — claude"
- Add a separate `enriched_title` field combining project + title
- Use the Loki label `project` to group within the pie chart query
