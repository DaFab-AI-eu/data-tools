import dafab_client as dc

# STAC scope for the DaFab catalog (e.g., "dafab" for production, "demo" for development).
STAC_SCOPE = "dafab"

# Available collection in DaFab's unified-catalog: sentinel_2_l2a, water_analysis, smart_agriculture
COLLECTION_ID = "water_analysis"

# Top facet catalog ID in DaFab's unified-catalog: "agriculture_season", "water_basin", "water_anomaly"
TOP_FACET_CATALOG_ID = "water_basin"

# Facet value catalog ID in DaFab's unified-catalog: "agriculture_season_winter", "agriculture_season_spring", "agriculture_season_summer", "agriculture_season_autumn", "water_anomaly_flood", "water_anomaly_drought", "water_anomaly_normal", "water_basin_ganges".
FACET_VALUE_CATALOG_ID = "water_basin_ganges"

# Original item ID in DaFab's unified-catalog (e.g., "S2A_45RYJ_20221205_0_L2A").
ORIGINAL_ITEM_ID = "S2A_45RYJ_20221205_0_L2A"

# Derived item ID in DaFab's unified-catalog (e.g., "S2A_45RYJ_20221205_0_L2A_water_analysis_100", "S2A_45RYJ_20221205_0_L2A_smart_agriculture_100", ...).
DERIVED_ITEM_ID = "S2A_31TEG_20220226_0_L2A_smart_agriculture_120"  # "S2A_45RYJ_20221205_0_L2A_water_analysis_100"  # "S2A_31TEG_20220226_0_L2A_smart_agriculture_120"

# Asset key to resolve under `assets` of the selected derived item.
DERIVED_ASSET_KEY = "dafab-field-boundaries"

# Local download directory used by the asset download examples below.
ASSET_DOWNLOAD_DIR = "demo-data/downloads"

# Start datetime (inclusive) used by Q1/Q3 filter examples.
FILTER_START_DATETIME = "2020-01-01T00:00:00Z"

# End datetime (inclusive) used by Q1/Q3 filter examples.
FILTER_END_DATETIME = "2020-12-31T23:59:59Z"

# Bounding box [min_long, min_lat, max_long, max_lat] used by Q2/Q3 filter examples.
FILTER_BBOX = [-0.6, 19.7, 96.6, 54.2]

# Minimum number of fields used by the Q4 nested metadata filter example.
SMART_AGRICULTURE_MIN_FIELDS = 100000

dc.ping()

dc.whoami()

dc.list_stac_scopes()

dc.list_catalogs_and_collections()
# If you need structured records for downstream processing, use dc.get_catalogs_and_collections() instead.
print(f"Structured rows available via dc.get_catalogs_and_collections(): {len(dc.get_catalogs_and_collections())}")

# Enhanced filter payload for STAC records whose metadata type is "Collection".
COLLECTION_TYPE_FILTER = {
    "filter": {
        "type": "comparison",
        "comparator": "equals",
        "path": ["type"],
        "value": "Collection",
        "valueType": "string",
    }
}

collection_type_item_ids = dc.get_items_by_enhanced_filter(COLLECTION_TYPE_FILTER, return_mode="ids")
print(collection_type_item_ids)

# Enhanced filter payload for STAC records whose metadata type is "Catalog".
CATALOG_TYPE_FILTER = {
    "filter": {
        "type": "comparison",
        "comparator": "equals",
        "path": ["type"],
        "value": "Catalog",
        "valueType": "string",
    }
}

catalog_type_item_ids = dc.get_items_by_enhanced_filter(CATALOG_TYPE_FILTER, return_mode="ids")
print(catalog_type_item_ids)

item_rows = dc.get_items()
print([item["name"] for item in item_rows])
print(f"Structured rows available via dc.get_items(): {len(item_rows)}")

collection_item_ids = dc.get_item_ids_by_collection_field(COLLECTION_ID)
print(f"Collection: {COLLECTION_ID}")
print(collection_item_ids)

top_facet_item_ids = dc.get_item_ids_by_top_facet_catalog(TOP_FACET_CATALOG_ID)

print(f"Top facet catalog: {TOP_FACET_CATALOG_ID}")
print(top_facet_item_ids)

facet_value_item_ids = dc.get_item_ids_by_facet_value_catalog(FACET_VALUE_CATALOG_ID)

print(f"Facet value catalog: {FACET_VALUE_CATALOG_ID}")
print(facet_value_item_ids)

related_item_ids = dc.get_related_item_ids_from_original_item(ORIGINAL_ITEM_ID)

print(f"Original item: {ORIGINAL_ITEM_ID}")
print(related_item_ids)

source_original_item_ids = dc.get_source_original_item_ids_from_derived_item(DERIVED_ITEM_ID)

print(f"Derived item: {DERIVED_ITEM_ID}")
print(source_original_item_ids)

sibling_ids = dc.get_sibling_derived_item_ids(
    ORIGINAL_ITEM_ID,
    collection_id=COLLECTION_ID,
)

print(f"Original item: {ORIGINAL_ITEM_ID} | Sibling filter collection: {COLLECTION_ID}")
print(sibling_ids)

q1_item_ids = dc.get_items_by_timerange(
    FILTER_START_DATETIME,
    FILTER_END_DATETIME,
    return_mode="ids",
)
print(q1_item_ids[:20])
print(f"Total matches: {len(q1_item_ids)}")

q2_item_ids = dc.get_items_by_bbox(
    FILTER_BBOX[0],
    FILTER_BBOX[1],
    FILTER_BBOX[2],
    FILTER_BBOX[3],
    return_mode="ids",
)
print(q2_item_ids[:20])
print(f"Total matches: {len(q2_item_ids)}")

