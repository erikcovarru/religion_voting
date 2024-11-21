# Import functions
from fun import load_geodata, load_election_data, load_religion_data, merge_data, extract_boundaries, merge_data_religion, plot_maps_side_by_side, plot_map_religion

# Define file paths for the geographic and election data
geo_filepath = '../data/DE_VG250.gpkg'
election_filepath = '../data/bw_2021.xlsx'
religion_filepath = '../data/1000A-1018_en.xlsx'

# Load and process geographic data
gem_data = load_geodata(geo_filepath)
eichsfeld_boundary, geisa = extract_boundaries(gem_data)

# Load and procces election data 
election_data = load_election_data(election_filepath)
map_data_bw = merge_data(gem_data, election_data)

# Load and process religion data
gem_data = load_geodata(geo_filepath)
religion_data = load_religion_data(religion_filepath)
map_data_religion = merge_data_religion(gem_data, religion_data)

# Plot
plot_maps_side_by_side(map_data_bw, eichsfeld_boundary, geisa, "../bld/maps", "voting_patterns.png")

# Plot the map for Catholic data
plot_map_religion(map_data_religion, eichsfeld_boundary, geisa, column='Catholic', cmap='Reds', legend_label='Catholics %', output_folder="../bld/maps",
    filename="catholic_distribution_map.png")
