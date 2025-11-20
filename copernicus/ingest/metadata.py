"""Ingest metadata from Copernicus STAC and archive using Dasi.

Example usage:
    python copernicus/ingest/metadata.py --product_id=S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809

"""

import argparse
import warnings

from pydasi import Dasi

from pydafab import CopernicusIngestor

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"
__version__ = "0.0.1"
__author__ = "Metin Cakircali"
__email__ = "metin.cakircali@ecmwf.int"


def _parse_arguments():
    arg_parser = argparse.ArgumentParser("ingest_metadata_copernicus_stac")
    arg_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    arg_parser.add_argument(
        "--product_id",
        type=str,
        required=True,
        help="Product ID to ingest from Copernicus STAC, e.g., S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809",
    )
    argparse.Namespace(verbose=False)
    return arg_parser.parse_args()


def main():
    """Ingest metadata from Copernicus STAC and archive using Dasi."""

    args = _parse_arguments()

    if args.verbose:
        print(f"Ingesting metadata of product: {args.product_id}")

    # create a metadata key for the archive
    [key, data] = CopernicusIngestor().retrieve(args.product_id)

    if data is None:
        warnings.warn("Product metadata not found!")
    else:
        dasi = Dasi("/tools/copernicus/ingest/metadata.yml")
        dasi.archive(key, data)


if __name__ == "__main__":
    main()
