"""
Unit tests for Copernicus search and ingest functionality.
"""

import hashlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from requests import RequestException

from pydafab.copernicus import CopernicusIngestor
from pydafab.dasi_copernicus import CopernicusKey
from pydafab.errors import AssetFetchError, AssetIntegrityError, AssetNotFoundError, ProductFetchError
from pydafab.ingest_tool import DasiProductHandler
from pydafab.planetary_computer import PlanetaryComputerIngestor


@pytest.fixture
def dummy_product():

    class DummyProduct:
        id = "S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809"
        collection_id = "sentinel-2-l2a"
        properties = {
            "platform": "Sentinel-2",
            "instruments": ["MSI"],
            "processing:version": "1.0",
            "grid:code": "T01UBS",
            "sat:relative_orbit": "44",
            "processing:datetime": "2025-01-23T23:09:11",
            "datetime": "2025-01-23T23:09:11",
        }
        assets = {
            "TCI_20m": MagicMock(media_type="image/jp2"),
            "WVP_10m": MagicMock(media_type="image/jp2"),
        }
        self_href = "http://example.com/product.json"

    return DummyProduct()


def test_make_key_from_product(dummy_product):
    key = CopernicusKey.from_stac("CDSE", dummy_product)
    assert key["source"] == "CDSE"
    assert key["mission"] == "S2C"
    assert key["level"] == "MSIL2A"
    assert key["gridcode"] == "T01UBS"
    assert key["procver"] == "05.11"
    assert key["procdate"] == "20250124T013809"
    assert key["takedate"] == "2025-01-23"
    assert key["taketime"] == "230911"
    assert key["orbit"] == "44"


def test_make_asset_key_from_product(dummy_product):
    key = CopernicusKey.from_stac("CDSE", dummy_product, "TCI_20m")
    assert key["asset_name"] == "TCI_20m"
    assert key["mediatype"] == "image_jp2"


def test_make_key_from_s1_rtc_product_id():
    key = CopernicusKey.from_product_id("MPC", "S1A_IW_GRDH_1SDV_20211220T182141_20211220T182206_041096_04E1DB_rtc")
    assert key["source"] == "MPC"
    assert key["mission"] == "S1A"
    assert key["mode"] == "IW"
    assert key["type"] == "GRDH"
    assert key["takedate"] == "2021-12-20"
    assert key["polarization"] == "DV"
    assert key["taketime"] == "182141"
    assert key["stoptime"] == "182206"
    assert key["orbit"] == "41096"


def test_make_key_from_s1_rtc_product_id_without_datatake():
    key = CopernicusKey.from_product_id("MPC", "S1A_IW_GRDH_1SDV_20250601T234858_20250601T234923_059459_rtc")
    assert key["taketime"] == "234858"
    assert key["stoptime"] == "234923"
    assert key["orbit"] == "59459"


def test_s1_rtc_slices_sharing_a_start_time_get_distinct_keys():
    shorter = CopernicusKey.from_product_id("MPC", "S1A_IW_GRDH_1SDV_20211220T182141_20211220T182206_041096_04E1DB_rtc")
    longer = CopernicusKey.from_product_id("MPC", "S1A_IW_GRDH_1SDV_20211220T182141_20211220T182216_041096_04E1DB_rtc")
    assert shorter != longer



@pytest.mark.parametrize(
    "product_id,collection",
    [
        ("S1A_IW_GRDH_1SDV_20250610T171650_20250610T171715_059587_rtc", "sentinel-1-rtc"),
        ("S1A_IW_GRDH_1SDV_20211220T182141_20211220T182206_041096_04E1DB_rtc", "sentinel-1-rtc"),
        ("S1A_IW_GRDH_1SDV_20250610T171650_20250610T171715_059587", "sentinel-1-grd"),
        ("S1A_IW_GRDH_1SDV_20250610T171650_20250610T171715_059587_0765DA", "sentinel-1-grd"),
        ("S1A_IW_GRDH_1SDV_20250610T171650_20250610T171715_059587_0765DA_D223_COG", "sentinel-1-grd"),
        ("S1A_IW_SLC__1SDV_20250610T171649_20250610T171717_059587_0765DA_CEB6", "sentinel-1-slc"),
    ],
)
def test_s1_collection_is_read_from_the_product_id(product_id, collection):
    assert CopernicusKey.from_product_id("CDSE", product_id)["collection"] == collection



