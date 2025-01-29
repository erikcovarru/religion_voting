import os
import requests
from PIL import Image
import rasterio
from rasterio.transform import from_bounds
import matplotlib.pyplot as plt
import numpy as np
import geopandas as gpd
import re
import json
import pandas as pd
from bs4 import BeautifulSoup
from rasterio.features import shapes

# Base URL of the map tiles
base_url = "https://www.atlas-europa.de/t02/konfessionen/Konfessionen/MAPTILEIMAGES_0/L00"

# Local directory to save the tiles
output_dir = "../../data/hre/digital_atlas/tiles"

# Loop through rows (R000000XX)
for row in range(3):  # Adjust the range based on your structure (e.g., 0 to 2 for 3 rows)
    row_dir = f"R{row:08d}"  # Format row as R00000000, R00000001, etc.
    os.makedirs(os.path.join(output_dir, row_dir), exist_ok=True)  # Create subdirectory for rows
    
    # Loop through columns (C000000XX)
    for col in range(3):  # Adjust range based on the number of columns (e.g., 0 to 2 for 3 columns)
        column_file = f"C{col:08d}.JPG"  # Format column as C00000000.JPG
        tile_url = f"{base_url}/{row_dir}/{column_file}"  # Full URL for the tile
        
        # Save path for the tile
        save_path = os.path.join(output_dir, row_dir, column_file)
        
        try:
            # Download the tile
            response = requests.get(tile_url, timeout=10)
            response.raise_for_status()  # Raise an error for HTTP failures
            
            # Save the tile locally
            with open(save_path, "wb") as file:
                file.write(response.content)
            
            print(f"Downloaded: {tile_url}")
        
        except requests.RequestException as e:
            print(f"Failed to download {tile_url}: {e}")

tile_dir = output_dir

# Define the tile size (assuming all tiles are the same size)
tile_size = 256  # Adjust if tiles are not 256x256

# Get all row directories (e.g., R00000000, R00000001, ...)
row_dirs = sorted([d for d in os.listdir(tile_dir) if d.startswith("R")])

# Initialize a list to hold stitched rows
rows = []

# Loop through each row directory
for row_dir in row_dirs:
    row_path = os.path.join(tile_dir, row_dir)
    
    # Get all tile images (e.g., C00000000.JPG, C00000001.JPG, ...)
    tiles = sorted([f for f in os.listdir(row_path) if f.endswith(".JPG")])
    
    # Open all tiles in the row
    row_images = [Image.open(os.path.join(row_path, tile)) for tile in tiles]
    
    # Determine the total width of the row (number of tiles * tile size)
    row_width = len(row_images) * tile_size
    
    # Create an empty image to hold the stitched row
    row_combined = Image.new("RGB", (row_width, tile_size))
    
    # Paste each tile into the combined row image
    for i, img in enumerate(row_images):
        row_combined.paste(img, (i * tile_size, 0))
    
    # Add the stitched row to the list of rows
    rows.append(row_combined)

# Now stitch all rows together into one large image
# Determine the final map dimensions
map_height = len(rows) * tile_size  # Number of rows * tile size
map_width = rows[0].width          # Width of a single row (all rows have the same width)

# Create an empty image to hold the entire stitched map
combined_map = Image.new("RGB", (map_width, map_height))

# Paste each row into the final stitched map
for i, row in enumerate(rows):
    combined_map.paste(row, (0, i * tile_size))

# Save the stitched map as a single image
stitched_map_path = "../../data/hre/digital_atlas/stitched_map/stitched_map.jpg"
combined_map.save(stitched_map_path)

print(f"Map stitching complete! Saved as {stitched_map_path}")


stitched_map_path = "../../data/hre/digital_atlas/stitched_map/stitched_map.jpg"
geo_tiff_path = "../../bld/maps/georeferenced_map.tif"

# Define the map bounds and CRS
bounds = (-456230.500963895, 4877042.18607861, 1016818.95627862, 6402413.07213028)  # UL and LR
crs = "EPSG:32633"

# Open the stitched JPEG map
with Image.open(stitched_map_path) as img:
    img_data = np.array(img)  # Convert to numpy array

