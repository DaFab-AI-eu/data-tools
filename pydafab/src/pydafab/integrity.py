import hashlib
import hmac
from collections.abc import Callable
from typing import Any

from .errors import AssetIntegrityError

_MULTIHASHERS: dict[int, Callable[[bytes], Any]] = {
    0x12: hashlib.sha256,
    0x16: hashlib.sha3_256,
}


def validate_asset_data(product_id: str, asset_name: str, asset: Any, data: bytes) -> None:
    """Check data against the STAC file:size and file:checksum describing the Asset.

    Empty data always fails: Dasi accepts a zero-length record but cannot
    retrieve one. Absent fields are not checked. Malformed or unsupported
    ones raise AssetIntegrityError, as does data that does not match them.
    """
    if not data:
        raise AssetIntegrityError(product_id, asset_name, "no data")

    extra_fields = asset.extra_fields

    expected_size = extra_fields.get("file:size")
    if expected_size is not None:
        try:
            expected_size = int(expected_size)
        except (TypeError, ValueError) as e:
            raise AssetIntegrityError(product_id, asset_name, "malformed file:size") from e
        if len(data) != expected_size:
            raise AssetIntegrityError(
                product_id, asset_name, f"{len(data)} bytes, expected {expected_size}"
            )

    encoded = extra_fields.get("file:checksum")
    if encoded is None:
        return

    try:
        multihash = bytes.fromhex(encoded)
    except (TypeError, ValueError) as e:
        raise AssetIntegrityError(product_id, asset_name, "malformed file:checksum") from e

    if len(multihash) < 2 or multihash[0] not in _MULTIHASHERS:
        algorithm = f"0x{multihash[0]:02x}" if multihash else "missing"
        raise AssetIntegrityError(
            product_id, asset_name, f"unsupported file:checksum algorithm {algorithm}"
        )

    hasher = _MULTIHASHERS[multihash[0]]
    expected_digest = multihash[2:]
    if multihash[1] != len(expected_digest) or len(expected_digest) != hasher(b"").digest_size:
        raise AssetIntegrityError(product_id, asset_name, "malformed file:checksum length")

    if not hmac.compare_digest(hasher(data).digest(), expected_digest):
        raise AssetIntegrityError(product_id, asset_name, "checksum does not match file:checksum")
