from __future__ import annotations

import shutil

from cursor_switch.auth import export_session_bundle
from cursor_switch.backup import create_init_backup
from cursor_switch.config import (
    AccountsConfig,
    load_accounts,
    save_accounts,
    validate_account_name,
    write_active,
)
from cursor_switch.log import log
from cursor_switch.paths import (
    DEFAULT_CURSOR_CLI,
    DEFAULT_CURSOR_CONFIG,
    DEFAULT_CURSOR_HOME,
    SHARED_CONFIG,
    SHARED_CURSOR_HOME,
    ensure_root,
    session_bundle_dir,
)


def _resolve_cursor_home_for_backup() -> tuple[Path, Path]:
    config_src = DEFAULT_CURSOR_CONFIG
    if DEFAULT_CURSOR_HOME.is_symlink():
        home_src = DEFAULT_CURSOR_HOME.resolve()
    else:
        home_src = DEFAULT_CURSOR_HOME
    return config_src, home_src


def run_init(default_account: str = "work", *, force: bool = False) -> None:
    validate_account_name(default_account)
    ensure_root()

    if SHARED_CONFIG.exists() and not force:
        raise RuntimeError(
            "Already initialized. Shared config exists. Use --force to re-run init."
        )

    if not DEFAULT_CURSOR_CONFIG.is_dir():
        raise FileNotFoundError(f"Cursor config not found: {DEFAULT_CURSOR_CONFIG}")
    if not DEFAULT_CURSOR_HOME.exists():
        raise FileNotFoundError(f"Cursor home not found: {DEFAULT_CURSOR_HOME}")

    config_src, home_src = _resolve_cursor_home_for_backup()
    create_init_backup(config_src, home_src, DEFAULT_CURSOR_CLI)

    SHARED_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    SHARED_CURSOR_HOME.parent.mkdir(parents=True, exist_ok=True)

    if SHARED_CONFIG.exists():
        shutil.rmtree(SHARED_CONFIG)
    if SHARED_CURSOR_HOME.exists():
        shutil.rmtree(SHARED_CURSOR_HOME)

    shutil.move(str(DEFAULT_CURSOR_CONFIG), str(SHARED_CONFIG))
    if DEFAULT_CURSOR_HOME.is_symlink():
        DEFAULT_CURSOR_HOME.unlink()
    elif DEFAULT_CURSOR_HOME.exists():
        shutil.move(str(DEFAULT_CURSOR_HOME), str(SHARED_CURSOR_HOME))
    else:
        SHARED_CURSOR_HOME.mkdir(parents=True, exist_ok=True)

    if not DEFAULT_CURSOR_HOME.exists():
        DEFAULT_CURSOR_HOME.symlink_to(SHARED_CURSOR_HOME)

    if DEFAULT_CURSOR_CONFIG.exists():
        if DEFAULT_CURSOR_CONFIG.is_symlink():
            DEFAULT_CURSOR_CONFIG.unlink()
        else:
            shutil.rmtree(DEFAULT_CURSOR_CONFIG)
    DEFAULT_CURSOR_CONFIG.symlink_to(SHARED_CONFIG)

    cfg = AccountsConfig(default=default_account, accounts={default_account: {}})
    save_accounts(cfg)
    write_active(default_account)
    export_session_bundle(default_account)
    session_bundle_dir(default_account)

    log(f"Initialized cursor-switch with default account {default_account}")


def run_init_account(name: str) -> None:
    validate_account_name(name)
    ensure_root()
    if not SHARED_CONFIG.is_dir():
        raise RuntimeError("Run `cursor-switch init` first.")

    cfg = load_accounts()
    if name in cfg.accounts:
        raise RuntimeError(f"Account {name!r} already exists.")
    cfg.accounts[name] = {}
    save_accounts(cfg)
    session_bundle_dir(name).mkdir(parents=True, exist_ok=True)
    log(f"Registered account {name}")
