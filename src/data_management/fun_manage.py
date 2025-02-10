import geopandas as gpd
import pandas as pd


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

