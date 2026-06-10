"""
Unit tests for Copernicus search and ingest functionality.
"""

import pytest
from requests import RequestException
from unittest.mock import MagicMock, patch
from pydafab.copernicus import CopernicusIngestor
from pydafab.dasi_copernicus import CopernicusKey
from pydafab.errors import AssetFetchError, AssetNotFoundError, ProductFetchError
from pydafab.ingest_tool import DasiProductHandler


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


@patch("pydafab.copernicus.StacIngestor.__init__", return_value=None)
@patch("pydafab.ingest_tool.Dasi")
def test_archive_product_and_assets(mock_dasi, mock_init, dummy_product, tmp_path):
    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor.catalog = MagicMock()
        ingestor.verbose = False
        ingestor.s3_endpoint = "https://eodata.dataspace.copernicus.eu"
        ingestor.source = "CDSE"
        tool = DasiProductHandler(ingestor, str(tmp_path))
        ingestor.fetch_product = MagicMock(return_value=({"key": "val"}, b"data"))
        ingestor.fetch_asset = MagicMock(
            return_value=(MagicMock(media_type="image/jp2"), b"data")
        )
        tool.archive_product(dummy_product)
        tool.archive_assets(dummy_product, ["TCI_20m", "WVP_10m"])
        assert mock_dasi.return_value.archive.call_count == 3


@patch("pydafab.copernicus.StacIngestor.__init__", return_value=None)
@patch("pydafab.ingest_tool.Dasi")
def test_archive_assets_raises_on_missing_asset(mock_dasi, mock_init, dummy_product, tmp_path):
    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor.s3_endpoint = "https://eodata.dataspace.copernicus.eu"
        ingestor.source = "CDSE"
        tool = DasiProductHandler(ingestor, str(tmp_path))

        with pytest.raises(AssetNotFoundError):
            tool.archive_assets(dummy_product, ["NOT_A_REAL_BAND"])

        mock_dasi.return_value.archive.assert_not_called()


@patch("pydafab.copernicus.StacIngestor.__init__", return_value=None)
@patch("pydafab.ingest_tool.Dasi")
def test_archive_assets_raises_on_fetch_failure(mock_dasi, mock_init, dummy_product, tmp_path):
    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor.s3_endpoint = "https://eodata.dataspace.copernicus.eu"
        ingestor.source = "CDSE"
        tool = DasiProductHandler(ingestor, str(tmp_path))
        ingestor.fetch_asset = MagicMock(side_effect=AssetFetchError("s3://bucket/key"))

        with pytest.raises(AssetFetchError):
            tool.archive_assets(dummy_product, ["TCI_20m", "WVP_10m"])


def test_fetch_s3_raises_on_boto_error():
    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor.s3_endpoint = "https://eodata.dataspace.copernicus.eu"
        with patch("boto3.resource", side_effect=Exception("connection refused")):
            with pytest.raises(AssetFetchError):
                ingestor._fetch_s3("s3://bucket/key")


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
