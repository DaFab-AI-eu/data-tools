import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from retention import Database, dir_size, parse_size, scan_databases, select_for_deletion

GB = 1024**3
NOW = 1_000_000_000
OLD = 1  # well before the age cutoff


def database(name, size, mtime):
    return Database(
        assets=Path(f"/data/assets/root/{name}"),
        metadata=Path(f"/data/metadata/root/{name}"),
        size=size,
        mtime=mtime,
    )


def select(databases, *, total=100 * GB, free=10 * GB, min_free_percent=20, delete_size=50 * GB, min_age_days=7):
    return select_for_deletion(
        databases,
        total=total,
        free=free,
        min_free_percent=min_free_percent,
        delete_size=delete_size,
        min_age_days=min_age_days,
        now=NOW,
    )


@pytest.mark.parametrize(
    "value,expected",
    [(1024, 1024), ("5GB", 5 * GB), ("5GiB", 5 * GB), ("500MB", 500 * 1024**2), ("2G", 2 * GB), ("0", 0)],
)
def test_parse_size(value, expected):
    assert parse_size(value) == expected


def test_parse_size_rejects_garbage():
    with pytest.raises(SystemExit):
        parse_size("5 bananas")


def test_oldest_first_until_free_target():
    dbs = [database("C", 4 * GB, OLD + 2), database("A", 4 * GB, OLD), database("B", 4 * GB, OLD + 1)]
    selected, freed, target = select(dbs)  # free 10GB, target 20GB -> need 10GB
    assert [d.assets.name for d in selected] == ["A", "B", "C"]  # oldest-first
    assert freed == 12 * GB
    assert 10 * GB + freed >= target


def test_delete_size_cap_stops_early():
    dbs = [database("A", 4 * GB, OLD), database("B", 4 * GB, OLD + 1), database("C", 4 * GB, OLD + 2)]
    selected, freed, target = select(dbs, delete_size=5 * GB)
    assert [d.assets.name for d in selected] == ["A", "B"]  # capped before reaching the 20GB target
    assert freed == 8 * GB
    assert 10 * GB + freed < target


def test_min_age_days_is_a_hard_floor():
    young = database("young", 10 * GB, NOW)  # newer than the 7-day cutoff
    old = database("old", 4 * GB, OLD)
    selected, freed, _ = select([young, old])
    assert [d.assets.name for d in selected] == ["old"]
    assert freed == 4 * GB


def test_above_threshold_selects_nothing():
    # free already at the target: entry guard on the first candidate stops immediately
    selected, freed, _ = select([database("A", 4 * GB, OLD)], free=20 * GB)
    assert selected == []
    assert freed == 0


def make_store(tmp_path):
    assets = tmp_path / "assets" / "root"
    metadata = tmp_path / "metadata" / "root"
    assets.mkdir(parents=True)
    metadata.mkdir(parents=True)
    return assets, metadata


def test_scan_pairs_aligned_and_sums_sizes(tmp_path):
    assets, metadata = make_store(tmp_path)
    (assets / "A").mkdir()
    (assets / "A" / "data").write_bytes(b"x" * 1000)
    (metadata / "A").mkdir()
    (metadata / "A" / "doc").write_bytes(b"y" * 50)

    dbs = {d.assets.name: d for d in scan_databases(assets, metadata)}

    assert dbs["A"].size == 1050  # asset bytes + aligned metadata bytes
    assert dbs["A"].metadata == metadata / "A"


def test_scan_fails_when_metadata_counterpart_missing(tmp_path):
    assets, metadata = make_store(tmp_path)
    (assets / "B").mkdir()
    (assets / "B" / "data").write_bytes(b"z" * 200)  # no aligned metadata dir

    with pytest.raises(SystemExit):
        scan_databases(assets, metadata)


def test_dir_size_ignores_symlinks(tmp_path):
    (tmp_path / "real").write_bytes(b"a" * 128)
    (tmp_path / "link").symlink_to(tmp_path / "real")
    assert dir_size(tmp_path) == 128