def test_s1_padded_product_type_is_parsed_by_position():
    key = CopernicusKey.from_product_id("CDSE", "S1A_IW_SLC__1SDV_20250610T171649_20250610T171717_059587_0765DA_CEB6")
    assert (key["type"], key["polarization"], key["taketime"], key["orbit"]) == ("SLC", "DV", "171649", "59587")

def test_s1_rtc_and_its_source_grd_get_distinct_keys():
    rtc = CopernicusKey.from_product_id("MPC", "S1A_IW_GRDH_1SDV_20250610T171650_20250610T171715_059587_rtc", "vv")
    grd = CopernicusKey.from_product_id("MPC", "S1A_IW_GRDH_1SDV_20250610T171650_20250610T171715_059587_0765DA", "vv")
    assert {k for k in rtc if rtc[k] != grd[k]} == {"collection"}


def test_s1_rejects_unsupported_product_type():
    with pytest.raises(ValueError):
        CopernicusKey.from_product_id("CDSE", "S1A_IW_RAW__0SDV_20250610T171650_20250610T171715_059587_0765DA_ABCD")


def test_key_rejects_item_from_another_collection():
    item = SimpleNamespace(id="S1A_IW_GRDH_1SDV_20250610T171650_20250610T171715_059587_rtc", collection_id="sentinel-1-grd")
    with pytest.raises(ValueError):
        CopernicusKey.from_stac("MPC", item)

@patch("pydafab.copernicus.StacIngestor.__init__", return_value=None)
@patch("pydafab.copernicus.StacIngestor.search")
def test_search_calls_super(mock_search, mock_init):
    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor.catalog = MagicMock()
        ingestor.verbose = False
        ingestor.s3_endpoint = "https://eodata.dataspace.copernicus.eu"
        params = {
            "max_items": 1,
            "collections": "sentinel-2-l2a",
            "datetime": "2025-01-01/2025-01-02",
            "bbox": "6.95,50.65,7.25,50.85",
            "cloud_cover_max": 100.0,
        }
        # list(ingestor.search(params))
        results = list(ingestor.search(params))
        print(results)
        assert mock_search.called



@pytest.mark.parametrize("collection,filtered", [("sentinel-2-l2a", True), ("sentinel-1-grd", False)])
@patch("pydafab.copernicus.StacIngestor.search")
def test_copernicus_filters_cloud_cover_only_for_optical(mock_search, collection, filtered):
    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        params = {"max_items": 1, "collections": collection, "datetime": "2025-01-01/2025-01-02",
                  "bbox": "6.95,50.65,7.25,50.85", "cloud_cover_max": 20.0}
        list(CopernicusIngestor().search(params))
    assert ("filter" in mock_search.call_args.args[0]) == filtered

@patch("pydafab.copernicus.StacIngestor.__init__", return_value=None)
@patch("pydafab.ingest_tool.Dasi")
def test_archive_product_and_assets(mock_dasi, mock_init, dummy_product, tmp_path):
    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor.catalog = MagicMock()
        ingestor.verbose = False
        ingestor.s3_endpoint = "https://eodata.dataspace.copernicus.eu"
        ingestor.source = "CDSE"
        tool = DasiProductHandler(ingestor.source, str(tmp_path))
        ingestor.fetch_product = MagicMock(return_value=({"key": "val"}, b"data"))
        ingestor.fetch_asset = MagicMock(
            return_value=(MagicMock(media_type="image/jp2"), b"data")
        )
        tool.archive_product(ingestor, dummy_product)
        tool.archive_assets(ingestor, dummy_product, ["TCI_20m", "WVP_10m"])
        assert mock_dasi.return_value.archive.call_count == 3


