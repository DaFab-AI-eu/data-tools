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
- **`DasiProductHandler`**: Coordinates archive, list, and retrieve operations across DASI stores
- **`CopernicusKey`**: Maps Sentinel-1 and Sentinel-2 product identifiers to schema-driven DASI keys
- **Command-line tools**: Provide focused search, ingest, stage, and retention operations

The base `StacIngestor` accepts configurable STAC catalogue and S3-compatible endpoints. The default Copernicus implementation uses the Copernicus Data Space catalogue and EO Data endpoint.

### 1.2 DASI Storage Model

Product metadata and binary assets are stored separately:

```text
DASI Storage
    ├─→ Metadata Store → Raw STAC product documents
    └─→ Asset Store    → Selected product assets
```

Separate DASI configuration and schema files define each store. Sentinel product identifiers are parsed into hierarchical archive keys containing source, mission, acquisition, processing, orbit, and spatial attributes. Asset keys extend the product key with the asset name and media type.

The supplied configuration uses `/data/metadata/root` and `/data/assets/root`, but the tools remain agnostic to the orchestration and storage environment.

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
3. **Key generation**: Parse the Sentinel identifier into a DASI metadata key
4. **Metadata archive**: Store and flush the product document
5. **Asset retrieval**: Download each requested asset from S3-compatible storage
6. **Asset archive**: Add asset name and media type to the key, then store and flush the asset data

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

Retention provides capacity- and age-driven lifecycle control for both DASI stores. Each immediate child of a store root is a self-contained FDB database directory, and whole directories are the only filesystem-safe unit to remove. The policy is read from `retention.yml`:

- `min_free_percent`: retention acts only when free disk space is below this, and deletes until it is met again
- `delete_size`: per-run cap on the bytes reclaimed
- `min_age_days`: databases whose directory mtime is younger than this are never deleted

The workflow:

1. **Store validation**: Confirm that the metadata and asset roots exist
2. **Threshold check**: Report disk usage; stop when free space is already at or above `min_free_percent`
3. **Selection**: Enumerate asset database directories, drop any younger than `min_age_days`, and choose the oldest-first (by directory mtime) until the free-space target is met or `delete_size` is reached, whichever comes first
4. **Aligned removal**: Each selected asset database also removes its same-named (aligned) directory in the metadata store
5. **Dry-run inspection**: Report each selected database and the projected free space without modifying anything
6. **Confirmed deletion**: Remove the selected directories only when `--do-it=true` is supplied

```bash
# Dry run
python copernicus/retention.py --path=/data --config=copernicus/ingest/retention.yml

# Apply the policy
python copernicus/retention.py --path=/data --config=copernicus/ingest/retention.yml --do-it=true

# Legacy full wipe of both store roots (ignores the policy)
python copernicus/retention.py --path=/data --clear-all --do-it=true
```

The store roots are preserved, paths outside them are not selected, and symbolic links are removed without traversing their targets.

#### Operational Considerations

Retention is designed to run as a **blocking scheduled task** — a maintenance window with no ingest or stage activity — rather than inside the archiving flow itself. Two characteristics motivate this: selection is by directory mtime, which reflects when data was written rather than when it was last needed; and the asset and metadata databases are removed as two consecutive operations rather than one transaction. Both are safe under a dedicated scheduled run.

---

## 3. Key Features and Capabilities

| Capability | Implementation |
|------------|----------------|
| **Catalogue Search** | Collection, datetime, bounding box, cloud cover, and result limits |
| **Product Lookup** | Exact STAC product ID with optional collection restriction |
| **Metadata Archive** | Raw STAC documents in a dedicated DASI store |
| **Asset Archive** | Selected S3 assets in a dedicated DASI store |
| **Duplicate Handling** | Existing products and requested assets are skipped |
| **Data Staging** | Metadata and selected assets written to local files |
| **Sentinel Support** | Sentinel-1 and Sentinel-2 compact product identifiers |
| **Storage Lifecycle** | Capacity- and age-based retention, or explicit full-store clearing, with dry-run inspection |
| **Integration Model** | Python API and command-line tools for automated workflows |

---

## 4. Conclusion

DaFab Data Tools provides a focused bridge between Copernicus catalogue and object-storage services and schema-driven DASI archives. Its layered architecture supports product discovery, selective ingestion, efficient staging, and explicit storage lifecycle control through both reusable Python interfaces and workflow-friendly commands.

The implementation supports Sentinel-1 and Sentinel-2 data without coupling the tools to a particular orchestration or storage deployment.

**Status:** Core search, ingestion, staging, and retention workflows implemented

**Availability:** `copernicus/` commands and the `pydafab` Python package
