import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# 1. Configuración de la página del Dashboard
st.set_page_config(
    page_title="Dashboard Mystery Interno - Autolux",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos estéticos personalizados
st.markdown("""
    <style>
    .main-title {
        font-size: 28px;
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 5px;
    }
    .subtitle {
        font-size: 14px;
        color: #555555;
        margin-bottom: 25px;
    }
    .metric-box {
        background-color: #F8FAFC;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #1E3A8A;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📊 Panel de Control: Mystery Interno - Autolux</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Análisis de auditorías de calidad, rendimiento de asesores y evolución histórica</div>', unsafe_allow_html=True)

# 2. Enlace público
SHEET_URL = "https://docs.google.com/spreadsheets/d/1_OCxCakgSVU0DRibdT2ZcsgtCK1YDjmDthePt_pr5Xo/edit?usp=sharing"

@st.cache_data(ttl=600)  # Se actualiza cada 10 minutos automáticamente
def cargar_datos_desde_enlace(url):
    if "/edit" in url:
        csv_url = url.split("/edit")[0] + "/export?format=csv"
    else:
        csv_url = url
    
    try:
        df = pd.read_csv(csv_url)
        df.columns = [str(col).strip() for col in df.columns]
        return df
    except Exception as e:
        st.error(f"Error al conectar con la base de datos de Google Sheets: {e}")
        return pd.DataFrame()

# Carga efectiva de los datos
df_raw = cargar_datos_desde_enlace(SHEET_URL)

if not df_raw.empty:
    columnas_disponibles = df_raw.columns.tolist()
    
    # Buscador inteligente de columnas predeterminadas
    col_vendedor = next((c for c in columnas_disponibles if c.lower() in ['vendedor', 'asesor']), None)
    col_q2 = next((c for c in columnas_disponibles if c.lower() == 'q2'), None)
    col_sucursal = next((c for c in columnas_disponibles if c.lower() in ['sucursal', 'agencia', 'filial']), None)
    col_fecha = next((c for c in columnas_disponibles if c.lower() in ['fecha', 'fecha y hora', 'mes']), None)
    
    # Configuración de Columnas en la barra lateral
    st.sidebar.header("⚙️ Configuración de Columnas")
    
    vendedor_seleccionado = st.sidebar.selectbox(
        "Columna Vendedor:", columnas_disponibles, 
        index=columnas_disponibles.index(col_vendedor) if col_vendedor else 0
    )
    q2_seleccionado = st.sidebar.selectbox(
        "Columna Indicador Principal (Q2):", columnas_disponibles, 
        index=columnas_disponibles.index(col_q2) if col_q2 else 0
    )
    sucursal_seleccionada = st.sidebar.selectbox(
        "Columna Sucursal:", columnas_disponibles, 
        index=columnas_disponibles.index(col_sucursal) if col_sucursal else 0
    )
    fecha_seleccionada = st.sidebar.selectbox(
        "Columna de Fecha/Tiempo:", columnas_disponibles, 
        index=columnas_disponibles.index(col_fecha) if col_fecha else 0
    )

    # 3. Limpieza y normalización de la métrica Q2
    df_procesado = df_raw.copy()
    
    def normalizar_metrica(val):
        if pd.isna(val):
            return np.nan
        val_str = str(val).strip().lower()
        if val_str in ['cumple', 'cumplido', 'si', 'sí', 'correcto']:
            return 100.0
        elif val_str in ['no cumple', 'no cumplido', 'no', 'incorrecto']:
            return 0.0
        elif val_str in ['parcial', 'parcialmente', 'parcialmente cumplido']:
            return 50.0
        elif val_str in ['n/a', 'na', 'no aplica']:
            return np.nan
        try:
            val_num = float(val_str.replace('%', '').replace(',', '.'))
            if val_num <= 1.0 and val_num > 0.0:
                return val_num * 100.0
            return val_num
        except ValueError:
            return np.nan

    df_procesado['Q2_Final'] = df_procesado[q2_seleccionado].apply(normalizar_metrica)
    
    # 4. Procesamiento de Fechas para el Histórico
    try:
        # Intentamos convertir la columna seleccionada a formato fecha
        df_procesado['Fecha_Clean'] = pd.to_datetime(df_procesado[fecha_seleccionada], errors='coerce')
        # Si la conversión funciona, extraemos Año, Mes y una etiqueta para el eje X (YYYY-MM)
        df_procesado['Año'] = df_procesado['Fecha_Clean'].dt.year
        df_procesado['Mes_Num'] = df_procesado['Fecha_Clean'].dt.month
        df_procesado['Año-Mes'] = df_procesado['Fecha_Clean'].dt.strftime('%Y-%m')
    except Exception:
        # Si la columna ya viene como texto de meses/años directamente, la dejamos como está
        df_procesado['Año-Mes'] = df_procesado[fecha_seleccionada].astype(str)
        df_procesado['Año'] = "N/D"
        df_procesado['Mes_Num'] = 1

    # Filtros globales en la barra lateral
    st.sidebar.header("🔍 Filtros Generales")
    
    todas_sucursales = sorted(df_procesado[sucursal_seleccionada].dropna().unique().tolist())
    sucursales_filtradas = st.sidebar.multiselect("Filtrar por Sucursal:", options=todas_sucursales, default=todas_sucursales)
    
    todos_vendedores = sorted(df_procesado[df_procesado[sucursal_seleccionada].isin(sucursales_filtradas)][vendedor_seleccionado].dropna().unique().tolist())
    vendedores_filtrados = st.sidebar.multiselect("Filtrar por Vendedor:", options=todos_vendedores, default=todos_vendedores)
    
    # Aplicación de filtros al set de datos activo
    df_filtrado = df_procesado[
        (df_procesado[sucursal_seleccionada].isin(sucursales_filtradas)) & 
        (df_procesado[vendedor_seleccionado].isin(vendedores_filtrados))
    ]

    # 5. Estructura de Pestañas (Se agrega la pestaña histórica)
    tab_resumen, tab_vendedores, tab_historico = st.tabs([
        "📋 Resumen General", 
        "👥 Pestaña de Vendedores", 
        "📈 Evolución Histórica"
    ])
    
    # --- PESTAÑA 1: RESUMEN GENERAL ---
    with tab_resumen:
        st.write("### 📈 Métricas Consolidadas de la Operación")
        total_auditorias = len(df_filtrado)
        promedio_q2_global = df_filtrado['Q2_Final'].mean()
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="metric-box"><span style="color:#555; font-size:13px; font-weight:bold;">TOTAL AUDITORÍAS</span><br><span style="font-size:26px; font-weight:bold; color:#1E3A8A;">{total_auditorias}</span></div>', unsafe_allow_html=True)
        with c2:
            val_q2_str = f"{promedio_q2_global:.1f}%" if not pd.isna(promedio_q2_global) else "N/D"
            st.markdown(f'<div class="metric-box"><span style="color:#555; font-size:13px; font-weight:bold;">CUMPLIMIENTO PROMEDIO Q2</span><br><span style="font-size:26px; font-weight:bold; color:#2ECC71;">{val_q2_str}</span></div>', unsafe_allow_html=True)
        with c3:
            muestras_con_nota = df_filtrado['Q2_Final'].dropna()
            val_opt_str = f"{(muestras_con_nota >= 90).sum() / len(muestras_con_nota) * 100:.1f}%" if len(muestras_con_nota) > 0 else "N/D"
            st.markdown(f'<div class="metric-box"><span style="color:#555; font-size:13px; font-weight:bold;">ÍNDICE DE EXCELENCIA (≥90%)</span><br><span style="font-size:26px; font-weight:bold; color:#0284C7;">{val_opt_str}</span></div>', unsafe_allow_html=True)
            
        st.write("---")
        st.write("#### 📑 Registro de Datos Completo")
        st.dataframe(df_raw, use_container_width=True)

    # --- PESTAÑA 2: VENDEDORES ---
    with tab_vendedores:
        st.write("### 📊 Rendimiento Individual del Equipo de Ventas")
        df_agrupado = df_filtrado.groupby(vendedor_seleccionado, as_index=False)['Q2_Final'].mean().dropna(subset=['Q2_Final'])
        
        if not df_agrupado.empty:
            def determinar_color_por_rango(porcentaje):
                if porcentaje >= 90.0: return "#2ecc71"
                elif porcentaje >= 80.0: return "#f39c12"
                else: return "#e74c3c"
            
            df_agrupado['Color_Asignado'] = df_agrupado['Q2_Final'].apply(determinar_color_por_rango)
            df_agrupado = df_agrupado.sort_values(by='Q2_Final', ascending=False)
            
            fig_bar = px.bar(
                df_agrupado, x=vendedor_seleccionado, y='Q2_Final',
                title=f"Cumplimiento del Indicador Principal ({q2_seleccionado}) por Asesor",
                labels={vendedor_seleccionado: "Asesor de Ventas", 'Q2_Final': "Porcentaje de Cumplimiento (%)"},
                text='Q2_Final'
            )
            fig_bar.update_traces(marker_color=df_agrupado['Color_Asignado'], texttemplate='%{text:.1f}%', textposition='outside', cliponaxis=False)
            fig_bar.update_layout(yaxis_range=[0, 115], template="plotly_white")
            st.plotly_chart(fig_bar, use_container_width=True)
            
            st.write("#### 🏆 Tabla de Posiciones")
            df_ranking = df_agrupado[[vendedor_seleccionado, 'Q2_Final']].copy()
            df_ranking.columns = ["Asesor de Ventas", "Promedio Indicador Q2 (%)"]
            st.dataframe(df_ranking.style.format({"Promedio Indicador Q2 (%)": "{:.2f}%"}), use_container_width=True, hide_index=True)
        else:
            st.warning("⚠️ No hay datos suficientes para calcular las métricas por vendedor.")

    # --- PESTAÑA 3: EVOLUCIÓN HISTÓRICA (NUEVA NUEVA NUEVA) ---
    with tab_historico:
        st.write("### 📈 Línea de Tendencia Temporal e Histórica")
        
        # Agrupamos por Sucursal, Año-Mes (y columnas de orden) para promediar el cumplimiento
        # Mantenemos las columnas de ordenamiento para asegurar que la gráfica no se desfase en el tiempo
        df_hist = df_filtrado.groupby([sucursal_seleccionada, 'Año-Mes'], as_index=False)['Q2_Final'].mean()
        df_hist = df_hist.dropna(subset=['Q2_Final']).sort_values(by='Año-Mes')
        
        if not df_hist.empty:
            # Gráfico de líneas histórico multivariable
            fig_line = px.line(
                df_hist,
                x='Año-Mes',
                y='Q2_Final',
                color=sucursal_seleccionada,
                title=f"Evolución Histórica del % de Cumplimiento ({q2_seleccionado}) por Sucursal",
                labels={'Año-Mes': "Línea Temporal (Año - Mes)", 'Q2_Final': "Porcentaje de Cumplimiento (%)", sucursal_seleccionada: "Sucursal"},
                markers=True # Añade puntos en cada mes para que sea claro el dato exacto
            )
            
            # Ajustes visuales de la línea temporal
            fig_line.update_traces(
                line=dict(width=3), 
                marker=dict(size=8),
                texttemplate='%{y:.1f}%',
                textposition='top center'
            )
            
            fig_line.update_layout(
                yaxis_range=[0, 110],
                xaxis_title="Período Auditoría",
                yaxis_title="Porcentaje Promedio (%)",
                template="plotly_white",
                hovermode="x unified" # Muestra los valores de todas las sucursales al pasar el mouse por el mismo mes
            )
            
            st.plotly_chart(fig_line, use_container_width=True)
            
            # Tabla de desglose de datos para auditorías más profundas
            st.write("#### 🔍 Matriz de Cumplimiento Histórico")
            df_pivot = df_hist.pivot(index=sucursal_seleccionada, columns='Año-Mes', values='Q2_Final')
            st.dataframe(df_pivot.style.format("{:.1f}%", na_rep="-"), use_container_width=True)
            
        else:
            st.warning("⚠️ No se pudieron generar métricas temporales. Verifica que la columna seleccionada contenga fechas válidas o texto con formato de meses.")

else:
    st.warning("⚠️ No se pudieron extraer datos de la URL provista.")
