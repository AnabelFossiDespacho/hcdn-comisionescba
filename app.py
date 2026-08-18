import pandas as pd
import requests
from bs4 import BeautifulSoup
import streamlit as st

st.set_page_config(
    page_title="Dashboard HCDN - Diputados por Córdoba",
    page_icon="🏛️",
    layout="wide",
)

st.title("🏛️ Monitor de Comisiones HCDN - Delegación Córdoba")
st.markdown(
    "Cruce automático entre la **Agenda Parlamentaria de la HCDN** y la nómina oficial de diputados."
)


# 1. Cargar base de datos local desde el archivo Excel
@st.cache_data
def cargar_datos_excel():
    archivo = "Comisiones DIP CÓRDOBA.xlsx"
    df = pd.read_excel(archivo)
    # Limpieza básica de espacios
    df["Diputado/a"] = df["Diputado/a"].str.strip()
    df["Comisión"] = df["Comisión"].str.strip()
    df["Cargo que ocupa"] = df["Cargo que ocupa"].str.strip()
    return df


try:
    df_diputados = cargar_datos_excel()
except Exception as e:
    st.error(f"Error al cargar el archivo Excel: {e}")
    st.stop()


# 2. Función para raspar la agenda oficial de la HCDN
@st.cache_data(ttl=1800)  # Se actualiza cada 30 minutos
def obtener_agenda_hcdn():
    url = "https://www.hcdn.gob.ar/comisiones/agenda/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        reuniones = []
        # Extrae las filas o bloques de la agenda
        for fila in soup.find_all("tr"):
            texto = fila.get_text(separator=" | ", strip=True)
            if len(texto) > 15 and "Comisión" in texto:
                reuniones.append(texto)

        return reuniones
    except Exception as e:
        st.warning(f"No se pudo consultar la web de la HCDN: {e}")
        return []


reuniones_semana = obtener_agenda_hcdn()

# 3. Menú Lateral (Filtros y Navegación)
st.sidebar.header("🔍 Navegación")
vista = st.sidebar.radio(
    "Seleccionar vista:",
    ["📅 Agenda de la Semana (Cruce)", "👥 Nómina de Diputados y Comisiones"],
)

# VISTA 1: Cruce de Agenda de la Semana
if vista == "📅 Agenda de la Semana (Cruce)":
    st.subheader("📅 Convocatorias de la Semana")

    if st.button("🔄 Actualizar Agenda"):
        st.cache_data.clear()
        st.rerun()

    if reuniones_semana:
        encontrados = 0

        for reunion in reuniones_semana:
            # Buscar qué diputados de la lista tienen comisiones en esta reunión
            asistentes_detectados = []

            for _, row in df_diputados.iterrows():
                comision_nombre = row["Comisión"]
                # Coincidencia flexible de texto
                if comision_nombre.lower() in reunion.lower():
                    asistentes_detectados.append(
                        f"• **{row['Diputado/a']}** - *{row['Cargo que ocupa']}* en la comisión de {comision_nombre}"
                    )

            if asistentes_detectados:
                encontrados += 1
                with st.expander(
                    f"📌 Convocatoria detectada: {reunion[:90]}...",
                    expanded=True,
                ):
                    st.write("**Detalle publicado por HCDN:**")
                    st.info(reunion)
                    st.write("**Diputados por Córdoba que integran el espacio:**")
                    for a in set(asistentes_detectados):
                        st.markdown(a)

        if encontrados == 0:
            st.info(
                "No se detectaron convocatorias esta semana para las comisiones integradas por tu nómina de diputados."
            )
    else:
        st.info(
            "No hay reuniones publicadas en la agenda oficial o el sitio no devolvió convocatorias activas."
        )

# VISTA 2: Nómina Completa
else:
    st.subheader("👥 Integración de Comisiones")

    # Filtro por Diputado
    diputado_sel = st.selectbox(
        "Filtrar por Diputado/a:", ["Todos"] + list(df_diputados["Diputado/a"].unique())
    )

    if diputado_sel != "Todos":
        df_filtrado = df_diputados[df_diputados["Diputado/a"] == diputado_sel]
    else:
        df_filtrado = df_diputados

    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
