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

Sentinel-1 compact name (9 tokens):
  MMM_BB_TTTR_LFPP_YYYYMMDDTHHMMSS_YYYYMMDDTHHMMSS_OOOOOO_DDDDDD_CCCC[.SAFE]
  e.g. S1A_IW_GRDH_1SDV_20230516T152430_20230516T152455_123456_ABCDEF_1234

    Mission (MMM):       S1A,"Sentinel-1A (also S1B, S1C)"
    Mode (BB):           IW,"Interferometric Wide swath (also SM, EW, WV; stripmap beams S1-S6; calibration RF/AN/EN)"
    Type/Res (TTTR):     GRDH,"Ground Range Detected, High resolution (types: RAW, SLC, GRD, OCN, ETA; res: F/H/M/_)"
    Class/Pol (LFPP):    1SDV,"Level 1, Standard class, Dual-pol Vertical (main VV + cross VH)"
                           L:  Processing level (0, 1, 2, A for ETAD)
                           F:  Product class (S=Standard, A=Annotation, N=Noise, C=Calibration, X=ETAD)
                           PP: Polarization (SH, SV, DH, DV, or single HH/HV/VV/VH)
    Sensing Start:       20230516T152430,"Start of acquisition (May 16, 2023 at 15:24:30 UTC)"
    Sensing Stop:        20230516T152455,"End of acquisition (May 16, 2023 at 15:24:55 UTC)"
    Absolute Orbit (O):  123456,"Absolute orbit number at product start time (000001-999999)"
    Mission Datatake:    ABCDEF,"Mission datatake ID uniquely identifying the SAR collection event (hex, 000001-FFFFFF)"
    Product Unique (C):  1234,"CRC-16 computed over the manifest file (hex, 0000-FFFF)"
"""


def _sanitize(value: object) -> str:
    return str(value).replace("/", "_").replace(":", "_")


class DasiKey(dict):

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
    def from_stac(cls, source: str, item: Item, asset_name: str | None = None) -> Self:
        return cls.from_product_id(source, item.id, asset_name)

    @classmethod
    def _from_s2(cls, source: str, stem: str, asset_name: str | None) -> Self:
        parts = stem.split("_")
        if len(parts) != 7:
            raise ValueError(f"Invalid Sentinel-2 product ID: {stem}")
        mission, _level, datatake, baseline, orbit, tile, discriminator = parts
        dt = datetime.strptime(datatake, "%Y%m%dT%H%M%S")
        key = cls(
            source=_sanitize(source),
            platform=mission,
            procver=f"{baseline[1:3]}.{baseline[3:5]}",  # Nxxyy
            gridcode=tile,
            takedate=dt.strftime("%Y-%m-%d"),
            taketime=dt.strftime("%H%M%S"),
            orbit=str(int(orbit[1:])),  # ROOO
            procdate=discriminator,
        )
        if asset_name is not None:
            key["asset_name"] = _sanitize(asset_name)
        return key

    @classmethod
    def _from_s1(cls, source: str, stem: str, asset_name: str | None) -> Self:
        parts = stem.split("_")
        if len(parts) != 9:
            raise ValueError(f"Invalid Sentinel-1 product ID: {stem}")
        mission, mode, type_res, lcp, start, _stop, abs_orbit, datatake, _crc = parts
        dt = datetime.strptime(start, "%Y%m%dT%H%M%S")
        key = cls(
            source=_sanitize(source),
            platform=mission,
            mode=mode,
            type=type_res,
            polarization=lcp[2:],  # LFPP
            takedate=dt.strftime("%Y-%m-%d"),
            taketime=dt.strftime("%H%M%S"),
            orbit=str(int(abs_orbit)),  # OOOOOO
            datatake=datatake,
        )
        if asset_name is not None:
            key["asset_name"] = _sanitize(asset_name)
        return key