@patch("pydafab.copernicus.StacIngestor.__init__", return_value=None)
@patch("pydafab.ingest_tool.Dasi")
def test_archive_assets_raises_on_missing_asset(mock_dasi, mock_init, dummy_product, tmp_path):
    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor.s3_endpoint = "https://eodata.dataspace.copernicus.eu"
        ingestor.source = "CDSE"
        tool = DasiProductHandler(ingestor.source, str(tmp_path))

        with pytest.raises(AssetNotFoundError):
            tool.archive_assets(ingestor, dummy_product, ["NOT_A_REAL_BAND"])

        mock_dasi.return_value.archive.assert_not_called()


@patch("pydafab.copernicus.StacIngestor.__init__", return_value=None)
@patch("pydafab.ingest_tool.Dasi")
def test_archive_assets_raises_on_fetch_failure(mock_dasi, mock_init, dummy_product, tmp_path):
    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor.s3_endpoint = "https://eodata.dataspace.copernicus.eu"
        ingestor.source = "CDSE"
        tool = DasiProductHandler(ingestor.source, str(tmp_path))
        ingestor.fetch_asset = MagicMock(side_effect=AssetFetchError("s3://bucket/key"))

        with pytest.raises(AssetFetchError):
            tool.archive_assets(ingestor, dummy_product, ["TCI_20m", "WVP_10m"])


@patch("pydafab.copernicus.StacIngestor.__init__", return_value=None)
@patch("pydafab.ingest_tool.Dasi")
def test_retrieve_assets_raises_on_missing_asset(mock_dasi, mock_init, dummy_product, tmp_path):
    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor.source = "CDSE"
        tool = DasiProductHandler(ingestor.source, str(tmp_path))

        with pytest.raises(AssetNotFoundError):
            list(tool.retrieve_assets(dummy_product.id, ["NOT_A_REAL_BAND"]))


def test_fetch_raises_on_boto_error():
    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor.s3_endpoint = "https://eodata.dataspace.copernicus.eu"
        with patch("boto3.resource", side_effect=Exception("connection refused")):
            with pytest.raises(AssetFetchError):
                ingestor._fetch("s3://bucket/key")


def test_fetch_asset_accepts_matching_size_and_checksum(dummy_product):
    data = b"data"
    asset = dummy_product.assets["TCI_20m"]
    asset.href = "s3://bucket/key"
    asset.extra_fields = {
        "file:size": len(data),
        "file:checksum": f"1220{hashlib.sha256(data).hexdigest()}",
    }

    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor._fetch = MagicMock(return_value=data)

        _asset, fetched = ingestor.fetch_asset(dummy_product, "TCI_20m")

    assert fetched == data



@pytest.mark.parametrize("digest,accepted", [(hashlib.md5, True), (lambda d: hashlib.sha3_256(d), False)])
def test_fetch_asset_reads_cdse_mislabelled_md5(dummy_product, digest, accepted):
    data = b"data"
    asset = dummy_product.assets["TCI_20m"]
    asset.href = "s3://bucket/key"
    asset.extra_fields = {"file:checksum": f"1610{digest(data).hexdigest()[:32]}"}

    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor._fetch = MagicMock(return_value=data)

        if accepted:
            assert ingestor.fetch_asset(dummy_product, "TCI_20m")[1] == data
        else:
            with pytest.raises(AssetIntegrityError):
                ingestor.fetch_asset(dummy_product, "TCI_20m")

def test_fetch_asset_raises_on_empty_data(dummy_product):
    asset = dummy_product.assets["TCI_20m"]
    asset.href = "s3://bucket/key"
    asset.extra_fields = {}

    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor._fetch = MagicMock(return_value=b"")

        with pytest.raises(AssetIntegrityError):
            ingestor.fetch_asset(dummy_product, "TCI_20m")


