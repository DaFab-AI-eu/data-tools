"""Ingest product and its assets from Copernicus STAC and archive using Dasi.

Example usage:
    python copernicus/pull-from-dasi.py --product_id=S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809 --output_dir=/tmp
    python copernicus/pull-from-dasi.py --product_id=S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809 --output_dir=/tmp --asset_keys=WVP_10m,TCI_20m

"""

import argparse
import logging
import os
import sys

from pydafab import CopernicusIngestor, DasiProductHandler

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"


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
        "--product_id",
        type=str,
        help="Product ID to ingest from Copernicus STAC, e.g., S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809",
        required=True,
    )
    arg_parser.add_argument(
        "--asset_keys",
        type=str,
        help="Comma-separated list of assets to ingest, e.g., WVP_10m,TCI_20m",
    )
    argparse.Namespace(verbose=False)
    return arg_parser.parse_args()


def main():
    """Pull product from Dasi."""

    args = parse_arguments()

    ingestor = CopernicusIngestor(verbose=args.verbose)

    product = ingestor.search_product(args.product_id)

    if product is None:
        sys.exit(f"Product [{args.product_id}] not found!")

    tool = DasiProductHandler(ingestor, args.config_dir)

    metadata = tool.retrieve_metadata(product)

    if metadata:
        os.makedirs(args.output_dir, exist_ok=True)
        output_file = os.path.join(args.output_dir, f"{product.id}.json")
        with open(output_file, "wb") as of:
            of.write(metadata)
        logging.info(f"Product metadata saved to: {output_file}")

    # Asset retrieval is optional, only if asset keys are provided
    if args.asset_keys:
        assets = tool.retrieve_assets(product, args.asset_keys.split(","))
        for asset_key, asset_data in assets.items():
            if asset_data:
                asset_output_file = os.path.join(
                    args.output_dir, f"{product.id}_{asset_key}.asset"
                )
                with open(asset_output_file, "wb") as of:
                    of.write(asset_data)
                logging.info(f"Asset [{asset_key}] saved to: {asset_output_file}")
            else:
                logging.warning(
                    f"Asset [{asset_key}] not found for product [{product.id}]!"
                )


if __name__ == "__main__":
    main()
