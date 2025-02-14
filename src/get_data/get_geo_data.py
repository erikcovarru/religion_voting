from src.get_data.fun_get_data import (
    download_geotiles, 
    download_js_file,
    parse_attributes, 
    build_geodata, 
    merge_and_save_enriched_map,
    round_geometry,
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

# Additional geometry cleaning:
# 1. Fix geometries with a zero-width buffer
enriched_gdf['geometry'] = enriched_gdf['geometry'].buffer(0)

# 2. Round geometries to reduce floating-point discrepancies
enriched_gdf['geometry'] = enriched_gdf['geometry'].apply(round_geometry)
    
# 3. Dissolve the geometries by region_id to merge adjacent parts
dissolved_gdf = enriched_gdf.dissolve(by="region_id")
    
# 4. Snap edges with a small positive then negative buffer
dissolved_gdf['geometry'] = dissolved_gdf['geometry'].buffer(0.01).buffer(-0.01)
dissolved_gdf = dissolved_gdf.dissolve(by="region_id")

# 5. Further simplify the geometries to remove residual vertical/horizontal lines
dissolved_gdf['geometry'] = dissolved_gdf['geometry'].simplify(tolerance=1.0, preserve_topology=True)
dissolved_gdf = dissolved_gdf.dissolve(by="region_id")

# Save the cleaned GeoDataFrame to file
dissolved_gdf.to_file(enriched_shapefile_path)
print(f"✅ Enriched map saved as Shapefile at {enriched_shapefile_path}")

# Plot the enriched map with OpenStreetMap basemap
import matplotlib.pyplot as plt
import contextily as ctx

fig, ax = plt.subplots(figsize=(12, 12))
dissolved_gdf.boundary.plot(ax=ax, color="black", linewidth=0.5)
ctx.add_basemap(ax, crs=dissolved_gdf.crs.to_string(), source=ctx.providers.OpenStreetMap.Mapnik)
ax.set_title("Enriched Map with OpenStreetMap Basemap")
plt.xlabel("UTM Easting")
plt.ylabel("UTM Northing")
plt.grid(True)
plt.show()
