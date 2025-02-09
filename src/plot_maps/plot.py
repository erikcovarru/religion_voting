from fun import (
    load_geodata,
    load_religion_data,
    merge_data_religion,
    overlay_catholic_regions_on_map,
    plot_hre_comparison,
    plot_religion_maps_side_by_side
)

import geopandas as gpd

# Define file paths
geo_filepath = '../../data/shapefiles/vg250_ebenen_1231/DE_VG250.gpkg'
religion_filepath = '../../data/zensus/religion.xlsx'
enriched_filepath =  '../../data/hre/digital_atlas/map/enriched_map.shp'

# 1) Load geographic data
gem_data = load_geodata(geo_filepath)

# 2) Load religion data
religion_data = load_religion_data(religion_filepath)

# 3) Merge them
map_data_religion = merge_data_religion(gem_data, religion_data)

# 4) Get enriched HRE map data
enriched_gdf = gpd.read_file(enriched_filepath)

plot_religion_maps_side_by_side(
    map_data_religion,
    columns=['Catholic', 'Protestant', 'None'],
    cmaps=['Reds', 'Blues', 'Greys'],
    legend_labels=['Catholics %', 'Protestants %', 'None %'],
    output_folder="../../bld/maps",
    filename="religion_maps_side_by_side.png"
)


plot_hre_comparison(
    enriched_gdf,
    geb_filter='r',
    konf_column='Konf',
    output_file='../../bld/maps/hre_comparison_unique_colors_fixed.png'
)

# 8) Overlay enriched polygons on Catholic map
# Overlay the clipped polygons on the Catholic map
overlay_catholic_regions_on_map(
    map_data_religion,
    enriched_gdf,
    religion_column='Catholic',
    filter_column_geb='Geb',
    filter_value_geb='r',
    filter_column_konf='Konf',
    filter_value_konf='ka',
    overlay_color='gray',
    fill_opacity=0.55
)

