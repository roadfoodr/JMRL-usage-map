import pandas as pd
import numpy as np
from geopy.distance import geodesic
import os

def calculate_nearest_branch(patron_lat, patron_lon, branches_df):
    """Calculate the nearest branch and its distance for a given patron location"""
    # Check for invalid coordinates
    if pd.isna(patron_lat) or pd.isna(patron_lon):
        return None, None
        
    distances = []
    for _, branch in branches_df.iterrows():
        # Skip if branch coordinates are invalid
        if pd.isna(branch['lat']) or pd.isna(branch['long']):
            continue
            
        branch_coords = (branch['lat'], branch['long'])
        patron_coords = (patron_lat, patron_lon)
        
        try:
            # Calculate distance in miles
            distance = geodesic(patron_coords, branch_coords).miles
            distances.append((branch['Name'], distance))
        except ValueError as e:
            print(f"Error calculating distance: {e}")
            print(f"Patron coords: {patron_coords}")
            print(f"Branch coords: {branch_coords}")
            continue
    
    # If no valid distances were calculated, return None
    if not distances:
        return None, None
        
    # Find the nearest branch and its distance
    nearest = min(distances, key=lambda x: x[1])
    return nearest[0], round(nearest[1], 3)

def main():
    # Read the input files
    data_dir = '../data'
    patrons_file = os.path.join(data_dir, 'patrons_geocoded_updated_091923.csv')
    branches_file = os.path.join(data_dir, 'JMRL_branches_geocoded.csv')
    
    # Read CSVs
    patrons_df = pd.read_csv(patrons_file)
    branches_df = pd.read_csv(branches_file)
    
    # Print initial data info
    print("Initial data summary:")
    print(f"Total patron records: {len(patrons_df)}")
    print(f"Records with valid coordinates: {patrons_df[['lat_anon', 'long_anon']].notna().all(axis=1).sum()}")
    print(f"Total branches: {len(branches_df)}")
    print(f"Branches with valid coordinates: {branches_df[['lat', 'long']].notna().all(axis=1).sum()}\n")
    
    # Initialize new columns
    patrons_df['nearest_branch_name'] = None
    patrons_df['nearest_branch_dist'] = None
    
    # Calculate nearest branch for each patron
    print("Calculating nearest branches...")
    processed = 0
    total_records = len(patrons_df)
    
    for idx, row in patrons_df.iterrows():
        nearest_branch, distance = calculate_nearest_branch(row['lat_anon'], row['long_anon'], branches_df)
        patrons_df.at[idx, 'nearest_branch_name'] = nearest_branch
        patrons_df.at[idx, 'nearest_branch_dist'] = distance
        
        processed += 1
        if processed % 1000 == 0:  # Progress update every 1000 records
            print(f"Processed {processed}/{total_records} records...")
    
    # Save the updated dataframe
    output_file = os.path.join(data_dir, 'patrons_geocoded_with_nearest_branch.csv')
    patrons_df.to_csv(output_file, index=False)
    print(f"\nProcessed {len(patrons_df)} patrons")
    print(f"Output saved to: {output_file}")
    
    # Print summary statistics
    print("\nSummary Statistics for Branch Distances (miles):")
    print(patrons_df['nearest_branch_dist'].describe())
    
    print("\nPatron count by nearest branch:")
    print(patrons_df['nearest_branch_name'].value_counts(dropna=False))
    
    # Print count of records where nearest branch couldn't be calculated
    null_count = patrons_df['nearest_branch_name'].isna().sum()
    if null_count > 0:
        print(f"\nRecords where nearest branch couldn't be calculated: {null_count}")

if __name__ == "__main__":
    main()