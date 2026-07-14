import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 1. Configuración de la página del Dashboard
st.set_page_config(
    page_title="Dashboard SSI y NPS - Autolux",
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

st.markdown('<div class="main-title">🎯 Tablero de Gestión: SSI y NPS - VENTAS</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Seguimiento de Satisfacción y Lealtad del Cliente frente a Objetivos</div>', unsafe_allow_html=True)

# 2. Conexión de Datos a la hoja "VENTAS26"
SHEET_ID = "1PGoOlFTN2WuuiEqRk0KPrcLZL6pEcFVeNWo35shsUSA"
SHEET_NAME = "VENTAS26"
# Utilizamos la API gviz de Google para traer directamente la pestaña especificada en formato CSV
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
    
    # NPS -> Última columna según instrucción
    col_nps = columnas_disponibles[-1]
    
    # Buscar columna Vendedor
    col_vend_detectada = next((c for c in columnas_disponibles if 'vendedor' in c.lower() or 'asesor' in c.lower()), columnas_disponibles[0])
    col_vendedor = st.sidebar.selectbox("Columna Vendedor:", columnas_disponibles, index=columnas_disponibles.index(col_vend_detectada))
    
    # Buscar columna SSI
    col_ssi_detectada = next((c for c in columnas_disponibles if 'ssi' in c.lower()), columnas_disponibles[0])
    col_ssi = st.sidebar.selectbox("Columna SSI:", columnas_disponibles, index=columnas_disponibles.index(col_ssi_detectada))
    
    # Buscar columna Fecha / Mes
    col_fecha_detectada = next((c for c in columnas_disponibles if 'fecha' in c.lower() or 'mes' in c.lower() or 'periodo' in c.lower()), columnas_disponibles[0])
    col_fecha = st.sidebar.selectbox("Columna Periodo (Fecha/Mes):", columnas_disponibles, index=columnas_disponibles.index(col_fecha_detectada))

    df_procesado = df_raw.copy()
    
    # Preparar Fechas (Periodos por Mes)
    try:
        df_procesado['Mes_Período'] = pd.to_datetime(df_procesado[col_fecha], errors='coerce').dt.strftime('%Y-%m')
        df_procesado['Mes_Período'] = df_procesado['Mes_Período'].fillna(df_procesado[col_fecha].astype(str))
    except:
        df_procesado['Mes_Período'] = df_procesado[col_fecha].astype(str)

    # Función robusta para calcular NPS
    def calcular_nps(serie):
        if len(serie.dropna()) == 0: return 0.0
        
        # Intentar convertir a numérico (escalas 0-10)
        serie_num = pd.to_numeric(serie, errors='coerce')
        if serie_num.notna().sum() > 0:
            promotores = (serie_num >= 9).sum()
            detractores = (serie_num <= 6).sum()
            total = serie_num.notna().sum()
            return (promotores - detractores) / total * 100.0
        else:
            # Si es texto (Promotor, Detractor, Pasivo)
            s_str = serie.astype(str).str.lower()
            promotores = s_str.str.contains('promotor').sum()
            detractores = s_str.str.contains('detractor').sum()
            total = len(s_str.replace(['nan', 'none', ''], pd.NA).dropna())
            if total == 0: return 0.0
            return (promotores - detractores) / total * 100.0

    # Limpiar SSI a numérico
    df_procesado['SSI_Num'] = pd.to_numeric(df_procesado[col_ssi].astype(str).str.replace(',', '.').str.replace('%', ''), errors='coerce')

    # 4. Filtros Globales (Meses y Vendedores)
    st.sidebar.header("🔍 Filtros de Visualización")
    
    meses_disp = sorted(df_procesado['Mes_Período'].unique().tolist())
    meses_sel = st.sidebar.multiselect("Periodo (Mes):", meses_disp, default=meses_disp)
    
    vendedores_disp = sorted(df_procesado[df_procesado['Mes_Período'].isin(meses_sel)][col_vendedor].dropna().unique().tolist())
    vendedores_sel = st.sidebar.multiselect("Vendedores:", vendedores_disp, default=vendedores_disp)

    # Aplicar filtros a los datos
    df_filtrado = df_procesado[
        (df_procesado['Mes_Período'].isin(meses_sel)) & 
        (df_procesado[col_vendedor].isin(vendedores_sel))
    ]

    # 5. Cálculos de Objetivos Generales
    OBJETIVO_SSI = 95.6
    OBJETIVO_NPS = 87.0
    
    ssi_actual = df_filtrado['SSI_Num'].mean()
    nps_actual = calcular_nps(df_filtrado[col_nps])

    # 6. Relojes / Indicadores (Gauges)
    st.write("### ⏱️ Estado Actual vs Objetivos")
    col1, col2 = st.columns(2)
    
    def crear_reloj(valor, titulo, objetivo, max_val, color_ok="#2ecc71", color_bad="#e74c3c"):
        valor = 0 if pd.isna(valor) else valor
        color_actual = color_ok if valor >= objetivo else color_bad
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=valor,
            number={'suffix': "%" if "NPS" in titulo else "", 'font': {'size': 40, 'color': color_actual}},
            delta={'reference': objetivo, 'increasing': {'color': color_ok}, 'decreasing': {'color': color_bad}},
            title={'text': titulo, 'font': {'size': 20, 'color': '#1E3A8A'}},
            gauge={
                'axis': {'range': [None, max_val], 'tickwidth': 1},
                'bar': {'color': color_actual},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, objetivo], 'color': '#F1F5F9'},
                    {'range': [objetivo, max_val], 'color': '#E2E8F0'}
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 4},
                    'thickness': 0.75,
                    'value': objetivo
                }
            }
        ))
        fig.update_layout(height=350, margin=dict(l=20, r=20, t=50, b=20))
        return fig

    with col1:
        st.plotly_chart(crear_reloj(ssi_actual, "Indicador SSI (Objetivo: 95.6)", OBJETIVO_SSI, 100), use_container_width=True)
    with col2:
        st.plotly_chart(crear_reloj(nps_actual, "Indicador NPS (Objetivo: 87%)", OBJETIVO_NPS, 100), use_container_width=True)

    st.write("---")
    
    # 7. Ranking de Vendedores y Cantidad de Encuestas
    st.write("### 🏆 Ranking de Vendedores y Volumen de Encuestas")
    
    resumen = []
    for vend, grupo in df_filtrado.groupby(col_vendedor):
        resumen.append({
            'Vendedor': vend,
            'Encuestas': len(grupo),
            'SSI_Promedio': grupo['SSI_Num'].mean(),
            'NPS': calcular_nps(grupo[col_nps])
        })
        
    df_resumen = pd.DataFrame(resumen).sort_values('SSI_Promedio', ascending=False).dropna(subset=['SSI_Promedio'])
    
    if not df_resumen.empty:
        # Gráfico Combinado (Barras agrupadas + Línea para conteo)
        fig_ranking = go.Figure()
        
        # Barra para SSI
        fig_ranking.add_trace(go.Bar(
            x=df_resumen['Vendedor'], y=df_resumen['SSI_Promedio'],
            name='SSI Promedio', marker_color='#3498db',
            text=df_resumen['SSI_Promedio'].apply(lambda x: f"{x:.1f}"), textposition='auto'
        ))
        
        # Barra para NPS
        fig_ranking.add_trace(go.Bar(
            x=df_resumen['Vendedor'], y=df_resumen['NPS'],
            name='NPS (%)', marker_color='#9b59b6',
            text=df_resumen['NPS'].apply(lambda x: f"{x:.1f}%"), textposition='auto'
        ))
        
        # Línea de puntos para Cantidad de Encuestas (Eje secundario)
        fig_ranking.add_trace(go.Scatter(
            x=df_resumen['Vendedor'], y=df_resumen['Encuestas'],
            name='Cant. Encuestas', mode='lines+markers+text',
            yaxis='y2', marker=dict(color='#e67e22', size=12, symbol='diamond'),
            line=dict(color='#e67e22', width=3, dash='dot'),
            text=df_resumen['Encuestas'], textposition='top center',
            textfont=dict(color='#d35400', size=14, weight='bold')
        ))
        
        fig_ranking.update_layout(
            barmode='group',
            xaxis_title="Vendedor / Asesor",
            yaxis=dict(title="Puntaje / Porcentaje", range=[0, max(110, df_resumen['SSI_Promedio'].max() * 1.1)]),
            yaxis2=dict(
                title="Cantidad de Encuestas", overlaying='y', side='right',
                range=[0, df_resumen['Encuestas'].max() * 1.5], showgrid=False
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            template="plotly_white",
            margin=dict(t=80)
        )
        
        st.plotly_chart(fig_ranking, use_container_width=True)
        
        # Tabla resumen inferior
        st.write("#### 📑 Datos Detallados por Vendedor")
        st.dataframe(
            df_resumen.style.format({
                'SSI_Promedio': "{:.1f}",
                'NPS': "{:.1f}%"
            }).background_gradient(subset=['SSI_Promedio', 'NPS'], cmap='Blues'),
            use_container_width=True, hide_index=True
        )
    else:
        st.warning("No hay suficientes datos para generar el ranking con los filtros aplicados.")
else:
    st.warning("No se pudo leer la hoja VENTAS26 o está vacía. Verifica el enlace y los permisos.")
