"""Custom exceptions for PyDaFab."""

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"
__version__ = "0.0.1"


class InvalidArgumentError(ValueError):
    """The argument provided is invalid."""

    def __str__(self):
        return f"Invalid argument: {self.name}"

    @property
    def name(self):
        (name,) = self.args
        return name


class ProductNotFoundError(RuntimeError):
    """The Product was not found."""

    def __str__(self):
        return f"No Product found for {self.name}"

    @property
    def name(self):
        (name,) = self.args
        return name


class AssetNotFoundError(RuntimeError):
    """The Asset was not found."""

    def __str__(self):
        name, product_id = self.args
        return f"No Asset found for {name} in product {product_id}"


class AssetFetchError(RuntimeError):
    """Fetching the Asset failed."""

    def __str__(self):
        return f"Failed to fetch Asset from {self.name}: {self.__cause__}"

    @property
    def name(self):
        (name,) = self.args
        return name


class AssetIntegrityError(RuntimeError):
    """An indexed or downloaded asset failed integrity validation."""

    def __str__(self):
        product_id, asset_name, reason = self.args
        return f"Asset integrity check failed for {product_id}/{asset_name}: {reason}"


class ProductFetchError(RuntimeError):
    """Fetching the Product failed."""

    def __str__(self):
        return f"Failed to fetch Product {self.name}: {self.__cause__}"

    @property
    def name(self):
        (name,) = self.args
        return name
