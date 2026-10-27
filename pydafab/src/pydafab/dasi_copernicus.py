from datetime import datetime
from typing import Self

from pystac import Item


"""
Sentinel-1: https://sentiwiki.copernicus.eu/web/s1-products
Sentinel-2: https://sentiwiki.copernicus.eu/web/s2-products

Sentinel-2 compact name (7 tokens):
  MMM_MSIXXX_YYYYMMDDHHMMSS_Nxxyy_ROOO_Txxxxx_<Product Discriminator>.SAFE
  e.g. S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809

    Mission (MMM):    S2C,Sentinel-2C (Launched Sept 2024)
    Level (MSIXXX):   MSIL2A,Level-2A (Bottom-of-Atmosphere Reflectance)
    Sensing Time:     20250123T230911,"Start of acquisition (Jan 23, 2025 at 23:09:11 UTC)"
    Baseline (Nxxyy): N0511,Processing Baseline version 05.11
    Orbit (ROOO):     R044,Relative Orbit Number 044
    Tile ID (Txxxxx): T01UBS,MGRS Tile identifier
    Discriminator:    20250124T013809,Unique ID (usually processing/generation time)

Sentinel-1 name (7 to 10 tokens): ESA products, and their RTC derivatives on the Microsoft
Planetary Computer, share the first seven tokens and differ only in the optional tail:
  MMM_BB_TTTR_LFPP_YYYYMMDDTHHMMSS_YYYYMMDDTHHMMSS_OOOOOO[_DDDDDD][_CCCC][_COG|_rtc]
  e.g. S1A_IW_GRDH_1SDV_20211220T182141_20211220T182206_041096_04E1DB_rtc   (MPC RTC)
       S1A_IW_GRDH_1SDV_20250601T234858_20250601T234923_059459_rtc          (MPC RTC)
       S1A_IW_GRDH_1SDV_20250610T171650_20250610T171715_059587_0765DA_D223_COG  (CDSE GRD)
       S1A_IW_SLC__1SDV_20250610T171649_20250610T171717_059587_0765DA_CEB6  (CDSE SLC)

    Mission (MMM):       S1A,"Sentinel-1A (also S1B, S1C, S1D)"
    Mode (BB):           IW,"Interferometric Wide swath (also SM, EW, WV; stripmap beams S1-S6; calibration RF/AN/EN)"
    Type/Res (TTTR):     GRDH,"Ground Range Detected, High resolution (types: RAW, SLC, GRD, OCN, ETA; res: F/H/M/_)"
    Class/Pol (LFPP):    1SDV,"Level 1, Standard class, Dual-pol Vertical (main VV + cross VH)"
                           L:  Processing level (0, 1, 2, A for ETAD)
                           F:  Product class (S=Standard, A=Annotation, N=Noise, C=Calibration, X=ETAD)
                           PP: Polarization (SH, SV, DH, DV, or single HH/HV/VV/VH)
    Sensing Start:       20211220T182141,"Start of acquisition (Dec 20, 2021 at 18:21:41 UTC)"
    Sensing Stop:        20211220T182206,"End of acquisition (Dec 20, 2021 at 18:22:06 UTC)"
    Absolute Orbit (O):  041096,"Absolute orbit number at product start time (000001-999999)"
    Mission Datatake:    04E1DB,"Mission datatake ID (hex); absent from many 2025 IDs, so it cannot key a product"
    Product Unique ID:   D223,"Checksum of the ESA product (hex); absent from RTC IDs"
    Tail:                rtc,"RTC derivative; COG marks the cloud-optimised ESA product"

    Slices of one datatake can share a start time, so the stop time keys a product.
    An RTC product carries its source GRD's identity, so only the collection, read from
    the tail, keeps the two apart.
"""


ITEM_ASSET = "item"

S2_COLLECTIONS = {"MSIL1C": "sentinel-2-l1c", "MSIL2A": "sentinel-2-l2a"}
S1_COLLECTIONS = {"GRD": "sentinel-1-grd", "SLC": "sentinel-1-slc"}


def _sanitize(value: object) -> str:
    s = str(value).split(";", 1)[0]
    return s.replace("/", "_").replace(":", "_")


