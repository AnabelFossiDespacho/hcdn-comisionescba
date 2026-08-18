import os
import pandas as pd
import requests
import urllib3
from bs4 import BeautifulSoup
import streamlit as st

# Desactivar advertencias SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(
    page_title="CONGRESO - COMISIONES DIPUTADOS CÓRDOBA - PROVINCIAS UNIDAS",
    page_icon="🏛️",
    layout="wide",
)

# Buscar la imagen local en varios formatos estándar
archivos_imagen = ["congreso.jpg", "congreso.jpeg", "congreso.png"]
imagen_encontrada = None

for archivo in archivos_imagen:
    if os.path.exists(archivo):
        imagen_encontrada = archivo
        break

if imagen_encontrada:
    st.image(imagen_encontrada, use_container_width=True)

st.title("🏛️ CONGRESO - COMISIONES DIPUTADOS CÓRDOBA - PROVINCIAS UNIDAS")
st.markdown(
    "Cruce automático entre la **Agenda Parlamentaria de la HCDN** y la nómina oficial de diputados."
)
