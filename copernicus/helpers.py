import logging


class ProductModifier:
    """Modifier for product and asset metadata."""

    def modify_product_metadata(self, key: dict, data: bytes) -> bytes:
        logging.debug(f"Modifying product metadata: {key}")
        return data

    def modify_asset(self, key: dict, data: bytes) -> bytes:
        logging.debug(f"Modifying asset: {key}")
        return data
