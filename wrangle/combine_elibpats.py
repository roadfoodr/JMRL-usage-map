import pandas as pd
import glob
import os
from pathlib import Path

def main():
    # Get the script's directory and construct path to data directory
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / 'data'
    
    # List to store individual dataframes
    dfs = []
    
    # Use glob to get all CSV files matching the pattern, in the data directory
    csv_files = list(data_dir.glob("elibpats_20[2][0-4].csv"))
    
    print(f"Found {len(csv_files)} files in {data_dir}")
    
    # Read each file and add year column
    for file in csv_files:
        # Extract year from filename (assuming format elibpats_YYYY.csv)
        year = int(file.stem.split('_')[1])
        
        # Read the CSV file
        df = pd.read_csv(file)
        
        # Rename the circulation column if it exists under either name
        if "Elib circ for patron" in df.columns:
            df = df.rename(columns={"Elib circ for patron": "circ_dig_current_year"})
        elif "Total circ for patron" in df.columns:
            df = df.rename(columns={"Total circ for patron": "circ_dig_current_year"})
        
        # Add year column
        df['year'] = year
        
        # Append to list of dataframes
        dfs.append(df)
        
        # Print info about each file as it's processed
        print(f"Processed {file.name}: {len(df)} records")
    
    # Combine all dataframes
    combined_df = pd.concat(dfs, ignore_index=True)
    
    # Reorder columns to put year first and circ_dig_current_year second
    cols = combined_df.columns.tolist()
    cols.remove('year')
    cols.remove('circ_dig_current_year')
    cols = ['year', 'circ_dig_current_year'] + cols
    
    combined_df = combined_df[cols]
    
    # Rename RECORD #(PATRON) to P ID
    combined_df = combined_df.rename(columns={"RECORD #(PATRON)": "P ID"})
    
    # Write the combined (but not grouped) dataframe
    output_file = data_dir / "elibpats_2020-2024_combined.csv"
    combined_df.to_csv(output_file, index=False)
    print(f"\nCombined data written to {output_file}")
    print(f"Total records: {len(combined_df)}")
    print(f"Columns: {', '.join(combined_df.columns)}")
    
    # Create grouped dataframe
    # First get the year ranges for each P ID
    year_ranges = combined_df.groupby('P ID').agg({
        'year': ['min', 'max']
    })
    year_ranges.columns = ['start_year', 'end_year']
    year_ranges = year_ranges.reset_index()
    
    # Convert years to dates with special handling for 2024
    year_ranges['circ_dig_start'] = pd.to_datetime(year_ranges['start_year'].astype(str) + '-01-01')
    year_ranges['circ_dig_end'] = year_ranges.apply(
        lambda x: pd.Timestamp(f"{x['end_year']}-08-31") if x['end_year'] == 2024 
        else pd.Timestamp(f"{x['end_year']}-12-31"), 
        axis=1
    )
    
    # Group by P ID and calculate aggregations
    grouped_df = combined_df.groupby('P ID').agg({
        'circ_dig_current_year': 'sum',  # Sum all years' circulation
        'P BARCODE': 'first',            # Keep the first occurrence of other fields
        'P TYPE': 'first',
        'HOME LIBR': 'first',
        'ADDRESS': 'first',
        'ADDRESS2': 'first'
    }).reset_index()
    
    # Rename the summed circulation column
    grouped_df = grouped_df.rename(columns={'circ_dig_current_year': 'circ_dig_total'})
    
    # Merge in the date range information
    grouped_df = grouped_df.merge(year_ranges[['P ID', 'circ_dig_start', 'circ_dig_end']], 
                                on='P ID', 
                                how='left')
    
    # Convert dates to string format YYYY-MM-DD
    grouped_df['circ_dig_start'] = grouped_df['circ_dig_start'].dt.strftime('%Y-%m-%d')
    grouped_df['circ_dig_end'] = grouped_df['circ_dig_end'].dt.strftime('%Y-%m-%d')
    
    # Calculate average circulation
    # Convert date strings back to datetime for calculation
    grouped_df['start_date'] = pd.to_datetime(grouped_df['circ_dig_start'])
    grouped_df['end_date'] = pd.to_datetime(grouped_df['circ_dig_end'])
    
    # Calculate years difference (including partial years)
    grouped_df['years_active'] = (
        (grouped_df['end_date'] - grouped_df['start_date']).dt.days / 365.25
    )
    
    # Calculate average circulation per year
    grouped_df['circ_dig_avg'] = (
        grouped_df['circ_dig_total'] / grouped_df['years_active']
    ).round(1)
    
    # Drop the temporary calculation columns
    grouped_df = grouped_df.drop(['start_date', 'end_date', 'years_active'], axis=1)
    
    # Reorder columns to put the specified columns first
    cols = grouped_df.columns.tolist()
    for col in ['circ_dig_end', 'circ_dig_start', 'circ_dig_total', 'P ID', 'circ_dig_avg']:
        cols.remove(col)
    cols = ['P ID', 'circ_dig_total', 'circ_dig_start', 'circ_dig_end', 'circ_dig_avg'] + cols
    
    grouped_df = grouped_df[cols]
    
    # Write the grouped dataframe
    grouped_output_file = data_dir / "elibpats_2020-2024_grouped.csv"
    grouped_df.to_csv(grouped_output_file, index=False)
    
    print(f"\nGrouped data written to {grouped_output_file}")
    print(f"Total unique patrons: {len(grouped_df)}")
    print(f"Columns: {', '.join(grouped_df.columns)}")
    
if __name__ == "__main__":
    main()