def test_fetch_asset_raises_on_size_mismatch(dummy_product):
    asset = dummy_product.assets["TCI_20m"]
    asset.href = "s3://bucket/key"
    asset.extra_fields = {"file:size": 4}

    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor._fetch = MagicMock(return_value=b"bad")

        with pytest.raises(AssetIntegrityError):
            ingestor.fetch_asset(dummy_product, "TCI_20m")


def test_fetch_asset_raises_on_checksum_mismatch(dummy_product):
    asset = dummy_product.assets["TCI_20m"]
    asset.href = "s3://bucket/key"
    asset.extra_fields = {
        "file:checksum": f"1220{hashlib.sha256(b'other').hexdigest()}",
    }

    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor._fetch = MagicMock(return_value=b"data")

        with pytest.raises(AssetIntegrityError):
            ingestor.fetch_asset(dummy_product, "TCI_20m")


@patch("pydafab.ingest_tool.Dasi")
def test_retrieve_assets_raises_on_empty_archived_asset(mock_dasi, dummy_product, tmp_path):
    dasi = MagicMock()
    record = MagicMock()
    record.key = {"asset_name": "TCI_20m", "mediatype": "image_jp2"}
    record.length = 0
    dasi.list.return_value = [record]
    mock_dasi.return_value = dasi
    tool = DasiProductHandler("CDSE", str(tmp_path))

    with pytest.raises(AssetIntegrityError):
        list(tool.retrieve_assets(dummy_product.id, ["TCI_20m"]))

    dasi.retrieve.assert_not_called()


def dasi_record(data=b"data"):
    return SimpleNamespace(key={"mediatype": "image_jp2"}, length=len(data), data=data)


@patch("pydafab.ingest_tool.Dasi")
def test_queries_dasi_in_lowercase(mock_dasi, dummy_product, tmp_path):
    dasi = MagicMock()
    dasi.list.return_value = [dasi_record()]
    dasi.retrieve.return_value = [dasi_record()]
    mock_dasi.return_value = dasi
    tool = DasiProductHandler("CDSE", str(tmp_path))

    list(tool.retrieve_assets(dummy_product.id, ["TCI_20m"]))

    for query in (dasi.list.call_args.args[0], dasi.retrieve.call_args.args[0]):
        values = [v for vs in query.values() for v in vs]
        assert values == [v.lower() for v in values]


@patch("pydafab.ingest_tool.Dasi")
def test_retrieve_assets_returns_requested_names(mock_dasi, dummy_product, tmp_path):
    dasi = MagicMock()
    dasi.list.side_effect = [[dasi_record()], [dasi_record()]]
    dasi.retrieve.side_effect = [[dasi_record(b"tci")], [dasi_record(b"wvp")]]
    mock_dasi.return_value = dasi
    tool = DasiProductHandler("CDSE", str(tmp_path))

    retrieved = list(tool.retrieve_assets(dummy_product.id, ["TCI_20m", "WVP_10m"]))

    assert retrieved == [("TCI_20m", "image_jp2", b"tci"), ("WVP_10m", "image_jp2", b"wvp")]


@patch("pydafab.ingest_tool.Dasi")
def test_archive_assets_skips_archived_assets(mock_dasi, dummy_product, tmp_path):
    dasi = MagicMock()
    dasi.list.side_effect = [[dasi_record()], []]
    mock_dasi.return_value = dasi
    tool = DasiProductHandler("CDSE", str(tmp_path))
    ingestor = MagicMock()
    ingestor.fetch_asset.return_value = (MagicMock(), b"data")

    tool.archive_assets(ingestor, dummy_product, ["TCI_20m", "WVP_10m"])

    ingestor.fetch_asset.assert_called_once_with(dummy_product, "WVP_10m")
    assert dasi.archive.call_count == 1



