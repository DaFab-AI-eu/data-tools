"""Retrieve a previously archived product and its assets from Dasi and save to local files.

Example usage:
    python copernicus/stage.py --collections=sentinel-2-l2a --product_id=S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809 --output_dir=/tmp
    python copernicus/stage.py --collections=sentinel-2-l2a --product_id=S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809 --output_dir=/tmp --asset_names=WVP_10m,TCI_20m

"""

import argparse
import logging
import os
import sys

from logging_setup import setup_logging
from pydafab import AssetNotFoundError, CopernicusIngestor, DasiProductHandler
from pydafab.helpers import media_subtype

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"

logger = logging.getLogger(__name__)


def parse_arguments():
    arg_parser = argparse.ArgumentParser("ingest_copernicus_product")
    arg_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    arg_parser.add_argument(
        "--config_dir",
        type=str,
        help="Path to the configuration directory for Dasi. default: /tools/copernicus/ingest",
        default="/tools/copernicus/ingest",
    )
    arg_parser.add_argument(
        "--output_dir",
        type=str,
        help="Directory to save the ingested product and assets. default: /tmp",
        required=True,
    )
    arg_parser.add_argument(
        "--collections",
        type=str,
        help="STAC collections to search in, e.g., sentinel-2-l2a",
        default="sentinel-2-l2a",
    )
    arg_parser.add_argument(
        "--product_id",
        type=str,
        help="Product ID to ingest from Copernicus STAC, e.g., S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809",
        required=True,
    )
    arg_parser.add_argument(
        "--asset_names",
        type=str,
        help="Comma-separated list of assets to ingest, e.g., WVP_10m,TCI_20m",
    )
    argparse.Namespace(verbose=False)
    return arg_parser.parse_args()


def main():
    """Pull product from Dasi."""

    args = parse_arguments()

    setup_logging(args.verbose)

    ingestor = CopernicusIngestor(verbose=args.verbose)
    handler = DasiProductHandler(ingestor.source, args.config_dir)

    os.makedirs(args.output_dir, exist_ok=True)

    found = False
    for metadata in handler.retrieve_metadata(args.product_id):
        output_file = os.path.join(args.output_dir, f"{args.product_id}.json")
        with open(output_file, "wb") as of:
            of.write(metadata)
        logger.info("Product metadata saved to: %s", output_file)
        found = True

    if not found:
        sys.exit(f"Product [{args.product_id}] not found!")

    if args.asset_names:
        try:
            for asset_name, key, data in handler.retrieve_assets(
                args.product_id, args.asset_names.split(",")
            ):
                ext = media_subtype(key["mediatype"])
                asset_output_file = os.path.join(
                    args.output_dir, f"{args.product_id}_{asset_name}.{ext}"
                )
                with open(asset_output_file, "wb") as of:
                    of.write(data)
                logger.info("Asset [%s] saved to: %s", asset_name, asset_output_file)
        except AssetNotFoundError as e:
            sys.exit(str(e))


if __name__ == "__main__":
    main()
