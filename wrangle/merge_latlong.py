# -*- coding: utf-8 -*-
"""
Created on Sat Sep 30 01:08:47 2023

@author: MDP
"""

import pandas as pd
import numpy as np
import geohash  # docs: https://github.com/vinsci/geohash/
#                 also: https://docs.quadrant.io/quadrant-geohash-algorithm
#            and maybe: https://www.pluralsight.com/resources/blog/cloud/location-based-search-results-with-dynamodb-and-geohash

import matplotlib.pyplot as plt

DATA_DIR = '../data/'
DATA_FILE = 'all patrons_091923.xlsx'
# GEOCODED_FILE = 'jmrl_data_v2.h5'
GEOCODED_FILE = 'jmrl_geocode.h5'
GEOCODED_DSTORE = 'patr_rec_geocoded'

OUT_FILE = 'patrons_geocoded_091923.xlsx'

# %% Read the GEOCODED file
print('Reading Geocoded file')
data_store = pd.HDFStore(f'{DATA_DIR}{GEOCODED_FILE}')
# dkeys = data_store.keys()
# Retrieve data using key
df_geocoded = data_store[f'{GEOCODED_DSTORE}']
data_store.close()

# %% Read the patrons file
print('Reading patrons file')
df_patrons = pd.read_excel(f'{DATA_DIR}{DATA_FILE}')
df_patrons.rename(columns={'RECORD #(PATRON)':'P ID', 'CREATED(PATRON)':'creation_date'}, inplace=True)

patroncols = [col for col in df_patrons.columns if "Unnamed" not in col]
df_patrons = df_patrons[patroncols]
# TODO: need to do some cleanup of the address field in df_patrons

# where addr1 is blank, use addr2 if possible
# https://stackoverflow.com/questions/71762736/pandas-replace-empty-cell-with-value-of-another-column
df_patrons['ADDRESS'] = df_patrons['ADDRESS'].replace('', pd.NA).fillna(df_patrons['ADDRESS2'])

# remove extraneous patron types (staff, teacher cards)
df_patrons = df_patrons[df_patrons['P TYPE'] <= 11]
# remove digital-only patrons
df_patrons = df_patrons[df_patrons['TOT CHKOUT'] > 0]

# %% try some matching
print('merging files')

df_patrons['addr_key'] = df_patrons['ADDRESS'].str.replace('$', ' ', regex=False)
df_patrons['addr_key'] = df_patrons['addr_key'].str.replace(', ', ' ', regex=False)
df_patrons['addr_key'] = df_patrons['addr_key'].str.replace('\s+', ' ', regex=True)
df_patrons['addr_key'] = df_patrons['addr_key'].str.upper()
df_geocoded['addr_key'] = df_geocoded['addr_combined'].str.replace('\s+', ' ', regex=True)
df_geocoded['addr_key'] = df_geocoded['addr_key'].str.upper()

df = pd.merge(df_patrons,df_geocoded[['addr_key','lat_orig', 'long_orig']], on='addr_key', how='left')
# Rows will be duplicated if more than one address row matches; i.e. 2 patrons at same address
df.drop_duplicates(subset=['P ID'], keep='first', ignore_index=True, inplace=True)
print(f'Matched rows:   {df["lat_orig"].count()}')
print(f'Unmatched rows: {df["lat_orig"].isna().sum()}')


# %% geohashing
print('geohashing')
df['geoloc'] = df.apply(lambda x: np.nan if pd.isna(x['lat_orig']) or pd.isna(x['long_orig'])
                        else geohash.encode(x['lat_orig'], x['long_orig'], precision=6), 
                        axis=1)

print('reverse geohashing')
def gh_decode(hash):
    if pd.isna(hash):
        lat, lon = hash, hash
    else:
        lat, lon = geohash.decode(hash)
    return pd.Series({"lat_geohash":lat, "long_geohash":lon})

df = df.join(df["geoloc"].apply(gh_decode))

# TODO add precision to decode; precompute and cache reverse geoloc at multiple levels of precision

# %% write the spreadsheet
print('writing spreadsheet')
df.to_excel(f'{DATA_DIR}{OUT_FILE}', index=False)


# %% experimental
plt.hist(df['TOT CHKOUT'], range=(1, 200), bins=40, density=True)