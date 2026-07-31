"""Reclaim DASI storage by deleting the oldest asset databases under a capacity policy.

The storage path contains the assets and metadata stores (e.g. /data, holding
/data/assets/root and /data/metadata/root). Each immediate child of a store root is a
self-contained FDB database directory (e.g. CDSE:S2A:MSIL2A:T48PWA); whole directories are
the only filesystem-safe unit to remove.

Retention acts only when free disk space falls below the configured threshold, then deletes
whole asset database directories oldest-first (by directory mtime) until the free-space target
is met or the per-run delete-size cap is reached, whichever comes first. Directories younger
than the minimum age are never deleted. Each deleted asset database also removes its aligned
(same-named) directory in the metadata store.

Pass --clear-all to wipe everything under both store roots (the legacy behaviour). Without
--do-it=true every mode is a dry run that only reports what would be deleted.

Example usage:
    python copernicus/retention.py
    python copernicus/retention.py --path=/data --do-it=true
    python copernicus/retention.py --path=/data --clear-all --do-it=true

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

STORE_NAMES = ("assets", "metadata")

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
    """An asset FDB database directory and its aligned metadata counterpart."""

    assets: Path
    metadata: Path
    size: int
    mtime: float


def parse_arguments():
    arg_parser = argparse.ArgumentParser("retention_dasi_db")
    arg_parser.add_argument(
        "--path",
        type=Path,
        help="Dasi storage path containing the assets and metadata stores. default: /data",
        default=Path("/data"),
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
        help="Wipe everything under both store roots, ignoring the retention policy.",
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


def validate_roots(storage_path):
    roots = {store: storage_path / store / "root" for store in STORE_NAMES}
    invalid = [root for root in roots.values() if not root.is_dir() or root.is_symlink()]
    if invalid:
        invalid_paths = ", ".join(str(path) for path in invalid)
        raise SystemExit(f"Dasi store root not found or unsafe (volume not mounted?): {invalid_paths}")
    return roots


def dir_size(path):
    return sum(child.stat().st_size for child in path.rglob("*") if child.is_file() and not child.is_symlink())


def scan_databases(assets_root, metadata_root):
    """List asset databases with their aligned metadata database and combined size.

    Every asset database must have a same-named metadata database; a missing counterpart
    means the store is in an unexpected state, so we fail loudly rather than proceed.
    """
    databases = []
    unaligned = []
    for assets in sorted(assets_root.iterdir()):
        if not assets.is_dir() or assets.is_symlink():
            continue
        metadata = metadata_root / assets.name
        if not metadata.is_dir() or metadata.is_symlink():
            unaligned.append(assets.name)
            continue
        size = dir_size(assets) + dir_size(metadata)
        databases.append(Database(assets, metadata, size, assets.stat().st_mtime))
    if unaligned:
        raise SystemExit(
            f"Asset databases missing an aligned metadata database under {metadata_root}: " + ", ".join(unaligned)
        )
    return databases


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


def run_retention(storage_path, roots, policy, do_it):
    usage = shutil.disk_usage(storage_path)
    free_pct = usage.free / usage.total * 100

    logger.info("Storage path: %s", storage_path)
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

    databases = scan_databases(roots["assets"], roots["metadata"])
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
        logger.info("%s: %s [%s]", verb, db.assets.name, format_size(db.size))
        if do_it:
            shutil.rmtree(db.assets)
            shutil.rmtree(db.metadata)

    projected_pct = (usage.free + freed) / usage.total * 100
    logger.info("%d database(s), freeing %s (projected free %.1f%%)", len(selected), format_size(freed), projected_pct)
    if usage.free + freed < target_free:
        logger.warning(
            "Target of %.1f%% not reached this run (delete-size cap or age floor).",
            policy.min_free_percent,
        )
    if not do_it:
        logger.info("Dry run: pass --do-it=true to delete these databases.")


def run_clear_all(roots, do_it):
    children = sorted(child for root in roots.values() for child in root.iterdir())
    logger.info("Clear-all under: %s", ", ".join(str(root) for root in roots.values()))
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

    if not args.path.is_dir():
        raise SystemExit(f"Dasi storage path not found (volume not mounted?): {args.path}")

    roots = validate_roots(args.path)

    if args.clear_all:
        run_clear_all(roots, do_it)
    else:
        run_retention(args.path, roots, load_policy(args.config), do_it)


if __name__ == "__main__":
    main()
