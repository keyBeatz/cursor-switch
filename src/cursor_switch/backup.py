from __future__ import annotations

import json
import os
import sys
import zipfile
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path

from cursor_switch.log import log
from cursor_switch.paths import DEFAULT_CURSOR_CLI

BACKUP_RETENTION = 7

CONFIG_DIRNAME = "config-Cursor"
CURSOR_HOME_DIRNAME = "cursor-home"
CONFIG_CLI_DIRNAME = "config-cursor-cli"

PROGRESS_BAR_WIDTH = 28


def project_root() -> Path:
    override = os.environ.get("CURSOR_SWITCH_PROJECT_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    here = Path(__file__).resolve().parent
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.home() / "Projects" / "cursor-switch"


BACKUPS_DIR = project_root() / "backups"


def ensure_backups_dir() -> Path:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    return BACKUPS_DIR


def _timestamp_local() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def backup_base_name(kind: str, *, detail: str) -> str:
    slug = detail.replace(" ", "-").replace("/", "-")
    return f"{_timestamp_local()}_{kind}_{slug}"


def format_bytes(num: int) -> str:
    if num >= 1024**3:
        return f"{num / 1024**3:.1f} GB"
    if num >= 1024**2:
        return f"{num / 1024**2:.1f} MB"
    if num >= 1024:
        return f"{num / 1024:.1f} KB"
    return f"{num} B"


def _resolve_source(path: Path) -> Path:
    if path.is_symlink():
        return path.resolve()
    return path


def _iter_files(root: Path, arc_prefix: str) -> Iterator[tuple[Path, str, int]]:
    root = _resolve_source(root)
    if not root.exists():
        return
    if root.is_file():
        yield root, f"{arc_prefix}/{root.name}", root.stat().st_size
        return
    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        resolved = _resolve_source(file_path)
        if not resolved.is_file():
            continue
        rel = resolved.relative_to(root)
        yield resolved, f"{arc_prefix}/{rel.as_posix()}", resolved.stat().st_size


def _collect_archive_entries(
    config_src: Path,
    home_src: Path,
    cli_src: Path | None = None,
) -> list[tuple[Path, str, int]]:
    entries: list[tuple[Path, str, int]] = []
    entries.extend(_iter_files(config_src, CONFIG_DIRNAME))
    entries.extend(_iter_files(home_src, CURSOR_HOME_DIRNAME))
    if cli_src is not None:
        entries.extend(_iter_files(cli_src, CONFIG_CLI_DIRNAME))
    return entries


def _render_progress(processed: int, total: int, label: str) -> None:
    pct = (processed / total * 100) if total else 100.0
    filled = int(PROGRESS_BAR_WIDTH * processed / total) if total else PROGRESS_BAR_WIDTH
    bar = "█" * filled + "░" * (PROGRESS_BAR_WIDTH - filled)
    short = label if len(label) <= 48 else "…" + label[-47:]
    line = (
        f"\r  [{bar}] {pct:5.1f}%  "
        f"{format_bytes(processed)}/{format_bytes(total)}  {short}"
    )
    print(line, end="", flush=True, file=sys.stderr)


def _build_readme_text(
    *,
    archive_name: str,
    kind: str,
    detail: str,
    config_src: Path,
    home_src: Path,
    cli_src: Path | None = None,
    extra: dict[str, str | None] | None = None,
) -> str:
    cli_src = cli_src if cli_src is not None else DEFAULT_CURSOR_CLI
    lines = [
        "Cursor Switch backup",
        "===================",
        "",
        f"Archive:         {archive_name}",
        f"Created (local): {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Created (UTC):   {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        f"Kind:            {kind}",
        f"Detail:          {detail}",
        "",
        "Contents inside the zip:",
        f"  {CONFIG_DIRNAME}/       — Cursor IDE user data (~/.config/Cursor)",
        f"  {CURSOR_HOME_DIRNAME}/  — Cursor home (~/.cursor)",
        f"  {CONFIG_CLI_DIRNAME}/   — Cursor CLI/agent auth (~/.config/cursor)",
        "  README.txt, meta.json",
        "",
        "Source paths at backup time:",
        f"  config:           {config_src}",
        f"  cursor-home:      {home_src}",
        f"  config-cursor-cli: {cli_src}",
        "",
    ]
    if extra:
        lines.append("Extra:")
        for key, value in extra.items():
            if value is not None:
                lines.append(f"  {key}: {value}")
        lines.append("")
    lines.extend(
        [
            "Restore:",
            f"  unzip {archive_name}",
            "  Then copy the three config-* folders back to the source paths above.",
            "  (Close Cursor first.)",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_zip_with_progress(
    zip_path: Path,
    file_entries: list[tuple[Path, str, int]],
    *,
    readme_text: str,
    meta: dict[str, object],
) -> None:
    total_bytes = sum(size for _, _, size in file_entries)
    file_count = len(file_entries)

    print(f"\nCreating backup archive: {zip_path.name}", file=sys.stderr)
    print(
        f"  {file_count:,} files, {format_bytes(total_bytes)} uncompressed",
        file=sys.stderr,
    )
    print("  Compressing…", file=sys.stderr)

    processed = 0
    large_threshold = 100 * 1024 * 1024

    with zipfile.ZipFile(
        zip_path,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=3,
    ) as archive:
        archive.writestr("README.txt", readme_text)
        archive.writestr("meta.json", json.dumps(meta, indent=2) + "\n")

        for index, (path, arcname, size) in enumerate(file_entries, start=1):
            if size >= large_threshold:
                print(
                    f"\n  Large file ({format_bytes(size)}): {arcname}",
                    file=sys.stderr,
                )
            archive.write(path, arcname=arcname)
            processed += size
            _render_progress(processed, total_bytes, arcname)

    print(file=sys.stderr)
    zip_size = zip_path.stat().st_size
    ratio = (zip_size / total_bytes * 100) if total_bytes else 0
    print(
        f"  Done: {format_bytes(zip_size)} on disk ({ratio:.0f}% of uncompressed)",
        file=sys.stderr,
    )


def create_full_backup(
    kind: str,
    detail: str,
    config_src: Path,
    home_src: Path,
    cli_src: Path | None = None,
    *,
    from_account: str | None = None,
    to_account: str | None = None,
) -> Path:
    ensure_backups_dir()
    base = backup_base_name(kind, detail=detail)
    zip_path = BACKUPS_DIR / f"{base}.zip"
    meta_path = BACKUPS_DIR / f"{base}.meta.json"
    readme_path = BACKUPS_DIR / f"{base}.txt"
    cli_src = cli_src if cli_src is not None else DEFAULT_CURSOR_CLI

    if zip_path.exists():
        raise RuntimeError(f"Backup already exists: {zip_path}")

    meta: dict[str, object] = {
        "kind": kind,
        "detail": detail,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "from_account": from_account,
        "to_account": to_account,
        "config_source": str(config_src),
        "cursor_home_source": str(home_src),
        "cursor_cli_source": str(cli_src),
        "config_dir": CONFIG_DIRNAME,
        "cursor_home_dir": CURSOR_HOME_DIRNAME,
        "cursor_cli_dir": CONFIG_CLI_DIRNAME,
        "archive": zip_path.name,
        "format": "zip",
    }
    readme_text = _build_readme_text(
        archive_name=zip_path.name,
        kind=kind,
        detail=detail,
        config_src=config_src,
        home_src=home_src,
        cli_src=cli_src,
        extra={"from_account": from_account, "to_account": to_account},
    )

    file_entries = _collect_archive_entries(config_src, home_src, cli_src)
    if not file_entries:
        raise RuntimeError(
            "Nothing to backup — config, cursor-home, and config-cursor-cli are missing or empty."
        )

    _write_zip_with_progress(zip_path, file_entries, readme_text=readme_text, meta=meta)

    meta["uncompressed_bytes"] = sum(size for _, _, size in file_entries)
    meta["compressed_bytes"] = zip_path.stat().st_size
    meta["file_count"] = len(file_entries)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    readme_path.write_text(readme_text, encoding="utf-8")

    prune_old_backups()
    log(f"Created backup archive {zip_path}")
    return zip_path


def create_init_backup(
    config_src: Path,
    home_src: Path,
    cli_src: Path | None = None,
) -> Path:
    return create_full_backup("init", "before-migration", config_src, home_src, cli_src)


def create_pre_switch_backup(
    from_account: str | None,
    to_account: str,
    config_src: Path,
    home_src: Path,
    cli_src: Path | None = None,
) -> Path:
    detail = f"{from_account}-to-{to_account}" if from_account else f"to-{to_account}"
    return create_full_backup(
        "pre-switch",
        detail,
        config_src,
        home_src,
        cli_src,
        from_account=from_account,
        to_account=to_account,
    )


def _backup_stems() -> list[str]:
    if not BACKUPS_DIR.is_dir():
        return []
    return sorted({p.stem for p in BACKUPS_DIR.glob("*.zip")}, reverse=True)


def prune_old_backups() -> None:
    for stem in _backup_stems()[BACKUP_RETENTION:]:
        for suffix in (".zip", ".meta.json", ".txt"):
            path = BACKUPS_DIR / f"{stem}{suffix}"
            if path.is_file():
                path.unlink()
                log(f"Pruned old backup {path.name}")


def list_backups() -> list[Path]:
    if not BACKUPS_DIR.is_dir():
        return []
    return sorted(BACKUPS_DIR.glob("*.zip"), key=lambda p: p.name, reverse=True)
