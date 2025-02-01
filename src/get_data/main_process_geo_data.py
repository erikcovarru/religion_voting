from fun_process_geo_data import (
    download_geotiles, 
    download_js_file,
    parse_attributes, 
    build_geodata, 
    merge_and_save_enriched_map
)
import os
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx

# Base URLs and directories
geotiles_base_url = "https://www.atlas-europa.de/t02/konfessionen/Konfessionen/GEOTILES_0"
attributes_base_url = "https://www.atlas-europa.de/t02/konfessionen/Konfessionen/ATTRIBUTES_0"
geotiles_output_dir = "../../data/hre/digital_atlas/geotiles"
attributes_output_dir = "../../data/hre/digital_atlas/attributes"
enriched_shapefile_path = "../../data/hre/digital_atlas/map/enriched_map.shp"

# Download GEOTILES
download_geotiles(
    base_url=geotiles_base_url,
    output_dir=geotiles_output_dir,
    zoom_levels=[1],  # Adjust zoom levels as needed
    num_tiles_x=10,
    num_tiles_y=10
)

# Download ATTRIBUTES
attribute_files = [f"{i}.JS" for i in range(40)]
for file_name in attribute_files:
    file_url = f"{attributes_base_url}/{file_name}"
    save_path = os.path.join(attributes_output_dir, file_name)
    download_js_file(file_url, save_path)

# Parse ATTRIBUTES
attributes_df = parse_attributes(attributes_output_dir)

# Build GeoDataFrame from GEOTILES
tiles_directory = f"{geotiles_output_dir}/TILES_1"  # Update for the correct zoom level
stitched_gdf = build_geodata(tiles_directory, zoomLevel=1)

# Merge and save enriched map
enriched_gdf = merge_and_save_enriched_map(
    stitched_gdf=stitched_gdf,
    attributes_df=attributes_df,
    output_path=enriched_shapefile_path
)

# Plot the enriched map with OpenStreetMap basemap
fig, ax = plt.subplots(figsize=(12, 12))
enriched_gdf.boundary.plot(ax=ax, color="red", linewidth=1)
ctx.add_basemap(ax, crs=enriched_gdf.crs.to_string(), source=ctx.providers.OpenStreetMap.Mapnik)
ax.set_title("Enriched Map with OpenStreetMap Basemap")
plt.xlabel("UTM Easting")
plt.ylabel("UTM Northing")
plt.grid(True)
plt.show()