class CopernicusKey(dict):
    def to_dasi_query(self) -> dict:
        """Convert to DASI query format. archive() takes scalars, list/retrieve() need lists.

        Values are lowercased: DASI stores keys lowercase but matches schema constraints
        against the query as given.
        """
        return {k: [v.lower()] for k, v in self.items()}

    @classmethod
    def from_product_id(
        cls, source: str, product_id: str, asset_name: str | None = None
    ) -> Self:
        mission = product_id.split("_", 1)[0]
        if mission.startswith("S2"):
            return cls._from_s2(source, product_id, asset_name)
        if mission.startswith("S1"):
            return cls._from_s1(source, product_id, asset_name)
        raise ValueError(f"Unknown mission prefix in product ID: {product_id}")

    @classmethod
    def item(cls, source: str, product_id: str) -> Self:
        """Key of the product's STAC document, archived beside its assets as a reserved asset."""
        key = cls.from_product_id(source, product_id, ITEM_ASSET)
        key["mediatype"] = "application_json"
        return key

    @classmethod
    def from_stac(cls, source: str, item: Item, asset_name: str | None = None) -> Self:
        key = cls.from_product_id(source, item.id, asset_name)
        if key["collection"] != item.collection_id:
            raise ValueError(f"Product {item.id} is in {item.collection_id}, but its ID names {key['collection']}")
        if asset_name is not None:
            key["mediatype"] = _sanitize(item.assets[asset_name].media_type)
        return key

    @classmethod
    def _from_s2(cls, source: str, stem: str, asset_name: str | None) -> Self:
        parts = stem.split("_")
        if len(parts) != 7:
            raise ValueError(f"Invalid Sentinel-2 product ID: {stem}")
        mission, level, datatake, baseline, orbit, tile, discriminator = parts
        if level not in S2_COLLECTIONS:
            raise ValueError(f"Unsupported Sentinel-2 product level {level!r}: {stem}")
        dt = datetime.strptime(datatake, "%Y%m%dT%H%M%S")
        key = cls(
            source=_sanitize(source),
            mission=mission,
            collection=S2_COLLECTIONS[level],
            level=level,
            gridcode=tile,
            procver=f"{baseline[1:3]}.{baseline[3:5]}",  # Nxxyy
            takedate=dt.strftime("%Y-%m-%d"),
            taketime=dt.strftime("%H%M%S"),
            procdate=discriminator,
            orbit=str(int(orbit[1:])),  # ROOO
        )
        if asset_name is not None:
            key["asset_name"] = _sanitize(asset_name)
        return key

    @classmethod
    def _from_s1(cls, source: str, stem: str, asset_name: str | None) -> Self:
        # The first four tokens are fixed width and padded with "_" (e.g. SLC__1SDV), so split by position.
        mission, mode, type_res, lcp = stem[0:3], stem[4:6], stem[7:11].rstrip("_"), stem[12:16]
        parts = stem[17:].split("_")
        if stem[3] + stem[6] + stem[11] + stem[16] != "____" or not 3 <= len(parts) <= 6:
            raise ValueError(f"Invalid Sentinel-1 product ID: {stem}")
        start, stop, abs_orbit = parts[:3]
        if parts[-1] == "rtc":
            collection = "sentinel-1-rtc"
        elif type_res[:3] in S1_COLLECTIONS:
            collection = S1_COLLECTIONS[type_res[:3]]
        else:
            raise ValueError(f"Unsupported Sentinel-1 product type {type_res!r}: {stem}")
        start_dt = datetime.strptime(start, "%Y%m%dT%H%M%S")
        stop_dt = datetime.strptime(stop, "%Y%m%dT%H%M%S")
        key = cls(
            source=_sanitize(source),
            mission=mission,
            collection=collection,
            mode=mode,
            type=type_res,
            takedate=start_dt.strftime("%Y-%m-%d"),
            polarization=lcp[2:],  # LFPP
            taketime=start_dt.strftime("%H%M%S"),
            stoptime=stop_dt.strftime("%H%M%S"),
            orbit=str(int(abs_orbit)),  # OOOOOO
        )
        if asset_name is not None:
            key["asset_name"] = _sanitize(asset_name)
        return key
