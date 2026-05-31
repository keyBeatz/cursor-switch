from __future__ import annotations

import shutil
from datetime import datetime, timezone

from cursor_switch.config import load_accounts, save_accounts, sync_accounts_from_dirs
from cursor_switch.log import log
from cursor_switch.paths import (
    DEFAULT_CURSOR_CONFIG,
    ROOT,
    SHARED_CONFIG,
    ensure_root,
)


def ensure_cursor_config_symlink() -> bool:
    """Point ~/.config/Cursor at shared config so desktop launches use migrated data."""
    if not SHARED_CONFIG.is_dir():
        raise RuntimeError("Not initialized. Run `cursor-switch init` first.")

    shared = SHARED_CONFIG.resolve()
    if DEFAULT_CURSOR_CONFIG.is_symlink():
        if DEFAULT_CURSOR_CONFIG.resolve() == shared:
            return False
        DEFAULT_CURSOR_CONFIG.unlink()

    if DEFAULT_CURSOR_CONFIG.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        stray = ROOT / f"stray-config-Cursor-{stamp}"
        shutil.move(str(DEFAULT_CURSOR_CONFIG), stray)
        log(f"Moved stray ~/.config/Cursor to {stray}")

    DEFAULT_CURSOR_CONFIG.symlink_to(SHARED_CONFIG)
    log("Linked ~/.config/Cursor -> shared/config")
    return True


def run_repair() -> None:
    ensure_root()
    cfg = load_accounts()
    registry_fixed = sync_accounts_from_dirs(cfg)
    if registry_fixed:
        save_accounts(cfg)
        log("Repaired accounts.toml from account directories")
    symlink_fixed = ensure_cursor_config_symlink()
    if not registry_fixed and not symlink_fixed:
        log("Nothing to repair")
