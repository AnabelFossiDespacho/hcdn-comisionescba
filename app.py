import base64
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

# Función para convertir la imagen local cargada a fondo atenuado
def aplicar_fondo_local():
    archivos = ["congreso.jpg", "congreso.jpeg", "congreso.png"]
    imagen_encontrada = next((f for f in archivos if os.path.exists(f)), None)
    
    if imagen_encontrada:
        with open(imagen_encontrada, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
        
        st.markdown(
            f"""
            <style>
            .stApp {{
                background: linear-gradient(rgba(255, 255, 255, 0.88), rgba(255, 255, 255, 0.88)), 
                            url("data:image/jpg;base64,{encoded_string}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )

# Aplicar el fondo
aplicar_fondo_local()

st.title("🏛️ CONGRESO - COMISIONES DIPUTADOS CÓRDOBA - PROVINCIAS UNIDAS")
st.markdown(
    "Cruce automático entre la **Agenda Parlamentaria de la HCDN** y la nómina oficial de diputados."
)
