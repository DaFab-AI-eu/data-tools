# DaFab Data Tools

## Introduction

DaFab Data Tools provides search, ingestion, archival, retrieval, and storage lifecycle operations for Copernicus Earth observation products. It connects STAC-compatible catalogues and object storage to DASI while exposing both a reusable Python package (`pydafab`) and command-line tools for automated workflows.

This deliverable describes the architectural design, implemented workflows, and key capabilities of the repository.

## 1. Architecture

The command-line tools expose search, ingest, stage, and retention workflows, while the `pydafab` package provides the reusable Copernicus, key-mapping, and DASI integration logic:

```text
Workflow or Operator
    └─→ Copernicus CLI Tools
            ├─→ search.py     → STAC Catalogue
            ├─→ ingest.py     → PyDaFab → STAC/S3 → DASI
            ├─→ stage.py      → PyDaFab → DASI → Filesystem
            └─→ retention.py  → DASI Storage
```

### 1.1 Core Components

The implementation comprises:

- **`CopernicusIngestor`**: Searches the Copernicus STAC catalogue and retrieves product metadata and assets
- **`PlanetaryComputerIngestor`**: Searches the Microsoft Planetary Computer STAC catalogue for Sentinel-1 RTC products and retrieves their metadata and assets
- **`DasiProductHandler`**: Coordinates archive, list, and retrieve operations across DASI stores
- **`CopernicusKey`**: Maps Sentinel-2, Sentinel-1 and Sentinel-1 RTC product identifiers to schema-driven DASI keys
- **Command-line tools**: Provide focused search, ingest, stage, and retention operations

The base `StacIngestor` accepts a configurable STAC catalogue; each implementation downloads assets from its own storage. The Copernicus implementation uses the Copernicus Data Space catalogue and S3 EO Data endpoint. The Planetary Computer implementation signs Azure Blob Storage hrefs. Commands pick the catalogue from `--collections` through `INGESTORS`: `sentinel-2-l2a`, `sentinel-1-grd` and `sentinel-1-slc` come from Copernicus and `sentinel-1-rtc` from the Planetary Computer.

### 1.2 DASI Storage Model

Product metadata and binary assets share one DASI store, defined by `dasi.yml` and `schema`:

```text
DASI Store (one database per acquisition month)
    └─→ Product → STAC document (reserved asset "metadata") + selected product assets
```

Sentinel product identifiers are parsed into hierarchical archive keys containing source, mission, acquisition, processing, orbit, and spatial attributes, extended with the asset name and media type. The raw STAC document is archived under the reserved asset name `metadata`, so a product's metadata and data always live in the same database. Databases are keyed by acquisition month, so whole-database retention removes whole months rather than a tile's entire history. Every key, including the date, is derived from the product ID. The schema types `takedate` as `YearMonth` at the database level, so FDB stores `2025-03-22` there as `202503`, and keeps the full date one level down; `YearMonth` needs FDB 5.22 or later. Queries name a whole date: `takedate=2025-03` is rejected, so list without `takedate` to see a month.

Every key carries a `collection` (`sentinel-2-l1c`, `sentinel-2-l2a`, `sentinel-1-grd`, `sentinel-1-slc` or `sentinel-1-rtc`), read from the product ID and checked against the STAC item. A derived product can keep the identity of its source: a Sentinel-1 RTC product keeps that of the GRD it was made from, so without the collection the two would share a key and overwrite each other. A DASI `list` that omits `collection` returns every collection; specify it to select one.

FDB joins the innermost key values (`asset_name:mediatype`) into an index key of at most 32 characters by default, which Sentinel-1 annotation assets exceed (e.g. `schema-calibration-iw1-vh:application_xml`). The image sets `FDB_INDEX_TYPE=BTreeIndex64` to allow 64; every process that *writes* to the store needs it. Readers do not, since each index records its own type.

The supplied configuration uses `/data/root`, but the tools remain agnostic to the orchestration and storage environment.

---

## 2. Core Workflows

### 2.1 Search Operation

Product discovery follows a four-step process:

1. **Search construction**: Collection, datetime, bounding box, cloud cover, and result limit are converted into a STAC Item Search
2. **Spatial filtering**: The bounding box is represented as a GeoJSON polygon
3. **Catalogue query**: Matching products are streamed from the Copernicus STAC API
4. **Result output**: Product identifiers are written to a JSON file

```bash
python copernicus/search.py \
  --collections=sentinel-2-l2a \
  --datetime=2025-01-21/2025-01-23 \
  --bbox=6.95,50.65,7.25,50.85 \
  --cloud_cover_max=20 \
  --output_file=/tmp/products.json
```

### 2.2 Ingest Operation

