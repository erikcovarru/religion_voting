import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from mpl_toolkits.axes_grid1 import make_axes_locatable
import os

# Function to load and filter geographic data
def load_geodata(filepath):
    gem_data = gpd.read_file(filepath, layer='vg250_gem')
    gem_data = gem_data[gem_data['SDV_ARS'].str.startswith('16')]  # Filter for Thüringen
    return gem_data

# Function to load and clean election data
def load_election_data(filepath):
    bw = pd.read_excel(filepath, skiprows=6)
    bw = bw.dropna(axis=1, how='all')
    bw = bw[pd.to_numeric(bw['Wähler'], errors='coerce').notna()]
    bw.reset_index(drop=True, inplace=True)
    new_column_names = ['wahlkreis', 'gemeinde_nr', 'gemeinde_name', 'stand', 'wahlberechtigte',
                        'whaler', 'wahlbeteiligung', 'ungultige', 'gultige', 'cdu', 'afd', 
                        'linke', 'spd', 'fdp', 'grune', 'freie', 'diepartei', 'ndp', 'opd', 
                        'piraten', 'v', 'mlpd', 'basis', 'mensch', 'humanistien',
                        'tierschutz', 'team', 'volt']
    bw.columns = new_column_names
    for col in ['afd', 'cdu']:
        bw[col] = bw[col].str.replace(',', '.').astype(float)
    bw['gemeinde_nr'] = bw['gemeinde_nr'].astype(str)
    return bw

# Function to merge geographic data with election data
def merge_data(geo_data, election_data):
    geo_data['gemeinde_nr_extracted'] = geo_data['SDV_ARS'].str[3:5] + geo_data['SDV_ARS'].str[-3:]
    geo_data_exploded = geo_data.explode('gemeinde_nr_extracted')
    map_data = geo_data_exploded.merge(
        election_data,
        left_on='gemeinde_nr_extracted',
        right_on='gemeinde_nr',
        how='left'
    )
    map_data = map_data.drop_duplicates(subset='SDV_ARS')
    return map_data

# Function to extract Eichsfeld and Geisa boundaries
def extract_boundaries(geo_data):
    eichsfeld_munis = geo_data[geo_data['SDV_ARS'].str[2:5] == '061']
    eichsfeld_boundary = eichsfeld_munis.dissolve()
    geisa = geo_data[geo_data['GEN'].isin(['Geisa', 'Buttlar', 'Schleid'])]
    geisa = geisa.dissolve()
    
    return eichsfeld_boundary, geisa


def plot_maps_side_by_side(map_data, eichsfeld_boundary, geisa, output_folder, filename="map_plot.png"):
    # Define party settings for AfD and CDU
    party_settings = {
        'afd': {'cmap': 'Blues', 'legend_label': 'AfD Vote %'},
        'cdu': {'cmap': 'Greys', 'legend_label': 'CDU Vote %'}
    }

    # Ensure map data and boundaries are in the correct CRS
    map_data = map_data.to_crs(epsg=3857)
    eichsfeld_boundary = eichsfeld_boundary.to_crs(epsg=3857)
    geisa = geisa.to_crs(epsg=3857)

    # Create subplots
    fig, axes = plt.subplots(1, 2, figsize=(18, 8))  # 1 row, 2 columns

    for i, (party, settings) in enumerate(party_settings.items()):
        ax = axes[i]  # Select the corresponding subplot axis
        cmap = settings['cmap']
        legend_label = settings['legend_label']

        # Define color scale range based on 5th to 95th percentiles
        vmin = map_data[party].quantile(0.05)
        vmax = map_data[party].quantile(0.95)

        # Create a mask for municipalities with data and those without
        has_data = map_data[party].notna()
        no_data = map_data[party].isna()

        # Plot municipalities with data
        map_data[has_data].plot(
            column=party,
            cmap=cmap,
            linewidth=0.5,
            ax=ax,
            edgecolor='0.5',
            legend=False,
            vmin=vmin,
            vmax=vmax
        )

        # Plot municipalities without data in gray with hatching
        map_data[no_data].plot(
            color='lightgray',
            linewidth=0.5,
            ax=ax,
            edgecolor='0.5',
            hatch='///'
        )

        # Plot Eichsfeld and Geisa boundaries
        eichsfeld_boundary.boundary.plot(ax=ax, color='red', linewidth=2)
        geisa.boundary.plot(ax=ax, color='red', linewidth=2, linestyle='--')

        # Add legends explicitly for each subplot
        eichsfeld_line = Line2D([0], [0], color='red', linewidth=2, label='Eichsfeld District')
        geisa_line = Line2D([0], [0], color='red', linewidth=2, linestyle='--', label='Geisa')
        ax.legend(handles=[eichsfeld_line, geisa_line], loc='lower left', frameon=True)

        # Set zoom based on data extent
        ax.set_xlim(map_data.total_bounds[0], map_data.total_bounds[2])  # Min and max longitude
        ax.set_ylim(map_data.total_bounds[1], map_data.total_bounds[3])  # Min and max latitude

        # Create colorbar
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="2%", pad=0.1)
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
        sm._A = []
        cbar = plt.colorbar(sm, cax=cax)
        cbar.set_label(legend_label)

        # Hide axes for a cleaner map
        ax.axis('off')

    # Adjust layout and save the plot
    plt.tight_layout()

    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Save the plot
    output_path = os.path.join(output_folder, filename)
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.show()

    print(f"Plot saved to {output_path}")




