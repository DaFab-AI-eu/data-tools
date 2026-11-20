"""Reclaim DASI storage by wiping whole FDB databases, least recently used first.

A database (e.g. /data/root/cdse:s2a:sentinel-2-l2a:msil2a:202503) holds every product
acquired in one month.

Does nothing unless free disk space is below min_free_percent (default 0: disabled). It
then wipes databases, longest idle first, until their sizes add up to the target.
    min_idle_days (default 30): never wipe databases read or written this recently
    delete_size_gb (default unlimited): stop a run once this much has been wiped
Access times and sizes come from FDB. Databases with no recorded access are never wiped.

Exits 3 if free space would still be below the target after wiping every idle database.

--clear-all wipes everything under the store root, ignoring the policy. Without
--do-it=true every mode is a dry run.

Example usage:
    python copernicus/retention.py
    python copernicus/retention.py --root=/data/root --do-it=true
    python copernicus/retention.py --root=/data/root --clear-all --do-it=true

"""

import argparse
import json
import logging
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml
from logging_setup import setup_logging
from pydasi import Dasi

logger = logging.getLogger(__name__)

GIB = 1024**3
SECONDS_PER_DAY = 86400
EXIT_TARGET_OUT_OF_REACH = 3
DEFAULT_POLICY = {"min_free_percent": 0, "min_idle_days": 30, "delete_size_gb": math.inf}

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"


def _parse_arguments() -> argparse.Namespace:
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
        help="Retention policy YAML; a missing file means every default. default: /tools/copernicus/ingest/retention.yml",
        default=Path("/tools/copernicus/ingest/retention.yml"),
    )
    arg_parser.add_argument(
        "--dasi-config",
        type=Path,
        help="Dasi configuration of the store. default: /tools/copernicus/ingest/dasi.yml",
        default=Path("/tools/copernicus/ingest/dasi.yml"),
    )
    arg_parser.add_argument(
        "--do-it",
        choices=["true", "false"],
        help="Wipe for real. default: false (dry run)",
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


def _full_date_key(key: dict[str, str]) -> dict[str, str]:
    """A database key as FDB requests accept it.

    FDB reports takedate as YearMonth; queries need a full date, so we expand 202503 to 2025-03-00, a day no product has.
    """
    month = key["takedate"]
    return {**key, "takedate": f"{month[:4]}-{month[4:]}-00"}


def _run_retention(root: Path, dasi_config: Path, policy: dict[str, float], do_it: bool) -> None:
    usage = shutil.disk_usage(root)
    target_free = usage.total * policy["min_free_percent"] / 100
    delete_size = policy["delete_size_gb"] * GIB

    logger.info(
        "Free space: %.1f of %.1f GiB (%.1f%%), target %.1f%%",
        usage.free / GIB,
        usage.total / GIB,
        usage.free / usage.total * 100,
        policy["min_free_percent"],
    )
    if usage.free >= target_free:
        logger.info("Free space above threshold; nothing to delete.")
        return

    idle = json.loads(
        subprocess.check_output(
            ["fdb-last-access", f"--config={dasi_config}", "--all", "--json", f"--older-than={policy['min_idle_days']}d"]
        )
    )
    dasi = Dasi(str(dasi_config))
    freed = 0
    for database in sorted(idle, key=lambda database: database["age"], reverse=True):
        if usage.free + freed >= target_free or freed >= delete_size:
            break
        key = _full_date_key(database["key"])
        stats = subprocess.check_output(
            ["fdb-stats", f"--config={dasi_config}", "--raw", "--minimum-keys=", ",".join(f"{k}={v}" for k, v in key.items())],
            text=True,
        )
        [total] = re.findall(r"^Total size\s*: ([\d,]+)", stats, re.MULTILINE)
        size = int(total.replace(",", ""))
        logger.info(
            "%s: %s [%.1f GiB, idle %d days]",
            "Wiping" if do_it else "Would wipe",
            ":".join(database["key"].values()),
            size / GIB,
            database["age"] // SECONDS_PER_DAY,
        )
        if do_it:
            for element in dasi.wipe({k: [v] for k, v in key.items()}, doit=True):
                logger.debug("%s", element)
        freed += size

    logger.info("Freeing %.1f GiB (projected free %.1f%%)", freed / GIB, (usage.free + freed) / usage.total * 100)
    if not do_it:
        logger.info("Dry run: pass --do-it=true to wipe these databases.")
    if usage.free + freed < target_free and freed < delete_size:
        logger.error("No idle databases left to wipe; free space stays below the target.")
        sys.exit(EXIT_TARGET_OUT_OF_REACH)


def _run_clear_all(root: Path, do_it: bool) -> None:
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


def main() -> None:
    args = _parse_arguments()
    setup_logging(args.verbose)
    do_it = args.do_it == "true"

    if not args.root.is_dir() or args.root.is_symlink():
        raise SystemExit(f"Dasi store root not found or unsafe (volume not mounted?): {args.root}")

    if args.clear_all:
        _run_clear_all(args.root, do_it)
    else:
        settings = yaml.safe_load(args.config.read_text()) if args.config.is_file() else None
        _run_retention(args.root, args.dasi_config, DEFAULT_POLICY | (settings or {}), do_it)


if __name__ == "__main__":
    main()