def test_item_key_shares_the_product_key(dummy_product):
    item = CopernicusKey.item("CDSE", dummy_product.id)
    asset = CopernicusKey.from_stac("CDSE", dummy_product, "TCI_20m")
    assert {k: v for k, v in item.items() if k not in ("asset_name", "mediatype")} == {
        k: v for k, v in asset.items() if k not in ("asset_name", "mediatype")
    }
    assert (item["asset_name"], item["mediatype"]) == ("item", "application_json")


@patch("pydafab.ingest_tool.Dasi")
def test_archive_product_stores_item_beside_assets(mock_dasi, dummy_product, tmp_path):
    dasi = MagicMock()
    dasi.list.return_value = []
    mock_dasi.return_value = dasi
    tool = DasiProductHandler("CDSE", str(tmp_path))
    ingestor = MagicMock()
    ingestor.fetch_product.return_value = b"{}"

    tool.archive_product(ingestor, dummy_product)

    dasi.archive.assert_called_once_with(CopernicusKey.item("CDSE", dummy_product.id), b"{}")
    dasi.flush.assert_called_once()


@patch("pydafab.ingest_tool.Dasi")
def test_archive_product_skips_archived_item(mock_dasi, dummy_product, tmp_path):
    dasi = MagicMock()
    dasi.list.return_value = [dasi_record()]
    mock_dasi.return_value = dasi
    tool = DasiProductHandler("CDSE", str(tmp_path))
    ingestor = MagicMock()

    tool.archive_product(ingestor, dummy_product)

    assert dasi.list.call_args.args[0] == CopernicusKey.item("CDSE", dummy_product.id).to_dasi_query()
    ingestor.fetch_product.assert_not_called()
    dasi.archive.assert_not_called()


@patch("pydafab.ingest_tool.Dasi")
def test_retrieve_metadata_reads_the_item(mock_dasi, dummy_product, tmp_path):
    dasi = MagicMock()
    dasi.retrieve.return_value = [dasi_record(b"{}")]
    mock_dasi.return_value = dasi
    tool = DasiProductHandler("CDSE", str(tmp_path))

    assert list(tool.retrieve_metadata(dummy_product.id)) == [b"{}"]
    assert dasi.retrieve.call_args.args[0] == CopernicusKey.item("CDSE", dummy_product.id).to_dasi_query()

def test_fetch_product_raises_on_request_error(dummy_product):
    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor.s3_endpoint = "https://eodata.dataspace.copernicus.eu"
        ingestor._session = MagicMock()
        ingestor._session.get.side_effect = RequestException("connection reset")
        with pytest.raises(ProductFetchError):
            ingestor.fetch_product(dummy_product)


def test_search_returns_dummy_product(dummy_product):
    """Test that CopernicusIngestor.search yields the dummy product."""
    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor.catalog = MagicMock()
        ingestor.verbose = False
        ingestor.s3_endpoint = "https://eodata.dataspace.copernicus.eu"
        # Mock catalog.search().items() to yield dummy_product
        ingestor.catalog.search.return_value.items.return_value = [dummy_product]
        params = {
            "max_items": 1,
            "collections": "sentinel-2-l2a",
            "datetime": "2025-01-01/2025-01-02",
            "bbox": "6.95,50.65,7.25,50.85",
            "cloud_cover_max": 100.0,
        }
        results = list(ingestor.search(params))
        assert len(results) == 1

        assert results[0].id == dummy_product.id
        assert results[0].collection_id == dummy_product.collection_id
        assert results[0].properties["platform"] == dummy_product.properties["platform"]
        assert "TCI_20m" in dummy_product.assets
        assert "WVP_10m" in dummy_product.assets
        assert results[0].self_href == dummy_product.self_href


