# -*- coding: utf-8 -*-
"""
Created on Fri Oct  6 01:32:35 2023

@author: MDP
"""

import pandas as pd

DATA_DIR = '../data/'
DATA_FILE = 'all physical items_091923.xlsx'

OUT_FILE = 'materials_091923.xlsx'

MATL_LOC_MAP = {
    'a': 'Gordon',
    'c': 'Crozet',
    'g': 'Greene',
    'l': 'Louisa',
    'm': 'Central',
    'n': 'Nelson',
    'r': 'Northside',
    's': 'Scottsville',
    'x': 'Bookmobile',
    'z': 'Historical Society'
    }


# %% Read the materials file
print('Reading materials file')
df_matls_orig = pd.read_excel(f'{DATA_DIR}{DATA_FILE}')

# %% For convenience
df_matls = df_matls_orig.sample(25000, random_state=99, axis=0, ignore_index=True)

# %% Remove extraneous columns and rows
matlcols = [col for col in df_matls.columns if "DATE" not in col]
df_matls = df_matls[matlcols]
df_matls.rename(columns={'LOCATION':'location_code_long'}, inplace=True)

df_matls = df_matls[~((df_matls['LPATRON']==0) & (df_matls['PATRON#']==0))]

# stash the index as a material ID
df_matls = df_matls.rename_axis('matl_ID').reset_index()

# %% Map location
df_matls['location_code'] = df_matls['location_code_long'].astype(str).str[0]
df_matls['location'] = df_matls['location_code'].map(MATL_LOC_MAP)

# %% concat two patron columns

df_matls_col2 = df_matls.copy()
df_matls_col2 = df_matls_col2[~(df_matls_col2['PATRON#']==0)]
df_matls_col2['patron'] = df_matls_col2['PATRON#']

df_matls = df_matls[~(df_matls['LPATRON']==0)]
df_matls['patron'] = df_matls['LPATRON']

# %% concat two patron columns (cont.)
df_matls = pd.concat([df_matls, df_matls_col2], axis=0, ignore_index=True)
matlcols = ['matl_ID', 'patron', 'location']
df_matls = df_matls[matlcols]

# %% concat two patron columns (cont.)
df_matls.drop_duplicates(ignore_index=True, inplace=True)

# %% These are all unique materials assigned with a patron and location.
#    Group by patron and location to count them.
matlcols = ['patron', 'location']
df_matls_grouped = df_matls.groupby(matlcols)['matl_ID'].count().reset_index()
df_matls_grouped.rename(columns={'matl_ID':'matl_count'}, inplace=True)

# %% find the most frequent location for each patron
df_patron_location = df_matls_grouped.copy()
df_patron_location.sort_values(by=['patron', 'matl_count', 'location'],
                               ascending=[True, False, True], 
                               axis=0, inplace=True)
df_patron_location.drop_duplicates(subset='patron', keep='first', 
                         ignore_index=True, inplace=True)
df_patron_location.rename(columns={'location':'frequent_location'}, inplace=True)

