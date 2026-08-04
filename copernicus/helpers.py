import logging

logger = logging.getLogger(__name__)


class ProductModifier:
    """Modifier for product and asset metadata."""

    def modify_product_metadata(self, key: dict, data: bytes) -> bytes:
        logger.debug("Modifying product metadata: %s", key)
        return data

    def modify_asset(self, key: dict, data: bytes) -> bytes:
        logger.debug("Modifying asset: %s", key)
        return data
