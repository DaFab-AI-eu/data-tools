"""Retrieve a previously archived product and its assets from Dasi and save to local files.

Example usage:
    python copernicus/stage.py --collections=sentinel-2-l2a --product_id=S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809 --output_dir=/tmp
    python copernicus/stage.py --collections=sentinel-2-l2a --product_id=S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809 --output_dir=/tmp --asset_names=WVP_10m,TCI_20m

"""

import argparse
import json
import logging
import os
import sys

from pystac import Item

from logging_setup import setup_logging
from pydafab import AssetIntegrityError, AssetNotFoundError, CopernicusIngestor, DasiProductHandler
from pydafab.helpers import media_subtype
from pydafab.integrity import validate_asset_data

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"

logger = logging.getLogger(__name__)


def _validate_retrieved_assets(product: Item, retrieved: list[tuple[str, dict, bytes]]) -> None:
    for asset_name, _key, data in retrieved:
        if asset_name not in product.assets:
            raise AssetNotFoundError(asset_name, product.id)
        validate_asset_data(
            product.id,
            asset_name,
            product.assets[asset_name],
            data,
            "retrieved",
        )


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
    handler = DasiProductHandler(ingestor, args.config_dir)

    os.makedirs(args.output_dir, exist_ok=True)

    product = None
    for metadata in handler.retrieve_metadata(args.product_id):
        if product is not None:
            sys.exit(f"Multiple metadata records found for product [{args.product_id}]")
        product = Item.from_dict(json.loads(metadata))
        if product.id != args.product_id:
            sys.exit(f"Archived metadata ID [{product.id}] does not match [{args.product_id}]")
        output_file = os.path.join(args.output_dir, f"{args.product_id}.json")
        with open(output_file, "wb") as of:
            of.write(metadata)
        logger.info("Product metadata saved to: %s", output_file)

    if product is None:
        sys.exit(f"Product [{args.product_id}] not found!")

    if args.asset_names:
        try:
            retrieved = list(handler.retrieve_assets(args.product_id, args.asset_names.split(",")))
            _validate_retrieved_assets(product, retrieved)

            for asset_name, key, data in retrieved:
                ext = media_subtype(key["mediatype"])
                asset_output_file = os.path.join(
                    args.output_dir, f"{args.product_id}_{asset_name}.{ext}"
                )
                with open(asset_output_file, "wb") as of:
                    of.write(data)
                logger.info("Asset [%s] saved to: %s", asset_name, asset_output_file)
        except (AssetNotFoundError, AssetIntegrityError) as e:
            sys.exit(str(e))


if __name__ == "__main__":
    main()
