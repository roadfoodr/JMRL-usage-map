# -*- coding: utf-8 -*-
"""
Created on Wed May 24 02:35:20 2023

@author: MDP
"""

import pandas as pd
# import geopandas as gpd
import numpy as np
import streamlit as st
from st_files_connection import FilesConnection

# from streamlit_utilities import check_password as check_password
from streamlit_utilities import category_colors, rgb_to_hex

# import os

import altair as alt
import pydeck as pdk

DATA_DIR = './data/'
S3_DIR = 'jmrl-visualization/'
S3_FILE = 'patrons_geocoded_091923.csv'
SHAPE_FILE = 'JMRL_counties.pickle'


# %% load data once
@st.cache_data
def load_data_s3(data_file):
    path = f'{S3_DIR}{data_file}'
    conn = st.connection('s3', type=FilesConnection)
    df_loaded = conn.read(path, input_format="csv", ttl=600)
    return df_loaded

@st.cache_data
def load_data_pickle(data_file):
    path = f'{DATA_DIR}{data_file}'
    df_loaded = pd.read_pickle(path)        
    return df_loaded

# %%  STREAMLIT APP LAYOUT
st.set_page_config(
    layout="wide",       # alternative option: 'wide'
    page_icon=":book:",
    page_title="JMRL usage")

# https://github.com/streamlit/streamlit/issues/6336
st.markdown(
    """
        <style>
            .appview-container .main .block-container {{
                padding-top: {padding_top}rem;
                padding-bottom: {padding_bottom}rem;
                }}

        </style>""".format(
        padding_top=3, padding_bottom=3
    ),
    unsafe_allow_html=True,
)

# if not check_password():
#     st.stop()
#     # pass


# %% load data
df = load_data_s3(S3_FILE)
# TODO: read this from S3
df_counties = load_data_pickle(SHAPE_FILE)

st.title("JMRL usage", anchor="title")
# st.write(df_counties.head(2))

# %% filter and rename
df['lat'] = df['lat_anon']
df['lon'] = df['long_anon']
df['Circ'] = df['TOT CHKOUT'] + df['TOT RENWAL']
usecols = ['Circ', 
       'creation_date', 'home_branch', 'jurisdiction',
       'card_type', 'lat', 'lon', 'geoloc',
       'lat_geohash', 'long_geohash', 'frequent_location',
       'frequent_location_tie']

df = df[usecols]

df.dropna(subset=['lat', 'lon'], inplace=True)
# df['color'] = [(200, 30, 0, 33)] * len(df)
df['color'] = df['home_branch'].map(category_colors)

# %% preview df

with st.expander("Data sample (anonymized)", expanded=False):
    st.write(f"##### Sample of data: {len(df)} total rows")
    st.dataframe(df.head(5))

# %% top columns
col11, col12 = st.columns(2)

# %% global filter controls

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
        format_func=lambda x: global_filter_options[x],
        key='global_filter_1'
        )
    
    if global_filter_field != 'All':
        global_filter_vals = df[global_filter_field].unique()
        global_filter_vals = global_filter_vals[~pd.isnull(global_filter_vals)]
        global_filter_vals = global_filter_vals[global_filter_vals != 'none']
        global_filter_vals = global_filter_vals[global_filter_vals != 'Historical Society']
        global_filter_choices = np.sort(global_filter_vals)
        with col11:
            global_filter_selection = st.selectbox(
                f'{global_filter_options[global_filter_field]} to filter by', 
                ['All'] + list(global_filter_choices))
        
    df_filtered = (df if (global_filter_field == 'All'
                          or global_filter_selection == 'All')
                   else df[df[global_filter_field] == global_filter_selection].copy()
                   )
# st.caption(f'Rows in current view: {len(df_filtered)}')
# st.dataframe(df_filtered.head(5))

# %% view style controls

with col11:
    st.caption(f'Rows in current view: {len(df_filtered)}')

with col11:
    view_style_options = {'ScatterplotLayer': 'Scatter plot',
                          'HeatmapLayer': 'Heat map',
                          }

    view_style = st.selectbox("View Style:",
                              view_style_options.keys(),
                              format_func=lambda x: view_style_options[x],
                              key='view_style_filter')

