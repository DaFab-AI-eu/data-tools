"""
Unit tests for Copernicus search and ingest functionality.
"""

import pytest
from unittest.mock import MagicMock, patch
from pydafab.copernicus import CopernicusIngestor
from pydafab.ingest_tool import IngestTool


@pytest.fixture
def dummy_product():

    class DummyProduct:
        id = "dummy_id"
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
        assets = {"TCI_20m": MagicMock(), "WVP_10m": MagicMock()}
        self_href = "http://example.com/product.json"

    return DummyProduct()


@pytest.fixture
def dummy_asset():

    class DummyAsset:
        extra_fields = {"gsd": "10"}
        ext = MagicMock()
        ext.proj.code = "32632"
        media_type = "image/tiff"

    return DummyAsset()


@patch("pydafab.copernicus.StacIngestor.__init__", return_value=None)
def test_make_key_from_product(mock_init, dummy_product):
    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor.catalog = MagicMock()
        ingestor.verbose = False
        ingestor.endpoint = "https://eodata.dataspace.copernicus.eu"

        key = ingestor.make_key_from_product(dummy_product)
        assert key["collection"] == "sentinel-2-l2a"
        assert key["platform"] == "Sentinel-2"
        assert key["procdate"] == "20250123T230911"
        assert key["takedate"] == "2025-01-23"
        assert key["taketime"] == "230911"

    key = ingestor.make_key_from_product(dummy_product)
    assert key["collection"] == "sentinel-2-l2a"
    assert key["platform"] == "Sentinel-2"
    assert key["procdate"] == "20250123T230911"
    assert key["takedate"] == "2025-01-23"
    assert key["taketime"] == "230911"


@patch("pydafab.copernicus.StacIngestor.__init__", return_value=None)
def test_make_asset_key_from_product(mock_init, dummy_product, dummy_asset):
    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor.catalog = MagicMock()
        ingestor.verbose = False
        ingestor.endpoint = "https://eodata.dataspace.copernicus.eu"

        key = ingestor.make_asset_key_from_product(dummy_product, dummy_asset)
        assert key["gsd"] == "10"
        assert key["project"] == "32632"
        assert key["mediatype"] == "image_tiff"


@patch("pydafab.copernicus.StacIngestor.__init__", return_value=None)
@patch("pydafab.copernicus.StacIngestor.search")
def test_search_calls_super(mock_search, mock_init):
    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor.catalog = MagicMock()
        ingestor.verbose = False
        ingestor.endpoint = "https://eodata.dataspace.copernicus.eu"
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
def test_archive_product_and_assets(mock_dasi, mock_init, dummy_product):
    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor.catalog = MagicMock()
        ingestor.verbose = False
        ingestor.endpoint = "https://eodata.dataspace.copernicus.eu"
        tool = IngestTool(ingestor)
        ingestor.fetch_product = MagicMock(return_value=({"key": "val"}, b"data"))
        ingestor.fetch_asset = MagicMock(return_value=({"key": "val"}, b"data"))
        tool.archive_product(dummy_product)
        tool.archive_assets(dummy_product, ["TCI_20m", "WVP_10m"])
        assert mock_dasi.return_value.archive.call_count == 3


def test_search_returns_dummy_product(dummy_product):
    """Test that CopernicusIngestor.search yields the dummy product."""
    with patch.object(CopernicusIngestor, "__init__", lambda self: None):
        ingestor = CopernicusIngestor()
        ingestor.catalog = MagicMock()
        ingestor.verbose = False
        ingestor.endpoint = "https://eodata.dataspace.copernicus.eu"
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
