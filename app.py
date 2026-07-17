import streamlit as st
import pandas as pd

st.set_page_config(page_title="Tablero de Calidad Comercial", layout="wide")
st.title("Tablero de Indicadores de Calidad - Área Comercial")

# 1. Configuración y carga de datos
SHEET_ID = "1PGoOlFTN2WuuiEqRk0KPrcLZL6pEcFVeNWo35shsUSA"
# Cambiamos a formato xlsx para poder especificar la pestaña
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

@st.cache_data(ttl=600)
def cargar_datos():
    try:
        # Leemos la pestaña específica "VENTAS26"
        df = pd.read_excel(URL, sheet_name="VENTAS26")
        
        # Aseguramos que la columna de fecha sea de tipo datetime
        # (Ajusta 'Fecha de encuesta' si en tu Excel tiene un nombre ligeramente distinto)
        df['Fecha de encuesta'] = pd.to_datetime(df['Fecha de encuesta'], errors='coerce')
        
        # Creamos una columna para agrupar por mes y año (Ej: '2026-01')
        df['Mes_Año'] = df['Fecha de encuesta'].dt.to_period('M').astype(str)
        return df
    except Exception as e:
        st.error(f"Error al cargar los datos: {e}")
        return pd.DataFrame()

df = cargar_datos()

if not df.empty:
    # --- IDENTIFICACIÓN DE COLUMNAS ---
    # Asumimos los nombres según tu instrucción. 
    # Tomamos la última columna dinámicamente para el NPS.
    col_nps = df.columns[-1] 
    
    # --- BARRA LATERAL: FILTROS ---
    st.sidebar.header("Filtros")
    
    # Filtro de Sucursal
    sucursales = df['Sucursal'].dropna().unique().tolist()
    sucursal_seleccionada = st.sidebar.multiselect("Seleccionar Sucursal", sucursales, default=sucursales)
    
    # Filtro de Mes
    meses = sorted(df['Mes_Año'].dropna().unique().tolist())
    mes_seleccionado = st.sidebar.multiselect("Seleccionar Mes", meses, default=meses)
    
    # Aplicar filtros al dataframe
    df_filtrado = df[
        (df['Sucursal'].isin(sucursal_seleccionada)) & 
        (df['Mes_Año'].isin(mes_seleccionado))
    ]
    
    st.divider()

    # --- KPIs PRINCIPALES ---
    st.subheader("Rendimiento Global vs Objetivos")
    
    # Cálculos promedios globales de la selección
    nps_promedio = df_filtrado[col_nps].mean() if not df_filtrado.empty else 0
    ssi_promedio = df_filtrado['SSI'].mean() if not df_filtrado.empty else 0
    
    # Objetivos
    obj_nps = 87.0
    obj_ssi = 95.6
    
    col1, col2 = st.columns(2)
    
    with col1:
        # st.metric colorea automáticamente positivo en verde y negativo en rojo
        st.metric(label="NPS Acumulado", 
                  value=f"{nps_promedio:.1f}%", 
                  delta=f"{nps_promedio - obj_nps:.1f}% (Obj: {obj_nps}%)")
        
    with col2:
        st.metric(label="SSI Acumulado", 
                  value=f"{ssi_promedio:.1f}", 
                  delta=f"{ssi_promedio - obj_ssi:.1f} (Obj: {obj_ssi})")
        
    st.divider()

    # --- TABLA Y GRÁFICO HISTÓRICO ---
    st.subheader("Evolución Mensual de Indicadores")
    
    # Agrupamos por mes para calcular promedios y conteos
    if not df_filtrado.empty:
        df_agrupado = df_filtrado.groupby('Mes_Año').agg(
            Q_encuestas=('Fecha de encuesta', 'count'),
            SSI_Promedio=('SSI', 'mean'),
            NPS_Promedio=(col_nps, 'mean'),
            Instalaciones=('01 - Instalaciones', 'mean'),
            Atencion_Vendedor=('02 - Atencion Vendedor', 'mean'),
            Atencion_Administracion=('03 - Atencion Administracion', 'mean'),
            Fecha_Entrega=('04 - Fecha de Entrega', 'mean'),
            Momento_Entrega=('05 - Momento de Entrega', 'mean')
        ).reset_index()

        # Separamos el área en dos columnas para el gráfico y la tabla
        tab1, tab2 = st.tabs(["Tabla de Datos", "Gráfico Histórico"])
        
        with tab1:
            # Función para aplicar colores condicionales dependiendo del rango de porcentaje
            def colorear_porcentaje(valor):
                if isinstance(valor, (int, float)):
                    if valor >= 90:
                        return 'color: #155724; background-color: #d4edda' # Verde
                    elif valor >= 80:
                        return 'color: #856404; background-color: #fff3cd' # Amarillo
                    else:
                        return 'color: #721c24; background-color: #f8d7da' # Rojo
                return ''
            
            # Aplicamos el estilo a todas las columnas numéricas excepto la cantidad de encuestas
            columnas_formatear = ['SSI_Promedio', 'NPS_Promedio', 'Instalaciones', 
                                  'Atencion_Vendedor', 'Atencion_Administracion', 
                                  'Fecha_Entrega', 'Momento_Entrega']
            
            st.dataframe(
                df_agrupado.style.format({col: "{:.1f}" for col in columnas_formatear})
                                 .map(colorear_porcentaje, subset=columnas_formatear),
                use_container_width=True
            )
            
        with tab2:
            # Preparamos el gráfico de líneas con NPS y SSI
            df_grafico = df_agrupado.set_index('Mes_Año')[['SSI_Promedio', 'NPS_Promedio']]
            st.line_chart(df_grafico, use_container_width=True)
            
    else:
        st.warning("No hay datos disponibles para los filtros seleccionados.")
