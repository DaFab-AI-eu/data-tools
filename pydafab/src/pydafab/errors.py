"""Custom exceptions for PyDaFab."""

__copyright__ = "Copyright 2025, ECMWF"
__license__ = "Apache License Version 2.0"
__version__ = "0.0.1"
__author__ = "Metin Cakircali"
__email__ = "metin.cakircali@ecmwf.int"


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
        return f"No Asset found for {self.name}"

    @property
    def name(self):
        (name,) = self.args
        return name
