import os

code_content = """import streamlit as st
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
st.markdown(\"\"\"
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
\"\"\", unsafe_allow_html=True)

st.markdown('<div class="main-title">📊 Panel de Control: Mystery Interno - Autolux</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Análisis automatizado de auditorías de calidad y cumplimiento del equipo de ventas</div>', unsafe_allow_html=True)

# 2. Enlace público provisto por el usuario
SHEET_URL = "https://docs.google.com/spreadsheets/d/1_OCxCakgSVU0DRibdT2ZcsgtCK1YDjmDthePt_pr5Xo/edit?usp=sharing"

@st.cache_data(ttl=600)  # Se actualiza cada 10 minutos automáticamente
def cargar_datos_desde_enlace(url):
    # Conversión del enlace de edición a exportación directa en formato CSV
    if "/edit" in url:
        csv_url = url.split("/edit")[0] + "/export?format=csv"
    else:
        csv_url = url
    
    try:
        df = pd.read_csv(csv_url)
        # Limpieza inicial de nombres de columnas
        df.columns = [str(col).strip() for col in df.columns]
        return df
    except Exception as e:
        st.error(f"Error al conectar con la base de datos de Google Sheets: {e}")
        return pd.DataFrame()

# Carga efectiva de los datos
df_raw = cargar_datos_desde_enlace(SHEET_URL)

if not df_raw.empty:
    # 3. Procesamiento inteligente e identificación de indicadores clave (Vendedor y Q2)
    columnas_disponibles = df_raw.columns.tolist()
    
    # Buscador inteligente de columnas para evitar fallas por minúsculas/mayúsculas
    col_vendedor = next((c for c in columnas_disponibles if c.lower() == 'vendedor'), None)
    col_q2 = next((c for c in columnas_disponibles if c.lower() == 'q2'), None)
    
    # Si no coinciden exactamente, tomamos selectores dinámicos por seguridad
    st.sidebar.header("⚙️ Configuración de Columnas")
    if col_vendedor:
        vendedor_seleccionado = st.sidebar.selectbox("Columna Vendedor detectada:", [col_vendedor] + columnas_disponibles, index=0)
    else:
        vendedor_seleccionado = st.sidebar.selectbox("Selecciona la columna del Vendedor:", columnas_disponibles)
        
    if col_q2:
        q2_seleccionado = st.sidebar.selectbox("Columna de Indicador (Q2) detectada:", [col_q2] + columnas_disponibles, index=0)
    else:
        q2_seleccionado = st.sidebar.selectbox("Selecciona la columna del Indicador Principal (Q2):", columnas_disponibles)

    # 4. Limpieza y normalización de la métrica Q2 (Numérica o Categórica)
    df_procesado = df_raw.copy()
    
    def normalizar_metrica(val):
        if pd.isna(val):
            return np.nan
        val_str = str(val).strip().lower()
        
        # Caso A: Si la celda contiene texto de cumplimiento directo (Checklist)
        if val_str in ['cumple', 'cumplido', 'si', 'sí', 'correcto']:
            return 100.0
        elif val_str in ['no cumple', 'no cumplido', 'no', 'incorrecto']:
            return 0.0
        elif val_str in ['parcial', 'parcialmente', 'parcialmente cumplido']:
            return 50.0
        elif val_str in ['n/a', 'na', 'no aplica']:
            return np.nan
            
        # Caso B: Si es un porcentaje o un número en formato texto (Ej: "85%", "85,5")
        try:
            val_num = float(val_str.replace('%', '').replace(',', '.'))
            if val_num <= 1.0 and val_num > 0.0:
                return val_num * 100.0
            return val_num
        except ValueError:
            return np.nan

    df_procesado['Q2_Final'] = df_procesado[q2_seleccionado].apply(normalizar_metrica)
    
    # Filtros avanzados en la barra lateral
    st.sidebar.header("🔍 Filtros de Búsqueda")
    
    # Filtro por Vendedor si existe la columna
    todos_vendedores = sorted(df_procesado[vendedor_seleccionado].dropna().unique().tolist())
    vendedores_filtrados = st.sidebar.multiselect("Filtrar por Vendedor:", options=todos_vendedores, default=todos_vendedores)
    
    # Aplicar filtros
    df_filtrado = df_procesado[df_procesado[vendedor_seleccionado].isin(vendedores_filtrados)]

    # 5. Creación de la interfaz mediante Pestañas (Tabs)
    tab_resumen, tab_vendedores = st.tabs(["📋 Resumen General", "👥 Pestaña de Vendedores"])
    
    with tab_resumen:
        st.write("### 📈 Métricas Consolidadas de la Operación")
        
        # Cálculo de Kpi's globales
        total_auditorias = len(df_filtrado)
        promedio_q2_global = df_filtrado['Q2_Final'].mean()
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'''
                <div class="metric-box">
                    <span style="color:#555; font-size:13px; font-weight:bold;">TOTAL AUDITORÍAS</span><br>
                    <span style="font-size:26px; font-weight:bold; color:#1E3A8A;">{total_auditorias}</span>
                </div>
            ''', unsafe_allow_html=True)
        with c2:
            val_q2_str = f"{promedio_q2_global:.1f}%" if not pd.isna(promedio_q2_global) else "N/D"
            st.markdown(f'''
                <div class="metric-box">
                    <span style="color:#555; font-size:13px; font-weight:bold;">CUMPLIMIENTO PROMEDIO Q2</span><br>
                    <span style="font-size:26px; font-weight:bold; color:#2ECC71;">{val_q2_str}</span>
                </div>
            ''', unsafe_allow_html=True)
        with c3:
            # Porcentaje de muestras óptimas (>= 90%)
            muestras_con_nota = df_filtrado['Q2_Final'].dropna()
            if len(muestras_con_nota) > 0:
                optimas = (muestras_con_nota >= 90).sum() / len(muestras_con_nota) * 100
                val_opt_str = f"{optimas:.1f}%"
            else:
                val_opt_str = "N/D"
            st.markdown(f'''
                <div class="metric-box">
                    <span style="color:#555; font-size:13px; font-weight:bold;">ÍNDICE DE EXCELENCIA (>=90%)</span><br>
                    <span style="font-size:26px; font-weight:bold; color:#0284C7;">{val_opt_str}</span>
                </div>
            ''', unsafe_allow_html=True)
            
        st.write("---")
        st.write("#### 📑 Registro de Datos Completo (Google Sheets)")
        st.dataframe(df_raw, use_container_width=True)

    with tab_vendedores:
        st.write("### 📊 Rendimiento Individual del Equipo de Ventas")
        
        # Agrupación por vendedor y cálculo del promedio de Q2
        df_agrupado = df_filtrado.groupby(vendedor_seleccionado, as_index=False)['Q2_Final'].mean()
        df_agrupado = df_agrupado.dropna(subset=['Q2_Final'])
        
        if not df_agrupado.empty:
            # Lógica de colores condicionales según el rango del % de porcentaje
            # Rangos estándar de calidad: Crítico (<80%), Regular (80-89.9%), Óptimo (>=90%)
            def determinar_color_por_rango(porcentaje):
                if porcentaje >= 90.0:
                    return "#2ecc71"  # Verde - Óptimo
                elif porcentaje >= 80.0:
                    return "#f39c12"  # Amarillo/Naranja - Regular
                else:
                    return "#e74c3c"  # Rojo - Crítico
            
            df_agrupado['Color_Asignado'] = df_agrupado['Q2_Final'].apply(determinar_color_por_rango)
            
            # Ordenar de mayor a menor rendimiento para una visualización jerárquica clara
            df_agrupado = df_agrupado.sort_values(by='Q2_Final', ascending=False)
            
            # Creación exacta del gráfico solicitado: Columnas en barras verticales
            fig = px.bar(
                df_agrupado,
                x=vendedor_seleccionado,
                y='Q2_Final',
                title=f"Cumplimiento del Indicador Principal ({q2_seleccionado}) por Asesor",
                labels={vendedor_seleccionado: "Asesor de Ventas", 'Q2_Final': "Porcentaje de Cumplimiento (%)"},
                text='Q2_Final'
            )
            
            # Configuración estética avanzada de las columnas en barras
            fig.update_traces(
                marker_color=df_agrupado['Color_Asignado'],  # Colores dinámicos por rango de %
                texttemplate='%{text:.1f}%',                 # Mostrar el porcentaje arriba de la barra
                textposition='outside',
                cliponaxis=False
            )
            
            fig.update_layout(
                yaxis_range=[0, 115],
                xaxis_title="Vendedores / Asesores",
                yaxis_title="Porcentaje (%)",
                template="plotly_white",
                margin=dict(t=50, b=50, l=50, r=50)
            )
            
            # Renderizado del gráfico de barras
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabla complementaria con ranking de vendedores
            st.write("#### 🏆 Tabla de Posiciones y Auditoría Interna")
            
            # Renombrar columnas para presentación final
            df_ranking = df_agrupado[[vendedor_seleccionado, 'Q2_Final']].copy()
            df_ranking.columns = ["Asesor de Ventas", "Promedio Indicador Q2 (%)"]
            
            # Mostrar tabla con formato de porcentaje impecable
            st.dataframe(
                df_ranking.style.format({"Promedio Indicador Q2 (%)": "{:.2f}%"}),
                use_container_width=True,
                hide_index=True
            )
            
            # Código de referencia para la leyenda de rangos
            st.markdown(\"\"\"
                <div style='background-color:#F1F5F9; padding:12px; border-radius:6px; font-size:12px;'>
                    <strong>Leyenda de Rangos de Cumplimiento:</strong><br>
                    🟢 <span style='color:#2ecc71; font-weight:bold;'>Óptimo (≥ 90%)</span> | 
                    🟡 <span style='color:#f39c12; font-weight:bold;'>Regular (80% - 89.9%)</span> | 
                    🔴 <span style='color:#e74c3c; font-weight:bold;'>Crítico (< 80%)</span>
                </div>
            \"\"\", unsafe_allow_html=True)
        else:
            st.warning("⚠️ No se encontraron registros válidos o numéricos en la columna seleccionada para generar las barras de rendimiento.")
            
else:
    st.warning("⚠️ La hoja de cálculo está vacía o el formato provisto no es el correcto. Por favor revisa el origen en Google Sheets.")
"""

with open("app.py", "w", encoding="utf-8") as f:
    f.write(code_content)

print("Archivo app.py generado exitosamente.")