q3_item_ids = dc.get_items_by_bbox_and_timerange(
    FILTER_BBOX,
    [FILTER_START_DATETIME, FILTER_END_DATETIME],
    return_mode="ids",
)
print(q3_item_ids[:20])
print(f"Total matches: {len(q3_item_ids)}")

Q4_COMPLEX_FILTER = {
    "filter": {
        "type": "logical",
        "combinator": "and",
        "filters": [
            {
                "type": "comparison",
                "comparator": "equals",
                "path": ["type"],
                "value": "Feature",
                "valueType": "string",
            },
            {
                "type": "comparison",
                "comparator": "equals",
                "path": ["collection"],
                "value": "smart_agriculture",
                "valueType": "string",
            },
            {
                "type": "comparison",
                "comparator": "greaterThan",
                "path": ["properties", "dafab:smart-agriculture", "number_of_fields"],
                "value": SMART_AGRICULTURE_MIN_FIELDS,
                "valueType": "number",
            },
        ],
    }
}

q4_item_ids = dc.get_items_by_enhanced_filter(
    Q4_COMPLEX_FILTER,
    return_mode="ids",
)
print(q4_item_ids[:20])
print(f"Total matches: {len(q4_item_ids)}")

q4_item_ids_mode = dc.get_items_by_enhanced_filter(
    Q4_COMPLEX_FILTER,
    return_mode="ids",
)
q4_item_metadata_mode = dc.get_items_by_enhanced_filter(
    Q4_COMPLEX_FILTER,
    return_mode="metadata",
)

sample_asset_hrefs = [
    item.get("assets", {}).get("dafab-field-boundaries", {}).get("href")
    for item in q4_item_metadata_mode[:5]
]

print(f"IDs mode count: {len(q4_item_ids_mode)}")
print(f"Metadata mode count: {len(q4_item_metadata_mode)}")
print(f"First IDs: {q4_item_ids_mode[:5]}")
print(f"First metadata asset hrefs (dafab-field-boundaries): {sample_asset_hrefs}")

q3_item_metadata = dc.get_items_by_bbox_and_timerange(
    FILTER_BBOX,
    [FILTER_START_DATETIME, FILTER_END_DATETIME],
    return_mode="metadata",
)
print(f"Rendering {len(q3_item_metadata)} items to demo-data/filters/bbox_map.html")
dc.get_map(q3_item_metadata, draw_ids=False)

# STAC root catalog ID used as the top-level entrypoint for discovery.
ROOT_CATALOG_ID = "stac"
print(dc.extract_metadata_value(value_path="", pname=ROOT_CATALOG_ID))

# STAC collection ID in the DaFab catalog (e.g., "sentinel_2_l2a", "water_analysis", "smart_agriculture", ... )
STAC_COLLECTION_ID = "water_analysis"
print(dc.extract_metadata_value(value_path="", pname=STAC_COLLECTION_ID))

print(dc.extract_metadata_value(value_path="", pname=TOP_FACET_CATALOG_ID))

print(dc.extract_metadata_value(value_path="", pname=FACET_VALUE_CATALOG_ID))

print(dc.extract_metadata_value(value_path="", pname=ORIGINAL_ITEM_ID))

print(dc.extract_metadata_value(value_path="", pname=DERIVED_ITEM_ID))

print(dc.extract_metadata_value(
    value_path="/assets/dafab-field-boundaries/href",
    pname=DERIVED_ITEM_ID,
))

PARTIAL_METADATA_PATHS = [
    "/id",
    "/collection",
    "/properties/datetime",
    "/assets/dafab-field-boundaries/href",
]
derived_item_partial_subset = dc.get_bulk_metadata(
    DERIVED_ITEM_ID,
    scope=STAC_SCOPE,
    paths=PARTIAL_METADATA_PATHS,
)
print(dc.as_json(derived_item_partial_subset))

dc.list_storages()

print(dc.as_json(dc.check_storage(rse_name="MELUXINA_S3")))

derived_item_asset_availability = dc.list_item_asset_entries(
    DERIVED_ITEM_ID,
    check_storage=True,
)
print(dc.as_json(derived_item_asset_availability))

derived_item_asset_entries = dc.list_item_asset_entries(
    DERIVED_ITEM_ID,
    check_storage=False,
)
print(dc.as_json(derived_item_asset_entries))

# Get automatically the download href based on a derived id and its asset destination (e.g. https://dafab.cern.ch/stac/assets/dafab/items/S2A_30TYN_20200311_1_L2A_smart_agriculture_120/dafab-field-boundaries)
stable_asset_href = dc.build_stable_asset_href(
    item_id=DERIVED_ITEM_ID,
    asset_key=DERIVED_ASSET_KEY,
)

stable_asset_download = dc.download_asset_from_stable_href(
    stable_href=stable_asset_href,
    destination_dir=ASSET_DOWNLOAD_DIR,
    overwrite=True,
)
print(dc.as_json(stable_asset_download))

item_asset_download = dc.download_item_asset(
    item_id=DERIVED_ITEM_ID,
    asset_key=DERIVED_ASSET_KEY,
    destination_dir=ASSET_DOWNLOAD_DIR,
    overwrite=True,
)
print(dc.as_json(item_asset_download))

all_derived_assets_download = dc.download_all_derived_item_assets(
    item_id=DERIVED_ITEM_ID,
    scope=STAC_SCOPE,
    destination_dir=ASSET_DOWNLOAD_DIR,
    overwrite=True,
)
print(dc.as_json(all_derived_assets_download))
