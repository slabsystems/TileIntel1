import streamlit as st, sys, platform

st.title("TileIntel smoketest")
st.write("Python:", sys.version)
st.write("Platform:", platform.platform())
st.write("It works if you can see this.")