# Function to load and clean religion data
def load_religion_data(filepath):
    religion_data = pd.read_excel(filepath, sheet_name=0, header=3)
    column_names = [
        "Region_Code", "Region_Name", "Population_Type", "Unit", "Total_Population", 
        "Protestant_e", "Protestant", "Catholic_e", "Catholic", "None_e", "None", "final_e"
    ]
    religion_data.columns = column_names
    religion_data = religion_data.dropna(subset=["Region_Code", "Region_Name"], how='all')
    
    # Convert relevant columns to numeric, replacing 'e' with NaN and filling with 0
    religion_data[['Protestant', 'Catholic', 'None']] = religion_data[['Protestant', 'Catholic', 'None']].apply(pd.to_numeric, errors='coerce').fillna(0)
    
    # Drop columns ending with '_e'
    religion_data = religion_data[[col for col in religion_data.columns if not col.endswith("_e")]]
    
    # Filter for Thüringen by code
    religion_data = religion_data[religion_data['Region_Code'].str.startswith('16')]
    return religion_data

# Function to merge geographic data with religion data
def merge_data_religion(geo_data, religion_data):
    map_data = geo_data.merge(religion_data, left_on='SDV_ARS', right_on='Region_Code', how='left')
    return map_data

# Generalized plot function for mapping any column data with selectable color scheme
def plot_map_religion(map_data, eichsfeld_boundary, geisa, column='Catholic', cmap='Reds', legend_label='Catholics %', output_folder=None, filename='religion_map.png'):
    # Ensure map data and boundaries are in the same CRS
    map_data = map_data.to_crs(epsg=3857)
    eichsfeld_boundary = eichsfeld_boundary.to_crs(epsg=3857)
    geisa = geisa.to_crs(epsg=3857)

    # Define color scale range for plotting
    vmin = map_data[column].quantile(0.05)
    vmax = map_data[column].quantile(0.95)

    # Plotting
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    map_data.plot(column=column, cmap=cmap, linewidth=0.5, ax=ax, edgecolor='0.5', legend=False, vmin=vmin, vmax=vmax)

    # Plot Eichsfeld and Geisa boundaries
    eichsfeld_boundary.boundary.plot(ax=ax, color='black', linewidth=2, label='Eichsfeld District')
    geisa.boundary.plot(ax=ax, color='black', linewidth=2, linestyle='--', label='Geisa')

    # Set zoom based on data extent
    ax.set_xlim(map_data.total_bounds[0], map_data.total_bounds[2])  # Min and max longitude
    ax.set_ylim(map_data.total_bounds[1], map_data.total_bounds[3])  # Min and max latitude

    # Create colorbar
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="2%", pad=0.1)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm._A = []
    cbar = plt.colorbar(sm, cax=cax)
    cbar.set_label(legend_label)

    # Create legend entries
    eichsfeld_line = Line2D([0], [0], color='black', linewidth=2, label='Eichsfeld District')
    geisa_line = Line2D([0], [0], color='black', linewidth=2, linestyle='--', label='Geisa')
    ax.legend(handles=[eichsfeld_line, geisa_line], loc='lower left')

    # Set title and display plot
    ax.axis('off')  # Hide axis

    # Save the plot if output folder is provided
    if output_folder:
        os.makedirs(output_folder, exist_ok=True)
        output_path = os.path.join(output_folder, filename)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {output_path}")

    plt.show()

