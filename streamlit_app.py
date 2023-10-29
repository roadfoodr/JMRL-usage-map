# -*- coding: utf-8 -*-
"""
Created on Wed May 24 02:35:20 2023

@author: MDP
"""

import pandas as pd
import numpy as np
import streamlit as st
from st_files_connection import FilesConnection

from streamlit_utilities import check_password as check_password

import random

# import seaborn as sns
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
# import altair as alt
# import pydeck as pdk

# DATA_DIR = './data/'
DATA_DIR = 'jmrl-visualization/'
# DATA_FILE = 'patrons_geocoded_grouped_091923.xlsx'
# DATA_FILE = 'patrons_geocoded_grouped_091923.csv'
DATA_FILE = 'patrons_geocoded_091923.csv'

map_style = 'mapbox://styles/mapbox/streets-v12'

# %% LOAD DATA ONCE
@st.cache_data
def load_data(data_file):
    path = f'{DATA_DIR}{data_file}'

    conn = st.experimental_connection('s3', type=FilesConnection)
    df = conn.read(path, input_format="csv", ttl=600)
        
    return df

# %%  STREAMLIT APP LAYOUT
st.set_page_config(
    layout="centered",       # alternative option: 'wide'
    page_icon=":book:",
    page_title="JMRL usage")  # Intentionally obscure

if not check_password():
    st.stop()
    # pass

df = load_data(DATA_FILE)

st.write("## JMRL usage")


# %% filter and rename
df['lat'] = df['lat_orig']
df['lon'] = df['long_orig']

usecols = ['TOT CHKOUT', 'TOT RENWAL', 
       'creation_date', 'home_branch', 'jurisdiction',
       'card_type', 'lat', 'lon', 'geoloc',
       'lat_geohash', 'long_geohash', 'frequent_location',
       'frequent_location_tie']

df = df[usecols]

df.dropna(subset=['lat', 'lon'], inplace=True)
# df['color'] = [(0.25, 0.4, 1.0, 0.1)] * len(df)

df['color'] = "#ffaa0030"

# %% preview df

st.write(f"##### Sample of data: {len(df)} rows")
st.dataframe(df.head(5))


# %% global filter
st.write("##### Global subset ")

col11, col12 = st.columns(2)
with col11:
    global_filter = 'All'
    global_filter_options = {'All': 'All patrons',
                             'jurisdiction': 'Jurisdiction',
                             'home_branch': 'Home Branch',
                             'frequent_location': 'Frequent Branch',
                             }

    global_filter_field = st.selectbox(
        'Global filter by:',
        global_filter_options.keys(),
        format_func=lambda x: global_filter_options[x]
        )
    
    if global_filter_field != 'All':
        global_filter_vals = df[global_filter_field].unique()
        global_filter_vals = global_filter_vals[~pd.isnull(global_filter_vals)]
        global_filter_vals = global_filter_vals[global_filter_vals != 'none']
        global_filter_vals = global_filter_vals[global_filter_vals != 'Historical Society']
        global_filter_choices = np.sort(global_filter_vals)
        with col12:
            global_filter_selection = st.selectbox(
                f'{global_filter_options[global_filter_field]} to filter by', 
                ['All'] + list(global_filter_choices))
        
    df_filtered = (df if (global_filter_field == 'All'
                          or global_filter_selection == 'All')
                   else df[df[global_filter_field] == global_filter_selection].copy()
                   )
st.write(f'Rows in current view: {len(df_filtered)}')
st.dataframe(df_filtered.head(5))

# %% set up color column
if False:
    # https://stackoverflow.com/questions/47398081/how-do-i-map-df-column-values-to-hex-color-in-one-go
    # https://matplotlib.org/stable/users/explain/colors/colormaps.html
    
    # color_source_col = 'Patron_count'
    color_source_col = 'Circ'
    # cmap = plt.cm.viridis
    # cmap = plt.cm.Reds
    # cmap = plt.cm.plasma
    # cmap = plt.cm.RdBu_r
    # cmap = plt.cm.PuRd
    cmap = plt.cm.BuGn
    # cmap = plt.cm.coolwarm
    
    # TODO: select the high_clip as a percentile of values, provide slider control
    norm = mcolors.Normalize(vmin=np.nanmin(df_grouped[color_source_col].values),
                               vmax=np.nanmax(df_grouped[color_source_col].values), 
                              # vmax=11900, 
                             clip=True)
    mapper = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    
    # df_grouped['color'] = df_grouped[color_source_col].apply(lambda x: mcolors.to_hex(mapper.to_rgba(x)))
    df_grouped['color'] = df_grouped[color_source_col].apply(lambda x: mapper.to_rgba(x, alpha=.4))



# %% display map
st.write("##### Map: selected patrons")
st.write(df_filtered['color'].value_counts())
# st.write(df_filtered.dtypes)
df_filtered['color'] = "#ffaa0030"

# st.map(data=df_filtered, zoom=9, color='color', size=50)
st.map(data=df_filtered, zoom=9, color='#6babd030', size=10)
