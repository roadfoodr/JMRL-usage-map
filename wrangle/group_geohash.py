# -*- coding: utf-8 -*-
"""
Created on Sat Sep 30 01:08:47 2023

@author: MDP
"""

import pandas as pd
# import geohash  # docs: https://github.com/vinsci/geohash/
# #                 also: https://docs.quadrant.io/quadrant-geohash-algorithm
# #            and maybe: https://www.pluralsight.com/resources/blog/cloud/location-based-search-results-with-dynamodb-and-geohash


DATA_DIR = '../data/'
DATA_FILE = 'patrons_geocoded_091923.xlsx'

OUT_FILE = 'patrons_geocoded_grouped_091923.xlsx'

# %% Read the geocoded patrons file
print('Reading geocoded patrons file')
df_patrons = pd.read_excel(f'{DATA_DIR}{DATA_FILE}')

patroncols = [col for col in df_patrons.columns if "ADDR" not in col]
df_patrons = df_patrons[patroncols]

df_patrons.dropna(inplace=True)

# %% Group via geoloc

# https://deanla.com/pandas_named_agg.html
df_grouped = df_patrons.groupby('geoloc').agg(
    Circ = ('TOT CHKOUT', 'sum'),
    Patron_count = ('TOT CHKOUT', 'count'),
    lat = ('lat_geohash', 'mean'),
    lon = ('long_geohash', 'mean')
    )


# %% write the spreadsheet
print('writing spreadsheet')
df_grouped.to_excel(f'{DATA_DIR}{OUT_FILE}', index=True)
