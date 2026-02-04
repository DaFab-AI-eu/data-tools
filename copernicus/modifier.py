import logging


class ProductModifier:
    """Modifier for product and asset metadata."""

    def modify_metadata(self, data: bytes) -> bytes:
        logging.debug("Modifying metadata")
        return data

    def modify_asset(self, asset_key: str, data: bytes) -> bytes:
        logging.debug(f"Modifying asset: {asset_key}")
        return data
