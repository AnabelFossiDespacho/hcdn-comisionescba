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

# 2. Extraer detalle del temario desde la citación
@st.cache_data(ttl=1800)
def obtener_detalle_citacion(url_citacion):
    if not url_citacion:
        return "No hay enlace de citación disponible."

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        res = requests.get(url_citacion, headers=headers, timeout=10, verify=False)
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
    url = "https://www.hcdn.gob.ar/comisiones/agenda/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        soup = BeautifulSoup(response.text, "html.parser")

        eventos = []
        bloques = soup.find_all(["tr", "div", "li"])

        for b in bloques:
            texto = b.get_text(separator=" | ", strip=True)

            if len(texto) > 25 and any(
                k in texto.upper()
                for k in ["COMISIÓN", "REUNIÓN", "INVITADOS", "INFORMATIVA", "CONJUNTA"]
            ):
                link_tag = b.find(
                    "a", string=lambda s: s and "citación" in s.lower()
                ) or b.find(
                    "a", href=lambda h: h and "citacion" in h.lower()
                )

                url_citacion = None
                if link_tag and link_tag.has_attr("href"):
                    href = link_tag["href"]
                    url_citacion = href if href.startswith("http") else f"https://www.hcdn.gob.ar{href}"

                eventos.append({"texto": texto, "citacion": url_citacion})

        vistos = set()
        eventos_unicos = []
        for ev in eventos:
            if ev["texto"] not in vistos:
                vistos.add(ev["texto"])
                eventos_unicos.append(ev)

        return eventos_unicos

    except Exception as e:
        st.warning(f"Error al conectar con la HCDN: {e}")
        return []

reuniones_semana = obtener_agenda_hcdn()

# --- ENCABEZADO E INTRODUCCIÓN GENERAL ---
st.title("🏛️ Monitor Parlamentario HCDN - Delegación Córdoba")
st.markdown(
    """
    Bienvenido/a al **Panel Control de Comisiones**. Este sistema realiza un cruce automático y en tiempo real 
    entre la **Agenda Oficial de la Cámara de Diputados de la Nación (HCDN)** y la nómina de **Diputados Nacionales por la Provincia de Córdoba**.
    """
)

# PESTAÑAS PRINCIPALES DEL PANEL
tab_panel, tab_agenda_completa, tab_nomina = st.tabs([
    "📊 Panel Principal (Resumen, Agenda y Gráficos)",
    "📋 Agenda HCDN Completa",
    "👥 Nómina de Diputados"
])

# ==========================================
# PESTAÑA 1: PANEL INTEGRAL (TODO EN UNO)
# ==========================================
with tab_panel:
    # 1. Tarjetas de Métricas de Presentación
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Diputados Monitoreados", df_diputados["Diputado/a"].nunique())
    m2.metric("Comisiones Cubiertas", df_diputados["Comisión"].nunique())
    m3.metric("Convocatorias Detectadas", len(reuniones_semana))
    
    # Calcular reuniones que afectan a Córdoba
    afectados_cnt = 0
    if reuniones_semana:
        for r in reuniones_semana:
            if any(row["Comisión"].lower() in r["texto"].lower() for _, row in df_diputados.iterrows()):
                afectados_cnt += 1
    m4.metric("Reuniones con Cba Involucrada", afectados_cnt)

    st.divider()

    # 2. Agenda con Cruce de Diputados
    col_ag, col_gf = st.columns([3, 2])

    with col_ag:
        st.subheader("📅 Convocatorias de la Semana (Cruce Córdoba)")
        if st.button("🔄 Actualizar Datos en Vivo"):
            st.cache_data.clear()
            st.rerun()

        if reuniones_semana:
            encontrados = 0
            for idx, item in enumerate(reuniones_semana):
                reunion_texto = item["texto"]
                url_citacion = item["citacion"]
                asistentes_detectados = []

                for _, row in df_diputados.iterrows():
                    comision = row["Comisión"]
                    diputado = row["Diputado/a"]
                    cargo = row["Cargo que ocupa"]

                    if comision.lower() in reunion_texto.lower():
                        asistentes_detectados.append({
                            "diputado": diputado,
                            "cargo": cargo,
                            "comision": comision
                        })

                if asistentes_detectados:
                    encontrados += 1
                    with st.expander(f"📌 Convocatoria #{encontrados}: {reunion_texto[:60]}...", expanded=True):
                        st.write("**Detalle:**")
                        st.info(reunion_texto)
                        
                        st.write("**Diputados Afectados:**")
                        dips_unicos = { (d['diputado'], d['cargo'], d['comision']) for d in asistentes_detectados }
                        for dip, cargo, com in dips_unicos:
                            badge_color = "🟢" if "Presidente" in cargo or "Vicepresidente" in cargo else "🔵"
                            st.markdown(f"**{badge_color} {dip}** (*{cargo}* - {com})")

                        if url_citacion:
                            st.divider()
                            st.markdown(f"🔗 [Ver Citación en HCDN]({url_citacion})")
                            with st.popover("📄 Leer Temario / Orden del Día"):
                                detalle = obtener_detalle_citacion(url_citacion)
                                st.text(detalle)

            if encontrados == 0:
                st.info("No hay reuniones programadas esta semana para las comisiones de los diputados por Córdoba.")
        else:
            st.info("No hay agenda disponible en este momento.")

    with col_gf:
        st.subheader("📊 Estadísticas Rápida")
        
        st.write("**Comisiones por Diputado/a:**")
        conteo_diputados = df_diputados["Diputado/a"].value_counts().reset_index()
        conteo_diputados.columns = ["Diputado/a", "Comisiones"]
        st.bar_chart(conteo_diputados.set_index("Diputado/a"), height=250)

        st.write("**Top Comisiones con Presencia de Cba:**")
        conteo_comisiones = df_diputados["Comisión"].value_counts().reset_index()
        conteo_comisiones.columns = ["Comisión", "Cant. Diputados"]
        st.dataframe(conteo_comisiones.head(7), use_container_width=True, hide_index=True, height=220)

# ==========================================
# PESTAÑA 2: AGENDA HCDN COMPLETA
# ==========================================
with tab_agenda_completa:
    st.subheader("📋 Agenda General Publicada por la HCDN")
    if reuniones_semana:
        for idx, item in enumerate(reuniones_semana):
            with st.expander(f"Evento #{idx+1}: {item['texto'][:90]}..."):
                st.write(item["texto"])
                if item["citacion"]:
                    st.markdown(f"🔗 [Ver Citación Oficial]({item['citacion']})")
                    detalle = obtener_detalle_citacion(item["citacion"])
                    st.text(detalle)
    else:
        st.info("No se pudo obtener la agenda general.")

# ==========================================
# PESTAÑA 3: NÓMINA DE DIPUTADOS
# ==========================================
with tab_nomina:
    st.subheader("👥 Integración de Comisiones y Diputados por Córdoba")
    diputado_sel = st.selectbox(
        "Filtrar por Diputado/a:",
        ["Todos"] + list(df_diputados["Diputado/a"].unique()),
    )

    if diputado_sel != "Todos":
        df_filtrado = df_diputados[df_diputados["Diputado/a"] == diputado_sel]
    else:
        df_filtrado = df_diputados

    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
