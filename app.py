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
    cols_subindices = [c for c in columnas_disponibles if any(x in c for x in ['01', '02', '03', '04', '05', '08', '09', '11'])]
    for c in cols_subindices:
        df_procesado[c] = pd.to_numeric(df_procesado[c].astype(str).str.replace(',', '.').str.replace('%', ''), errors='coerce')

    # 4. Filtros Globales en Barra Lateral
    st.sidebar.header("🔍 Filtros de Visualización")
    
    años_disp = sorted([a for a in df_procesado['Año'].unique() if a != "0"], reverse=True)
    año_sel = st.sidebar.selectbox("Año:", ["Todos"] + años_disp)
    
    bocas_disp = sorted(df_procesado[col_sucursal].dropna().astype(str).unique().tolist())
    boca_sel = st.sidebar.selectbox("Seleccionar Boca de Venta:", ["Todas"] + bocas_disp)

    # Aplicar filtros de Año y Boca
    df_filtrado = df_procesado.copy()
    if año_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado['Año'] == año_sel]
    if boca_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado[col_sucursal].astype(str) == boca_sel]

    # 5. Creación de Pestañas
    tab_resumen, tab_ranking, tab_evolucion = st.tabs(["⏱️ Relojes de Objetivos", "🏆 Ranking Vendedores", "📅 Evolución Mensual"])

    # --- PESTAÑA 1: RELOJES ---
    with tab_resumen:
        st.write("### Estado Actual vs Objetivos Generales")
        OBJETIVO_SSI = 95.6
        OBJETIVO_NPS = 87.0
        
        ssi_actual = df_filtrado['SSI_Num'].mean()
        nps_actual = calcular_nps(df_filtrado[col_nps])

        col1, col2 = st.columns(2)
        def crear_reloj(valor, titulo, objetivo, max_val, color_ok="#2ecc71", color_bad="#e74c3c"):
            valor = 0 if pd.isna(valor) else valor
            color_actual = color_ok if valor >= objetivo else color_bad
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta", value=valor,
                number={'suffix': "%" if "NPS" in titulo else "", 'font': {'size': 40, 'color': color_actual}},
                delta={'reference': objetivo, 'increasing': {'color': color_ok}, 'decreasing': {'color': color_bad}},
                title={'text': titulo, 'font': {'size': 20, 'color': '#1E3A8A'}},
                gauge={'axis': {'range': [None, max_val], 'tickwidth': 1}, 'bar': {'color': color_actual},
                       'steps': [{'range': [0, objetivo], 'color': '#F1F5F9'}, {'range': [objetivo, max_val], 'color': '#E2E8F0'}],
                       'threshold': {'line': {'color': "black", 'width': 4}, 'thickness': 0.75, 'value': objetivo}}
            ))
            fig.update_layout(height=350, margin=dict(l=20, r=20, t=50, b=20))
            return fig

        with col1: st.plotly_chart(crear_reloj(ssi_actual, "Indicador SSI (Objetivo: 95.6)", OBJETIVO_SSI, 100), use_container_width=True)
        with col2: st.plotly_chart(crear_reloj(nps_actual, "Indicador NPS (Objetivo: 87%)", OBJETIVO_NPS, 100), use_container_width=True)

    # --- PESTAÑA 2: RANKING ---
    with tab_ranking:
        st.write("### Ranking de Vendedores y Volumen de Encuestas")
        resumen = []
        for vend, grupo in df_filtrado.groupby(col_vendedor):
            resumen.append({'Vendedor': vend, 'Encuestas': len(grupo), 'SSI_Promedio': grupo['SSI_Num'].mean(), 'NPS': calcular_nps(grupo[col_nps])})
            
        df_resumen = pd.DataFrame(resumen).sort_values('SSI_Promedio', ascending=False).dropna(subset=['SSI_Promedio'])
        
        if not df_resumen.empty:
            fig_ranking = go.Figure()
            fig_ranking.add_trace(go.Bar(x=df_resumen['Vendedor'], y=df_resumen['SSI_Promedio'], name='SSI', marker_color='#3498db', text=df_resumen['SSI_Promedio'].apply(lambda x: f"{x:.1f}"), textposition='auto'))
            fig_ranking.add_trace(go.Bar(x=df_resumen['Vendedor'], y=df_resumen['NPS'], name='NPS (%)', marker_color='#9b59b6', text=df_resumen['NPS'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/D"), textposition='auto'))
            fig_ranking.add_trace(go.Scatter(x=df_resumen['Vendedor'], y=df_resumen['Encuestas'], name='Cant. Encuestas', mode='lines+markers+text', yaxis='y2', marker=dict(color='#e67e22', size=12), line=dict(color='#e67e22', dash='dot'), text=df_resumen['Encuestas'], textposition='top center'))
            
            fig_ranking.update_layout(barmode='group', xaxis_title="Vendedor", yaxis=dict(title="Puntaje", range=[0, 110]), yaxis2=dict(title="Encuestas", overlaying='y', side='right', range=[0, df_resumen['Encuestas'].max() * 1.5]), template="plotly_white")
            st.plotly_chart(fig_ranking, use_container_width=True)
        else:
            st.warning("No hay datos para mostrar el ranking.")

    # --- PESTAÑA 3: EVOLUCIÓN MENSUAL Y SUBÍNDICES (NUEVA) ---
    with tab_evolucion:
        st.write(f"### Desempeño Mensual - Boca de Venta: {boca_sel} | Año: {año_sel}")
        
        # Agrupación por Mes
        if 'Mes_Num' in df_filtrado.columns:
            df_mensual = df_filtrado.sort_values('Mes_Num').groupby('Mes_Nombre', sort=False)
        else:
            df_mensual = df_filtrado.groupby('Mes_Nombre', sort=False)

        resumen_mensual = []
        for mes, grupo in df_mensual:
            fila = {
                'Mes': mes.capitalize(),
                'Q encuestas': len(grupo),
                'SSI Puro': grupo['SSI_Num'].mean(),
                'NPS dealer': calcular_nps(grupo[col_nps])
            }
            # Agregar promedios de los subíndices dinámicamente
            for c in cols_subindices:
                fila[c] = grupo[c].mean()
            resumen_mensual.append(fila)

        df_tabla_mensual = pd.DataFrame(resumen_mensual)

        if not df_tabla_mensual.empty:
            # 1. Gráfico de Evolución Relacionado
            fig_evolucion = go.Figure()
            fig_evolucion.add_trace(go.Scatter(x=df_tabla_mensual['Mes'], y=df_tabla_mensual['SSI Puro'], mode='lines+markers+text', name='SSI Puro', line=dict(color='#1E3A8A', width=3), marker=dict(size=10), text=df_tabla_mensual['SSI Puro'].apply(lambda x: f"{x:.1f}"), textposition='top center'))
            fig_evolucion.add_trace(go.Scatter(x=df_tabla_mensual['Mes'], y=df_tabla_mensual['NPS dealer'], mode='lines+markers+text', name='NPS dealer', line=dict(color='#2ecc71', width=3), marker=dict(size=10), text=df_tabla_mensual['NPS dealer'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else ""), textposition='bottom center'))
            
            fig_evolucion.update_layout(title="Evolución de SSI y NPS por Mes", xaxis_title="Mes", yaxis_title="Puntaje / Porcentaje", yaxis_range=[0, 110], template="plotly_white", hovermode="x unified")
            st.plotly_chart(fig_evolucion, use_container_width=True)

            # 2. Tabla de Datos Formateada
            st.write("#### Cuadro de Mando Mensual y Subíndices")
            
            # Fila de Totales
            totales = {
                'Mes': 'Total',
                'Q encuestas': df_tabla_mensual['Q encuestas'].sum(),
                'SSI Puro': df_filtrado['SSI_Num'].mean(),
                'NPS dealer': calcular_nps(df_filtrado[col_nps])
            }
            for c in cols_subindices:
                totales[c] = df_filtrado[c].mean()
                
            df_tabla_mensual.loc[len(df_tabla_mensual)] = totales

            # Formateo visual para la tabla
            formatos = {'Q encuestas': '{:.0f}', 'SSI Puro': '{:.1f}', 'NPS dealer': '{:.1f}%'}
            for c in cols_subindices:
                formatos[c] = '{:.1f}'

            st.dataframe(
                df_tabla_mensual.style.format(formatos, na_rep="-").apply(
                    lambda x: ['font-weight: bold; background-color: #f0f2f6' if x['Mes'] == 'Total' else '' for i in x], axis=1
                ),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("No hay datos registrados para los filtros seleccionados.")

else:
    st.warning("No se pudo leer la hoja VENTAS26 o está vacía.")