def test_fetch_asset_verifies_planetary_computer_md5():
    """The Planetary Computer puts a bare MD5 hex in file:checksum, not a multihash."""
    data = b"data"
    asset = MagicMock(extra_fields={"file:checksum": hashlib.md5(data).hexdigest()})

    with patch.object(PlanetaryComputerIngestor, "__init__", lambda self: None):
        ingestor = PlanetaryComputerIngestor()
        ingestor.catalog = MagicMock()
        ingestor.catalog.search.return_value.items.return_value = iter([MagicMock(id="rtc", assets={"vv": asset})])
        product = ingestor.search_product("rtc")

        ingestor._fetch = MagicMock(return_value=data)
        _asset, fetched = ingestor.fetch_asset(product, "vv")
        assert fetched == data

        ingestor._fetch = MagicMock(return_value=b"tampered")
        with pytest.raises(AssetIntegrityError):
            ingestor.fetch_asset(product, "vv")


def planetary_computer_ingestor() -> PlanetaryComputerIngestor:
    with patch("pydafab.ingestor.Client.open"):
        return PlanetaryComputerIngestor()


def test_planetary_computer_signs_once_per_container():
    ingestor = planetary_computer_ingestor()
    signed = MagicMock()
    signed.json.return_value = {
        "msft:expiry": "2999-01-01T00:00:00Z",
        "href": "https://account.blob.core.windows.net/container/a.tiff?se=2999&sig=secret",
    }
    blob = MagicMock(content=b"data")
    ingestor._session = MagicMock()
    ingestor._session.get.side_effect = [signed, blob, blob]

    assert ingestor._fetch("https://account.blob.core.windows.net/container/a.tiff") == b"data"
    assert ingestor._fetch("https://account.blob.core.windows.net/container/b.tiff") == b"data"

    urls = [call.args[0] for call in ingestor._session.get.call_args_list]
    assert urls == [
        "https://planetarycomputer.microsoft.com/api/sas/v1/sign",
        "https://account.blob.core.windows.net/container/a.tiff?se=2999&sig=secret",
        "https://account.blob.core.windows.net/container/b.tiff?se=2999&sig=secret",
    ]


def test_planetary_computer_renews_an_expired_token():
    ingestor = planetary_computer_ingestor()
    signed = MagicMock()
    signed.json.return_value = {
        "msft:expiry": "2000-01-01T00:00:00Z",
        "href": "https://account.blob.core.windows.net/container/a.tiff?sig=secret",
    }
    ingestor._session = MagicMock()
    ingestor._session.get.side_effect = [signed, MagicMock(content=b"data"), signed, MagicMock(content=b"data")]

    ingestor._fetch("https://account.blob.core.windows.net/container/a.tiff")
    ingestor._fetch("https://account.blob.core.windows.net/container/b.tiff")

    assert ingestor._session.get.call_count == 4


def test_planetary_computer_wraps_a_malformed_sign_response():
    ingestor = planetary_computer_ingestor()
    ingestor._session = MagicMock()
    ingestor._session.get.return_value.json.return_value = {"error": "nope"}

    with pytest.raises(AssetFetchError):
        ingestor._fetch("https://account.blob.core.windows.net/container/a.tiff")


def test_planetary_computer_fetches_api_assets_unsigned():
    ingestor = planetary_computer_ingestor()
    ingestor._session = MagicMock()
    ingestor._session.get.return_value.content = b"png"
    href = "https://planetarycomputer.microsoft.com/api/data/v1/item/preview.png?collection=c&item=i"

    assert ingestor._fetch(href) == b"png"
    assert [call.args[0] for call in ingestor._session.get.call_args_list] == [href]


def test_copernicus_fetch_splits_bucket_and_key():
    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor.s3_endpoint = "https://eodata.dataspace.copernicus.eu"
        ingestor._s3 = MagicMock()
        ingestor._s3.Object.return_value.get.return_value = {"Body": MagicMock(read=lambda: b"data")}

        assert ingestor._fetch("s3://sentinel-1/path/to/key") == b"data"

    ingestor._s3.Object.assert_called_once_with("sentinel-1", "path/to/key")
