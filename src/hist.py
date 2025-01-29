import os
import requests
from PIL import Image
import rasterio
from rasterio.transform import from_bounds
import matplotlib.pyplot as plt
import numpy as np
import geopandas as gpd



 Base URL for attributes
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



# Plot the polygons
fig, ax = plt.subplots(figsize=(10, 10))
map_gdf.plot(ax=ax, edgecolor="black", facecolor="none")  # Just outlines

# Formatting
ax.set_title("Extracted Polygons from GeoTIFF")
plt.show()