"""Ingest product and its assets from Copernicus STAC and archive using Dasi.

Example usage:
    python copernicus/ingest.py --product_id=S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809 --assets=WVP_10m,TCI_20m

"""

import argparse
import sys

import warnings

from pydafab.errors import AssetNotFoundError, ProductNotFoundError
from pydasi import Dasi

from pydafab import CopernicusIngestor

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"
__version__ = "0.0.1"
__author__ = "Metin Cakircali"
__email__ = "metin.cakircali@ecmwf.int"


def parse_arguments():
    arg_parser = argparse.ArgumentParser("ingest_metadata_copernicus_stac")
    arg_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    arg_parser.add_argument(
        "--product_id",
        type=str,
        help="Product ID to ingest from Copernicus STAC, e.g., S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809",
        required=True,
    )
    arg_parser.add_argument(
        "--assets",
        type=str,
        help="Comma-separated list of assets to ingest, e.g., WVP_10m,TCI_20m",
        required=True,
    )
    argparse.Namespace(verbose=False)
    return arg_parser.parse_args()


class ArchiveTool():

    def __init__(self, ingestor):
        self.__ingestor = ingestor
        self.__verbose = ingestor.verbose

    def archive_product(self, product):
        """Ingest product from Copernicus STAC and archive using Dasi."""

        if self.__verbose:
            print(f"Archiving product: {product.id}")

        try:
            key, data = self.__ingestor.fetch_product(product)
        except ProductNotFoundError:
            sys.exit(f"Product [{product.id}] not found!")

        dasi = Dasi("/tools/copernicus/ingest/metadata.yml")
        # dasi.archive(key, data)

        print(f"Archiving product: {product.id}\nkey: {key}")

        if self.__verbose:
            print(f"Finished archiving product: {product.id}")

    def archive_assets(self, product, asset_keys):
        """Given product, archive assets from Copernicus S3 using Dasi."""

        if self.__verbose:
            print(f"Archiving assets of product: {product.id}")

        dasi = Dasi("/tools/copernicus/ingest/assets.yml")

        for asset_key in asset_keys:
            try:
                key, data = self.__ingestor.fetch_asset(product, asset_key)
            except AssetNotFoundError:
                warnings.warn(
                    f"Asset [{asset_key}] not found in product [{product.id}]!"
                )
                continue

            print(f"Archiving key: {key} of product: {product.id}")
            dasi.archive(key, data)

        if self.__verbose:
            print(f"Finished archiving assets of product: {product.id}")


def main():
    """Ingest product from Copernicus STAC and archive using Dasi."""

    args = parse_arguments()

    ingestor = CopernicusIngestor(verbose=args.verbose)

    product = ingestor.find_product(args.product_id)

    archiver = ArchiveTool(ingestor)

    archiver.archive_product(product)

    archiver.archive_assets(product, args.assets.split(","))


if __name__ == "__main__":
    main()
