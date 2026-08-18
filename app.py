import pandas as pd
import requests
import urllib3
from bs4 import BeautifulSoup
import streamlit as st

# Desactivar advertencias SSL de la web de la HCDN
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


# 1. Cargar base de datos local desde Excel
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


# 2. Función para extraer el detalle del temario desde el link de la citación
@st.cache_data(ttl=1800)
def obtener_detalle_citacion(url_citacion):
    if not url_citacion:
        return "No hay link de citación disponible."

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        res = requests.get(
            url_citacion, headers=headers, timeout=10, verify=False
        )
        soup = BeautifulSoup(res.text, "html.parser")

        # Buscar el bloque principal del temario
        contenido = soup.find(
            "div",
            class_=lambda c: c and ("contenido" in str(c) or "temario" in str(c)),
        ) or soup.find("article") or soup.find("main")

        if contenido:
            texto = contenido.get_text(separator="\n", strip=True)
            if len(texto) > 30:
                return texto
        
        # Respaldo: obtener párrafos estructurados
        parrafos = []
        for p in soup.find_all("p"):
            p_texto = p.get_text(strip=True)
            if len(p_texto) > 20:
                parrafos.append(p_texto)

        return "\n\n".join(parrafos) if parrafos else "Detalle de citación no disponible directamente en HTML (posible PDF adjunto)."

    except Exception as e:
        return f"Error al consultar el detalle de la citación: {e}"


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
                # Extraer URL de 'Ver citación'
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

        # Eliminar duplicados
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
        "📋 Toda la Agenda HCDN (con Temarios)",
        "👥 Nómina de Diputados y Comisiones",
    ],
)

# VISTA 1: Cruce de la Semana con Diputados por Córdoba
if vista == "📅 Agenda de la Semana (Cruce)":
    st.subheader("📅 Convocatorias Detectadas esta Semana")

    if st.button("🔄 Actualizar Agenda"):
        st.cache_data.clear()
        st.rerun()

    if reuniones_semana:
        encontrados = 0

        for item in reuniones_semana:
            reunion_texto = item["texto"]
            url_citacion = item["citacion"]
            asistentes_detectados = []

            for _, row in df_diputados.iterrows():
                comision = row["Comisión"]
                diputado = row["Diputado/a"]
                cargo = row["Cargo que ocupa"]

                if comision.lower() in reunion_texto.lower():
                    asistentes_detectados.append(
                        f"• **{diputado}** - *{cargo}* (Comisión: {comision})"
                    )

            if asistentes_detectados:
                encontrados += 1
                with st.expander(
                    f"📌 Convocatoria: {reunion_texto[:80]}...", expanded=True
                ):
                    st.write("**Resumen de la convocatoria:**")
                    st.info(reunion_texto)

                    st.write("**Diputados por Córdoba involucrados:**")
                    for a in set(asistentes_detectados):
                        st.markdown(a)

                    st.divider()

                    # Mostrar TEMARIO COMPLETO
                    if url_citacion:
                        st.subheader("📄 Temario y Orden del Día (Citación Oficial)")
                        with st.spinner("Cargando temario detallado de la HCDN..."):
                            detalle = obtener_detalle_citacion(url_citacion)
                            st.text_area(
                                "Detalle extraído:",
                                value=detalle,
                                height=200,
                                key=f"txt_{encontrados}",
                            )
                        st.markdown(
                            f"🔗 [Abrir documento en web HCDN]({url_citacion})"
                        )
                    else:
                        st.caption("Esta convocatoria no incluye enlace directo a citación.")

        if encontrados == 0:
            st.info(
                "No se detectaron reuniones para las comisiones asignadas a tus diputados esta semana."
            )
            st.markdown(
                "👉 *Consulta la pestaña **'📋 Toda la Agenda HCDN'** para revisar el listado completo con temarios.*"
            )
    else:
        st.info("No hay reuniones cargadas actualmente.")

# VISTA 2: Toda la agenda publicada con sus temarios
elif vista == "📋 Toda la Agenda HCDN (con Temarios)":
    st.subheader("📋 Convocatorias Oficiales y Temarios HCDN")

    if reuniones_semana:
        for idx, item in enumerate(reuniones_semana):
            with st.expander(f"Evento #{idx+1}: {item['texto'][:90]}..."):
                st.write("**Información General:**")
                st.write(item["texto"])

                if item["citacion"]:
                    st.markdown("**Temario de la Citación:**")
                    detalle = obtener_detalle_citacion(item["citacion"])
                    st.info(detalle)
                    st.markdown(f"🔗 [Ver Citación en Web HCDN]({item['citacion']})")
                else:
                    st.caption("Sin citación adjunta.")
    else:
        st.info("No se pudo obtener la agenda general.")

# VISTA 3: Nómina Completa
else:
    st.subheader("👥 Integración de Comisiones")
    diputado_sel = st.selectbox(
        "Filtrar por Diputado/a:",
        ["Todos"] + list(df_diputados["Diputado/a"].unique()),
    )

    if diputado_sel != "Todos":
        df_filtrado = df_diputados[df_diputados["Diputado/a"] == diputado_sel]
    else:
        df_filtrado = df_diputados

    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
