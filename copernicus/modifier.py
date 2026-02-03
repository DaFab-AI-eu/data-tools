
import logging

"""Modifier for product and asset metadata."""
class ProductModifier:

    def modify_product_metadata(self, data: bytes) -> bytes:
        logging.debug("Modifying product metadata")
        return data


    def modify_asset_metadata(self, data: bytes) -> bytes:
        logging.debug("Modifying asset metadata")
        return data
