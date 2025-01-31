#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import math
import geopandas as gpd
from shapely.geometry import Polygon
import geopandas as gpd
import matplotlib.pyplot as plt

################################################################################
# 1) GLOBAL VARIABLES (FOR TILES_1)
################################################################################

g_rwUL = (-456230.500963895, 6402413.07213028)   # upper-left corner (UTM)
g_rwLR = (1016818.95627862, 4877042.18607861)    # lower-right corner (UTM)

# If TILES_0 => 1.0, TILES_1 => 6.6137..., we pick zoomLevel=1
g_baseMapExt = [732, 758]  # base dimension (width=732, height=758) at zoom=0
g_zoomFactors = [1.0, 6.61370869565217]
zoomLevel = 1  # TILES_1

# Each tile is 512×512 px
g_geoTileSize = [512, 512]

################################################################################
# 2) JS-EQUIVALENT FUNCTIONS
################################################################################

def get_zoomFactor():
    return g_zoomFactors[zoomLevel]

def get_scaleFactor():
    """
    scale = abs( (g_baseMapExt[1]*zoomFactor) / (g_rwLR[1] - g_rwUL[1]) )
    """
    baseH = g_baseMapExt[1]
    zoomF = get_zoomFactor()
    real_world_height = (g_rwLR[1] - g_rwUL[1])
    return abs((baseH * zoomF) / real_world_height)

def px2rw(pxVal):
    """ pxVal / scaleFactor => px => meters """
    return pxVal / get_scaleFactor()

def px2rw_point(pxPt):
    """
    JS px2rw_point(pxPt):
      X_UTM = g_rwUL[0] + px2rw(pxX)
      Y_UTM = g_rwUL[1] - px2rw(pxY)
    """
    pxX, pxY = pxPt
    X_UTM = g_rwUL[0] + px2rw(pxX)
    Y_UTM = g_rwUL[1] - px2rw(pxY)
    return (X_UTM, Y_UTM)

################################################################################
# 3) TILE COORDINATE TRANSFORM (SWAP ROW AND COL)
################################################################################

def tile_coords_to_utm(row, col, local_x, local_y):
    """
    row, col = tile indices
    local_x, local_y = [0..512]
    
    NOTE: We swap usage: global_pxX = row*g_tileW, global_pxY=col*g_tileH
    to avoid the diagonal offset from the original (col, row).
    """
    tileW, tileH = g_geoTileSize
    
    # SWAP row↔col for the pixel offsets
    global_pxX = row * tileW + local_x
    global_pxY = col * tileH + local_y

    # convert to UTM
    return px2rw_point((global_pxX, global_pxY))

################################################################################
# 4) PARSE A SINGLE TILE FILE
################################################################################

def parse_js_file(filepath, row, col):
    polygons = []
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        # coords="..." 
        matches = re.findall(
            r'coords="([^"]+)" href="javascript:show_popup\((\d+)\);" id="(\d+)_area" title="([^"]+)"',
            content
        )
        for coords_str, region_id, _, region_name in matches:
            coord_list = list(map(int, coords_str.split(",")))

            points_utm = []
            for i in range(0, len(coord_list), 2):
                x_local = coord_list[i]
                y_local = coord_list[i+1]

                X_UTM, Y_UTM = tile_coords_to_utm(row, col, x_local, y_local)
                points_utm.append((X_UTM, Y_UTM))

            if len(points_utm) >= 3:
                polygons.append({
                    "geometry": Polygon(points_utm),
                    "region_id": int(region_id),
                    "region_name": region_name
                })
    return polygons

################################################################################
# 5) BUILD FULL GDF (TILES_1)
################################################################################

def build_full_geodata(tiles_root, num_rows=10, num_cols=10):
    """
    TILES_1 => row=0..9, col=0..9 => 100 .JS
    """
    all_polygons = []
    subdir = os.path.join(tiles_root, "TILES_1")

    for row_idx in range(num_rows):
        for col_idx in range(num_cols):
            js_filename = f"{row_idx}_{col_idx}.JS"
            file_path = os.path.join(subdir, js_filename)
            if os.path.isfile(file_path):
                poly_list = parse_js_file(file_path, row_idx, col_idx)
                all_polygons.extend(poly_list)
            else:
                print(f"File not found: {file_path}")

    if all_polygons:
        gdf = gpd.GeoDataFrame(all_polygons, geometry="geometry")
        gdf.crs = "EPSG:32633"
    else:
        gdf = gpd.GeoDataFrame(columns=["geometry","region_id","region_name"], geometry="geometry")

    return gdf

################################################################################
# 6) MAIN
################################################################################

if __name__ == "__main__":
    tiles_root = "../../data/hre/digital_atlas/geotiles"
    gdf_utm = build_full_geodata(tiles_root, num_rows=10, num_cols=10)

    if not gdf_utm.empty:
        out_path = "../../data/hre/digital_atlas/map/enriched_map_utm_TILES1_swapped.shp"
        gdf_utm.to_file(out_path)
        print(f"✅ Saved polygons (row↔col swapped) -> {out_path}")
    else:
        print("⚠️ No polygons extracted!")



# 2) Plot it (outline only)
fig, ax = plt.subplots(figsize=(8, 8))
gdf_utm.plot(ax=ax, color="none", edgecolor="black")

ax.set_title("Scaled TILES_1 Puzzle")
plt.show()
