import os
import requests
import re
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Polygon
import pandas as pd
import os
import re
import requests
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Polygon
import pandas as pd

# -------------------- STEP 1: DOWNLOAD JS FILES -------------------- #
base_url = "https://www.atlas-europa.de/t02/konfessionen/Konfessionen/GEOTILES_0"
output_dir = "../../data/hre/digital_atlas/geotiles"
os.makedirs(output_dir, exist_ok=True)

def download_js_file(file_url, save_path):
    try:
        response = requests.get(file_url, timeout=10)
        response.raise_for_status()
        with open(save_path, "wb") as file:
            file.write(response.content)
        print(f"✅ Downloaded: {file_url}")
    except Exception as e:
        print(f"⚠️ Failed to download {file_url}: {e}")

tile_dirs = [f"TILES_{i}" for i in range(2)]
num_tiles_x, num_tiles_y = 10, 10

for tile_dir in tile_dirs:
    dir_url = f"{base_url}/{tile_dir}"
    local_dir = os.path.join(output_dir, tile_dir)
    os.makedirs(local_dir, exist_ok=True)

    for row in range(num_tiles_y):
        for col in range(num_tiles_x):
            tile_file = f"{row}_{col}.JS"
            tile_url = f"{dir_url}/{tile_file}"
            save_path = os.path.join(local_dir, tile_file)

            download_js_file(tile_url, save_path)

print("✅ All .JS files downloaded.")


# -------------------- STEP 2: PARSE JS FILES -------------------- #
def parse_js_file(file_path, tile_height=2048):
    """
    Parse .JS polygons, flipping the Y coordinate to avoid upside-down shapes.
    Adjust tile_height if your tiles are not 2048 px high.
    """
    polygons = []
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

        # Regex to find coords="...", plus region_id and region_name
        matches = re.findall(
            r'coords="([^"]+)" href="javascript:show_popup\((\d+)\);" id="(\d+)_area" title="([^"]+)"',
            content
        )
        for match in matches:
            coords_str, region_id, _, region_name = match
            coord_list = list(map(int, coords_str.split(",")))  # e.g. [x1,y1, x2,y2, ...]

            # Flip each Y coordinate:  newY = tile_height - oldY
            # This ensures top-down -> bottom-up
            points = []
            for i in range(0, len(coord_list), 2):
                x = coord_list[i]
                y = coord_list[i + 1]
                y_flipped = tile_height - y  # Flip
                points.append((x, y_flipped))

            if len(points) > 2:  # must have >=3 points to form a polygon
                polygons.append({
                    "geometry": Polygon(points),
                    "region_id": int(region_id),
                    "region_name": region_name
                })

    return polygons

all_polygons = []
for root, dirs, files in os.walk(output_dir):
    for file in files:
        if file.endswith(".JS"):
            file_path = os.path.join(root, file)
            # If your tiles are 2048 px high, keep tile_height=2048
            # Otherwise, adjust to whatever the real tile dimension is.
            all_polygons.extend(parse_js_file(file_path, tile_height=2048))

if all_polygons:
    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(all_polygons, geometry="geometry")

    # Assign a CRS. Be aware: 
    # - This "EPSG:32633" is still not correct for real-world 
    #   unless you do scaling/offset. 
    # - But flipping the Y here ensures they're not upside down 
    #   in a naive plot.
    gdf.crs = "EPSG:32633"

    shapefile_path = "../../data/hre/digital_atlas/map/geotiles_map.shp"
    gdf.to_file(shapefile_path)
    print(f"✅ Polygons saved as Shapefile at {shapefile_path}")
else:
    print("⚠️ No polygons were extracted from the .JS files!")
    gdf = gpd.GeoDataFrame(columns=["geometry", "region_id", "region_name"], geometry="geometry")


# -------------------- STEP 1: DOWNLOAD JS FILES -------------------- #

# Base URL for attributes
base_url = "https://www.atlas-europa.de/t02/konfessionen/Konfessionen/ATTRIBUTES_0"

# Local directory to save downloaded attribute files
output_dir = "../../data/hre/digital_atlas/attributes"
os.makedirs(output_dir, exist_ok=True)

# List of attribute file names (adjust as per your directory listing)
attribute_files = [f"{i}.JS" for i in range(0, 40)]  # Adjust range based on actual files

# Download each file
for file_name in attribute_files:
    file_url = f"{base_url}/{file_name}"
    save_path = os.path.join(output_dir, file_name)

    try:
        response = requests.get(file_url, timeout=10)
        response.raise_for_status()
        with open(save_path, "wb") as file:
            file.write(response.content)
        print(f"Downloaded: {file_url}")
    except requests.RequestException as e:
        print(f"Failed to download {file_url}: {e}")

print("✅ All attribute files downloaded.")

# -------------------- STEP 2: PARSE JS FILES -------------------- #

# Path to the directory containing .js files
attributes_dir = "../../data/hre/digital_atlas/attributes"

# Initialize a list to collect all attributes
all_attributes = []

# Parse .JS files dynamically
for filename in os.listdir(attributes_dir):
    if filename.endswith(".JS"):
        file_path = os.path.join(attributes_dir, filename)
        with open(file_path, "r", encoding="utf-8") as file:
            js_content = file.read()
            # Match the structure of `add_content` calls
            matches = re.findall(r'add_content\((\d+),"(.*?)"\)', js_content)
            for match in matches:
                region_id = int(match[0])  # Extract region ID
                data = match[1].split(",")  # Split attributes by comma
                parsed_data = {}
                for item in data:
                    # Handle `key||value` structure
                    if "||" in item:
                        key, value = item.split("||", 1)  # Split into key and value
                        parsed_data[key.strip()] = value.strip()  # Add to parsed data
                parsed_data["region_id"] = region_id  # Add region ID
                all_attributes.append(parsed_data)

# Convert the list of dictionaries into a pandas DataFrame
attributes_df = pd.DataFrame(all_attributes)

# -------------------- STEP 3: HANDLE MISSING DATA -------------------- #

# Ensure all columns are included, even if some are missing in certain rows
attributes_df.fillna("", inplace=True)  # Replace NaN with empty strings for better merging

# Inspect the DataFrame
print(f"Parsed {len(attributes_df)} regions with attributes.")
print(attributes_df.head())


# -------------------- STEP 4: MERGE AND PLOT -------------------- #

# Ensure `gdf` and `attributes_df` are not empty before merging
if not gdf.empty and not attributes_df.empty:
    # Merge GeoDataFrame with attributes DataFrame
    enriched_gdf = gdf.merge(attributes_df, on="region_id", how="left")


# Clean column names in the enriched GeoDataFrame
enriched_gdf.columns = (
    enriched_gdf.columns.str.strip()  # Remove leading/trailing spaces
    .str.replace('"', '', regex=False)  # Remove double quotes
    .str.replace(' ', '_', regex=False)  # Replace spaces with underscores
    .str.replace("&#", '', regex=False)  # Optional: Remove HTML-encoded characters
)

# Clean up problematic columns
columns_to_clean = ["Konf", "Geb", "HT_NAME", "region_name"]  # Adjust this list based on your DataFrame

for column in columns_to_clean:
    if column in enriched_gdf.columns:
        enriched_gdf[column] = enriched_gdf[column].str.strip('" ')  # Remove leading/trailing quotes and spaces


# Save the enriched GeoDataFrame as a Shapefile
enriched_shapefile_path = "../../data/hre/digital_atlas/map/enriched_map.shp"
enriched_gdf.to_file(enriched_shapefile_path)
print(f"✅ Enriched map saved as Shapefile at {enriched_shapefile_path}")
