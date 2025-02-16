import os
import requests
import re
import xml.etree.ElementTree as ET

from fun_get_data import(
    download_images,
    generate_possible_folders,
    generate_possible_filenames,
    generate_vrt
)

# Base URL for downloading tiles
maptiles_base_url = "https://www.atlas-europa.de/t02/konfessionen/Konfessionen/MAPTILEIMAGES_0/L01"

# Output directory for storing downloaded images
output_directory = "../../data/hre/digital_atlas/maptiles"
os.makedirs(output_directory, exist_ok=True)

# 🔹 Run the full process
downloaded_files = download_images()
vrt_file = generate_vrt(downloaded_files)

print("\n🎯 All tiles downloaded and Virtual Raster created. Load the `.vrt` in QGIS!")
