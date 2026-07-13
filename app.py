import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración principal de la aplicación
st.set_page_config(page_title="Dashboard Mystery Interno - Autolux", layout="wide")
st.title("📊 Registro de Mystery Interno - Autolux")

# Función para cargar los datos desde Google Sheets
@st.cache_data
def cargar_datos(url):
    # Convertir el enlace de Google Sheets a formato CSV para lectura con pandas
    # Es fundamental que el enlace tenga el acceso configurado como "Cualquier persona con el enlace"
    if "/edit" in url:
        csv_url = url.split("/edit")[0] + "/export?format=csv"
    else:
        csv_url = url
        
    try:
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        st.error(f"Error al cargar los datos: Verifica los permisos del enlace. Detalles: {e}")
        return pd.DataFrame()

# Panel lateral para ingresar la URL
st.sidebar.header("Configuración de Datos")
sheet_link = st.sidebar.text_input(
    "Enlace de Google Sheets", 
    placeholder="Pega aquí el enlace de tu hoja de cálculo..."
)

if sheet_link:
    df = cargar_datos(sheet_link)
    
    if not df.empty:
        # Creación de las pestañas
        tab_general, tab_vendedores = st.tabs(["Resumen General", "Vendedores"])
        
        with tab_general:
            st.subheader("Datos Generales de las Evaluaciones")
            st.dataframe(df, use_container_width=True)
            
        with tab_vendedores:
            st.subheader("Rendimiento del Equipo de Ventas")
            
            # Verificamos que las columnas necesarias existan en el DataFrame
            # Ajusta los nombres exactos de tus columnas si difieren un poco
            if 'Vendedor' in df.columns and 'Q2' in df.columns:
                
                # Agrupamos por vendedor evaluando el indicador Q2
                df_vendedores = df.groupby('Vendedor', as_index=False)['Q2'].mean()
                
                # Aplicamos la lógica de colores dependiendo del rango de % porcentaje
                def asignar_color(valor):
                    if valor >= 80:
                        return '#00CC96'  # Verde - Óptimo
                    elif valor >= 50:
                        return '#FFA15A'  # Naranja - Intermedio
                    else:
                        return '#EF553B'  # Rojo - Crítico
                        
                df_vendedores['Color'] = df_vendedores['Q2'].apply(asignar_color)
                
                # Gráfico de columnas en barras para la pestaña de vendedores midiendo Q2
                fig = px.bar(
                    df_vendedores, 
                    x='Vendedor', 
                    y='Q2', 
                    title="Indicador Q2 por Vendedor",
                    labels={'Q2': 'Porcentaje Q2 (%)'},
                    text='Q2'
                )
                
                # Formateo visual: Asignación de los rangos de colores y texto en las barras
                fig.update_traces(
                    marker_color=df_vendedores['Color'], 
                    texttemplate='%{text:.1f}%', 
                    textposition='outside'
                )
                # Ajustamos el rango del eje Y para que siempre se visualice en escala 0-100%
                fig.update_layout(yaxis_range=[0, 110]) 
                
                st.plotly_chart(fig, use_container_width=True)
                
            else:
                st.warning("⚠️ Asegúrate de que la hoja de cálculo contenga las columnas exactamente llamadas 'Vendedor' y 'Q2' para generar el gráfico.")
else:
    st.info("👈 Por favor, pega el enlace de tu hoja de cálculo de Google en el menú lateral para iniciar.")
