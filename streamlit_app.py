# -*- coding: utf-8 -*-
"""
Created on Wed May 24 02:35:20 2023

@author: MDP
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import streamlit as st

from streamlit_utilities import category_colors, rgb_to_hex, load_data_s3, load_data_pickle, compute_median_patron

import altair as alt
import pydeck as pdk

PATRONS_FILE = 'patrons_finalized_102724.csv'
BRANCHES_FILE = 'JMRL_branches_geocoded.csv'
SHAPE_FILE = 'JMRL_counties.pickle'


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

# %% load data
df = load_data_s3(PATRONS_FILE)
df_branches = load_data_s3(BRANCHES_FILE)
# TODO: read this from S3
df_counties = load_data_pickle(SHAPE_FILE)

st.title("JMRL usage", anchor="title")
# st.write(df_counties.head(2))

# %% prepare branch data
df_branches = df_branches[['Name', 'lat', 'long']].copy()
df_branches.columns = ['name', 'lat', 'lon']  # Rename to match patron data format

# %% filter and rename
df['lat'] = df['lat_anon']
df['lon'] = df['long_anon']
df['Circ'] = df['circ_combined_total']
df['creation_date'] = df['circ_phy_start']
usecols = ['Circ', 
       'creation_date', 'home_branch', 'jurisdiction',
       'card_type', 'lat', 'lon', 'geoloc',
       'lat_geohash', 'long_geohash', 'frequent_location',
       'frequent_location_tie', 'nearest_branch_name', 'nearest_branch_dist',
       'circ_phy_avg', 'circ_dig_avg', 'circ_dig_ratio']

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
                             'nearest_branch_name': 'Nearest Branch',
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
category_colors_hex = [rgb_to_hex(*rgb) for rgb in category_colors.values()]

aggregate_field_options = {
    'frequent_location': 'Frequent Branch',
    'home_branch': 'Home Branch',
    'jurisdiction': 'Jurisdiction',
    'nearest_branch_name': 'Nearest Branch',
    'circ_dig_ratio': 'Digital Use Ratio',
    'median_patron': 'Median Patron',
    }

with col12:
    aggregate_field = st.selectbox(
        'Categorize by:',
        aggregate_field_options.keys(),
        format_func=lambda x: aggregate_field_options[x],
        key='aggregate_field_1'
        )

# Compute groupby statistics based on categorization type
if aggregate_field == 'median_patron':
    # Compute median patron metrics
    median_patron = compute_median_patron(df_filtered)
    
    # Create single-row DataFrame for the bar chart
    df_grouped = pd.DataFrame([{
        'category': 'Median Patron',
        'jurisdiction': median_patron['jurisdiction'],
        'count': len(df_filtered),  # Show total number of patrons represented
        'frequent_location': median_patron['frequent_location'],
        'home_branch': median_patron['home_branch'],
        'nearest_branch_dist': median_patron['nearest_branch_dist'],
        'circ_phy_avg': median_patron['circ_phy_avg'],
        'circ_dig_avg': median_patron['circ_dig_avg']
    }])
    
    tooltip_fields = [
        alt.Tooltip('jurisdiction', title='Jurisdiction'),
        alt.Tooltip('count', title='Patrons Represented'),
        alt.Tooltip('frequent_location', title='Most Common Branch'),
        alt.Tooltip('home_branch', title='Most Common Home'),
        alt.Tooltip('nearest_branch_dist', title='Median Distance (mi)', format='.2f'),
        alt.Tooltip('circ_phy_avg', title='Median Physical Circ/Year', format='.1f'),
        alt.Tooltip('circ_dig_avg', title='Median Digital Circ/Year', format='.1f')
    ]
    
    # Create the chart
    c = alt.Chart(df_grouped).mark_bar().encode(
        x=alt.X('jurisdiction',
                title='Jurisdiction'),
        y=alt.Y('count',
                title='Number of Patrons Represented'),
        color=alt.Color('jurisdiction', 
                       scale=alt.Scale(domain=list(category_colors.keys()), 
                                     range=category_colors_hex),
                       legend=None),
        tooltip=tooltip_fields
    )

    # Update the map data for median patron
    df_latlon = pd.DataFrame([{
        'lat': median_patron['lat'],
        'lon': median_patron['lon'],
        'color': category_colors[median_patron['jurisdiction']],
        'tooltip_value': (
            f"Most Common Branch: {median_patron['frequent_location']}\n"
            f"Home Branch: {median_patron['home_branch']}\n"
            f"Jurisdiction: {median_patron['jurisdiction']}\n"
            f"Distance: {median_patron['nearest_branch_dist']:.2f} mi\n"
            f"Physical Circ/Yr: {median_patron['circ_phy_avg']:.1f}\n"
            f"Digital Circ/Yr: {median_patron['circ_dig_avg']:.1f}"
        ),
        'tooltip_name': 'Median Patron Stats'
    }])

elif aggregate_field == 'nearest_branch_name':
    # For nearest branch view, include both count and average distance
    df_grouped = (df_filtered[[aggregate_field, 'nearest_branch_dist']]
                 .groupby(aggregate_field)
                 .agg({
                     'nearest_branch_dist': 'mean',
                     aggregate_field: 'size'
                 })
                 .rename(columns={aggregate_field: 'count'})
                 .reset_index())
    df_grouped['nearest_branch_dist'] = df_grouped['nearest_branch_dist'].round(2)
    
    tooltip_fields = [
        alt.Tooltip(aggregate_field, title='Branch'),
        alt.Tooltip('count', title='Count'),
        alt.Tooltip('nearest_branch_dist', title='Avg Distance (mi)')
    ]
    chart_title = aggregate_field_options[aggregate_field]
    chart_x_field = aggregate_field

elif aggregate_field == 'circ_dig_ratio':
    # Create manual bins for digital ratio
    bins = [i/20 for i in range(21)]  # Creates [0, 0.05, 0.1, ..., 0.95, 1.0]
    labels = [f"{bins[i]:.2f}-{bins[i+1]:.2f}" for i in range(len(bins)-1)]
    
    df_filtered['ratio_bin'] = pd.cut(df_filtered['circ_dig_ratio'], 
                                    bins=bins,
                                    labels=labels,
                                    include_lowest=True)
    
    df_grouped = (df_filtered.groupby('ratio_bin')
                 .agg({
                     'circ_dig_ratio': 'mean',
                     'ratio_bin': 'size'
                 })
                 .rename(columns={'ratio_bin': 'count'})
                 .reset_index())
    
    tooltip_fields = [
        alt.Tooltip('ratio_bin', title='Digital Ratio Range'),
        alt.Tooltip('count', title='Count'),
        alt.Tooltip('circ_dig_ratio', title='Avg Ratio', format='.2%')
    ]
    
    chart_title = aggregate_field_options[aggregate_field]
    chart_x_field = 'ratio_bin'

else:
    # For other views, just get the count
    df_grouped = df_filtered[[aggregate_field]].groupby(
        by=[aggregate_field], as_index=False).value_counts(sort=True, ascending=False)
    
    tooltip_fields = [
        alt.Tooltip(aggregate_field, title=aggregate_field_options[aggregate_field].replace(' Branch', '')),
        alt.Tooltip('count', title='Count')
    ]


# For digital ratio, use a red-to-blue color scheme
if aggregate_field == 'circ_dig_ratio':
    # Create manual bins for digital ratio
    bins = [i/20 for i in range(21)]  # Creates [0, 0.05, 0.1, ..., 0.95, 1.0]
    # Create percentage labels (e.g., "5%" instead of "0.00-0.05")
    labels = [f"{int(bins[i+1]*100)}%" for i in range(len(bins)-1)]
    
    df_filtered['ratio_bin'] = pd.cut(df_filtered['circ_dig_ratio'], 
                                    bins=bins,
                                    labels=labels,
                                    include_lowest=True)
    
    df_grouped = (df_filtered.groupby('ratio_bin')
                 .agg({
                     'circ_dig_ratio': 'mean',
                     'ratio_bin': 'size'
                 })
                 .rename(columns={'ratio_bin': 'count'})
                 .reset_index())
    
    # Calculate bin centers for coloring (still using original decimal values)
    df_grouped['bin_center'] = [(i+0.5)/20 for i in range(20)]
    
    # Create color mapping
    df_grouped['color'] = df_grouped['bin_center'].apply(
        lambda x: f"rgb({int(255 * (1-x))}, 0, {int(255 * x)})"
    )
    
    # Create the chart with explicit encoding
    c = alt.Chart(df_grouped).mark_bar(
        width=20  # Set bar width
    ).encode(
        x=alt.X('ratio_bin:N',
                title='Digital Use Ratio',
                sort=None),
        y=alt.Y('count:Q',
                title='Number of Patrons'),
        color=alt.Color('color:N',
                       scale=None),  # Use the pre-calculated colors
        tooltip=[
            alt.Tooltip('ratio_bin:N', title='Digital Ratio'),
            alt.Tooltip('count:Q', title='Count'),
            alt.Tooltip('circ_dig_ratio:Q', title='Avg Ratio', format='.1%')
        ]
    ).properties(
        width=alt.Step(20)  # Set step size between bars
    )

elif aggregate_field == 'median_patron':
    # Compute median patron metrics
    median_patron = compute_median_patron(df_filtered)
    
    # Create single-row DataFrame for the bar chart
    df_grouped = pd.DataFrame([{
        'jurisdiction': median_patron['jurisdiction'],
        'count': len(df_filtered),  # Show total number of patrons represented
        'frequent_location': median_patron['frequent_location'],
        'home_branch': median_patron['home_branch'],
        'nearest_branch_dist': median_patron['nearest_branch_dist'],
        'circ_phy_avg': median_patron['circ_phy_avg'],
        'circ_dig_avg': median_patron['circ_dig_avg']
    }])

    tooltip_fields = [
        alt.Tooltip('jurisdiction', title='Jurisdiction'),
        alt.Tooltip('count', title='Patrons Represented'),
        alt.Tooltip('frequent_location', title='Most Common Branch'),
        alt.Tooltip('home_branch', title='Most Common Home'),
        alt.Tooltip('nearest_branch_dist', title='Median Distance (mi)', format='.2f'),
        alt.Tooltip('circ_phy_avg', title='Avg Physical Circ/Year', format='.1f'),
        alt.Tooltip('circ_dig_avg', title='Avg Digital Circ/Year', format='.1f')
    ]

    # Create the chart
    c = alt.Chart(df_grouped).mark_bar().encode(
        x=alt.X('jurisdiction',
                title='Jurisdiction'),
        y=alt.Y('count',
                title='Number of Patrons Represented'),
        color=alt.Color('jurisdiction', 
                       scale=alt.Scale(domain=list(category_colors.keys()), 
                                     range=category_colors_hex),
                       legend=None),
        tooltip=tooltip_fields
    )
    
else:
    # For other views, filter out zero counts
    if aggregate_field == 'nearest_branch_name':
        # Include both count and average distance
        df_grouped = (df_filtered
                     .groupby(aggregate_field)
                     .agg({
                         'nearest_branch_dist': 'mean',
                         aggregate_field: 'size'
                     })
                     .rename(columns={aggregate_field: 'count'})
                     .reset_index())
        df_grouped['nearest_branch_dist'] = df_grouped['nearest_branch_dist'].round(2)
        tooltip_fields = [
            alt.Tooltip(aggregate_field, title='Branch'),
            alt.Tooltip('count', title='Count'),
            alt.Tooltip('nearest_branch_dist', title='Avg Distance (mi)')
        ]
    else:
        # Regular count-only grouping for other fields
        df_grouped = df_filtered[[aggregate_field]].groupby(
            by=[aggregate_field], as_index=False).value_counts(sort=True, ascending=False)
        
        
        tooltip_fields = [
            alt.Tooltip(aggregate_field, title=aggregate_field_options[aggregate_field].replace(' Branch', '')),
            alt.Tooltip('count', title='Count')
        ]
        
    # Filter out any entries with zero counts
    df_grouped = df_grouped[df_grouped['count'] > 0]

    # Additional filtering to omit bars that don't have a color assigned
    valid_categories = set(category_colors.keys())
    df_grouped = df_grouped[df_grouped[aggregate_field].isin(valid_categories)]


    c = alt.Chart(df_grouped).mark_bar().encode(
        x=alt.X(aggregate_field,
                title=aggregate_field_options[aggregate_field],
                sort=alt.SortField(field='count',
                                 order='descending',
                                 ),
                ),
        y=alt.Y('count'),
        color=alt.Color(aggregate_field, 
                       scale=alt.Scale(domain=list(category_colors.keys()), 
                                     range=category_colors_hex,
                                     ),
                       legend=None),
        tooltip=tooltip_fields
    )


with col12:
    # st.write(df_grouped.head(10))
    st.altair_chart(c, use_container_width=True)


# %% set up color column
color_source_col = 'jurisdiction' if aggregate_field == 'median_patron' else aggregate_field
if color_source_col == 'circ_dig_ratio':
    # For digital ratio, create a red-to-blue color scale
    df_filtered['color'] = df_filtered['circ_dig_ratio'].apply(
        lambda x: [255 * (1-x),  # Red component
                  0,            # Green component
                  255 * x,      # Blue component
                  32 if x < 0.05 else 64]  # Alpha - more transparent for low use
    )
    # Add summary stats for digital ratio
    with col11:
        st.caption("Average digital use ratio: {:.1%}".format(
            df_filtered['circ_dig_ratio'].mean()))
else:
    # Additional filtering to omit markers that don't have a color assigned
    valid_categories = set(category_colors.keys())
    if aggregate_field != 'median_patron':
        df_filtered = df_filtered[df_filtered[aggregate_field].isin(valid_categories)]
    
    # Update colors based on selected categorization
    df_filtered['color'] = df_filtered[color_source_col].map(category_colors)
    # Add summary stats for nearest branch when that view is selected
    if color_source_col == 'nearest_branch_name':
        with col11:
            st.caption("Average distance to nearest branch: {:.2f} miles".format(
                df_filtered['nearest_branch_dist'].mean()))


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

# Prepare map data differently for median patron vs other views
if aggregate_field == 'median_patron':
    median_patron = compute_median_patron(df_filtered)
    df_latlon = pd.DataFrame([{
        'lat': median_patron['lat'],
        'lon': median_patron['lon'],
        'color': category_colors[median_patron['jurisdiction']],
        'tooltip_value': (
            f"\nMost Common Branch: {median_patron['frequent_location']}\n"
            f"Home Branch: {median_patron['home_branch']}\n"
            f"Jurisdiction: {median_patron['jurisdiction']}\n"
            f"Distance: {median_patron['nearest_branch_dist']:.2f} mi\n"
            f"Physical Circ/Yr: {median_patron['circ_phy_avg']:.1f}\n"
            f"Digital Circ/Yr: {median_patron['circ_dig_avg']:.1f}"
        ),
        'tooltip_name': 'Median Patron Stats'
    }])
else:
    df_latlon = df_filtered[['lat', 'lon', 'color']].copy()
    df_latlon['tooltip_value'] = df_filtered[color_source_col]
    df_latlon['tooltip_value'].fillna(value="None", inplace=True)
    df_latlon['tooltip_name'] = aggregate_field_options[color_source_col]
    # st.write(df_latlon.head(10))

df_branches['tooltip_name'] = 'Branch'
df_branches['tooltip_value'] = df_branches['name']

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
            height=850,
            ),
        layers=[
            # County boundaries layer
            pdk.Layer(
                type="GeoJsonLayer",
                data=df_counties,
                line_width_min_pixels=1.5,
                pickable=False,
                auto_highlight=True,
                stroked=True,
                filled=False,
                get_line_color=[0, 0, 0, 48],
            ),
            # Patron layer (ScatterplotLayer or HeatmapLayer)
            pdk.Layer(
                # 'ScatterplotLayer',
                # 'HeatmapLayer',
                view_style,
                opacity=1.0 if aggregate_field == 'median_patron' else 0.2,
                data=df,
                get_position=['lon', 'lat'],
                # get_color='[0, 100, 30, 80]',
                get_color='color',
                get_radius=200 if aggregate_field == 'median_patron' else 50,
                radius_min_pixels=8 if aggregate_field == 'median_patron' else 1.5,
                radius_max_pixels=30 if aggregate_field == 'median_patron' else 20,
                pickable=True,
                auto_highlight=True,
                ),
            # Outer dark gray circle for branches
            pdk.Layer(
                "ScatterplotLayer",
                data=df_branches,
                get_position=['lon', 'lat'],
                get_color=[48, 48, 48, 255],  # Dark gray
                get_radius=150,
                radius_min_pixels=6,
                radius_max_pixels=20,
                pickable=True,
                opacity=1.0,
            ),
            # Inner white circle for branches
            pdk.Layer(
                "ScatterplotLayer",
                data=df_branches,
                get_position=['lon', 'lat'],
                get_color=[255, 255, 255, 255],  # White
                get_radius=100,
                radius_min_pixels=2,
                radius_max_pixels=6,
                pickable=True,
                opacity=1.0,
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


# %% Add scatter plot for digital use ratio vs distance
if aggregate_field == 'circ_dig_ratio':
    st.subheader("Digital Use vs Distance Analysis", anchor="digital-distance")
    
    # Get the required columns and filter for distance <= 30 miles
    digital_distance_data = df_filtered[
        ['circ_dig_ratio', 'nearest_branch_dist']
    ].copy()
    digital_distance_data = digital_distance_data[
        (digital_distance_data['nearest_branch_dist'] <= 30) & 
        (digital_distance_data['nearest_branch_dist'].notna()) &
        (digital_distance_data['circ_dig_ratio'].notna())
    ]
    
    # Create color gradient based on digital ratio (same as map coloring)
    digital_distance_data['color'] = digital_distance_data['circ_dig_ratio'].apply(
        lambda x: f"rgb({int(255 * (1-x))}, 0, {int(255 * x)})"
    )
    
    # Base chart with common x and y encodings
    base = alt.Chart(digital_distance_data).encode(
        x=alt.X('nearest_branch_dist:Q',
                title='Distance to Nearest Branch (miles)',
                scale=alt.Scale(domain=[0, 30])),
        y=alt.Y('circ_dig_ratio:Q',
                title='Digital Use Ratio',
                axis=alt.Axis(format='%'))
    )
    
    # Create scatter plot
    scatter = base.mark_circle(
        opacity=0.2,  # More transparent
        size=20,      # Smaller circles
        filled=True   # Filled circles
    ).encode(
        color=alt.Color('color:N', scale=None),  # Use pre-calculated colors
        tooltip=[
            alt.Tooltip('nearest_branch_dist:Q', 
                       title='Distance (miles)',
                       format='.2f'),
            alt.Tooltip('circ_dig_ratio:Q', 
                       title='Digital Ratio',
                       format='.1%')
        ]
    )

    # Add trend line
    trend_line = base.transform_regression(
        'nearest_branch_dist', 'circ_dig_ratio'
    ).mark_line(
        color='#006666',
        strokeWidth=2 
    )

    # Combine trend line and scatter plot
    chart = (trend_line + scatter).properties(
        height=400
    )

    st.altair_chart(chart, use_container_width=True)