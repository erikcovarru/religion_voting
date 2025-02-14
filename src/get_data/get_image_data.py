import os
import requests
import re
import xml.etree.ElementTree as ET

# Base URL for downloading tiles
maptiles_base_url = "https://www.atlas-europa.de/t02/konfessionen/Konfessionen/MAPTILEIMAGES_0/L01"

# Output directory for storing downloaded images
output_directory = "../../data/hre/digital_atlas/maptiles"
os.makedirs(output_directory, exist_ok=True)

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

# 🔹 Run the full process
downloaded_files = download_images()
vrt_file = generate_vrt(downloaded_files)

print("\n🎯 All tiles downloaded and Virtual Raster created. Load the `.vrt` in QGIS!")
