import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 1. Configuración de la página del Dashboard
st.set_page_config(
    page_title="Dashboard Calidad y Ventas - Autolux",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main-title { font-size: 28px; font-weight: bold; color: #1E3A8A; margin-bottom: 5px; }
    .subtitle { font-size: 14px; color: #555555; margin-bottom: 25px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🎯 Tablero de Gestión: SSI, NPS y Subíndices - VENTAS</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Seguimiento de Satisfacción, Lealtad del Cliente y Evolución Mensual</div>', unsafe_allow_html=True)

# 2. Conexión de Datos a la hoja "VENTAS26"
SHEET_ID = "1PGoOlFTN2WuuiEqRk0KPrcLZL6pEcFVeNWo35shsUSA"
SHEET_NAME = "VENTAS26"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

@st.cache_data(ttl=600)
def cargar_datos(url):
    try:
        df = pd.read_csv(url)
        df.columns = [str(col).strip() for col in df.columns]
        return df
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        return pd.DataFrame()

df_raw = cargar_datos(CSV_URL)

if not df_raw.empty:
    columnas_disponibles = df_raw.columns.tolist()
    
    # 3. Detección Inteligente de Columnas
    st.sidebar.header("⚙️ Configuración de Columnas")
    
    col_nps = columnas_disponibles[-1]
    col_vend_detectada = next((c for c in columnas_disponibles if 'vendedor' in c.lower() or 'asesor' in c.lower()), columnas_disponibles[0])
    col_vendedor = st.sidebar.selectbox("Columna Vendedor:", columnas_disponibles, index=columnas_disponibles.index(col_vend_detectada))
    
    col_ssi_detectada = next((c for c in columnas_disponibles if 'ssi' in c.lower()), columnas_disponibles[0])
    col_ssi = st.sidebar.selectbox("Columna SSI:", columnas_disponibles, index=columnas_disponibles.index(col_ssi_detectada))
    
    col_fecha_detectada = next((c for c in columnas_disponibles if 'fecha' in c.lower() or 'mes' in c.lower() or 'periodo' in c.lower()), columnas_disponibles[0])
    col_fecha = st.sidebar.selectbox("Columna Fecha:", columnas_disponibles, index=columnas_disponibles.index(col_fecha_detectada))

    col_sucursal_detectada = next((c for c in columnas_disponibles if 'boca' in c.lower() or 'sucursal' in c.lower() or 'concesionario' in c.lower()), columnas_disponibles[0])
    col_sucursal = st.sidebar.selectbox("Columna Boca de Venta:", columnas_disponibles, index=columnas_disponibles.index(col_sucursal_detectada))

    df_procesado = df_raw.copy()
    
    # Preparar Fechas (Meses y Años)
    try:
        df_procesado['Fecha_DT'] = pd.to_datetime(df_procesado[col_fecha], errors='coerce')
        df_procesado['Mes_Nombre'] = df_procesado['Fecha_DT'].dt.strftime('%B').str.lower()
        df_procesado['Mes_Num'] = df_procesado['Fecha_DT'].dt.month
        df_procesado['Año'] = df_procesado['Fecha_DT'].dt.year.fillna(0).astype(int).astype(str)
    except:
        df_procesado['Mes_Nombre'] = df_procesado[col_fecha].astype(str)
        df_procesado['Mes_Num'] = 1
        df_procesado['Año'] = "N/D"

    # Funciones de cálculo
    def calcular_nps(serie):
        if len(serie.dropna()) == 0: return np.nan
        serie_num = pd.to_numeric(serie, errors='coerce')
        if serie_num.notna().sum() > 0:
            promotores = (serie_num >= 9).sum()
            detractores = (serie_num <= 6).sum()
            return (promotores - detractores) / serie_num.notna().sum() * 100.0
        else:
            s_str = serie.astype(str).str.lower()
            promotores = s_str.str.contains('promotor').sum()
            detractores = s_str.str.contains('detractor').sum()
            total = len(s_str.replace(['nan', 'none', ''], pd.NA).dropna())
            if total == 0: return np.nan
            return (promotores - detractores) / total * 100.0

    # Limpieza de columnas numéricas (SSI y Subíndices)
    df_procesado['SSI_Num'] = pd.to_numeric(df_procesado[col_ssi].astype(str).str.replace(',', '.').str.replace('%', ''), errors='coerce')
    
    # Identificar columnas de subíndices (01, 02, etc.)
    cols_subindices = [c for c in columnas_disponibles if any(x in c for x in ['
