# Clear workspace
rm(list = ls())

# Load required packages
if (!require("pacman")) install.packages("pacman")
pacman::p_load(restatis, rstudioapi, dplyr)

# Set working directory to script location (Modify as needed)
setwd(dirname(rstudioapi::getActiveDocumentContext()$path))

# Load Zensus credentials
gen_auth_get(database = "zensus")

# Define all Zensus table categories
table_categories <- c("1*", "2*", "3*", "4*", "5*", "6*")

# Create an empty list to store successful downloads
downloaded_data <- list()

# Loop through each major table category
for (category in table_categories) {
  print(paste("🔍 Processing category:", category))
  
  # Retrieve tables for the current category
  tables <- gen_catalogue(
    code = category,  
    database = "zensus",
    category = "tables",
    detailed = TRUE
  )
  
  # Extract all table codes
  if (!is.null(tables$Tables)) {
    category_name <- names(tables$Tables)[1]  # Get category name dynamically
    table_codes <- tables$Tables[[category_name]][["Code"]]
    
    # ✅ **Filter only tables that contain "W" or "w" in the code**
    w_tables <- table_codes[grep("[Ww]", table_codes)]  # Case-insensitive
    
    print(paste("Found", length(w_tables), "W-tables in category", category))
    
    # Loop over each filtered table code
    for (table_code in w_tables) {
      print(paste("Attempting to download:", table_code))  # Status message
      
      # Try downloading the table
      tryCatch({
        data <- gen_table(
          name = table_code,
          database = "zensus",
          regionalvariable = "GEOWK1",  # Municipality-level
          regionalkey = "",  # All municipalities
          language = "en"
        )
        
        # Store data in the list
        downloaded_data[[table_code]] <- data
        print(paste("✅ Successfully downloaded:", table_code))  # Success message
        
      }, error = function(e) {
        print(paste("❌ Error downloading", table_code, "- Skipping to next table."))
      })
    }
  } else {
    print(paste("⚠️ No tables found in category:", category))
  }
}

# Print summary of successful downloads
print(paste("🎉 Download complete. Successfully downloaded", length(downloaded_data), "tables."))


# Check if we have downloaded any tables
if (length(downloaded_data) == 0) {
  print("⚠️ No data available for merging.")
} else {
  print("🔄 Merging downloaded tables...")
  
  # Start with the first dataset as a base
  merged_data <- downloaded_data[[1]]
  
  # Loop through the rest of the tables and merge on `1_variable_attribute_code`
  for (i in 2:length(downloaded_data)) {
    table <- downloaded_data[[i]]
    
    # Ensure the merging key (`1_variable_attribute_code`) exists
    if ("1_variable_attribute_code" %in% colnames(table)) {
      merged_data <- full_join(merged_data, table, by = "1_variable_attribute_code")
      print(paste("✅ Merged table", names(downloaded_data)[i], "successfully."))
    } else {
      print(paste("⚠️ Skipping", names(downloaded_data)[i], "- No matching key."))
    }
  }
  
  # Print summary of the merged dataset
  print(paste("🎉 Merging complete! Final dataset contains", nrow(merged_data), "rows and", ncol(merged_data), "columns."))
  
  # Optional: View the first few rows
  head(merged_data)
}
