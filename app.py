import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
import gspread

# Configuración inicial de la página
st.set_page_config(
    page_title="Portal de Auditoría - Mystery Shopping", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Portal de Auditoría - Registro de Mystery")

# 1. VALIDACIÓN DE SEGURIDAD (Evita el KeyError y muestra un mensaje limpio)
if "gcp_service_account" not in st.secrets:
    st.error("❌ No se encontraron las credenciales 'gcp_service_account' en los Secrets de Streamlit Cloud.")
    st.markdown("""
    **Para solucionarlo:**
    1. Ve al dashboard de [Streamlit Cloud](https://share.streamlit.io/).
    2. Busca tu aplicación `Registro-de-Mystery`.
    3. Haz clic en los tres puntos (`⋮`) y selecciona **Settings**.
    4. Ve a la sección **Secrets** y pega el contenido de tu cuenta de servicio de Google Cloud en formato TOML:
    ```toml
    [gcp_service_account]
    type = "service_account"
    project_id = "tu-proyecto"
    private_key_id = "tu-key-id"
    private_key = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"
    client_email = "tu-cuenta-de-servicio@..."
    # ... el resto de campos de tu JSON
    ```
    """)
    st.stop()

# 2. FUNCIÓN PARA CONECTARSE A GOOGLE SHEETS
@st.cache_data(ttl=600)  # Guarda en caché los datos por 10 minutos para optimizar velocidad
def cargar_datos_mystery():
    try:
        # Cargar credenciales desde los Secrets seguros de Streamlit
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict)
        gc = gspread.authorize(creds)
        
        # ID de tu hoja de cálculo obtenido de la URL
        spreadsheet_id = "1_OCxCakgSVU0DRibdT2ZcsgtCK1YDjmDthePt_pr5Xo"
        sh = gc.open_by_key(spreadsheet_id)
        
        # Abrir la pestaña específica solicitada
        worksheet = sh.worksheet("Registro de Mystery")
        
        # Convertir los datos a DataFrame
        filas = worksheet.get_all_values()
        if len(filas) > 0:
            return pd.DataFrame(filas[1:], columns=filas[0])
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Error de conexión con Google Sheets: {e}")
        return pd.DataFrame()

# Carga de la base de datos de Autolux
df_mystery = cargar_datos_mystery()

# 3. RENDERIZADO DEL PORTAL Y FILTROS
if not df_mystery.empty:
    # Limpieza rápida de los datos de porcentaje para facilitar análisis futuros
    if 'Resultado' in df_mystery.columns:
        df_mystery['Resultado_Num'] = df_mystery['Resultado'].str.replace('%', '').str.replace(',', '.').str.strip()
        df_mystery['Resultado_Num'] = pd.to_numeric(df_mystery['Resultado_Num'], errors='coerce')

    # Filtros Dinámicos en la barra lateral
    st.sidebar.header("Filtros de Auditoría")
    
    # Filtro por Sucursal (Salta, Jujuy, Tartagal)
    if 'Sucursal' in df_mystery.columns:
        sucursales = ['Todas'] + sorted([s for s in df_mystery['Sucursal'].unique() if s])
        sucursal_sel = st.sidebar.selectbox("📍 Sucursal", sucursales)
        if sucursal_sel != 'Todas':
            df_mystery = df_mystery[df_mystery['Sucursal'] == sucursal_sel]

    # Filtro por Asesor Comercial
    if 'Asesor Comercial' in df_mystery.columns:
        asesores = ['Todos'] + sorted([a for a in df_mystery['Asesor Comercial'].unique() if a])
        asesor_sel = st.sidebar.selectbox("👤 Asesor Comercial", asesores)
        if asesor_sel != 'Todos':
            df_mystery = df_mystery[df_mystery['Asesor Comercial'] == asesor_sel]

    # Vista Principal del Tablero
    st.subheader("📋 Registros Históricos de Evaluaciones")
    st.dataframe(df_mystery, use_container_width=True)
    
    st.caption("Los datos se actualizan automáticamente cada 10 minutos desde la hoja de cálculo matriz.")
else:
    st.info("Esperando la correcta vinculación de las credenciales para desplegar la base de datos.")
