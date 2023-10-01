# -*- coding: utf-8 -*-
"""
Created on Wed May 24 02:35:20 2023

@author: MDP
"""

import pandas as pd
import numpy as np
import streamlit as st

import random

# import seaborn as sns
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
# import altair as alt
# import pydeck as pdk

DATA_DIR = './data/'
DATA_FILE = 'patrons_geocoded_grouped_091923.xlsx'

map_style = 'mapbox://styles/mapbox/streets-v12'

# %% LOAD DATA ONCE
@st.cache_data
def load_data(data_file):
    path = f'{DATA_DIR}{data_file}'
    
    skiprows_p = 1.0  # e.g. 100% of the lines
    # https://stackoverflow.com/questions/22258491/read-a-small-random-sample-from-a-big-csv-file-into-a-python-data-frame
    # keep the header, then take only p% of lines

    df = pd.read_excel(
        path,
        # nrows=100,
        nrows=None,
        skiprows=lambda i: i>0 and random.random() > skiprows_p,
        header=0,
    )
        
    return df

# %%  STREAMLIT APP LAYOUT
st.set_page_config(
    layout="centered",       # alternative option: 'wide'
    page_icon=":book:",
    page_title="JMRL usage")  # Intentionally obscure

df_grouped = load_data(DATA_FILE)
# TODO temporarily removing a specific outlier pending data exploration
# df_grouped = df_grouped[df_grouped['geoloc'] != 'dqb0q5']

st.write("## JMRL usage")

# %% set up color column

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


st.write(f"##### Sample of data: {len(df_grouped)} rows")
st.dataframe(df_grouped.head(5))

# %% display map
st.write("##### Map: aggregated patrons")

st.map(data=df_grouped, zoom=9, color='color', size=300)


