import pandas as pd
import requests
import urllib3
from bs4 import BeautifulSoup
import streamlit as st

# Desactivar advertencias SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(
    page_title="Dashboard HCDN - Diputados por Córdoba",
    page_icon="🏛️",
    layout="wide",
)

st.title("🏛️ Monitor de Comisiones HCDN - Delegación Córdoba")
st.markdown(
    "Cruce automático entre la **Agenda Parlamentaria de la HCDN** y la nómina oficial de diputados."
)


# 1. Cargar base de datos desde Excel
@st.cache_data
def cargar_datos_excel():
    archivo = "Comisiones DIP CORDOBA.xlsx"
    df = pd.read_excel(archivo)
    df["Diputado/a"] = df["Diputado/a"].astype(str).str.strip()
    df["Comisión"] = df["Comisión"].astype(str).str.strip()
    df["Cargo que ocupa"] = df["Cargo que ocupa"].astype(str).str.strip()
    return df


try:
    df_diputados = cargar_datos_excel()
except Exception as e:
    st.error(f"Error al cargar el archivo Excel: {e}")
    st.stop()


# 2. Extraer detalle del temario desde el link de citación
@st.cache_data(ttl=1800)
def obtener_detalle_citacion(url_citacion):
    if not url_citacion:
        return "No hay enlace de citación disponible."

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        res = requests.get(
            url_citacion, headers=headers, timeout=10, verify=False
        )
        soup = BeautifulSoup(res.text, "html.parser")

        contenido = soup.find(
            "div",
            class_=lambda c: c and ("contenido" in str(c) or "temario" in str(c)),
        ) or soup.find("article") or soup.find("main")

        if contenido:
            texto = contenido.get_text(separator="\n", strip=True)
            if len(texto) > 30:
                return texto

        parrafos = []
        for p in soup.find_all("p"):
            p_texto = p.get_text(strip=True)
            if len(p_texto) > 20:
                parrafos.append(p_texto)

        return "\n\n".join(parrafos) if parrafos else "Sin detalle disponible en formato HTML."

    except Exception as e:
        return f"Error al consultar el detalle: {e}"


# 3. Obtener agenda oficial HCDN
@st.cache_data(ttl=300)
def obtener_agenda_hcdn():
    url = "[https://www.hcdn.gob.ar/comisiones/agenda/](https://www.hcdn.gob.ar/comisiones/agenda/)"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(
            url, headers=headers, timeout=10, verify=
