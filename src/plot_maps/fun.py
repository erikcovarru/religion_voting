import numpy as np
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import ListedColormap
import seaborn as sns
import contextily as ctx
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

def plot_religion_maps_side_by_side(
    map_data_religion,
    columns=['Catholic', 'Protestant', 'None'],
    cmaps=['Reds', 'Blues', 'Greys'],
    legend_labels=['Catholics %', 'Protestants %', 'None %'],
    output_folder=None,
    filename="religion_maps_side_by_side.png"
):
    map_data_religion = map_data_religion.to_crs(epsg=3857)

    fig, axes = plt.subplots(1, 3, figsize=(30, 12))  # Increased figure size

    for i, (column, cmap, legend_label) in enumerate(zip(columns, cmaps, legend_labels)):
        ax = axes[i]

        vmin = map_data_religion[column].quantile(0.05)
        vmax = map_data_religion[column].quantile(0.95)

        map_data_religion.plot(
            column=column,
            cmap=cmap,
            linewidth=0.0,
            ax=ax,
            edgecolor='none',
            legend=False,
            vmin=vmin,
            vmax=vmax
        )

        ax.set_title(f"Distribution of {legend_label}", fontsize=30)  # Larger title
        ax.axis('off')

        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="5%", pad=0.1)
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
        sm._A = []
        cbar = plt.colorbar(sm, cax=cax)
        cbar.set_label(legend_label, fontsize=18)  # Larger colorbar label
        cbar.ax.tick_params(labelsize=12)  # Larger ticks on the colorbar

    plt.tight_layout()

    if output_folder:
        os.makedirs(output_folder, exist_ok=True)
        output_path = os.path.join(output_folder, filename)
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✅ Plot saved to {output_path}")

    plt.show()

def overlay_catholic_regions_on_map(
    map_data_religion,
    enriched_gdf,
    religion_column='Catholic',
    filter_column_geb='Geb',
    filter_value_geb='r',
    filter_column_konf='Konf',
    filter_value_konf='ka',
    overlay_color='gray',
    fill_opacity=0.3
):
    enriched_gdf = enriched_gdf.to_crs(map_data_religion.crs)

    filtered_gdf = enriched_gdf[
        (enriched_gdf[filter_column_geb] == filter_value_geb) &
        (enriched_gdf[filter_column_konf] == filter_value_konf)
    ]

    filtered_gdf = filtered_gdf[filtered_gdf.is_valid]
    germany_boundary = map_data_religion.unary_union
    clipped_gdf = filtered_gdf.intersection(germany_boundary)
    clipped_gdf = gpd.GeoDataFrame(geometry=clipped_gdf, crs=map_data_religion.crs)
    clipped_gdf = clipped_gdf[~clipped_gdf.is_empty]

    vmin = map_data_religion[religion_column].quantile(0.05)
    vmax = map_data_religion[religion_column].quantile(0.95)

    fig, ax = plt.subplots(figsize=(14, 10))  # Increased figure size
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

    clipped_gdf.plot(
        ax=ax,
        color=overlay_color,
        alpha=fill_opacity,
        edgecolor="black",
        linewidth=0.5,
        label="Catholic states within HRE"
    )

    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="2%", pad=0.1)
    sm = plt.cm.ScalarMappable(cmap='Reds', norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm._A = []
    cbar = plt.colorbar(sm, cax=cax)
    cbar.set_label(f'{religion_column} (%)', fontsize=14)  # Larger label
    cbar.ax.tick_params(labelsize=12)  # Larger ticks

    legend_elements = [Line2D([0], [0], color=overlay_color, lw=2, label="Catholic states within HRE")]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=14)  # Larger legend

    ax.axis('off')
    ax.set_title("Distribution of Catholics overlayed with HRE borders", fontsize=30)  # Larger title
    plt.show()

def plot_hre_comparison(
    enriched_gdf, 
    geb_filter='r', 
    konf_column='Konf', 
    output_file=None
):
    hre_gdf = enriched_gdf[enriched_gdf['Geb'] == geb_filter]

    if hre_gdf.empty:
        print("⚠️ No polities found with Geb =", geb_filter)
        return

    hre_gdf = hre_gdf.to_crs(epsg=3857)  

    unique_ids = hre_gdf['region_id'].unique()
    n_colors = len(unique_ids)
    color_palette = sns.color_palette("tab20", n_colors=n_colors)
    color_map = {region: color for region, color in zip(unique_ids, color_palette)}
    hre_gdf['region_color'] = hre_gdf['region_id'].map(color_map)

    fig, axes = plt.subplots(1, 2, figsize=(24, 12))  # Increased figure size

    hre_gdf.plot(
        color=hre_gdf['region_color'],
        linewidth=0.5,
        ax=axes[0],
        edgecolor='black',
        legend=False
    )
    ctx.add_basemap(axes[0], source=ctx.providers.OpenStreetMap.Mapnik, alpha=0.5)
    axes[0].set_title("Holy Roman Empire Polities in 1648", fontsize=30)  # Larger title
    axes[0].axis('off')

    hre_gdf.plot(
        column=konf_column,
        cmap='tab10',
        linewidth=0.5,
        ax=axes[1],
        edgecolor='black',
        legend=True
    )
    ctx.add_basemap(axes[1], source=ctx.providers.OpenStreetMap.Mapnik, alpha=0.5)
    axes[1].set_title("Religions in the Empire", fontsize=30)  # Larger title
    axes[1].axis('off')

    plt.tight_layout()

    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"✅ Plot saved to {output_file}")

    plt.show()