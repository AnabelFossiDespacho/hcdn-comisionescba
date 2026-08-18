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
    url = "https://www.hcdn.gob.ar/comisiones/agenda/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        response = requests.get(
            url, headers=headers, timeout=10, verify=False
        )
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
                    url_citacion = (
                        href if href.startswith("http") else f"https://www.hcdn.gob.ar{href}"
                    )

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

# 4. Navegación Lateral
st.sidebar.header("🔍 Navegación")
vista = st.sidebar.radio(
    "Seleccionar vista:",
    [
        "📅 Agenda de la Semana (Cruce)",
        "📊 Gráficos y Estadísticas",
        "📋 Toda la Agenda HCDN (con Temarios)",
        "👥 Nómina de Diputados y Comisiones",
    ],
)

# VISTA 1: Cruce de la Semana con Diseño Visual Mejorado
if vista == "📅 Agenda de la Semana (Cruce)":
    st.subheader("📅 Convocatorias Detectadas esta Semana")

    col_btn, _ = st.columns([1, 4])
    with col_btn:
        if st.button("🔄 Actualizar Agenda"):
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
                
                # Encabezado visual para cada reunión
                st.markdown("---")
                
                # Tarjeta principal del evento
                with st.container():
                    st.markdown(f"### 📌 Convocatoria #{encontrados}")
                    
                    # Dividir la información en 2 columnas: Datos de la reunión | Diputados
                    col_info, col_dips = st.columns([3, 2])

                    with col_info:
                        st.markdown("#### 📋 Detalle Oficial")
                        st.info(reunion_texto)
                        
                        if url_citacion:
                            st.markdown(f"🔗 [**Ver citación oficial en la web de HCDN**]({url_citacion})")

                    with col_dips:
                        st.markdown("#### 👥 Diputados por Córdoba")
                        
                        # Mostrar cada diputado como una tarjeta limpia
                        dips_unicos = { (d['diputado'], d['cargo'], d['comision']) for d in asistentes_detectados }
                        for dip, cargo, com in dips_unicos:
                            badge_color = "🟢" if "Presidente" in cargo or "Vicepresidente" in cargo else "🔵"
                            st.markdown(
                                f"""
                                <div style="background-color: #f0f2f6; padding: 10px; border-radius: 8px; margin-bottom: 8px;">
                                    <b>{badge_color} {dip}</b><br>
                                    <small><b>Cargo:</b> {cargo} | <b>Comisión:</b> {com}</small>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                    # Subsección desplegable para el Temario / Orden del Día
                    if url_citacion:
                        with st.expander("📄 Ver Temario y Orden del Día Completo", expanded=False):
                            with st.spinner("Cargando orden del día..."):
                                detalle = obtener_detalle_citacion(url_citacion)
                                st.markdown(f"```text\n{detalle}\n
