import os
import re
import requests
import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

# Define global parameters
g_rwUL = (-456230.500963895, 6402413.07213028)  # upper-left UTM
g_rwLR = (1016818.95627862, 4877042.18607861)  # lower-right UTM
g_baseMapExt = [732, 758]  # Base dimension at zoom=0
g_zoomFactors = [1.0, 6.61370869565217]  # Scaling factors
g_geoTileSize = [512, 512]  # Tile size in pixels

# Manual offsets for alignment adjustments
row_offset = 0  # Adjust for row shifting, in UTM units
col_offset = 0  # Adjust for column shifting, in UTM units

def get_zoomFactor(zoomLevel):
    return g_zoomFactors[zoomLevel]

def get_scaleFactor(zoomLevel):
    baseH = g_baseMapExt[1]
    zoomF = get_zoomFactor(zoomLevel)
    real_world_height = (g_rwLR[1] - g_rwUL[1])
    return abs((baseH * zoomF) / real_world_height)

def px2rw(pxVal, zoomLevel):
    return pxVal / get_scaleFactor(zoomLevel)

def px2rw_point_with_offset(pxPt, row, col, zoomLevel):
    pxX, pxY = pxPt
    X_UTM = g_rwUL[0] + px2rw(pxX, zoomLevel) + col * col_offset
    Y_UTM = g_rwUL[1] - px2rw(pxY, zoomLevel) - row * row_offset
    return (X_UTM, Y_UTM)

def parse_js_file(filepath, row, col, zoomLevel):
    polygons = []
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        matches = re.findall(r'coords="([^"]+)" href="javascript:show_popup\((\d+)\);" id="(\d+)_area" title="([^"]+)"', content)
        for coords_str, region_id, _, region_name in matches:
            coord_list = list(map(int, coords_str.split(",")))
            points_utm = []
            for i in range(0, len(coord_list), 2):
                x_local = coord_list[i]
                y_local = coord_list[i + 1]
                X_UTM, Y_UTM = px2rw_point_with_offset((x_local, y_local), row, col, zoomLevel)
                points_utm.append((X_UTM, Y_UTM))
            if len(points_utm) >= 3:
                polygons.append({
                    "geometry": Polygon(points_utm),
                    "region_id": int(region_id),
                    "region_name": region_name
                })
    return polygons

def build_geodata(tiles_dir, zoomLevel):
    all_polygons = []
    for filename in os.listdir(tiles_dir):
        if filename.endswith(".JS"):
            row, col = map(int, filename.replace(".JS", "").split("_"))
            file_path = os.path.join(tiles_dir, filename)
            all_polygons.extend(parse_js_file(file_path, row, col, zoomLevel))
    return gpd.GeoDataFrame(all_polygons, geometry="geometry", crs="EPSG:32633")

def download_js_file(file_url, save_path):
    try:
        response = requests.get(file_url, timeout=10)
        response.raise_for_status()
        with open(save_path, "wb") as file:
            file.write(response.content)
        print(f"✅ Downloaded: {file_url}")
    except Exception as e:
        print(f"⚠️ Failed to download {file_url}: {e}")

def download_geotiles(base_url, output_dir, zoom_levels, num_tiles_x, num_tiles_y):
    os.makedirs(output_dir, exist_ok=True)
    for zoom_level in zoom_levels:
        tile_dir = f"TILES_{zoom_level}"
        dir_url = f"{base_url}/{tile_dir}"
        local_dir = os.path.join(output_dir, tile_dir)
        os.makedirs(local_dir, exist_ok=True)
        for row in range(num_tiles_y):
            for col in range(num_tiles_x):
                tile_file = f"{row}_{col}.JS"
                tile_url = f"{dir_url}/{tile_file}"
                save_path = os.path.join(local_dir, tile_file)
                download_js_file(tile_url, save_path)

def parse_attributes(attributes_dir):
    all_attributes = []
    for filename in os.listdir(attributes_dir):
        if filename.endswith(".JS"):
            file_path = os.path.join(attributes_dir, filename)
            with open(file_path, "r", encoding="utf-8") as file:
                js_content = file.read()
                matches = re.findall(r'add_content\((\d+),"(.*?)"\)', js_content)
                for match in matches:
                    region_id = int(match[0])
                    data = match[1].split(",")
                    parsed_data = {}
                    for item in data:
                        if "||" in item:
                            key, value = item.split("||", 1)
                            parsed_data[key.strip()] = value.strip()
                    parsed_data["region_id"] = region_id
                    all_attributes.append(parsed_data)
    return pd.DataFrame(all_attributes)

def merge_and_save_enriched_map(stitched_gdf, attributes_df, output_path):
    if not stitched_gdf.empty and not attributes_df.empty:
        enriched_gdf = stitched_gdf.merge(attributes_df, on="region_id", how="left")
        enriched_gdf.columns = (
            enriched_gdf.columns.str.strip()
            .str.replace('"', '', regex=False)
            .str.replace(' ', '_', regex=False)
            .str.replace("&#", '', regex=False)
        )
        enriched_gdf.to_file(output_path)
        print(f"✅ Enriched map saved as Shapefile at {output_path}")
        return enriched_gdf  # Ensure it returns the merged dataframe
    else:
        print("⚠️ No data to merge.")
        return None  # Return None explicitly if merging fails

