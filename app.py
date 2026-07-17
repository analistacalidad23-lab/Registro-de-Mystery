import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Tablero de Calidad Comercial", layout="wide")
st.title("Tablero de Indicadores de Calidad - Área Comercial")

# 1. Configuración y carga de datos
SHEET_ID = "1PGoOlFTN2WuuiEqRk0KPrcLZL6pEcFVeNWo35shsUSA"
URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

@st.cache_data(ttl=600)
def cargar_datos():
    try:
        df = pd.read_excel(URL, sheet_name="VENTAS26")
        
        # Limpieza: eliminamos columnas completamente vacías o "Unnamed" que a veces se generan al exportar
        df = df.dropna(axis=1, how='all')
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        df['Fecha de encuesta'] = pd.to_datetime(df['Fecha de encuesta'], errors='coerce')
        df['Mes_Año'] = df['Fecha de encuesta'].dt.to_period('M').astype(str)
        return df
    except Exception as e:
        st.error(f"Error al cargar los datos: {e}")
        return pd.DataFrame()

# Función para calcular el NPS a partir de las categorías de texto
def calcular_nps(series):
    # Estandarizamos los textos a minúsculas sin espacios extra
    s = series.astype(str).str.strip().str.lower()
    promotores = (s == 'promotor').sum()
    detractores = (s == 'detractor').sum()
    
    # Contamos solo los válidos
    total = s.isin(['promotor', 'neutro', 'detractor']).sum()
    
    if total == 0: 
        return 0.0
    return ((promotores / total) - (detractores / total)) * 100

df = cargar_datos()

