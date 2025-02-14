import os
import pyreadr
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
from shapely.ops import snap
from shapely.geometry import Polygon, MultiPolygon

from fun_manage import (
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

# Ensure CRS matches the municipalities
catholic_hre_gdf = catholic_hre_gdf.to_crs(gem_data.crs)

# Compute Germany’s boundary as the union of all municipalities using union_all()
germany_boundary = gem_data.geometry.union_all()

# Clip the Catholic HRE polygon to only keep parts inside Germany
catholic_hre_clipped = catholic_hre_gdf.intersection(germany_boundary)

# --- Dissolve and Clean up the Catholic HRE Geometry ---
# First, combine all Catholic areas using union_all()
catholic_hre_union = catholic_hre_clipped.geometry.union_all()

# Set parameters for snapping and hole filling.
# Adjust these based on the scale of your data.
snap_tolerance = 1e-2        # vertices within this distance will be snapped together
hole_area_threshold = 1000   # holes with an area below this threshold (in CRS units²) will be filled

# Use snapping to “fix” misaligned boundaries.
catholic_hre_snapped = snap(catholic_hre_union, catholic_hre_union, snap_tolerance)
# A zero-width buffer cleans minor artifacts.
catholic_hre_snapped = catholic_hre_snapped.buffer(0)

# Define a function to fill only small holes in a polygon.
def fill_small_holes(poly, area_threshold):
    """
    Returns a new Polygon where interior rings (holes) with area below area_threshold are removed.
    """
    if poly.interiors:
        new_interiors = []
        for interior in poly.interiors:
            ring_poly = Polygon(interior)
            # Keep only holes larger than the threshold.
            if ring_poly.area >= area_threshold:
                new_interiors.append(interior)
        return Polygon(poly.exterior, new_interiors)
    else:
        return poly

# Process each component separately.
if catholic_hre_snapped.geom_type == 'MultiPolygon':
    filled_polys = []
    for poly in catholic_hre_snapped.geoms:
        # Instead of taking the exterior (which would lose all holes), fill only very small ones.
        filled_poly = fill_small_holes(poly, hole_area_threshold)
        filled_polys.append(filled_poly)
    catholic_hre_final = MultiPolygon(filled_polys)
else:
    catholic_hre_final = fill_small_holes(catholic_hre_snapped, hole_area_threshold)

# Final check: Ensure the geometry is valid.
if not catholic_hre_final.is_valid:
    catholic_hre_final = catholic_hre_final.buffer(0)

# Convert back to a GeoDataFrame.
catholic_hre_clipped = gpd.GeoDataFrame(geometry=[catholic_hre_final], crs=gem_data.crs)

# Optionally, simplify the geometry further (adjust tolerance as needed) while preserving topology.
catholic_hre_clipped["geometry"] = catholic_hre_clipped.simplify(tolerance=500, preserve_topology=True)

# Save the cleaned Catholic HRE polygon.
catholic_hre_clipped.to_file(hre_clipped_filepath, driver="GPKG")
print("✅ Simplified Catholic HRE polygon saved!")

# ----------------------------------------------------------------------
# 4. Merge Geospatial Data with Election Data
# ----------------------------------------------------------------------
# Rename 'ags' in election data to avoid conflict.
df_national = df_national.rename(columns={'ags': 'ags_election'})

# Merge Election Data with Municipalities.
map_data_national = gem_data.merge(df_national, left_on='AGS', right_on='ags_election', how='left')

# Merge with Religion Data.
map_data_national = merge_data_religion(map_data_national, religion_data)

# Drop duplicate 'AGS' column if present.
map_data_national = map_data_national.drop(columns=['ags'], errors='ignore')

# ----------------------------------------------------------------------
# 5. Compute Signed Distance to Catholic HRE Border
# ----------------------------------------------------------------------
# Extract the cleaned geometry (which may be a MultiPolygon) from the GeoDataFrame.
catholic_poly = catholic_hre_clipped.iloc[0].geometry

# Ensure the final geometry is valid.
if not catholic_poly.is_valid:
    catholic_poly = catholic_poly.buffer(0)

# Compute centroids for each municipality.
map_data_national["centroid"] = map_data_national.geometry.centroid

# Compute the distance from each centroid to the Catholic HRE boundary.
map_data_national["distance_to_border"] = map_data_national["centroid"].apply(
    lambda pt: pt.distance(catholic_poly.boundary)
)

# Assign positive distance for points inside (contained in any part), negative if outside.
map_data_national["signed_distance_to_border"] = map_data_national.apply(
    lambda row: row["distance_to_border"] if catholic_poly.contains(row["centroid"]) else -row["distance_to_border"],
    axis=1
)

# Create an absolute distance column (for plotting) while preserving the signed distance.
map_data_national["abs_distance_to_border"] = map_data_national["signed_distance_to_border"].abs()

# Remove the temporary centroid column.
if "centroid" in map_data_national.columns:
    map_data_national = map_data_national.drop(columns=["centroid"])

# ----------------------------------------------------------------------
# 6. Save Cleaned Dataset with Only Signed Distance
# ----------------------------------------------------------------------
output_filepath = f"{output_folder}merged_national_with_signed_distance.gpkg"
map_data_national.to_file(output_filepath, driver="GPKG")
print("✅ Clean dataset with signed distance saved in:", output_folder)

# ----------------------------------------------------------------------
# 7. Visualize Absolute Distance to Catholic HRE Border
# ----------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(12, 10))

# Plot municipalities using the absolute distance for the color scale.
map_data_national.plot(
    ax=ax, column="abs_distance_to_border",
    cmap="coolwarm", edgecolor="none",
    linewidth=0.2, alpha=0.8, legend=True
)

# Overlay the simplified Catholic HRE polygon border.
catholic_hre_clipped.plot(
    ax=ax, color="none", edgecolor="black",
    linewidth=2, label="Simplified Catholic HRE Border"
)

# Customize the plot appearance.
ax.set_title("Absolute Distance to Catholic HRE Border (Simplified)", fontsize=14)
ax.legend()
ax.axis("off")  # Hide axes

plt.show()
