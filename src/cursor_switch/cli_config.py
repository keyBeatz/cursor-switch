from __future__ import annotations

import shutil
from pathlib import Path

from cursor_switch.log import log
from cursor_switch.paths import DEFAULT_CURSOR_CLI

BUNDLE_CLI_DIR = "cursor-cli"


def export_cli_config(bundle: Path) -> list[str]:
    """Copy ~/.config/cursor into session bundle. Returns exported filenames."""
    src = DEFAULT_CURSOR_CLI
    dest = bundle / BUNDLE_CLI_DIR
    exported: list[str] = []
    if not src.is_dir():
        return exported
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    exported = [p.name for p in dest.iterdir() if p.is_file()]
    if exported:
        log(f"Exported cursor-cli files: {', '.join(exported)}")
    return exported


def import_cli_config(bundle: Path) -> None:
    """Restore ~/.config/cursor from session bundle."""
    src = bundle / BUNDLE_CLI_DIR
    if not src.is_dir():
        return
    DEFAULT_CURSOR_CLI.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        if item.is_file():
            shutil.copy2(item, DEFAULT_CURSOR_CLI / item.name)
    log(f"Imported cursor-cli config into {DEFAULT_CURSOR_CLI}")


def clear_cli_config() -> None:
    """Remove CLI auth so cursor-agent prompts for login."""
    if DEFAULT_CURSOR_CLI.is_dir():
        shutil.rmtree(DEFAULT_CURSOR_CLI)
        log(f"Cleared cursor-cli config at {DEFAULT_CURSOR_CLI}")
