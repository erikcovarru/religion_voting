import os
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import shapefile  # pyshp
from shapely.errors import TopologicalError
import matplotlib.patches as mpatches

# 1) File path to your shapefile
shp_file_path = '../data/hre/manual/territories_manual.shp'

# 2) Classification function (same as before).
def classify_religion(value):
    val_str = str(value).lower()
    protestant_keywords = {"lutheran", "calvinist", "reformed", "free"}
    catholic_keyword = "roman-catholic"

    if value is None or any(x in val_str for x in ["secular", "unclear", "radical"]):
        return "Unclear"
    if catholic_keyword in val_str:
        if any(p in val_str for p in protestant_keywords):
            return "Mixed"
        else:
            return "Catholic"
    if any(p in val_str for p in protestant_keywords):
        return "Protestant"
    if "mixed" in val_str:
        return "Mixed"
    return "Unclear"

# 3) Helper function to determine the religion active at a given year
def get_religion_for_year(row, year):
    """
    If the 'year' falls within [start_rel, end_rel),
    return row['religion']. Otherwise return 'Unclear'.
    """
    start_ = row['start_rel']
    end_ = row['end_rel']

    # If start or end is missing, we can't be certain
    if pd.isna(start_) or pd.isna(end_):
        return "Unclear"

    # We assume [start_rel <= year < end_rel]
    if start_ <= year < end_:
        return row['religion']
    else:
        return "Unclear"

# 4) Map each final category to a color
religion_colors = {
    "Catholic": "red",
    "Protestant": "blue",
    "Mixed": "purple",
    "Unclear": "white"
}

try:
    # A) Read the shapefile
    gdf = gpd.read_file(shp_file_path)

    # B) Repair geometries if needed
    def repair_geometry(geom):
        if geom and not geom.is_valid:
            try:
                return geom.buffer(0)
            except TopologicalError:
                return None
        return geom

    gdf['geometry'] = gdf['geometry'].apply(repair_geometry)
    gdf = gdf[gdf['geometry'].notnull()]

    # C) Build new columns for 1555 and 1648
    gdf['religion_1555_raw'] = gdf.apply(lambda row: get_religion_for_year(row, 1555), axis=1)
    gdf['religion_1648_raw'] = gdf.apply(lambda row: get_religion_for_year(row, 1648), axis=1)

    # D) Classify each new column with your existing logic
    gdf['religion_1555'] = gdf['religion_1555_raw'].apply(classify_religion)
    gdf['religion_1648'] = gdf['religion_1648_raw'].apply(classify_religion)

    # E) Create color columns for each year
    gdf['color_1555'] = gdf['religion_1555'].map(religion_colors)
    gdf['color_1648'] = gdf['religion_1648'].map(religion_colors)

    # ========== PLOT #1: 1555 ==========
    fig, ax = plt.subplots(figsize=(10, 6))
    gdf.plot(
        ax=ax,
        color=gdf["color_1555"],
        edgecolor='None'
    )

    patches_1555 = [
        mpatches.Patch(color=color, label=label)
        for label, color in religion_colors.items()
    ]
    ax.legend(handles=patches_1555, loc='upper left', title="Religion 1555")
    ax.set_title("Religion in 1555")
    ax.axis('off')  # optional, remove lat/long
    plt.show()

    # ========== PLOT #2: 1648 ==========
    fig, ax = plt.subplots(figsize=(10, 6))
    gdf.plot(
        ax=ax,
        color=gdf["color_1648"],
        edgecolor='None'
    )

    patches_1648 = [
        mpatches.Patch(color=color, label=label)
        for label, color in religion_colors.items()
    ]
    ax.legend(handles=patches_1648, loc='upper left', title="Religion 1648")
    ax.set_title("Religion in 1648")
    ax.axis('off')
    plt.show()

except Exception as e:
    print(f"Error: {e}")
