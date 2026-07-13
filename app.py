import streamlit as st
from google.oauth2.service_account import Credentials
import gspread

# Configuración de conexión (usando los secrets de Streamlit Cloud)
def get_data():
    creds_dict = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_dict)
    gc = gspread.authorize(creds)
    
    # Abrir el documento y la hoja específica
    sh = gc.open_by_key("1_OCxCakgSVU0DRibdT2ZcsgtCK1YDjmDthePt_pr5Xo")
    worksheet = sh.worksheet("Registro de Mystery")
    
    return worksheet.get_all_values()

# Carga de datos
data = get_data()
# Convertir a DataFrame de Pandas para análisis
import pandas as pd
df = pd.DataFrame(data[1:], columns=data[0])

st.write("Portal de Auditoría - Registro de Mystery")
st.dataframe(df)
