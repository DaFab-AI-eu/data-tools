import hashlib
from unittest.mock import MagicMock

import pytest

from pydafab.errors import AssetIntegrityError
from pydafab.integrity import validate_asset_data


@pytest.mark.parametrize(
    ("code", "digest"),
    [(0x12, hashlib.sha256), (0x16, hashlib.sha3_256)],
)
def test_accepts_supported_multihash_checksums(code, digest):
    data = b"data"
    asset = MagicMock(
        extra_fields={
            "file:size": len(data),
            "file:checksum": f"{code:02x}20{digest(data).hexdigest()}",
        }
    )

    validate_asset_data("product", "asset", asset, data, "downloaded")


def test_rejects_size_mismatch():
    asset = MagicMock(extra_fields={"file:size": 4})

    with pytest.raises(AssetIntegrityError, match="downloaded 3 bytes, expected 4"):
        validate_asset_data("product", "asset", asset, b"bad", "downloaded")


@pytest.mark.parametrize("checksum", ["not-hex", f"161f{'00' * 32}"])
def test_rejects_malformed_checksum(checksum):
    asset = MagicMock(extra_fields={"file:checksum": checksum})

    with pytest.raises(AssetIntegrityError, match="malformed file:checksum"):
        validate_asset_data("product", "asset", asset, b"data", "downloaded")


def test_rejects_checksum_mismatch():
    asset = MagicMock(
        extra_fields={"file:checksum": f"1620{hashlib.sha3_256(b'xxxx').hexdigest()}"}
    )

    with pytest.raises(AssetIntegrityError, match="checksum does not match"):
        validate_asset_data("product", "asset", asset, b"data", "downloaded")