# -*- coding: utf-8 -*-
"""Página común de las apps de Lolium: encabezado, barra lateral, clima del repositorio y descarga en Excel.

Reemplaza al motor PREDWEEM (red neuronal y balance hídrico), que las apps ya no ejecutan: la página muestra solo
la alerta de grandes flujos (``visualizacion_alerta_lolmu.mostrar_alerta_lolmu``) con el clima diario del
repositorio (``meteo_daily.csv``, actualizado por el workflow de cada app).
"""
from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import streamlit as st

FONDO_CSS = """<style>
.stApp { background: #f4f6f3; }
[data-testid="stAppViewContainer"] > .main, [data-testid="stMain"] { background: transparent; }
[data-testid="stSidebar"] { background-color: #e8f3ea; border-right: 1px solid #cfe3d3; }
[data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label { color: #14532d !important; }
[data-testid="stCaptionContainer"], .stCaption { color: #4b5563 !important; }
h1, h2, h3, h4 { color: #1f2937; }
header[data-testid="stHeader"] {visibility: hidden;}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>"""


def encabezado(titulo: str, titulo_pestana: str) -> None:
    """Configuración de la página, fondo liso claro y título."""
    try:
        st.set_page_config(page_title=titulo_pestana, layout="wide", page_icon="🌾")
    except Exception:  # noqa: BLE001  (ya configurada en esta ejecución)
        pass
    st.markdown(FONDO_CSS, unsafe_allow_html=True)
    st.title(titulo)


def barra_lateral(base: Path, localidad: str) -> dict:
    """Logo y parámetros del tiempo térmico y de la ventana del graminicida de barbecho."""
    logo = Path(base) / "logo.png"
    if logo.is_file():
        st.sidebar.image(str(logo), width="stretch")
    else:
        st.sidebar.markdown("## 🌾 PREDWEEM")
        st.sidebar.caption(f"Lolium — {localidad}")
    st.sidebar.markdown("## ⚙️ Graminicida de barbecho")
    st.sidebar.caption("Tiempo térmico sobre la temperatura media del aire y ventana del graminicida de barbecho "
                       "(600–800 °Cd: raigrás de 4 a 6 macollos).")
    c1, c2 = st.sidebar.columns(2)
    with c1:
        t_base = st.number_input("T Base", value=2.0, step=0.5)
    with c2:
        t_opt = st.number_input("T Óptima Max", value=20.0, step=1.0)
    t_crit = st.sidebar.slider("T Crítica (Stop)", 26.0, 42.0, 30.0)
    st.sidebar.markdown("**Objetivos (°Cd)**")
    tt_control = st.sidebar.number_input("TT inicio de la ventana (4 macollos, °Cd)", min_value=0, value=600, step=10)
    tt_limite = st.sidebar.number_input("TT fin de la ventana (6 macollos, °Cd)", min_value=0, value=800, step=10)
    return dict(t_base=float(t_base), t_opt=float(t_opt), t_crit=float(t_crit),
                tt_control=float(tt_control), tt_limite=float(tt_limite))


@st.cache_data(ttl=900, show_spinner=False)
def _leer_meteo(ruta: str, modificado: float) -> pd.DataFrame:  # noqa: ARG001  (``modificado`` invalida el caché)
    return pd.read_csv(ruta)


def cargar_meteo(base: Path, url_respaldo: str | None = None) -> pd.DataFrame | None:
    """Clima diario de la campaña (registrado y pronóstico) desde ``meteo_daily.csv`` del repositorio; si falta y
    hay ``url_respaldo``, desde esa dirección."""
    ruta = Path(base) / "meteo_daily.csv"
    try:
        if ruta.is_file():
            return _leer_meteo(str(ruta), ruta.stat().st_mtime)
        if url_respaldo:
            return pd.read_csv(url_respaldo)
    except Exception as e:  # noqa: BLE001
        st.error(f"No se pudo leer el clima: {e}")
        return None
    st.warning("No se encontró `meteo_daily.csv` en el repositorio.")
    return None


def _escribir_hoja(writer, tabla, nombre):
    if not isinstance(tabla, pd.DataFrame) or tabla.empty:
        return
    tabla.to_excel(writer, sheet_name=nombre, index=False)
    hoja = writer.sheets[nombre]
    ult = max(0, len(tabla.columns) - 1)
    hoja.freeze_panes(1, 0)
    hoja.autofilter(0, 0, len(tabla), ult)
    hoja.set_column(0, ult, 18)


def descarga_excel(resultados: dict | None, nombre: str, clave: str) -> None:
    """Botón de descarga con los resultados que muestra la app (hojas de ``mostrar_alerta_lolmu``)."""
    if not isinstance(resultados, dict) or not resultados:
        return
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter", datetime_format="dd/mm/yyyy", date_format="dd/mm/yyyy") as writer:
        for hoja, tabla in resultados.items():
            _escribir_hoja(writer, tabla, hoja)
    emision = resultados["Resumen"].set_index("Indicador")["Valor"].get("Fecha de emisión", "") if "Resumen" in resultados else ""
    st.divider()
    st.subheader("📥 Descarga de resultados")
    st.caption("Excel con los resultados que muestra la app para la fecha de emisión elegida: qué hacer esta semana, nivel y "
               "probabilidad de gran flujo, ventana del graminicida de barbecho (600–800 °Cd), residual a la siembra, "
               "emergencia acumulada esperada, alerta semanal, tiempo térmico, conteos usados, clima, parámetros y validación.")
    st.download_button(label="📊 Descargar resultados en Excel", data=buf.getvalue(),
                       file_name=f"PREDWEEM_Lolium_{nombre}_alerta_{str(emision).replace('/', '-') or 'resultados'}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch", key=clave)
