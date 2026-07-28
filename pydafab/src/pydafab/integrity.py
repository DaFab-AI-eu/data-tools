import hashlib
import hmac
from collections.abc import Callable
from typing import Any

from .errors import AssetIntegrityError


_MULTIHASHERS: dict[int, Callable[[bytes], Any]] = {
    0x12: hashlib.sha256,
    0x16: hashlib.sha3_256,
}


def validate_asset_data(
    product_id: str,
    asset_name: str,
    asset: Any,
    data: bytes,
    source: str,
) -> None:
    extra_fields = asset.extra_fields
    expected_size = extra_fields.get("file:size")
    try:
        expected_size = int(expected_size) if expected_size is not None else None
    except (TypeError, ValueError) as e:
        raise AssetIntegrityError(product_id, asset_name, "malformed file:size") from e

    if expected_size is not None and len(data) != expected_size:
        raise AssetIntegrityError(
            product_id,
            asset_name,
            f"{source} {len(data)} bytes, expected {expected_size}",
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
        raise AssetIntegrityError(product_id, asset_name, f"unsupported file:checksum algorithm {algorithm}")

    hasher = _MULTIHASHERS[multihash[0]]
    expected_digest = multihash[2:]
    if multihash[1] != len(expected_digest) or len(expected_digest) != hasher(b"").digest_size:
        raise AssetIntegrityError(product_id, asset_name, "malformed file:checksum length")

    if not hmac.compare_digest(hasher(data).digest(), expected_digest):
        raise AssetIntegrityError(product_id, asset_name, f"{source} checksum does not match file:checksum")