Product ingestion follows a six-step process:

1. **Product lookup**: Find the requested product ID in the STAC catalogue
2. **Metadata retrieval**: Download the raw STAC product document
3. **Key generation**: Parse the Sentinel identifier into a DASI key
4. **Metadata archive**: Store the product document as the reserved asset `metadata`
5. **Asset retrieval**: Download each requested asset from S3-compatible storage
6. **Asset archive**: Add asset name and media type to the key, store the asset data, then flush the document and assets together

```bash
python copernicus/ingest.py \
  --collections=sentinel-2-l2a \
  --product_id=S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809 \
  --asset_names=WVP_10m,TCI_20m
```

Existing metadata and requested assets are detected and skipped, allowing ingestion to be rerun without downloading or archiving the same records again. Missing assets are reported while other requested assets continue processing.

### 2.3 Stage Operation

Staging retrieves archived data into local files:

1. **Query generation**: Reconstruct the DASI query from the product ID
2. **Metadata retrieval**: Write the product document as `<product_id>.json`
3. **Asset resolution**: List available assets and resolve their media types
4. **Selective retrieval**: Retrieve only the requested asset names
5. **File output**: Write each asset as `<product_id>_<asset_name>.<extension>`

```bash
python copernicus/stage.py \
  --product_id=S2C_MSIL2A_20250123T230911_N0511_R044_T01UBS_20250124T013809 \
  --asset_names=WVP_10m,TCI_20m \
  --output_dir=/tmp/staged
```

Metadata retrieval is mandatory, while asset retrieval is optional and selective.

### 2.4 Retention Operation

Retention provides capacity- and age-driven lifecycle control for the DASI store. Each immediate child of the store root is a self-contained FDB database directory holding every product acquired in one month, and whole directories are the only filesystem-safe unit to remove. The policy is read from `retention.yml`:

- `min_free_percent`: retention acts only when free disk space is below this, and deletes until it is met again
- `delete_size`: per-run cap on the bytes reclaimed
- `min_age_days`: databases whose directory mtime is younger than this are never deleted

The workflow:

1. **Store validation**: Confirm that the store root exists
2. **Threshold check**: Report disk usage; stop when free space is already at or above `min_free_percent`
3. **Selection**: Enumerate database directories, drop any younger than `min_age_days`, and choose the oldest-first (by directory mtime) until the free-space target is met or `delete_size` is reached, whichever comes first
4. **Dry-run inspection**: Report each selected database and the projected free space without modifying anything
5. **Confirmed deletion**: Remove the selected directories only when `--do-it=true` is supplied

```bash
# Dry run
python copernicus/retention.py --root=/data/root --config=copernicus/ingest/retention.yml

# Apply the policy
python copernicus/retention.py --root=/data/root --config=copernicus/ingest/retention.yml --do-it=true

# Legacy full wipe of the store root (ignores the policy)
python copernicus/retention.py --root=/data/root --clear-all --do-it=true
```

The store root is preserved, paths outside them are not selected, and symbolic links are removed without traversing their targets.

#### Operational Considerations

Retention is designed to run as a **blocking scheduled task** — a maintenance window with no ingest or stage activity — rather than inside the archiving flow itself, because it removes database directories directly rather than through FDB. Selection is by directory mtime, which reflects when data was written rather than when it was last needed.

---

## 3. Key Features and Capabilities

| Capability | Implementation |
|------------|----------------|
| **Catalogue Search** | Collection, datetime, bounding box, cloud cover, and result limits |
| **Product Lookup** | Exact STAC product ID with optional collection restriction |
| **Product Archive** | Raw STAC documents and selected assets in one DASI store, keyed by acquisition month |
| **Duplicate Handling** | Existing products and requested assets are skipped |
| **Data Staging** | Metadata and selected assets written to local files |
| **Sentinel Support** | Sentinel-2 and Sentinel-1 GRD/SLC from Copernicus; Sentinel-1 radiometrically terrain corrected (RTC) from the Planetary Computer |
| **Storage Lifecycle** | Capacity- and age-based retention, or explicit full-store clearing, with dry-run inspection |
| **Integration Model** | Python API and command-line tools for automated workflows |

---

## 4. Conclusion

DaFab Data Tools provides a focused bridge between Copernicus catalogue and object-storage services and schema-driven DASI archives. Its layered architecture supports product discovery, selective ingestion, efficient staging, and explicit storage lifecycle control through both reusable Python interfaces and workflow-friendly commands.

The implementation supports Sentinel-1 and Sentinel-2 data without coupling the tools to a particular orchestration or storage deployment.

**Status:** Core search, ingestion, staging, and retention workflows implemented

**Availability:** `copernicus/` commands and the `pydafab` Python package
