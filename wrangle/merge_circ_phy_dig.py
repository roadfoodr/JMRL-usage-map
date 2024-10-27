import pandas as pd
from pathlib import Path

def main():
    # Get the script's directory and construct path to data directory
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent / 'data'
    
    # Read both input files
    geocoded_file = data_dir / "patrons_geocoded_091923.csv"
    elibpats_file = data_dir / "elibpats_2020-2024_grouped.csv"
    
    geo_df = pd.read_csv(geocoded_file)
    elib_df = pd.read_csv(elibpats_file)
    
    original_rows = len(geo_df)
    print(f"Read geocoded patrons file: {len(geo_df):,} records")
    print(f"Read elibpats file: {len(elib_df):,} records")
    
    # Before proceeding, let's do an analysis using outer join
    analysis_df = pd.merge(
        geo_df[['P ID']],  # Just need P ID for analysis
        elib_df[['P ID', 'circ_dig_total']],
        on='P ID',
        how='outer',
        indicator=True
    )
    
    # Analyze the merge results
    only_physical = analysis_df['_merge'] == 'left_only'
    only_digital = analysis_df['_merge'] == 'right_only'
    both = analysis_df['_merge'] == 'both'
    
    print("\nMerge Analysis:")
    print(f"Records with only physical circulation: {only_physical.sum():,}")
    print(f"Records with only digital circulation: {only_digital.sum():,}")
    print(f"Records with both types: {both.sum():,}")
    
    # Now proceed with the actual data processing
    # Calculate circ_phy_total
    geo_df['circ_phy_total'] = geo_df['TOT CHKOUT'] + geo_df['TOT RENWAL']
    
    # Rename creation_date to circ_phy_start
    geo_df = geo_df.rename(columns={'creation_date': 'circ_phy_start'})
    
    # Add circ_phy_end
    geo_df['circ_phy_end'] = '2023-09-19'
    
    # Calculate circ_phy_avg
    # Convert dates to datetime for calculation
    geo_df['start_date'] = pd.to_datetime(geo_df['circ_phy_start'])
    geo_df['end_date'] = pd.to_datetime(geo_df['circ_phy_end'])
    
    # Calculate years difference (including partial years)
    geo_df['years_active'] = (
        (geo_df['end_date'] - geo_df['start_date']).dt.days / 365.25
    )
    
    # Enforce minimum 6-month period (0.5 years)
    geo_df['years_active'] = geo_df['years_active'].clip(lower=0.5)
    
    # Calculate average circulation per year
    geo_df['circ_phy_avg'] = (
        geo_df['circ_phy_total'] / geo_df['years_active']
    ).round(1)
    
    # Drop temporary calculation columns
    geo_df = geo_df.drop(['start_date', 'end_date', 'years_active'], axis=1)
    
    # Merge in the digital circulation data
    # Select only the columns we want from elibpats
    elib_cols = ['P ID', 'circ_dig_total', 'circ_dig_start', 'circ_dig_end', 'circ_dig_avg']
    elib_df = elib_df[elib_cols]
    
    # Merge the dataframes using left join to maintain original number of rows
    geo_df = pd.merge(
        geo_df,
        elib_df,
        on='P ID',
        how='left'
    )
    
    # Handle missing values in digital circulation columns
    geo_df['circ_dig_total'] = geo_df['circ_dig_total'].fillna(0)
    geo_df['circ_dig_avg'] = geo_df['circ_dig_avg'].fillna(0)
    geo_df['circ_dig_start'] = geo_df['circ_dig_start'].fillna(geo_df['circ_phy_start'])
    geo_df['circ_dig_end'] = geo_df['circ_dig_end'].fillna(geo_df['circ_phy_end'])
    
    # Calculate new combined statistics
    # First convert dates to datetime for comparison
    geo_df['phy_start_dt'] = pd.to_datetime(geo_df['circ_phy_start'])
    geo_df['phy_end_dt'] = pd.to_datetime(geo_df['circ_phy_end'])
    geo_df['dig_start_dt'] = pd.to_datetime(geo_df['circ_dig_start'])
    geo_df['dig_end_dt'] = pd.to_datetime(geo_df['circ_dig_end'])
    
    # Calculate combined total
    geo_df['circ_combined_total'] = geo_df['circ_phy_total'] + geo_df['circ_dig_total']
    
    # Find start and end dates for combined timespan
    geo_df['combined_start_dt'] = geo_df[['phy_start_dt', 'dig_start_dt']].min(axis=1)
    geo_df['combined_end_dt'] = geo_df[['phy_end_dt', 'dig_end_dt']].max(axis=1)
    
    # Calculate years active (with 6-month minimum)
    geo_df['combined_years'] = (
        (geo_df['combined_end_dt'] - geo_df['combined_start_dt']).dt.days / 365.25
    ).clip(lower=0.5)
    
    # Calculate combined average
    geo_df['circ_combined_avg'] = (
        geo_df['circ_combined_total'] / geo_df['combined_years']
    ).round(1)
    
    # Calculate digital ratio
    geo_df['circ_dig_ratio'] = (
        geo_df['circ_dig_avg'] / (geo_df['circ_dig_avg'] + geo_df['circ_phy_avg'])
    ).round(2)
    
    # Clean up temporary columns
    geo_df = geo_df.drop([
        'phy_start_dt', 'phy_end_dt', 
        'dig_start_dt', 'dig_end_dt',
        'combined_start_dt', 'combined_end_dt',
        'combined_years'
    ], axis=1)
    
    # Define all columns in their desired order
    first_cols = [
        'P ID',
        'TOT CHKOUT',
        'TOT RENWAL',
        'circ_phy_total',
        'circ_phy_avg',
        'circ_phy_start',
        'circ_phy_end',
        'circ_dig_total',
        'circ_dig_avg',
        'circ_dig_start',
        'circ_dig_end',
        'circ_combined_total',
        'circ_combined_avg',
        'circ_dig_ratio',
        'CIRCACTIVE',
        'HOME LIBR',
        'P TYPE'
    ]
    
    # Get remaining columns in their original order
    remaining_cols = [col for col in geo_df.columns if col not in first_cols]
    
    # Combine the column lists
    cols = first_cols + remaining_cols
    
    # Reorder the dataframe columns
    geo_df = geo_df[cols]
    
    # Write the updated file
    output_file = data_dir / "patrons_geocoded_updated_091923.csv"
    geo_df.to_csv(output_file, index=False)
    
    print(f"\nUpdated geocoded data written to {output_file}")
    print(f"Total records: {len(geo_df):,}")
    print(f"Columns: {', '.join(geo_df.columns)}")
    
    # Print some statistics about the new columns
    print("\nStatistics for new columns:")
    print("\ncirc_combined_total:")
    print(geo_df['circ_combined_total'].describe())
    print("\ncirc_combined_avg:")
    print(geo_df['circ_combined_avg'].describe())
    print("\ncirc_dig_ratio:")
    print(geo_df['circ_dig_ratio'].describe())

if __name__ == "__main__":
    main()
