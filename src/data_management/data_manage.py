import os
import pyreadr
import geopandas as gpd

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
national_rds_path = '../../data/election/federal_muni_harm.rds'
hre_filepath = "../data/hre/digital_atlas/maptiles/WHRE.shp"  

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

# Define the SN_L keys corresponding to current West German states.
# (Adjust these keys as needed for your dataset.)
west_germany_keys = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10']

# Filter municipalities to only include those in West Germany.
west_germany_admin = gem_data[gem_data["SN_L"].isin(west_germany_keys)].copy()

# Load the historical Catholic HRE polygon and ensure CRS match.
catholic_hre = gpd.read_file(hre_filepath)
catholic_hre = catholic_hre.to_crs(west_germany_admin.crs)

# ----------------------------------------------------------------------
# 3. PREPARE THE HRE BOUNDARY FOR WEST GERMANY
# ----------------------------------------------------------------------
# Compute the full union of the HRE polygon(s)
hre_union = catholic_hre.unary_union

# Compute the West Germany boundary as a single polygon (union of West German municipalities)
west_germany_boundary = west_germany_admin.geometry.unary_union

# Obtain only those parts of the HRE boundary that lie within West Germany.
# This gives the boundary segments used for distance calculations.
internal_west_hre_border = hre_union.boundary.intersection(west_germany_boundary)

# Also, compute the West German portion of the HRE region. This will be used to assign
# a positive (treated) sign to municipalities inside the HRE.
west_hre_polygon = hre_union.intersection(west_germany_boundary)

# ----------------------------------------------------------------------
# 4. COMPUTE DISTANCES (RUNNING VARIABLE)
# ----------------------------------------------------------------------
# Compute centroids for each West German municipality
west_germany_admin["centroid"] = west_germany_admin.geometry.centroid

# For each municipality, compute the distance from its centroid to the internal HRE border (only within West Germany)
west_germany_admin["distance_to_border"] = west_germany_admin["centroid"].apply(
    lambda pt: pt.distance(internal_west_hre_border)
)

# Assign a signed distance:
#   Positive if the centroid lies within the West HRE polygon (historically Catholic),
#   Negative if outside (historically Protestant).
west_germany_admin["signed_distance_to_border"] = west_germany_admin.apply(
    lambda row: row["distance_to_border"] if west_hre_polygon.contains(row["centroid"]) else -row["distance_to_border"],
    axis=1
)

# Optionally, drop the temporary centroid column
west_germany_admin = west_germany_admin.drop(columns=["centroid"])

# ----------------------------------------------------------------------
# 5. MERGE COMPUTED DISTANCES WITH THE FULL GEOSPATIAL DATA
# ----------------------------------------------------------------------
# Merge the signed distance from the West German subset into the full municipalities data.
# Municipalities outside West Germany will have missing (NaN) signed_distance_to_border.
gem_data = gem_data.merge(
    west_germany_admin[['AGS', 'signed_distance_to_border']],
    on='AGS',
    how='left'
)

# ----------------------------------------------------------------------
# 6. MERGE GEOSPATIAL DATA WITH ELECTION AND RELIGION DATA
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
# 7. SAVE CLEANED DATASET WITH SIGNED DISTANCE & CLIPPED HRE POLYGON
# ----------------------------------------------------------------------
# Define the output geopackage file path.
output_filepath = f"{output_folder}merged_national_with_signed_distance.gpkg"

# Save the merged municipality data as one layer (e.g., "municipalities").
map_data_national.to_file(output_filepath, driver="GPKG", layer="municipalities")

# Save the clipped HRE polygon (West German portion) as a separate layer.
west_hre_gdf = gpd.GeoDataFrame({'geometry': [west_hre_polygon]}, crs=west_germany_admin.crs)
west_hre_gdf.to_file(output_filepath, driver="GPKG", layer="west_hre_polygon")

print("✅ Clean dataset with signed distance and clipped HRE polygon saved in:", output_filepath)
