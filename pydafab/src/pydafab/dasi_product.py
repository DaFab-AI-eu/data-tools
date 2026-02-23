import logging
from datetime import datetime

from pystac import Asset, Item, asset
from typing import overload

logger = logging.getLogger(__name__)


"""
https://sentiwiki.copernicus.eu/web/s2-products

Compact Naming Convention
The compact naming convention of Sentinel-2 User products is arranged as follows:

MMM_MSIXXX_YYYYMMDDHHMMSS_Nxxyy_ROOO_Txxxxx_<Product Discriminator>.SAFE
example: S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809

Mission (MMM):    S2C,Sentinel-2C (Launched Sept 2024)
Level (MSIXXX):   MSIL2A,Level-2A (Bottom-of-Atmosphere Reflectance)
Sensing Time:     20250123T230911,"Start of acquisition (Jan 23, 2025 at 23:09:11 UTC)"
Baseline (Nxxyy): N0511,Processing Baseline version 05.11
Orbit (ROOO):     R044,Relative Orbit Number 044
Tile ID (Txxxxx): T01UBS,MGRS Tile identifier
Discriminator:    20250124T013809,Unique ID (usually processing/generation time)
"""


class DasiProduct:

    @overload
    def __init__(self, *, source: str, product_id: str): ...

    @overload
    def __init__(self, *, source: str, product: Item): ...

    def __init__(self, source: str = "CDSE", product_id: str | None = None, product: Item | None = None):

        if (product_id is not None) == (product is not None):
            raise ValueError("Exactly one of 'product_id' or 'product' must be provided.")

        if product:
            self._key = {
                "source": source,
                "collection": getattr(product, "collection_id", "null"),
                "platform": product.properties["platform"],
                "instruments": product.properties["instruments"][0],
                "procver": product.properties["processing:version"],
                "gridcode": product.properties["grid:code"],
                "orbit": product.properties["sat:relative_orbit"],
            }
            # Processing date and time format: YYYYMMDDTHHMMSS
            dt = datetime.fromisoformat(product.properties["processing:datetime"])
            self._key["procdate"] = dt.strftime("%Y%m%dT%H%M%S")
            # Acquisition date and time format: YYYY-MM-DD and HHMMSS
            dt = datetime.fromisoformat(product.properties["datetime"])
            self._key["takedate"] = dt.strftime("%Y-%m-%d")
            self._key["taketime"] = dt.strftime("%H%M%S")
        elif product_id:
            # S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809
            parts = product_id.split("_")
            self._key = {
                "source": source,
                "mission": parts[0],
                "level": parts[1],
                "datatake": parts[2],
                "baseline": parts[3],
                "orbit": parts[4],
                "tile": parts[5],
                "discriminator": parts[6],
            }
        else:
            raise ValueError("Either 'product_id' or 'product' must be provided.")

    def _fix(self):
        for fix in [("/", "_"), (":", "_")]:
            for k, v in self._key.items():
                self._key[k] = str(v).replace(*fix)

    @property
    def key(self):
        self._fix()
        return self._key

    def set_asset(self, asset: Asset):

        self._key["gsd"] = asset.extra_fields.get("gsd", "0")
        self._key["project"] = getattr(asset.ext.proj, "code", "null")
        self._key["mediatype"] = getattr(asset, "media_type", "null")

        return self.key
