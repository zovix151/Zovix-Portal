import streamlit as st
from workspace_ui import render_workspace_header

K = "studio_change_mode_btn"
render_workspace_header(K, "AI CREATIVE STUDIO")
st.markdown(f"""
<style>
[data-testid="stMain"]:has(.st-key-{K}) [data-testid="stButton"] > button {{
  box-sizing:border-box !important; width:100% !important; min-height:44px !important; text-transform:uppercase !important;
  padding:9px 12px !important; border-radius:11px !important; white-space:normal !important;
}}
@media (max-width:768px) {{
  [data-testid="stMain"] .block-container [data-testid="stHorizontalBlock"] {{flex-wrap:wrap !important;}}
  [data-testid="stMain"] .block-container [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{flex:1 1 calc(100% - 10px) !important;width:100% !important;}}
  [data-testid="stMain"]:has(.st-key-{K}) [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{width:100% !important;max-width:100% !important;}}
}}
</style>
""", unsafe_allow_html=True)
st.write("content")
