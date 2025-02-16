import os
import re
import requests
import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon
import shapely.wkt
import re
import xml.etree.ElementTree as ET

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
        # Merge the GeoDataFrame and attributes DataFrame
        enriched_gdf = stitched_gdf.merge(attributes_df, on="region_id", how="left")
        
        # Clean column names
        enriched_gdf.columns = (
            enriched_gdf.columns.str.strip()
            .str.replace('"', '', regex=False)
            .str.replace(' ', '_', regex=False)
            .str.replace("&#", '', regex=False)
        )

        # Clean the content of specific columns
        columns_to_clean = ["HT_NAME", "Konf", "Geb"]
        for column in columns_to_clean:
            if column in enriched_gdf.columns:
                enriched_gdf[column] = (
                    enriched_gdf[column]
                    .str.strip('" ')  # Remove trailing/leading quotes and spaces
                    .str.replace("&#", '', regex=False)  # Remove HTML entities
                )

        # Save the enriched GeoDataFrame to file
        enriched_gdf.to_file(output_path)
        print(f"✅ Enriched map saved as Shapefile at {output_path}")
        return enriched_gdf  # Return the cleaned and merged GeoDataFrame
    else:
        print("⚠️ No data to merge.")
        return None  # Return None explicitly if merging fails



def round_geometry(geom, precision=3):
    # Convert geometry to WKT with rounded coordinates, then load it back
    return shapely.wkt.loads(shapely.wkt.dumps(geom, rounding_precision=precision))


def generate_possible_folders():
    """
    Generate subfolder names with A-F, 0-9, and 10-13.
    This will produce folders like:
      - R0000000A to R0000000F
      - R00000000 to R00000009
      - R00000010 to R00000013
    """
    # A-F
    subfolders = [f"R0000000{chr(i)}" for i in range(65, 71)]
    # 0-9
    subfolders += [f"R0000000{i}" for i in range(10)]
    # 10-13 (note: range(10, 14) yields 10, 11, 12, 13)
    subfolders += [f"R000000{i}" for i in range(10, 14)]
    return subfolders

def generate_possible_filenames():
    """
    Generate image filenames with A-F, 0-9, and 10-12.
    This will produce filenames like:
      - C0000000A.JPG to C0000000F.JPG
      - C00000000.JPG to C00000009.JPG
      - C00000010.JPG to C00000012.JPG
    """
    # A-F
    filenames = [f"C0000000{chr(i)}.JPG" for i in range(65, 71)]
    # 0-9
    filenames += [f"C0000000{i}.JPG" for i in range(10)]
    # 10-12 (note: range(10, 13) yields 10, 11, 12)
    filenames += [f"C000000{i}.JPG" for i in range(10, 13)]
    return filenames

def download_images():
    """Download images and save them with unique filenames."""
    subfolders = generate_possible_folders()
    filenames = generate_possible_filenames()
    downloaded_files = []

    for subfolder in subfolders:
        for filename in filenames:
            image_url = f"{maptiles_base_url}/{subfolder}/{filename}"
            # Create a unique filename combining folder and file names
            unique_filename = f"{subfolder}_{filename}"
            save_path = os.path.join(output_directory, unique_filename)

            try:
                response = requests.get(image_url, stream=True)
                if response.status_code == 200:
                    with open(save_path, "wb") as file:
                        for chunk in response.iter_content(1024):
                            file.write(chunk)
                    print(f"✅ Downloaded {filename} as {unique_filename}")
                    downloaded_files.append((subfolder, filename, save_path))
                else:
                    print(f"❌ Skipped {filename}: Not found at {image_url}.")
            except Exception as e:
                print(f"⚠️ Error downloading {filename}: {e}")

    return downloaded_files

def generate_vrt(downloaded_files):
    """Generate a Virtual Raster (.vrt) that correctly positions all downloaded tiles."""
    vrt_path = os.path.join(output_directory, "merged_tiles.vrt")
    vrt_root = ET.Element("VRTDataset")

    # Tile dimensions (adjust if needed)
    tile_width, tile_height = 256, 256
    min_row, max_row = float("inf"), float("-inf")
    min_col, max_col = float("inf"), float("-inf")

    tile_info = []
    # Regex to capture one or more hexadecimal characters from both folder and filename parts
    pattern = r"R0000000([A-F0-9]+)_C0000000([A-F0-9]+)\.JPG"

    for subfolder, filename, file_path in downloaded_files:
        combined_name = f"{subfolder}_{filename}"
        match = re.search(pattern, combined_name)
        if match:
            # Interpret the captured groups as hexadecimal values
            row = int(match.group(1), 16)
            col = int(match.group(2), 16)
            min_row = min(min_row, row)
            max_row = max(max_row, row)
            min_col = min(min_col, col)
            max_col = max(max_col, col)
            # Use basename so that the VRT can refer to the image relative to its location
            tile_info.append((row, col, os.path.basename(file_path)))
        else:
            print(f"❌ Failed to parse filename: {combined_name}")

    if not tile_info:
        print("No valid tiles found. Exiting VRT generation.")
        return None

    # Calculate overall raster dimensions based on the grid of tiles
    raster_width = (max_col - min_col + 1) * tile_width
    raster_height = (max_row - min_row + 1) * tile_height
    vrt_root.set("rasterXSize", str(raster_width))
    vrt_root.set("rasterYSize", str(raster_height))

    # Create a VRT with three bands (assuming the JPEG images are in RGB)
    for band in range(1, 4):  # Bands 1 (Red), 2 (Green), 3 (Blue)
        raster_band = ET.SubElement(vrt_root, "VRTRasterBand", dataType="Byte", band=str(band))
        for row, col, filename in tile_info:
            simple_source = ET.SubElement(raster_band, "SimpleSource")
            ET.SubElement(simple_source, "SourceFilename", relativeToVRT="1").text = filename
            ET.SubElement(simple_source, "SourceBand").text = str(band)
            # Define the source rectangle covering the entire tile
            ET.SubElement(simple_source, "SrcRect", xOff="0", yOff="0",
                          xSize=str(tile_width), ySize=str(tile_height))
            # Calculate destination offsets relative to the minimum row and col
            x_offset = (col - min_col) * tile_width
            y_offset = (row - min_row) * tile_height
            ET.SubElement(simple_source, "DstRect", xOff=str(x_offset), yOff=str(y_offset),
                          xSize=str(tile_width), ySize=str(tile_height))

    # Write the VRT XML to file
    vrt_data = ET.tostring(vrt_root, encoding="utf-8").decode()
    with open(vrt_path, "w") as vrt_file:
        vrt_file.write(vrt_data)

    print(f"✅ VRT file created: {vrt_path}")
    return vrt_path
