import os
import pyreadr
import pandas as pd
import geopandas as gpd
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union
import matplotlib.pyplot as plt
import contextily as ctx

from src.data_management.fun_manage import (
    load_geodata,
    load_religion_data,
    merge_data_religion
)

# ----------------------------------------------------------------------
# 1. Define File Paths
# ----------------------------------------------------------------------
geo_filepath = '../../data/shapefiles/vg250_ebenen_1231/DE_VG250.gpkg'
religion_filepath = '../../data/zensus/religion.xlsx'
enriched_filepath = '../../data/hre/digital_atlas/map/enriched_map.shp'  # HRE Map

national_rds_path = '../../data/election/federal_muni_harm.rds'

hre_clipped_filepath = '../../bld/data/catholic_hre_clipped.gpkg'  # Where we save the clipped HRE map

output_folder = "../../bld/data/"
os.makedirs(output_folder, exist_ok=True)

# ----------------------------------------------------------------------
# 2. Load Data
# ----------------------------------------------------------------------

# Load Religion Data
religion_data = load_religion_data(religion_filepath)

# Load Election Data
result_national = pyreadr.read_r(national_rds_path)
df_national = result_national[None]

# Load Geospatial Data (Municipalities)
gem_data = load_geodata(geo_filepath)

# ----------------------------------------------------------------------
# 3. Clip the Catholic HRE Polygon to Modern Germany
# ----------------------------------------------------------------------

# Load Enriched HRE Map
enriched_gdf = gpd.read_file(enriched_filepath)

# Filter for Catholic regions (Konf = "ka")
catholic_hre_gdf = enriched_gdf[enriched_gdf["Konf"] == "ka"].copy()

# Ensure CRS Matches
catholic_hre_gdf = catholic_hre_gdf.to_crs(gem_data.crs)

# Compute Germany’s boundary as the union of all municipalities
germany_boundary = gem_data.unary_union

# Clip the Catholic HRE polygon to only keep parts inside Germany
catholic_hre_clipped = catholic_hre_gdf.intersection(germany_boundary)

# Combine all geometries in the Catholic HRE polygon into a single smooth geometry
catholic_hre_clipped = catholic_hre_clipped.unary_union

# Convert back to GeoDataFrame for compatibility
catholic_hre_clipped = gpd.GeoDataFrame(
    geometry=[catholic_hre_clipped], crs=gem_data.crs
)

# Simplify the polygon to remove jagged edges (adjust tolerance for smoother results)
catholic_hre_clipped["geometry"] = catholic_hre_clipped.simplify(tolerance=500, preserve_topology=True)

# Save the clipped Catholic HRE polygon
catholic_hre_clipped.to_file(hre_clipped_filepath, driver="GPKG")
print("✅ Simplified Catholic HRE polygon saved!")

# ----------------------------------------------------------------------
# 4. Merge Geospatial Data with Election Data
# ----------------------------------------------------------------------

# Rename 'ags' in election data to avoid conflict
df_national = df_national.rename(columns={'ags': 'ags_election'})

# Merge Election Data with Municipalities
map_data_national = gem_data.merge(df_national, left_on='AGS', right_on='ags_election', how='left')

# Merge with Religion Data
map_data_national = merge_data_religion(map_data_national, religion_data)

# Drop Duplicate 'AGS' Column
map_data_national = map_data_national.drop(columns=['ags'], errors='ignore')

# ----------------------------------------------------------------------
# 5. Compute Signed Distance to Catholic HRE Border
# ----------------------------------------------------------------------

# Convert municipalities to centroids
map_data_national["centroid"] = map_data_national.geometry.centroid

# Compute minimum distance from each municipality's centroid to Catholic HRE border
map_data_national["distance_to_border"] = map_data_national["centroid"].apply(
    lambda x: catholic_hre_clipped.geometry.distance(x).min()
)

# Correct signed distance: Positive inside, Negative outside
map_data_national["signed_distance_to_border"] = map_data_national.apply(
    lambda row: row["distance_to_border"] if catholic_hre_clipped.contains(row["centroid"]).any() else -row["distance_to_border"],
    axis=1
)

# Ensure only one geometry column before saving
if "centroid" in map_data_national.columns:
    map_data_national = map_data_national.drop(columns=["centroid"])

# ----------------------------------------------------------------------
# 6. Save Cleaned Dataset with Only Signed Distance
# ----------------------------------------------------------------------

# Save the final national dataset with signed distance only
output_filepath = f"{output_folder}merged_national_with_signed_distance.gpkg"
map_data_national.to_file(output_filepath, driver="GPKG")

print("✅ Clean dataset with signed distance saved in:", output_folder)

# ----------------------------------------------------------------------
# 7. Visualize Signed Distance to Catholic HRE Border
# ----------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(12, 10))

# Plot municipalities with color based on signed distance
map_data_national.plot(
    ax=ax, column="signed_distance_to_border",
    cmap="coolwarm", edgecolor="black",
    linewidth=0.2, alpha=0.8, legend=True
)

# Plot the simplified Catholic HRE polygon
catholic_hre_clipped.plot(
    ax=ax, color="none", edgecolor="black",
    linewidth=2, label="Simplified Catholic HRE Border"
)

# Add a basemap for context
ctx.add_basemap(ax, source=ctx.providers.OpenStreetMap.Mapnik, crs=map_data_national.crs, alpha=0.5)

# Customize the Plot
ax.set_title("Signed Distance to Catholic HRE Border (Simplified)", fontsize=14)
ax.legend()
ax.axis("off")  # Hide axes

plt.show()