# %% set up bar chart

aggregate_field = 'frequent_location'
sort_field = 'count'

aggregate_field_options = {
    'frequent_location': 'Frequent Branch',
    'home_branch': 'Home Branch',
    'jurisdiction': 'Jurisdiction',
    }

with col12:
    aggregate_field = st.selectbox(
        'Categorize by:',
        aggregate_field_options.keys(),
        format_func=lambda x: aggregate_field_options[x],
        key='aggregate_field_1'
        )

df_grouped = df_filtered[[aggregate_field]].groupby(
    by=[aggregate_field], as_index=False).value_counts(sort=True, ascending=False)
# df_grouped.reset_index(inplace=True)

category_colors_hex = [rgb_to_hex(*rgb) for rgb in category_colors.values()]

c = alt.Chart(df_grouped).mark_bar().encode(
    x=alt.X(aggregate_field,
            title=aggregate_field_options[aggregate_field],
            sort=alt.SortField(field=sort_field,
                                order='descending',
                                ),
            ),
    y=alt.Y(sort_field),
    color = alt.Color(aggregate_field, 
                      scale=alt.Scale(domain=list(category_colors.keys()), 
                                      range=category_colors_hex,
                                      ),
                       legend=None)
    )


with col12:
    # st.write(df_grouped.head(10))
    st.altair_chart(c, use_container_width=True)


# %% set up color column
color_source_col = aggregate_field
df_filtered['color'] = df_filtered[color_source_col].map(category_colors)


# %% map background controls

MAP_BACKGROUND_CONTROL = False
map_style_options = { 'mapbox://styles/mpowers38111/clogll9d8006p01qjcy6b5vzm': 'Style 1', 
                      'mapbox://styles/mapbox/light-v11': 'Style 2',
                      }
map_style, *unused = map_style_options.keys()

if MAP_BACKGROUND_CONTROL:
    
    with col12:
        map_style = st.radio('Map Background', map_style_options.keys(),
                                format_func=lambda x: map_style_options[x])

# %% construct and display map

df_latlon = df_filtered[['lat', 'lon', 'color']].copy()
df_latlon['tooltip_value'] = df_filtered[color_source_col]
df_latlon['tooltip_value'].fillna(value="None", inplace=True)
df_latlon['tooltip_name'] = aggregate_field_options[color_source_col]

# st.write(df_latlon.head(10))

def construct_patron_map(df, map_style):
    patron_map = pdk.Deck(
        # map_style=None,
        map_style=map_style,
        initial_view_state=pdk.ViewState(
            # latitude=38.06,
            # longitude=-78.517,
            latitude=df['lat'].mean(),
            longitude=df['lon'].mean(),
            zoom=9,
            ),
        layers=[
            pdk.Layer(
                type = "GeoJsonLayer",
                data=df_counties,
                line_width_min_pixels=1.5,
                pickable=False,
                auto_highlight=True,
                stroked=True,
                filled=False,
                get_line_color=[0, 0, 0, 48],
                ),
            pdk.Layer(
                # 'ScatterplotLayer',
                # 'HeatmapLayer',
                view_style,
                opacity=.2,
                data=df,
                get_position=['lon', 'lat'],
                # get_color='[0, 100, 30, 80]',
                get_color='color',
                get_radius=50,
                radius_min_pixels=1.33,
                radius_max_pixels=20,
                pickable=True,
                auto_highlight=True,
                ),
            ],
        tooltip = {
            # Can only display tooltip from one pickable layer, currently ScatterplotLayer
            "text": "{tooltip_name}: {tooltip_value}"
            },
        )
    return patron_map

st.subheader("Map: Patrons (as selected)", anchor="map")

patron_map = construct_patron_map(df_latlon, map_style)
st.pydeck_chart(patron_map)

# Possible performance improvement, but not displaying background map tiles
# import streamlit.components.v1 as components
# components.html(patron_map.to_html(as_string=True), height=600)