if not df.empty:
    # Nos aseguramos de tomar la última columna real y válida con datos
    col_nps = df.columns[-1] 
    
    df['SSI'] = pd.to_numeric(df['SSI'], errors='coerce')
    
    if 'Q2' in df.columns:
        df['Q2'] = pd.to_numeric(df['Q2'], errors='coerce')
    
    # --- BARRA LATERAL: FILTROS ---
    st.sidebar.header("Filtros")
    
    sucursales = df['Boca de Venta'].dropna().unique().tolist()
    sucursal_seleccionada = st.sidebar.multiselect("Seleccionar Boca de Venta", sucursales, default=sucursales)
    
    meses = sorted(df['Mes_Año'].dropna().unique().tolist())
    mes_seleccionado = st.sidebar.multiselect("Seleccionar Mes", meses, default=meses)
    
    df_filtrado = df[
        (df['Boca de Venta'].isin(sucursal_seleccionada)) & 
        (df['Mes_Año'].isin(mes_seleccionado))
    ]
    
    st.divider()

    # --- KPIs PRINCIPALES ---
    st.subheader("Rendimiento Global vs Objetivos")
    
    nps_promedio = calcular_nps(df_filtrado[col_nps]) if not df_filtrado.empty else 0
    ssi_promedio = df_filtrado['SSI'].mean() if not df_filtrado.empty else 0
    
    obj_nps = 87.0
    obj_ssi = 95.6
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric(label="NPS Acumulado", 
                  value=f"{nps_promedio:.1f}%", 
                  delta=f"{nps_promedio - obj_nps:.1f}% (Obj: {obj_nps}%)")
        
    with col2:
        st.metric(label="SSI Acumulado", 
                  value=f"{ssi_promedio:.1f}", 
                  delta=f"{ssi_promedio - obj_ssi:.1f} (Obj: {obj_ssi})")
        
    st.divider()

    # --- TABS DE VISUALIZACIÓN ---
    st.subheader("Análisis Detallado")
    
    if not df_filtrado.empty:
        tab1, tab2, tab3 = st.tabs(["Tabla de Datos", "Gráfico Histórico", "Vendedores"])
        
        def obtener_color_grafico(valor):
            if pd.isna(valor): return '#cccccc'
            if valor >= 90: return '#155724'
            elif valor >= 80: return '#856404'
            else: return '#721c24'

        def colorear_porcentaje(valor):
            if isinstance(valor, (int, float)) and not pd.isna(valor):
                if valor >= 90:
                    return 'color: #155724; background-color: #d4edda'
                elif valor >= 80:
                    return 'color: #856404; background-color: #fff3cd'
                else:
                    return 'color: #721c24; background-color: #f8d7da'
            return ''
        
        with tab1:
            df_agrupado = df_filtrado.groupby('Mes_Año').agg(
                Q_encuestas=('Fecha de encuesta', 'count'),
                SSI_Promedio=('SSI', 'mean'),
                NPS_Promedio=(col_nps, calcular_nps),
                Instalaciones=('01 - Instalaciones', 'mean'),
                Atencion_Vendedor=('02 - Atencion Vendedor', 'mean'),
                Atencion_Administracion=('03 - Atencion Administracion', 'mean'),
                Fecha_Entrega=('04 - Fecha de Entrega', 'mean'),
                Momento_Entrega=('05 - Momento de Entrega', 'mean')
            ).reset_index()

            columnas_formatear = ['SSI_Promedio', 'NPS_Promedio', 'Instalaciones', 
                                  'Atencion_Vendedor', 'Atencion_Administracion', 
                                  'Fecha_Entrega', 'Momento_Entrega']
            
            st.dataframe(
                df_agrupado.style.format({col: "{:.1f}" for col in columnas_formatear}, na_rep="-")
                                 .map(colorear_porcentaje, subset=columnas_formatear),
                use_container_width=True
            )
            
        with tab2:
            fig = go.Figure()
            
            colores_ssi = [obtener_color_grafico(v) for v in df_agrupado['SSI_Promedio']]
            fig.add_trace(go.Scatter(
                x=df_agrupado['Mes_Año'],
                y=df_agrupado['SSI_Promedio'],
                mode='lines+markers+text',
                name='SSI Promedio',
                text=[f"{v:.1f}" if not pd.isna(v) else "" for v in df_agrupado['SSI_Promedio']],
                textposition="top center",
                marker=dict(color=colores_ssi, size=12, line=dict(color='white', width=1)),
                line=dict(color='gray', width=2)
            ))
            
            colores_nps = [obtener_color_grafico(v) for v in df_agrupado['NPS_Promedio']]
            fig.add_trace(go.Scatter(
                x=df_agrupado['Mes_Año'],
                y=df_agrupado['NPS_Promedio'],
                mode='lines+markers+text',
                name='NPS Promedio',
                text=[f"{v:.1f}%" if not pd.isna(v) else "" for v in df_agrupado['NPS_Promedio']],
                textposition="bottom center",
                marker=dict(color=colores_nps, size=12, line=dict(color='white', width=1)),
                line=dict(color='lightgray', width=2, dash='dash')
            ))

            fig.update_layout(
                xaxis_title='Mes',
                yaxis_title='Puntuación',
                hovermode='x unified',
                margin=dict(l=20, r=20, t=30, b=20)
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            st.write("### NPS por Vendedor y Periodo")
            
            if 'Vendedor' in df_filtrado.columns:
                nps_vendedor = df_filtrado.groupby(['Vendedor', 'Mes_Año']).agg(
                    NPS=(col_nps, calcular_nps)
                ).reset_index()
                
                pivot_nps = nps_vendedor.pivot(index='Vendedor', columns='Mes_Año', values='NPS')
                st.dataframe(pivot_nps.style.format("{:.1f}", na_rep="-").map(colorear_porcentaje), use_container_width=True)
                
                st.divider()
                st.write("### Desempeño Comercial (Indicador Q2)")
                if 'Q2' in df_filtrado.columns:
                    q2_vendedor = df_filtrado.groupby('Vendedor')['Q2'].mean().reset_index()
                    colores_q2 = [obtener_color_grafico(v) for v in q2_vendedor['Q2']]
                    
                    fig_bars = go.Figure(data=[
                        go.Bar(
                            x=q2_vendedor['Vendedor'],
                            y=q2_vendedor['Q2'],
                            marker_color=colores_q2,
                            text=[f"{v:.1f}" if not pd.isna(v) else "" for v in q2_vendedor['Q2']],
                            textposition='auto'
                        )
                    ])
                    fig_bars.update_layout(xaxis_title='Vendedor', yaxis_title='Q2 Promedio', margin=dict(l=20, r=20, t=30, b=20))
                    st.plotly_chart(fig_bars, use_container_width=True)
                else:
                    st.info("💡 La columna 'Q2' no se encontró. Verifica el nombre exacto en tu Excel para habilitar el gráfico de barras.")
            else:
                st.info("💡 La columna 'Vendedor' no se encontró. Verifica el nombre exacto en tu Excel para habilitar la tabla.")

    else:
        st.warning("No hay datos disponibles para los filtros seleccionados.")
