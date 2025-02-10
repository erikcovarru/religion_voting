# Install necessary packages if not installed
if (!requireNamespace("sf", quietly = TRUE)) install.packages("sf")
if (!requireNamespace("rdrobust", quietly = TRUE)) install.packages("rdrobust")
if (!requireNamespace("ggplot2", quietly = TRUE)) install.packages("ggplot2")

# Load required libraries
library(sf)
library(rdrobust)
library(ggplot2)


# Set working directory to script location (Modify as needed)
setwd(dirname(rstudioapi::getActiveDocumentContext()$path))

# ----------------------------------------------------------------------
# 1. Load Data
# ----------------------------------------------------------------------
data_path <- "../../bld/data/merged_national_with_hre_clipped.gpkg"

# Load dataset using sf (spatial data format)
map_data <- st_read(data_path)

# ----------------------------------------------------------------------
# 2. Define Variables for Fuzzy RDD
# ----------------------------------------------------------------------
# Running variable: Distance to Catholic HRE border
map_data$running_var <- map_data$dist_to_catholic_border  # Ensure this column exists

# Treatment variable: Overlap with Catholic HRE (continuous treatment for fuzzy RDD)
map_data$treatment <- map_data$hre_catholic_overlap_pct  # Between 0 and 1

# Outcome variable: Far-right vote share
map_data$outcome <- map_data$far_right

# ----------------------------------------------------------------------
# 3. Perform Fuzzy RDD using rdrobust
# ----------------------------------------------------------------------
# Run fuzzy RDD
fuzzy_rdd <- rdrobust(
    y = map_data$outcome,         # Outcome variable
    x = map_data$running_var,     # Running variable (distance to border)
    fuzzy = map_data$treatment,   # Fuzzy treatment (overlap with Catholic HRE)
    kernel = "triangular",        # Triangular kernel for local fitting
    bwselect = "mserd"            # Bandwidth selection rule
)

# Print RDD Results
summary(fuzzy_rdd)

# ----------------------------------------------------------------------
# 4. Visualize RDD Results
# ----------------------------------------------------------------------
ggplot(map_data, aes(x = running_var, y = outcome, color = treatment)) +
    geom_point(alpha = 0.5) +
    geom_smooth(method = "lm", se = FALSE) +
    labs(
        title = "Fuzzy RDD: Far-Right Vote Share vs. Distance to Catholic HRE Border",
        x = "Distance to Catholic HRE Border (meters)",
        y = "Far-Right Vote Share (%)"
    ) +
    theme_minimal()



