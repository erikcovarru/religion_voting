# Import the necessary functions
from fun import (
    load_geodata,
    load_religion_data,
    merge_data_religion,
    plot_map_religion
)

# Define file paths
geo_filepath = '../data/DE_VG250.gpkg'
religion_filepath = '../data/1000A-1018_en.xlsx'

# 1) Load geographic data
gem_data = load_geodata(geo_filepath)

# 2) Load religion data
religion_data = load_religion_data(religion_filepath)

# 3) Merge them
map_data_religion = merge_data_religion(gem_data, religion_data)

# 4) Plot the map for Catholics (no Eichsfeld/Geisa boundaries)
plot_map_religion(
    map_data_religion,
    column='Catholic',
    cmap='Reds',
    legend_label='Catholics %',
    output_folder="../bld/maps",
    filename="catholic_distribution_map.png"
)
