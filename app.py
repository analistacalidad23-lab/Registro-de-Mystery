import streamlit as st
import pandas as pd

# 1. Configuración básica de la página
st.set_page_config(page_title="Tablero de Calidad Comercial", layout="wide")
st.title("Tablero de Indicadores de Calidad - Área Comercial")

# 2. URL de Google Sheets adaptada para descarga en formato CSV
SHEET_ID = "1PGoOlFTN2WuuiEqRk0KPrcLZL6pEcFVeNWo35shsUSA"
# Si tu documento tiene varias pestañas, por defecto traerá la primera. 
# Luego te muestro cómo traer otras si lo necesitas.
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# 3. Función para leer los datos
# Usamos cache_data para que Streamlit no descargue el archivo cada vez que haces un clic,
# el "ttl=600" hace que los datos se refresquen cada 10 minutos (600 segundos).
@st.cache_data(ttl=600)
def cargar_datos():
    try:
        # Leemos el CSV directamente desde la URL
        df = pd.read_csv(URL)
        return df
    except Exception as e:
        st.error(f"Se produjo un error al intentar conectar con la base de datos: {e}")
        return None

# 4. Ejecución y visualización
with st.spinner('Conectando a la base de datos...'):
    df = cargar_datos()

if df is not None:
    st.success("¡Conexión exitosa! Base de datos cargada correctamente.")
    
    st.subheader("Vista previa de los datos")
    # Mostramos las primeras 10 filas para verificar que las columnas y datos están bien
    st.dataframe(df.head(10)) 
    
    # st.write(df.shape) # Opcional: Para ver (filas, columnas) totales
