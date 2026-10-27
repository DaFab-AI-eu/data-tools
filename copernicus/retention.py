"""Reclaim DASI storage by deleting whole databases, oldest first.

Each immediate child of the store root (e.g. /data/root) is a self-contained FDB database
directory such as cdse:s2a:msil2a:2025-03-22, holding the STAC documents and assets of every
product acquired that day — the only unit that is safe to delete on the filesystem.

Retention acts only when free disk space falls below the configured threshold. It then
deletes databases oldest first (by directory mtime) until the free-space target is met or
the per-run delete-size cap is reached. Databases younger than the minimum age are never
deleted.

Pass --clear-all to wipe everything under the store root (the legacy behaviour). Without
--do-it=true every mode is a dry run that only reports what would be deleted.

Example usage:
    python copernicus/retention.py
    python copernicus/retention.py --root=/data/root --do-it=true
    python copernicus/retention.py --root=/data/root --clear-all --do-it=true

"""

import argparse
import logging
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

import yaml
from logging_setup import setup_logging

logger = logging.getLogger(__name__)

SIZE_UNITS = {
    "": 1,
    "b": 1,
    "k": 1024,
    "kb": 1024,
    "kib": 1024,
    "m": 1024**2,
    "mb": 1024**2,
    "mib": 1024**2,
    "g": 1024**3,
    "gb": 1024**3,
    "gib": 1024**3,
    "t": 1024**4,
    "tb": 1024**4,
    "tib": 1024**4,
    "p": 1024**5,
    "pb": 1024**5,
    "pib": 1024**5,
}

SECONDS_PER_DAY = 86400

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"


@dataclass(frozen=True)
class Policy:
    """Retention thresholds read from the YAML config."""

    min_free_percent: float
    delete_size: int
    min_age_days: int


@dataclass(frozen=True)
class Database:
    """An FDB database directory under the store root."""

    path: Path
    size: int
    mtime: float


def parse_arguments():
    arg_parser = argparse.ArgumentParser("retention_dasi_db")
    arg_parser.add_argument(
        "--root",
        type=Path,
        help="Dasi store root holding the database directories. default: /data/root",
        default=Path("/data/root"),
    )
    arg_parser.add_argument(
        "--config",
        type=Path,
        help="Retention policy YAML. default: /tools/copernicus/ingest/retention.yml",
        default=Path("/tools/copernicus/ingest/retention.yml"),
    )
    arg_parser.add_argument(
        "--do-it",
        choices=["true", "false"],
        help="Actually delete the items. default: false (dry run)",
        default="false",
    )
    arg_parser.add_argument(
        "--clear-all",
        action="store_true",
        help="Wipe everything under the store root, ignoring the retention policy.",
    )
    arg_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    return arg_parser.parse_args()


def format_size(num_bytes):
    size = float(num_bytes)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB"):
        if size < 1024 or unit == "PiB":
            return f"{size:.1f} {unit}"
        size /= 1024


def parse_size(value):
    """Parse a byte count from a plain number or a human string like '5GB' / '5GiB'."""
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().lower().replace(" ", "")
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([a-z]*)", text)
    if not match or match.group(2) not in SIZE_UNITS:
        raise SystemExit(f"Invalid size value in retention config: {value!r}")
    number, unit = match.groups()
    return int(float(number) * SIZE_UNITS[unit])


def load_policy(config_path):
    if not config_path.is_file():
        raise SystemExit(f"Retention config not found: {config_path}")
    data = yaml.safe_load(config_path.read_text()) or {}
    try:
        return Policy(
            min_free_percent=float(data["min_free_percent"]),
            delete_size=parse_size(data["delete_size"]),
            min_age_days=int(data["min_age_days"]),
        )
    except KeyError as e:
        raise SystemExit(f"Retention config missing key: {e}")


def dir_size(path):
    return sum(child.stat().st_size for child in path.rglob("*") if child.is_file() and not child.is_symlink())


def scan_databases(root):
    return [
        Database(path, dir_size(path), path.stat().st_mtime)
        for path in sorted(root.iterdir())
        if path.is_dir() and not path.is_symlink()
    ]


def select_for_deletion(databases, *, total, free, min_free_percent, delete_size, min_age_days, now):
    """Return the oldest-first databases to delete: free-target gated, size-capped, age-floored."""
    target_free = total * min_free_percent / 100
    cutoff = now - min_age_days * SECONDS_PER_DAY
    eligible = sorted((db for db in databases if db.mtime < cutoff), key=lambda db: db.mtime)

    selected = []
    freed = 0
    for db in eligible:
        if free + freed >= target_free or freed >= delete_size:
            break
        selected.append(db)
        freed += db.size
    return selected, freed, target_free


def run_retention(root, policy, do_it):
    usage = shutil.disk_usage(root)
    free_pct = usage.free / usage.total * 100

    logger.info("Store root: %s", root)
    logger.info(
        "Free space: %s of %s (%.1f%%), target %.1f%%",
        format_size(usage.free),
        format_size(usage.total),
        free_pct,
        policy.min_free_percent,
    )

    if free_pct >= policy.min_free_percent:
        logger.info("Free space above threshold; nothing to delete.")
        return

    databases = scan_databases(root)
    selected, freed, target_free = select_for_deletion(
        databases,
        total=usage.total,
        free=usage.free,
        min_free_percent=policy.min_free_percent,
        delete_size=policy.delete_size,
        min_age_days=policy.min_age_days,
        now=time.time(),
    )

    if not selected:
        logger.info("No databases older than %d days are eligible for deletion.", policy.min_age_days)
        return

    verb = "Deleting" if do_it else "Would delete"
    for db in selected:
        logger.info("%s: %s [%s]", verb, db.path.name, format_size(db.size))
        if do_it:
            shutil.rmtree(db.path)

    projected_pct = (usage.free + freed) / usage.total * 100
    logger.info("%d database(s), freeing %s (projected free %.1f%%)", len(selected), format_size(freed), projected_pct)
    if usage.free + freed < target_free:
        logger.warning(
            "Target of %.1f%% not reached this run (delete-size cap or age floor).",
            policy.min_free_percent,
        )
    if not do_it:
        logger.info("Dry run: pass --do-it=true to delete these databases.")


def run_clear_all(root, do_it):
    children = sorted(root.iterdir())
    logger.info("Clear-all under: %s", root)
    logger.info("Found %d items", len(children))

    for child in children:
        if do_it:
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
            logger.info("Deleted: %s", child)
        else:
            logger.info("Would delete: %s", child)

    if not do_it:
        logger.info("Dry run: pass --do-it=true to delete these items.")


def main():
    args = parse_arguments()
    setup_logging(args.verbose)
    do_it = args.do_it == "true"

    if not args.root.is_dir() or args.root.is_symlink():
        raise SystemExit(f"Dasi store root not found or unsafe (volume not mounted?): {args.root}")

    if args.clear_all:
        run_clear_all(args.root, do_it)
    else:
        run_retention(args.root, load_policy(args.config), do_it)


if __name__ == "__main__":
    main()
