# Cursor data locations

Where Cursor stores data on Linux, and how **cursor-switch** treats each path.

## Summary table

| Path | What it is | Managed by cursor-switch | On account switch |
|------|------------|--------------------------|-------------------|
| `~/.config/Cursor` | IDE user data (settings, chats DB, workspaces) | **Yes** — moved to `shared/config/` on init; `--user-data-dir` | **Shared** (chats/plans stay) |
| `~/.cursor` | Cursor home (plans, projects, extensions, `cli-config.json`) | **Yes** — moved to `shared/cursor-home/`; symlink | **Shared** |
| `~/.config/cursor` | **CLI / `cursor agent`** auth (`auth.json`, prompt history) | **Yes** — stays in place; backed up & swapped | **Per account** (session bundle) |
| `~/.config/cursor-accounts` | **This tool** (bundles, `accounts.toml`, logs) | **Yes** — our runtime dir | Tool metadata only |
| `~/.local/share/cursor-agent` | Installed `cursor-agent` binaries/versions | **No** | Ignored (reinstallable) |
| `~/.cursor-server` | Remote SSH server state | **No** | Ignored (remote workflows) |
| `~/.cache/cursor-compile-cache` | Compile cache | **No** | Ignored (regenerates) |

## Details

### `~/.config/Cursor` (capital C)

- VS Code–style app data for the **desktop IDE**
- **Chats**: `User/globalStorage/state.vscdb` (`cursorDiskKV`, `composer.composerHeaders`)
- **Workspaces**: `User/workspaceStorage/<hash>/`
- **Auth (IDE)**: `cursorAuth/*` keys inside `state.vscdb` — swapped per account, not duplicated

After `cursor-switch init`, this tree lives at:

`~/.config/cursor-accounts/shared/config/`

### `~/.cursor`

- `plans/` — plan markdown files (**shared**)
- `projects/` — agent transcripts, MCP project cache (**shared**)
- `extensions/` — extensions (`--extensions-dir`)
- `cli-config.json` — IDE/agent CLI settings including `authInfo` — **swapped per account**
- `statsig-cache.json` — feature flags cache — **swapped per account**
- `agent-cli-state.json` — UI flags only — **shared** (not account-specific)

After init: `~/.config/cursor-accounts/shared/cursor-home/` (symlinked as `~/.cursor`).

### `~/.config/cursor` (lowercase)

- **`auth.json`** — JWT tokens for **`cursor agent`** terminal CLI
- **`prompt_history.json`** — CLI prompt history

**Not moved on init** — remains at `~/.config/cursor`.

On switch:

- Exported to `accounts/<name>/session-bundle/cursor-cli/`
- Restored from bundle when switching accounts

Included in backup zips as `config-cursor-cli/`.

### `~/.config/cursor-accounts`

Created by cursor-switch:

```
accounts/<name>/session-bundle/   # per-account auth snapshots
shared/config/                    # IDE data
shared/cursor-home/               # ~/.cursor content
accounts.toml, active, session.json, switch.log
```

### Not managed (safe to ignore for account switching)

| Path | Why ignore |
|------|------------|
| `~/.local/share/cursor-agent` | Versioned CLI install (~500MB); not login state |
| `~/.cursor-server` | Remote development server; separate from local IDE login |
| `~/.cache/cursor-compile-cache` | Ephemeral build cache |

If you use **Remote SSH** heavily, remote chat state may live under `.cursor-server/data/User/` — that is a separate concern from local account switching.

## Backup zip layout

Each backup under `~/Projects/cursor-switch/backups/*.zip` contains:

```
config-Cursor/        ← ~/.config/Cursor (or shared/config)
cursor-home/          ← ~/.cursor (or shared/cursor-home)
config-cursor-cli/    ← ~/.config/cursor
README.txt
meta.json
```

## Session bundle (per account)

```
accounts/work/session-bundle/
  state-keys.json       # IDE auth keys from state.vscdb
  cli-config.json       # ~/.cursor/cli-config.json
  statsig-cache.json
  cursor-cli/           # ~/.config/cursor (auth.json, etc.)
  meta.json
```
