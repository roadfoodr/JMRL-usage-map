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

FREQ_LOC_FILE = 'frequent_locations_091923.xlsx'
# GEOCODED_FILE = 'jmrl_data_v2.h5'
GEOCODED_FILE = 'jmrl_geocode.h5'
GEOCODED_DSTORE = 'patr_rec_geocoded'

OUT_FILE = 'patrons_geocoded_091923.xlsx'

HOME_BRANCH_MAP = {
    'a': 'Gordon',
    'alock': 'Gordon',
    'c': 'Crozet',
    'clock': 'Crozet',
    'drive': 'Northside',
    'g': 'Greene',
    'glock': 'Greene',
    'l': 'Louisa',
    'm': 'Central',
    'n': 'Nelson',
    'none': 'none',
    'r': 'Northside',
    'rms': 'Northside',
    's': 'Scottsville',
    'x': 'Bookmobile',
    'z': 'error',
    }

P_JURIS_MAP = {
    0: 'Albemarle',
    1: 'Albemarle',
    2: 'Charlottesville',
    3: 'Charlottesville',
    4: 'Greene',
    5: 'Greene',
    6: 'Louisa',
    7: 'Louisa',
    8: 'Nelson',
    9: 'Nelson',
    10: 'Out of Area',
    11: 'Out of Area',
    12: 'Albemarle',
    13: 'Charlottesville',
    14: 'Greene',
    15: 'Louisa',
    16: 'Nelson',
    17: 'Out of Area',
    18: 'Library Use',
    19: 'In-House Use',
    20: 'Compromised',
    22: 'Banned Patron',
    24: 'Postcard Registration',
    32: 'Albemarle',
    33: 'Charlottesville',
    34: 'Greene',
    35: 'Louisa',
    36: 'Nelson',
    }

P_AGE_MAP = {
    0: 'Adult',
    1: 'Juvenile',
    2: 'Adult',
    3: 'Juvenile',
    4: 'Adult',
    5: 'Juvenile',
    6: 'Adult',
    7: 'Juvenile',
    8: 'Adult',
    9: 'Juvenile',
    10: 'Adult',
    11: 'Juvenile',
    12: 'Staff',
    13: 'Staff',
    14: 'Staff',
    15: 'Staff',
    16: 'Staff',
    17: 'Staff',
    18: 'Staff',
    19: 'Adult',
    20: 'Adult',
    22: 'Adult',
    24: 'Adult',
    32: 'Teacher',
    33: 'Teacher',
    34: 'Teacher',
    35: 'Teacher',
    36: 'Teacher',
    }


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

# %% more wrangling
str_cols = ['P ID', 'HOME LIBR', 'ADDRESS', 'ADDRESS2']
for str_col in str_cols:
    df_patrons[str_col] = df_patrons[str_col].str.strip()

df_patrons['home_branch'] = df_patrons['HOME LIBR'].map(HOME_BRANCH_MAP)
df_patrons['jurisdiction'] = df_patrons['P TYPE'].map(P_JURIS_MAP)
df_patrons['card_type'] = df_patrons['P TYPE'].map(P_AGE_MAP)

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


# %% also merge frequent location

print('Reading frequent locations file')
df_freq_locations = pd.read_excel(f'{DATA_DIR}{FREQ_LOC_FILE}')

# %% also merge frequent location

if 'matl_count' in df_freq_locations.columns:
    df_freq_locations.drop(axis='columns', columns=['matl_count'], inplace=True)

df['patron_abbrev'] = df['P ID'].str.slice(1, -1).astype(int)
df = df.merge(df_freq_locations, how='left', on=['patron_abbrev'])

# %% write the spreadsheet
print('writing spreadsheet')
df.to_excel(f'{DATA_DIR}{OUT_FILE}', index=False)

# %% experimental
plt.hist(df['TOT CHKOUT'], range=(1, 200), bins=40, density=True)