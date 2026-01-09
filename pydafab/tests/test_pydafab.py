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
