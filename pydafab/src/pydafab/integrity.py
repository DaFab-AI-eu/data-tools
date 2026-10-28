import hashlib
import hmac
from collections.abc import Callable
from typing import Any

from .errors import AssetIntegrityError

# Multihash prefix for a 16-byte MD5 digest
MD5_MULTIHASH_PREFIX = "d50110"

# Multihash prefix (varint algorithm code, then digest length) for each supported hash.
# Varints must be minimally encoded, so each prefix has exactly one valid form.
_MULTIHASHERS: dict[bytes, Callable[..., Any]] = {
    bytes.fromhex("1220"): hashlib.sha256,
    bytes.fromhex("1620"): hashlib.sha3_256,
    bytes.fromhex("d50110"): hashlib.md5,
}


def validate_asset_data(
    product_id: str,
    asset_name: str,
    data: bytes,
    expected_size: Any = None,
    checksum: Any = None,
) -> None:
    """Check data against the STAC file:size and file:checksum describing the Asset.

    Empty data always fails: Dasi accepts a zero-length record but cannot
    retrieve one. A None size or checksum is not checked. A malformed or
    unsupported one raises AssetIntegrityError, as does data that does not
    match it. The checksum is a hex-encoded multihash.
    """
    if not data:
        raise AssetIntegrityError(product_id, asset_name, "no data")

    if expected_size is not None:
        try:
            expected_size = int(expected_size)
        except (TypeError, ValueError) as e:
            raise AssetIntegrityError(product_id, asset_name, "malformed file:size") from e
        if len(data) != expected_size:
            raise AssetIntegrityError(
                product_id, asset_name, f"{len(data)} bytes, expected {expected_size}"
            )

    if checksum is None:
        return

    try:
        multihash = bytes.fromhex(checksum)
    except (TypeError, ValueError) as e:
        raise AssetIntegrityError(product_id, asset_name, "malformed file:checksum") from e

    for prefix, hasher in _MULTIHASHERS.items():
        if multihash.startswith(prefix) and len(multihash) == len(prefix) + hasher().digest_size:
            break
    else:
        raise AssetIntegrityError(product_id, asset_name, "unsupported or malformed file:checksum")

    if not hmac.compare_digest(hasher(data).digest(), multihash[len(prefix):]):
        raise AssetIntegrityError(product_id, asset_name, "checksum does not match file:checksum")
