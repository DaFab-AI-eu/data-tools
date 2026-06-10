"""Ingest product and its assets from Copernicus STAC and archive using Dasi.

Example usage:
    python copernicus/ingest.py --product_id=S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809 --asset_names=WVP_10m,TCI_20m

"""

import argparse
import sys

import helpers

from pydafab import (
    AssetFetchError,
    AssetNotFoundError,
    CopernicusIngestor,
    DasiProductHandler,
    ProductFetchError,
    ProductNotFoundError,
)


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
        required=True,
    )
    argparse.Namespace(verbose=False)
    return arg_parser.parse_args()


def main():
    """Ingest product from Copernicus STAC and archive using Dasi."""

    args = parse_arguments()

    ingestor = CopernicusIngestor(verbose=args.verbose)

    try:
        product = ingestor.search_product(args.product_id, collections=[args.collections])

        handler = DasiProductHandler(ingestor, args.config_dir)

        modifier = helpers.ProductModifier()

        handler.archive_product(product, modifier)

        requested = [name for name in args.asset_names.split(",") if name]
        handler.archive_assets(product, requested, modifier)
    except (ProductNotFoundError, ProductFetchError, AssetNotFoundError, AssetFetchError) as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
