# Usage

## Install

```bash
cd ~/Projects/cursor-switch
uv sync
uv tool install -e .
```

Verify:

```bash
cursor-switch --version
cursor-switch status
```

## First-time setup

### 1. Initialize from your current Cursor install

```bash
cursor-switch init work
```

This will:

- Copy `~/.config/Cursor` and `~/.cursor` to `~/.config/cursor-accounts/backup-init-<timestamp>/`
- Move live data into `~/.config/cursor-accounts/shared/`
- Symlink `~/.cursor` → shared cursor home
- Symlink `~/.config/Cursor` → shared IDE config (so desktop launches use your chats/auth)
- Export auth for account `work`

**Close Cursor before running init.**

### 2. Add a second account

```bash
cursor-switch init-account alt
cursor-switch alt
```

Cursor opens with the **same chats and plans** but prompts login for the new account. After signing in:

```bash
cursor-switch export-auth alt
```

### 3. Switch anytime

```bash
cursor-switch work    # back to first account
cursor-switch alt     # second account, fresh quota
```

## Commands

| Command | Description |
|---------|-------------|
| `cursor-switch init [name]` | One-time migration (`--force` to re-run) |
| `cursor-switch init-account <name>` | Register another account slot |
| `cursor-switch <name>` | Switch account (shorthand for `switch`) |
| `cursor-switch switch <name>` | Switch account |
| `cursor-switch switch <name> --no-launch` | Switch without starting Cursor |
| `cursor-switch switch <name> --skip-backup` | Switch without creating a zip backup |
| `cursor-switch export-auth [name]` | Save current login tokens to bundle |
| `cursor-switch launch [name] [paths...]` | Launch Cursor (optionally switch first) |
| `cursor-switch status` | Show active account, paths, backups |
| `cursor-switch list` | List configured accounts |
| `cursor-switch repair` | Fix accounts registry and `~/.config/Cursor` symlink |

## Environment

| Variable | Purpose |
|----------|---------|
| `CURSOR_SWITCH_CURSOR_BIN` | Override path to `cursor` binary |

## Typical workflow (2–4× per month)

1. Hit rate limit on account A
2. `cursor-switch alt`
3. Continue working (same project folders reopen)
4. When done or limit hit again: `cursor-switch work`

## After Cursor upgrades

Run a test switch and verify chats still appear. If login UI breaks, re-run:

```bash
cursor-switch export-auth <account>
```

for each account after logging in once.

## Troubleshooting

**"Database still busy"**  
Usually stale SQLite sidecar files (`state.vscdb-wal` / `-shm`) left after Cursor closed, or **cursor-agent** (Cursor CLI) still running. Run `cursor-switch status` — if `cursor-agent: running`, stop your CLI session first. Recent versions checkpoint the WAL automatically when nothing holds the file open.

**"Cursor is still running"**  
Fully quit Cursor (all windows). Check `cursor-switch status`.

**Login prompt / empty chats after init**  
You may have opened Cursor from the desktop menu before `~/.config/Cursor` was linked to shared data. Run `cursor-switch repair`, then `cursor-switch work` (or `cursor-switch launch work`).

**`list` empty or "Unknown account"**  
Run `cursor-switch repair` to rebuild `accounts.toml` from account directories.

**"No session bundle for account"** (older versions)  
New accounts have no saved tokens yet. `cursor-switch switch <name>` clears auth and opens Cursor for login; then run `cursor-switch export-auth <name>`.

**Chats missing in sidebar**  
Ensure you open the **same folder path** as before. Chats are keyed by workspace path.

**Restore from backup**  
Copy from `~/Projects/cursor-switch/backups/<name>.zip` — unzip and restore — see [safety.md](safety.md).
