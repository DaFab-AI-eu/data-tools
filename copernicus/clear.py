"""Clear the Dasi store by deleting everything under its storage path.

The storage path is the directory that contains both the assets and metadata
stores (e.g. /data, holding /data/assets/root and /data/metadata/root). Without
--do-it=true this is a dry run that only reports what would be deleted.

Example usage:
    python copernicus/clear.py
    python copernicus/clear.py --path=/data --do-it=true

"""

import argparse
import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

STORE_NAMES = ("assets", "metadata")

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"


def parse_arguments():
    arg_parser = argparse.ArgumentParser("clear_dasi_db")
    arg_parser.add_argument(
        "--path",
        type=Path,
        help="Dasi storage path containing the assets and metadata stores. default: /data",
        default=Path("/data"),
    )
    arg_parser.add_argument(
        "--do-it",
        choices=["true", "false"],
        help="Actually delete the items. default: false (dry run)",
        default="false",
    )
    return arg_parser.parse_args()


def format_size(num_bytes):
    size = float(num_bytes)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB", "PiB"):
        if size < 1024 or unit == "PiB":
            return f"{size:.1f} {unit}"
        size /= 1024


def store_items(storage_path):
    store_roots = [storage_path / store / "root" for store in STORE_NAMES]
    invalid = [root for root in store_roots if not root.is_dir() or root.is_symlink()]
    if invalid:
        invalid_paths = ", ".join(str(path) for path in invalid)
        raise SystemExit(f"Dasi store root not found or unsafe (volume not mounted?): {invalid_paths}")

    return sorted(child for root in store_roots for child in root.iterdir())


def main():
    args = parse_arguments()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    do_it = args.do_it == "true"

    if not args.path.is_dir():
        raise SystemExit(f"Dasi storage path not found (volume not mounted?): {args.path}")

    items = store_items(args.path)

    logger.info("Storage path: %s", args.path)
    logger.info("Found %d items", len(items))

    store_files = (
        path
        for store in STORE_NAMES
        for path in (args.path / store / "root").rglob("*")
        if path.is_file() and not path.is_symlink()
    )
    used = sum(path.stat().st_size for path in store_files)
    free = shutil.disk_usage(args.path).free
    logger.info("DASI used: %s", format_size(used))
    logger.info("Free space: %s", format_size(free))

    if not do_it:
        for child in items:
            logger.info("Would delete: %s", child)
        logger.info("Dry run: pass --do-it=true to delete these items.")
    else:
        for child in items:
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
            logger.info("Deleted: %s", child)


if __name__ == "__main__":
    main()
