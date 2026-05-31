from __future__ import annotations

from cursor_switch.auth import (
    clear_session_auth,
    export_session_bundle,
    has_session_bundle,
    import_session_bundle,
)
from cursor_switch.backup import create_pre_switch_backup
from cursor_switch.config import (
    account_exists,
    load_accounts,
    read_active,
    write_active,
)
from cursor_switch.cursor_proc import (
    launch_cursor,
    quit_cursor,
    save_session,
    wal_idle,
)
from cursor_switch.log import log
from cursor_switch.paths import (
    DEFAULT_CURSOR_CLI,
    SESSION_FILE,
    SHARED_CONFIG,
    SHARED_CURSOR_HOME,
    SHARED_EXTENSIONS,
    STATE_DB,
)


def run_switch(target: str, *, launch: bool = True, skip_backup: bool = False) -> None:
    cfg = load_accounts()
    if not account_exists(cfg, target):
        raise RuntimeError(f"Unknown account {target!r}. Run `cursor-switch list`.")

    if not SHARED_CONFIG.is_dir():
        raise RuntimeError("Not initialized. Run `cursor-switch init` first.")

    current = read_active()
    if current == target:
        log(f"Already on account {target}")
        if launch:
            folders = save_session(SESSION_FILE)
            launch_cursor(SHARED_CONFIG, SHARED_EXTENSIONS, folders or None)
        return

    folders = save_session(SESSION_FILE)
    quit_cursor()
    if not wal_idle(STATE_DB):
        holders = "Cursor IDE, cursor-agent (CLI), or another tool"
        raise RuntimeError(
            f"Database still busy: {STATE_DB}. "
            f"Close {holders} completely and retry."
        )

    if not skip_backup:
        create_pre_switch_backup(
            current, target, SHARED_CONFIG, SHARED_CURSOR_HOME, DEFAULT_CURSOR_CLI
        )
    else:
        log("Skipping pre-switch backup (--skip-backup)")

    if current:
        export_session_bundle(current)

    if has_session_bundle(target):
        import_session_bundle(target)
    else:
        log(
            f"No saved auth for {target!r}; clearing tokens — "
            f"sign in in Cursor, then run: cursor-switch export-auth {target}"
        )
        clear_session_auth()
    write_active(target)
    log(f"Switched active account to {target}")

    if launch:
        launch_cursor(SHARED_CONFIG, SHARED_EXTENSIONS, folders or None)


def run_export_auth(account: str | None = None) -> None:
    cfg = load_accounts()
    name = account or read_active()
    if not name:
        raise RuntimeError("No active account. Pass an account name explicitly.")
    if not account_exists(cfg, name):
        raise RuntimeError(f"Unknown account {name!r}.")
    export_session_bundle(name)