# Validate the shape of the image data
if img_data.shape[-1] != 3:  # Ensure it's RGB
    raise ValueError("Image is not in RGB format!")

# Create the GeoTIFF
height, width, _ = img_data.shape
with rasterio.open(
    geo_tiff_path,
    "w",
    driver="GTiff",
    height=height,
    width=width,
    count=3,  # Number of bands (R, G, B)
    dtype="uint8",
    crs=crs,
    transform=from_bounds(*bounds, width, height),
) as dst:
    dst.write(img_data[:, :, 0], 1)  # Red band
    dst.write(img_data[:, :, 1], 2)  # Green band
    dst.write(img_data[:, :, 2], 3)  # Blue band

print(f"GeoTIFF successfully recreated at {geo_tiff_path}")


# Base URL for attributes
base_url = "https://www.atlas-europa.de/t02/konfessionen/Konfessionen/ATTRIBUTES_0"

# Local directory to save downloaded attribute files
output_dir = "../../data/hre/digital_atlas/attributes"

# List of attribute file names (adjust as per your directory listing)
attribute_files = [
    "2.JS", "3.JS", "9.JS", "10.JS", "11.JS", "12.JS", "14.JS",
    "15.JS", "16.JS", "17.JS", "18.JS", "19.JS", "28.JS"
]

# Loop through each file in the list and download it
for file_name in attribute_files:
    file_url = f"{base_url}/{file_name}"  # Construct the full URL
    save_path = os.path.join(output_dir, file_name)

    try:
        # Download the file
        print(f"Downloading {file_url}...")
        response = requests.get(file_url, timeout=10)
        response.raise_for_status()  # Raise an error for bad HTTP responses

        # Save the file locally
        with open(save_path, "wb") as file:
            file.write(response.content)
        print(f"Saved to {save_path}")

    except requests.HTTPError as http_err:
        print(f"HTTP error occurred while downloading {file_url}: {http_err}")
    except requests.RequestException as req_err:
        print(f"Request error occurred while downloading {file_url}: {req_err}")

# Path to the directory containing .js files
attributes_dir = "../../data/hre/digital_atlas/attributes"

# Initialize a list to collect all attributes
all_attributes = []

# Loop through all .js files and parse their contents
for filename in os.listdir(attributes_dir):
    if filename.endswith(".JS"):
        file_path = os.path.join(attributes_dir, filename)
        with open(file_path, "r", encoding="utf-8") as file:
            js_content = file.read()
            # Extract data from each `add_content` line
            matches = re.findall(r'add_content\((\d+),"(.*?)"\)', js_content)
            for match in matches:
                region_id = int(match[0])  # ID
                data = match[1].split(",")  # Split attributes
                # Parse key-value pairs (e.g., "HT_NAME||Baden-Durlach")
                parsed_data = {kv.split("||")[0]: kv.split("||")[1] for kv in data}
                parsed_data["region_id"] = region_id  # Add region ID
                all_attributes.append(parsed_data)

# Convert the list of dictionaries into a pandas DataFrame
attributes_df = pd.DataFrame(all_attributes)

# Inspect the DataFrame
print(attributes_df.head())


# Convert GeoTIFF raster to polygons
geo_tiff_path = "../../bld/maps/georeferenced_map.tif"
with rasterio.open(geo_tiff_path) as src:
    mask = src.read(1) > 0  # Mask for non-zero regions
    results = [
        {"geometry": geometry, "properties": {"value": value}}
        for geometry, value in shapes(src.read(1), mask=mask, transform=src.transform)
    ]

# Create a GeoDataFrame from the results
map_gdf = gpd.GeoDataFrame.from_features(results, crs=src.crs)

# Inspect the GeoDataFrame
print(map_gdf.head())


# Merge GeoDataFrame with attributes
merged_map = map_gdf.merge(attributes_df, left_on="value", right_on="region_id", how="left")

# Inspect the merged data
print(merged_map.head())

# Plot the map with religious confessions
fig, ax = plt.subplots(figsize=(12, 8))
merged_map.plot(
    column="Konf",  # Religious confession
    cmap="coolwarm",  # Color scheme
    legend=True,
    ax=ax
)

plt.title("HRE Map by Religious Confession")
plt.axis("off")
plt.show()