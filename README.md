# Cursor Account Switcher

Switch between Cursor IDE accounts when you hit API limits, without losing **chat history**, **plans**, or **workspace state**.

Cursor stores conversations locally in SQLite—not per account on the server. This tool keeps one shared data store and swaps only **auth tokens** when you switch.

## Quick start

```bash
cd ~/Projects/cursor-switch
uv sync
uv tool install -e .

# One-time migration (backs up originals, moves config into shared layout)
cursor-switch init work

# Register a second account
cursor-switch init-account alt

# Switch to alt (quits Cursor, backs up config + ~/.cursor, swaps auth, relaunches)
cursor-switch alt
# Sign in via Cursor UI once, then:
cursor-switch export-auth alt

# Switch back — same chats and plans, account A quota
cursor-switch work
```

Shorthand: `cursor-switch work` is the same as `cursor-switch switch work`.

## Requirements

- Linux (tested paths: `~/.config/Cursor`, `~/.cursor`)
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Cursor IDE installed (`cursor` on PATH)

## Documentation

- [Usage guide](docs/usage.md)
- [Architecture](docs/architecture.md)
- [Data locations](docs/data-locations.md) — all Cursor folders on disk
- [Safety & backups](docs/safety.md)

## How it works (short)

| Shared (never swapped) | Swapped per account |
|------------------------|---------------------|
| Chat DB (`state.vscdb` bulk) | `cursorAuth/*` tokens |
| Plans, projects, settings | `cli-config.json` auth |
| Extensions, workspaceStorage | `statsig-cache.json`, `~/.config/cursor/` (CLI auth) |

Every switch: quit Cursor → **full zip backup** of IDE config + `~/.cursor` + `~/.config/cursor` → export old auth → import new auth → relaunch.

Backups live in **`~/Projects/cursor-switch/backups/`** as **`.zip` archives** (gitignored), keeping the last **7**. Compression progress is shown in the terminal.

## Project layout

```
~/Projects/cursor-switch/     # this repo (Python CLI)
~/.config/cursor-accounts/    # runtime data (created by init)
```

## License

MIT — use at your own risk; auth injection is unsupported by Cursor.
