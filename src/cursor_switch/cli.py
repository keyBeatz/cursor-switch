from __future__ import annotations

import argparse
import sys

from cursor_switch import __version__
from cursor_switch.config import list_account_names, load_accounts, read_active
from cursor_switch.cursor_proc import cursor_agent_running, cursor_running, load_session_folders
from cursor_switch.init_cmd import run_init, run_init_account
from cursor_switch.backup import BACKUP_RETENTION, BACKUPS_DIR, format_bytes, list_backups
from cursor_switch.paths import (
    ACCOUNTS_FILE,
    DEFAULT_CURSOR_CONFIG,
    ROOT,
    SHARED_CONFIG,
    STATE_DB,
    is_initialized,
)
from cursor_switch.repair_cmd import run_repair
from cursor_switch.switch_cmd import run_export_auth, run_switch


def _cmd_init(args: argparse.Namespace) -> None:
    run_init(args.account, force=args.force)


def _cmd_init_account(args: argparse.Namespace) -> None:
    run_init_account(args.account)


def _cmd_switch(args: argparse.Namespace) -> None:
    run_switch(
        args.account,
        launch=not args.no_launch,
        skip_backup=args.skip_backup,
    )


def _cmd_export_auth(args: argparse.Namespace) -> None:
    run_export_auth(args.account)


def _cmd_launch(args: argparse.Namespace) -> None:
    if args.account:
        run_switch(args.account, launch=False)
    folders = list(args.paths) or load_session_folders(SESSION_FILE)
    from cursor_switch.cursor_proc import launch_cursor
    from cursor_switch.paths import SHARED_CONFIG, SHARED_EXTENSIONS

    launch_cursor(SHARED_CONFIG, SHARED_EXTENSIONS, folders or None)


def _cmd_status(_: argparse.Namespace) -> None:
    initialized = is_initialized()
    active = read_active()
    cfg = load_accounts() if ACCOUNTS_FILE.exists() else None
    print(f"cursor-switch {__version__}")
    print(f"Root:        {ROOT}")
    print(f"Initialized: {initialized}")
    print(f"Active:      {active or '(none)'}")
    print(f"Cursor:      {'running' if cursor_running() else 'not running'}")
    print(
        f"cursor-agent: {'running' if cursor_agent_running() else 'not running'}"
    )
    if cfg:
        for name in list_account_names(cfg):
            email = cfg.accounts[name].get("email", "")
            bundle = ROOT / "accounts" / name / "session-bundle" / "meta.json"
            if bundle.exists():
                import json

                meta = json.loads(bundle.read_text(encoding="utf-8"))
                email = meta.get("email") or email
            marker = " *" if name == active else ""
            print(f"  - {name}{marker}: {email or '(no bundle yet)'}")
    if DEFAULT_CURSOR_CONFIG.is_symlink():
        target = DEFAULT_CURSOR_CONFIG.resolve()
        ok = target == SHARED_CONFIG.resolve()
        print(f"Config link: {DEFAULT_CURSOR_CONFIG} -> {target} ({'ok' if ok else 'WRONG'})")
    elif DEFAULT_CURSOR_CONFIG.exists():
        print(
            f"Config link: {DEFAULT_CURSOR_CONFIG} is a real directory (not shared). "
            "Run `cursor-switch repair` or launch via `cursor-switch launch`."
        )
    else:
        print(f"Config link: missing (run `cursor-switch repair`)")
    if STATE_DB.exists():
        size_mb = STATE_DB.stat().st_size / (1024 * 1024)
        print(f"State DB:    {STATE_DB} ({size_mb:.0f} MB)")
    print(f"Backups dir: {BACKUPS_DIR}")
    backups = list_backups()
    print(f"Backups:     {len(backups)} kept (max {BACKUP_RETENTION})")
    for entry in backups[:3]:
        size = format_bytes(entry.stat().st_size)
        print(f"  - {entry.name} ({size})")
    if len(backups) > 3:
        print(f"  ... and {len(backups) - 3} more")


def _cmd_repair(_: argparse.Namespace) -> None:
    run_repair()


def _cmd_list(_: argparse.Namespace) -> None:
    cfg = load_accounts()
    active = read_active()
    for name in list_account_names(cfg):
        suffix = " (active)" if name == active else ""
        print(f"{name}{suffix}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cursor-switch",
        description="Switch Cursor IDE accounts with shared chats and plans.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init", help="Migrate current Cursor install into shared layout")
    init_p.add_argument(
        "account",
        nargs="?",
        default="work",
        help="Default account name (default: work)",
    )
    init_p.add_argument("--force", action="store_true", help="Re-run init even if shared config exists")
    init_p.set_defaults(func=_cmd_init)

    init_acc = sub.add_parser("init-account", help="Register another account slot")
    init_acc.add_argument("account", help="Account name")
    init_acc.set_defaults(func=_cmd_init_account)

    export_p = sub.add_parser("export-auth", help="Save current auth tokens into session bundle")
    export_p.add_argument("account", nargs="?", help="Account name (default: active)")
    export_p.set_defaults(func=_cmd_export_auth)

    launch_p = sub.add_parser("launch", help="Launch Cursor with shared config")
    launch_p.add_argument("account", nargs="?", help="Switch to account before launch")
    launch_p.add_argument("paths", nargs="*", help="Folders to open")
    launch_p.set_defaults(func=_cmd_launch)

    sub.add_parser("status", help="Show configuration status").set_defaults(func=_cmd_status)
    sub.add_parser("list", help="List accounts").set_defaults(func=_cmd_list)
    sub.add_parser(
        "repair",
        help="Fix accounts.toml registry and ~/.config/Cursor symlink",
    ).set_defaults(func=_cmd_repair)

    switch_p = sub.add_parser("switch", help="Switch account (alias: default command)")
    switch_p.add_argument("account", help="Target account")
    switch_p.add_argument("--no-launch", action="store_true", help="Switch without starting Cursor")
    switch_p.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip the full zip backup before switching (faster; less safe)",
    )
    switch_p.set_defaults(func=_cmd_switch)

    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Shorthand: `cursor-switch work` -> `cursor-switch switch work`
    if (
        argv
        and not argv[0].startswith("-")
        and argv[0] not in {
            "init",
            "init-account",
            "export-auth",
            "launch",
            "status",
            "list",
            "repair",
            "switch",
        }
    ):
        argv = ["switch", *argv]

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (RuntimeError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
