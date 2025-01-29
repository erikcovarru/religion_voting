import os
import pyreadr
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt

# If you have a custom function that loads geodata, use it (e.g., from fun.py).
# Otherwise, replace the `load_geodata(...)` call below with `gpd.read_file(geo_filepath)`.
from fun import load_geodata

# -----------------------------------------------------------------------------
# 1. Define paths to your data
# -----------------------------------------------------------------------------
geo_filepath = '../data/shapefiles/vg250_ebenen_1231/DE_VG250.gpkg'

national_rds_path = '../data/election/federal_muni_harm.rds'
state_rds_path    = '../data/election/state_harm.rds'
muni_rds_path     = '../data/election/municipal_harm.rds'

# -----------------------------------------------------------------------------
# 2. Read R data
# -----------------------------------------------------------------------------
result_national = pyreadr.read_r(national_rds_path)
result_state    = pyreadr.read_r(state_rds_path)
result_muni     = pyreadr.read_r(muni_rds_path)

# Each RDS file typically contains one or more objects.
# If it only has one, you'll find it under the key `None`.
df_national = result_national[None]
df_state    = result_state[None]
df_muni     = result_muni[None]

# -----------------------------------------------------------------------------
# 3. Load geospatial data
# -----------------------------------------------------------------------------
# If you do NOT have the custom load_geodata() function, you can do:
# gem_data = gpd.read_file(geo_filepath)

gem_data = load_geodata(geo_filepath)

# -----------------------------------------------------------------------------
# 4. Merge: geo + election data
#    Ensure 'AGS' in the geodata matches 'ags' in your election data.
# -----------------------------------------------------------------------------
map_data_national = gem_data.merge(
    df_national,
    left_on='AGS',
    right_on='ags',
    how='left'
)

map_data_state = gem_data.merge(
    df_state,
    left_on='AGS',
    right_on='ags',
    how='left'
)

map_data_muni = gem_data.merge(
    df_muni,
    left_on='AGS',
    right_on='ags',
    how='left'
)

# -----------------------------------------------------------------------------
# 5. Plot for NATIONAL
# -----------------------------------------------------------------------------
# a) Get unique election years (remove NaN just in case)
unique_years_national = map_data_national['election_year'].dropna().unique()

# b) Sort them so we can plot chronologically
unique_years_national = sorted(unique_years_national)

# c) Loop and plot
for y in unique_years_national:
    subset_national = map_data_national[map_data_national['election_year'] == y]
    
    ax = subset_national.plot(
        column='far_right',  # change this if your column has a different name
        cmap='Greys',
        legend=True,
        edgecolor='none',
        figsize=(8, 8)
    )
    ax.set_title(f'Far Right Votes (National), {y}', fontsize=14)
    ax.set_axis_off()
    
    plt.tight_layout()
    plt.show()

# -----------------------------------------------------------------------------
# 6. Plot for STATE
# -----------------------------------------------------------------------------
unique_years_state = map_data_state['election_year'].dropna().unique()
unique_years_state = sorted(unique_years_state)

for y in unique_years_state:
    subset_state = map_data_state[map_data_state['election_year'] == y]
    
    ax = subset_state.plot(
        column='afd',
        cmap='Greys',
        legend=True,
        edgecolor='none',
        figsize=(8, 8)
    )
    ax.set_title(f'Far Right Votes (State), {y}', fontsize=14)
    ax.set_axis_off()
    
    plt.tight_layout()
    plt.show()

# -----------------------------------------------------------------------------
# 7. Plot for MUNICIPAL
# -----------------------------------------------------------------------------
unique_years_muni = map_data_muni['election_year'].dropna().unique()
unique_years_muni = sorted(unique_years_muni)

for y in unique_years_muni:
    subset_muni = map_data_muni[map_data_muni['election_year'] == y]
    
    ax = subset_muni.plot(
        column='afd',
        cmap='Greys',
        legend=True,
        edgecolor='none',
        figsize=(8, 8)
    )
    ax.set_title(f'Far Right Votes (Municipal), {y}', fontsize=14)
    ax.set_axis_off()
    
    plt.tight_layout()
    plt.show()
