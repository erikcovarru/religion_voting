import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from mpl_toolkits.axes_grid1 import make_axes_locatable
import os

def load_geodata(filepath):
    """Load municipalities from GeoPackage (or any supported file)."""
    gem_data = gpd.read_file(filepath, layer='vg250_gem')
    return gem_data

def load_religion_data(filepath):
    """Load religion data and keep only necessary columns."""
    religion_data = pd.read_excel(filepath, sheet_name=0, header=3)
    column_names = [
        "Region_Code", "Region_Name", "Population_Type", "Unit", "Total_Population", 
        "Protestant_e", "Protestant", "Catholic_e", "Catholic", "None_e", "None", "final_e"
    ]
    religion_data.columns = column_names
    religion_data = religion_data.dropna(subset=["Region_Code", "Region_Name"], how='all')
    
    # Convert relevant columns to numeric, replacing errors with NaN, then fill with 0
    religion_data[['Protestant', 'Catholic', 'None']] = (
        religion_data[['Protestant', 'Catholic', 'None']]
        .apply(pd.to_numeric, errors='coerce')
        .fillna(0)
    )
    
    # Drop columns ending with '_e'
    religion_data = religion_data[[col for col in religion_data.columns if not col.endswith("_e")]]

    # (Optional) Filter for a specific federal state by code, e.g., Thüringen starts with '16'
    # religion_data = religion_data[religion_data['Region_Code'].str.startswith('16')]

    return religion_data

def merge_data_religion(geo_data, religion_data):
    """
    Merge GeoDataFrame with religion DataFrame.
    Note: Ensure `Region_Code` aligns with the GeoDataFrame's ID column (e.g., 'SDV_ARS').
    """
    map_data = geo_data.merge(
        religion_data,
        left_on='SDV_ARS',
        right_on='Region_Code',
        how='left'
    )
    return map_data

def plot_map_religion(
    map_data,
    column='Catholic',
    cmap='Reds',
    legend_label='Catholics %',
    output_folder=None,
    filename='religion_map.png'
):
    """
    Plot the specified religion column on a GeoDataFrame,
    without Eichsfeld or Geisa boundaries.
    """
    # Ensure map data is in a consistent CRS (e.g., Web Mercator)
    map_data = map_data.to_crs(epsg=3857)

    # Define color scale range for plotting
    vmin = map_data[column].quantile(0.05)
    vmax = map_data[column].quantile(0.95)

    # Plotting
    _, ax = plt.subplots(1, 1, figsize=(12, 8))
    map_data.plot(
        column=column,
        cmap=cmap,
        linewidth=0.0,
        ax=ax,
        edgecolor='none',
        legend=False,
        vmin=vmin,
        vmax=vmax
    )

    # Set zoom based on data extent
    ax.set_xlim(map_data.total_bounds[0], map_data.total_bounds[2])
    ax.set_ylim(map_data.total_bounds[1], map_data.total_bounds[3])

    # Create colorbar
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="2%", pad=0.1)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm._A = []
    cbar = plt.colorbar(sm, cax=cax)
    cbar.set_label(legend_label)

    # Optionally set a title
    ax.set_title(f"Distribution of {legend_label}")

    # Hide axis for a cleaner map
    ax.axis('off')

    # Save the plot if output folder is provided
    if output_folder:
        os.makedirs(output_folder, exist_ok=True)
        output_path = os.path.join(output_folder, filename)
        plt.savefig(output_path, dpi=600, bbox_inches='tight')
        print(f"Plot saved to {output_path}")

    plt.show()

def overlay_polygons_on_map(
    map_data_religion,
    enriched_gdf,
    religion_column='Catholic',
    filter_column='Konf',
    filter_value='k',
    overlay_color='blue'
):
    """
    Overlay polygons from enriched_gdf onto the existing religion map,
    ensuring only relevant polygons overlapping with Germany are shown.
    
    :param map_data_religion: A GeoDataFrame already merged with religion data.
    :param enriched_gdf: A GeoDataFrame with historical polygons to overlay.
    :param religion_column: Column name in map_data_religion (e.g., 'Catholic').
    :param filter_column: Column in enriched_gdf to filter on (e.g., 'Konf').
    :param filter_value: Specific value in the filter_column (e.g., 'k').
    :param overlay_color: Color to draw boundary overlays.
    """

    # Ensure both datasets are in the same CRS
    enriched_gdf = enriched_gdf.to_crs(map_data_religion.crs)

    # Filter enriched polygons that intersect with Germany
    enriched_gdf = gpd.sjoin(enriched_gdf, map_data_religion, how="inner", predicate ="intersects")

    # Further filter enriched polygons by the specified column and value
    filtered_gdf = enriched_gdf[enriched_gdf[filter_column] == filter_value]

    # Define color scale range for the underlying religion map
    vmin = map_data_religion[religion_column].quantile(0.05)
    vmax = map_data_religion[religion_column].quantile(0.95)

    # Plot the underlying map_data_religion
    fig, ax = plt.subplots(figsize=(12, 8))
    map_data_religion.plot(
        column=religion_column,
        cmap='Reds',
        linewidth=0.0,
        ax=ax,
        edgecolor='none',
        legend=False,
        vmin=vmin,
        vmax=vmax
    )

    # Overlay HRE polygons
    filtered_gdf.boundary.plot(
        ax=ax,
        color=overlay_color,
        linewidth=0.5,
        label=f'{filter_value} Regions'
    )

    # Create a colorbar
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="2%", pad=0.1)
    sm = plt.cm.ScalarMappable(cmap='Reds', norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm._A = []
    cbar = plt.colorbar(sm, cax=cax)
    cbar.set_label(f'{religion_column} (%)')

    # Add legend for overlay
    legend_elements = [Line2D([0], [0], color=overlay_color, lw=2, label=f'{filter_value} Regions')]
    ax.legend(handles=legend_elements, loc='upper right')

    # Clean up axes and show
    ax.axis('off')
    ax.set_title(f'{religion_column} Distribution with {filter_value} Overlay')
    plt.show()
