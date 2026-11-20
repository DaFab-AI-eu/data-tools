"""End to end against FDB access timestamps and a real store: runs in the DASI image."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RETENTION = Path(__file__).parent / "retention.py"
SCHEMA = Path(__file__).parent / "ingest" / "schema"

pytestmark = pytest.mark.skipif(shutil.which("fdb-last-access") is None, reason="needs FDB with access timestamps")


def s2_key(mission, takedate, asset):
    return {
        "source": "cdse", "mission": mission, "collection": "sentinel-2-l2a", "level": "msil2a",
        "takedate": takedate, "gridcode": "t32ulb", "procver": "05.11", "taketime": "103741",
        "procdate": "20250322t161215", "orbit": "8", "asset_name": asset, "mediatype": "image_jp2",
    }


@pytest.fixture
def store(tmp_path):
    """Four S2 month databases: idle since January, idle since June, just written, and never recorded."""
    from pydasi import Dasi

    root = tmp_path / "root"
    root.mkdir()
    dasi_config = tmp_path / "dasi.yml"
    dasi_config.write_text(
        f"schema: {SCHEMA}\ncatalogue: toc\nstore: file\nspaces:\n  - roots:\n      - path: {root}\n"
    )
    dasi = Dasi(str(dasi_config))
    for mission, takedate in [("s2a", "2025-03-05"), ("s2a", "2025-03-22"), ("s2b", "2025-04-10"),
                              ("s2c", "2025-05-10"), ("s2c", "2025-06-10")]:
        dasi.archive(s2_key(mission, takedate, "b01"), b"x" * 1024)
    dasi.flush()

    def touch(mission, when):
        subprocess.run(
            ["fdb-touch", f"--config={dasi_config}", "--read", "--write", "--raw", "--minimum-keys=",
             f"--time={when}", f"source=cdse,mission={mission}"],
            check=True, capture_output=True,
        )

    touch("s2a", "20260101")
    touch("s2b", "20260601")
    for name in ("read.timestamp", "write.timestamp"):
        (root / "cdse:s2c:sentinel-2-l2a:msil2a:202506" / name).unlink()

    policy = tmp_path / "retention.yml"

    def run(do_it, **settings):
        policy.write_text("".join(f"{name}: {value}\n" for name, value in settings.items()))
        result = subprocess.run(
            [sys.executable, str(RETENTION), f"--root={root}", f"--config={policy}",
             f"--dasi-config={dasi_config}", f"--do-it={do_it}"],
            capture_output=True, text=True, check=False,
        )
        return result.returncode, sorted(path.name for path in root.iterdir()), result.stderr

    return run


TARGET_OUT_OF_REACH = 3
COLD = "cdse:s2a:sentinel-2-l2a:msil2a:202503"
WARM = "cdse:s2b:sentinel-2-l2a:msil2a:202504"
FRESH = "cdse:s2c:sentinel-2-l2a:msil2a:202505"
UNKNOWN = "cdse:s2c:sentinel-2-l2a:msil2a:202506"


def test_delete_size_stops_after_the_least_recently_used_database(store):
    exit_code, remaining, log = store(do_it="true", min_free_percent=100, min_idle_days=7, delete_size_gb="0.000001")
    assert exit_code == 0
    assert remaining == [WARM, FRESH, UNKNOWN]
    assert f"Wiping: {COLD}" in log


def test_never_wipes_recently_accessed_or_unrecorded_databases(store):
    exit_code, remaining, log = store(do_it="true", min_free_percent=100, min_idle_days=7)
    assert exit_code == TARGET_OUT_OF_REACH
    assert remaining == [FRESH, UNKNOWN]
    assert log.index(f"Wiping: {COLD}") < log.index(f"Wiping: {WARM}")


def test_min_idle_days_defaults_to_30(store):
    _, remaining, _ = store(do_it="true", min_free_percent=100)
    assert remaining == [FRESH, UNKNOWN]


def test_min_idle_days_0_spares_only_unrecorded_databases(store):
    _, remaining, _ = store(do_it="true", min_free_percent=100, min_idle_days=0)
    assert remaining == [UNKNOWN]


def test_without_min_free_percent_nothing_is_wiped(store):
    exit_code, remaining, _ = store(do_it="true")
    assert exit_code == 0
    assert remaining == [COLD, WARM, FRESH, UNKNOWN]


def test_dry_run_wipes_nothing(store):
    exit_code, remaining, log = store(do_it="false", min_free_percent=100, min_idle_days=7)
    assert exit_code == TARGET_OUT_OF_REACH
    assert remaining == [COLD, WARM, FRESH, UNKNOWN]
    assert f"Would wipe: {COLD}" in log
