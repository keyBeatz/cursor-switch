# Safety & backups

## Risk level

This tool modifies Cursor's local SQLite database. That is **unsupported** by Cursor—the same class of operation as [cursaves](https://github.com/Callum-Ward/cursaves) or [cursor-chat-transfer](https://github.com/ibrahim317/cursor-chat-transfer).

For **2–4 switches per month** with mandatory full backups, the risk is acceptable for personal use.

## Where backups live

```
~/Projects/cursor-switch/backups/          # gitignored
  2026-05-31_22-04-05_init_before-migration.zip
  2026-05-31_22-04-05_init_before-migration.meta.json
  2026-05-31_22-04-05_init_before-migration.txt
  2026-05-31_22-15-30_pre-switch_work-to-alt.zip
  ...
```

Each backup is a **zip archive** plus small sidecars:

| File | Purpose |
|------|---------|
| `*.zip` | Full backup (`config-Cursor/`, `cursor-home/`, README, meta) |
| `*.meta.json` | Machine-readable summary (size, accounts, paths) |
| `*.txt` | Human-readable README without opening the zip |

Inside the zip:

- `config-Cursor/` — IDE user data
- `cursor-home/` — `~/.cursor`
- `config-cursor-cli/` — `~/.config/cursor` (CLI agent auth)

**Retention:** last **7** zip backups; sidecars are removed with their zip.

While compressing, the CLI prints a live progress bar on stderr (bytes processed / total).

## Mandatory safeguards (built in)

1. **Quit Cursor first**
2. **WAL idle check**
3. **Full zip backup before every switch** — both config trees
4. **Auth patch on DB copy** + `integrity_check`
5. **Retention** — keeps last **7** backups

## Manual restore

With Cursor **fully closed**:

```bash
BACKUP=~/Projects/cursor-switch/backups/2026-05-31_22-15-30_pre-switch_work-to-alt
cd /tmp
unzip "$BACKUP.zip"

# Shared layout (after init):
cp -a config-Cursor/. ~/.config/cursor-accounts/shared/config/
cp -a cursor-home/. ~/.config/cursor-accounts/shared/cursor-home/
cp -a config-cursor-cli/. ~/.config/cursor/

# Pre-init layout:
cp -a config-Cursor/. ~/.config/Cursor/
cp -a cursor-home/. ~/.cursor/
cp -a config-cursor-cli/. ~/.config/cursor/
```

Or read `$BACKUP.txt` for the exact paths recorded at backup time.

## Recommended habits

- Run `cursor-switch export-auth <name>` after any fresh login
- Run `cursor-switch status` to see recent `.zip` sizes
- After Cursor updates: test `work → alt → work` once
