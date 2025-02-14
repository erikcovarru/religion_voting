import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import os
from mpl_toolkits.axes_grid1 import make_axes_locatable

def load_religion_data(filepath):
    """Load and clean religion data from an Excel file."""
    religion_data = pd.read_excel(filepath, sheet_name=0, header=3)

    # Define expected column names
    column_names = [
        "Region_Code", "Region_Name", "Population_Type", "Unit", "Total_Population", 
        "Protestant_e", "Protestant", "Catholic_e", "Catholic", "None_e", "None", "final_e"
    ]
    
    # Assign new column names
    religion_data.columns = column_names
    
    # Drop rows with missing region codes or names
    religion_data = religion_data.dropna(subset=["Region_Code", "Region_Name"], how='all')

    # Convert necessary columns to numeric
    religion_data[['Protestant', 'Catholic', 'None']] = (
        religion_data[['Protestant', 'Catholic', 'None']]
        .apply(pd.to_numeric, errors='coerce')
        .fillna(0)
    )

    # Remove unnecessary columns (ending with "_e")
    religion_data = religion_data[[col for col in religion_data.columns if not col.endswith("_e")]]

    return religion_data

def merge_data_religion(geo_data, religion_data):
    """
    Merge GeoDataFrame (German boundaries) with religion data.
    Assumes the geo_data has a column 'SDV_ARS' that matches 'Region_Code' in the religion data.
    """
    merged_data = geo_data.merge(
        religion_data,
        left_on='SDV_ARS',
        right_on='Region_Code',
        how='left'
    )
    return merged_data

def plot_map_religion_with_historical_border(
    religion_filepath,
    german_admin_filepath,
    historical_polygon_filepath,
    column='Catholic',
    cmap='Reds',
    legend_label='Catholics %',
    overlay_color='blue',
    overlay_opacity=0.4,
    output_folder=None,
    filename='religion_map.png'
):
    """
    Plots the religion data (merged with German boundaries) and overlays the historical polygon
    clipped to modern German borders.
    """

    # Load religion data
    religion_data = load_religion_data(religion_filepath)

    # Load the German administrative boundaries
    german_admin = gpd.read_file(german_admin_filepath)

    # Merge religion data with administrative boundaries
    map_data = merge_data_religion(german_admin, religion_data)

    # Load the historical polygon
    historical_polygon = gpd.read_file(historical_polygon_filepath)

    # Ensure all datasets have the same CRS
    historical_polygon = historical_polygon.to_crs(german_admin.crs)
    map_data = map_data.to_crs(german_admin.crs)

    # Compute Germany’s boundary as a single polygon
    germany_boundary = german_admin.geometry.unary_union

    # Clip the historical polygon to retain only areas within Germany
    historical_polygon_clipped = historical_polygon.intersection(germany_boundary)

    # Convert back to a GeoDataFrame
    historical_polygon_clipped = gpd.GeoDataFrame(geometry=historical_polygon_clipped, crs=german_admin.crs)

    # Remove empty geometries (if any)
    historical_polygon_clipped = historical_polygon_clipped[~historical_polygon_clipped.is_empty]

    # Define color scale range for religion data
    vmin = map_data[column].quantile(0.05)
    vmax = map_data[column].quantile(0.95)

    # Create figure
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))

    # Plot the religion data
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

    # Overlay the historical border (clipped to Germany)
    historical_polygon_clipped.plot(
        ax=ax,
        color=overlay_color,
        edgecolor="black",
        linewidth=1,
        alpha=overlay_opacity,
        label="Clipped Historical Borders"
    )

    # Adjust map zoom based on data extent
    ax.set_xlim(map_data.total_bounds[0], map_data.total_bounds[2])
    ax.set_ylim(map_data.total_bounds[1], map_data.total_bounds[3])

    # Create a colorbar
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="2%", pad=0.1)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm._A = []
    cbar = plt.colorbar(sm, cax=cax)
    cbar.set_label(legend_label)

    # Title & Cleanup
    ax.set_title(f"Distribution of {legend_label} with Historical Borders", fontsize=14)
    ax.axis('off')

    # Save the plot if output folder is specified
    if output_folder:
        os.makedirs(output_folder, exist_ok=True)
        output_path = os.path.join(output_folder, filename)
        plt.savefig(output_path, dpi=600, bbox_inches='tight')
        print(f"Plot saved to {output_path}")

    # Show plot
    plt.show()


# --- ✅ **Run the Function** ---
religion_filepath = "../data/zensus/religion.xlsx"
german_admin_filepath = "../data/shapefiles/vg250_ebenen_1231/DE_VG250.gpkg"
historical_polygon_filepath = "../data/hre/digital_atlas/maptiles/shape_WHRE.shp"

plot_map_religion_with_historical_border(
    religion_filepath,
    german_admin_filepath,
    historical_polygon_filepath,
    column="Catholic",
    cmap="Reds",
    legend_label="Catholics %",
    overlay_color="blue",
    overlay_opacity=0.3
)
