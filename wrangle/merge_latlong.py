# -*- coding: utf-8 -*-
"""
Created on Sat Sep 30 01:08:47 2023

@author: MDP
"""

import pandas as pd

DATA_DIR = '../data/'
DATA_FILE = 'all patrons.xlsx'
# GEOCODED_FILE = 'jmrl_data_v2.h5'
GEOCODED_FILE = 'jmrl_geocode.h5'
GEOCODED_DSTORE = 'patr_rec_geocoded'

OUT_FILE = 'patrons_091923.csv'


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

# TODO: need to do some cleanup of the address field in df_patrons


# %% try some matching
print('merging files')

df_patrons['addr_key'] = df_patrons['ADDRESS'].str.replace('$', ' ', regex=False)
df_patrons['addr_key'] = df_patrons['addr_key'].str.replace(', ', ' ', regex=False)
df_patrons['addr_key'] = df_patrons['addr_key'].str.upper()
df_geocoded['addr_key'] = df_geocoded['addr_combined'].str.upper()

df = pd.merge(df_patrons,df_geocoded[['addr_key','lat_orig', 'long_orig']], on='addr_key', how='left')
# Rows will be duplicated if more than one address row matches; i.e. 2 patrons at same address
df.drop_duplicates(subset=['P ID'], keep='first', ignore_index=True, inplace=True)
print(f'Matched rows:   {df["lat_orig"].count()}')
print(f'Unmatched rows: {df["lat_orig"].isna().sum()}')