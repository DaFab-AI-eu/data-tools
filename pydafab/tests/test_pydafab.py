def test_import_pydafab():
    import pydafab

    # version
    assert hasattr(pydafab, "__version__")
    assert isinstance(pydafab.__version__, str)
    assert len(pydafab.__version__) > 0

    # submodules
    for submodule in ["copernicus", "ingestor", "helpers", "errors"]:
        assert hasattr(pydafab, submodule), f"Missing submodule: {submodule}"

    # classes can be imported
    from pydafab.copernicus import CopernicusIngestor
    from pydafab.ingestor import StacIngestor


def test_copernicus_ingestor_initialization():
    from pydafab.copernicus import CopernicusIngestor
    from pydafab.ingestor import StacIngestor

    # Patch Client.open to avoid network call and JSON errors
    from unittest.mock import patch, MagicMock

    with patch("pydafab.ingestor.Client.open", return_value=MagicMock()):
        ci = CopernicusIngestor()
        assert isinstance(ci, CopernicusIngestor)
        si = StacIngestor("https://example.com", "https://s3.example.com")
        assert isinstance(si, StacIngestor)


def test_reading_from_dasi_needs_no_stac_client(tmp_path):
    """The handler reads Dasi by source name, so reading opens no STAC catalog."""

    from unittest.mock import patch

    from pydafab.ingest_tool import DasiProductHandler

    with patch("pydafab.ingest_tool.Dasi"), patch("pydafab.ingestor.Client.open") as open_catalog:
        handler = DasiProductHandler("CDSE", str(tmp_path))
        list(handler.retrieve_metadata("S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809"))

    open_catalog.assert_not_called()
