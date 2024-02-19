# -*- coding: utf-8 -*-
"""
Created on Thu May 25 00:56:32 2023

@author: MDP
"""

import streamlit as st


category_colors = {
    'Bookmobile': (227, 119, 194, 128),
    'Central': (214, 39, 40, 128),
    'Charlottesville': (214, 39, 40, 128),
    'Crozet': (255, 127, 14, 128),
    'Gordon': (148, 103, 189, 128),
    'Greene': (44, 160, 44, 128),
    'Louisa': (188, 189, 34, 128),
    'Nelson': (140, 86, 75, 128),
    'Northside': (31, 119, 180, 128),
    'Albemarle': (31, 119, 180, 128),
    'Out of Area': (127, 127, 127, 128),
    'Scottsville': (23, 190, 207, 128)
}


def hex_to_rgb(hex):
  return [int(hex[i:i+2], 16) for i in (0, 2, 4)]

def rgb_to_hex(red, green, blue, alpha):
    """Return color as #rrggbb for the given color values."""
    return '#%02x%02x%02x' % (red, green, blue)


def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct.
        return True
