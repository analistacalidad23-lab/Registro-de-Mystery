import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# 1. Configuración de la página
st.set_page_config(
    page_title="Dashboard Calidad y Ventas - Autolux",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main-title { font-size: 28px; font-weight: bold; color: #3498db; margin-bottom: 5px; }
    .subtitle { font-size: 14px; color: #a0a0a0; margin-bottom: 25px; }
    
    /* Estilo para fijar los filtros en la parte superior al hacer scroll */
    .sticky-filters {
        position: sticky;
        top: 0px;
        z-index: 999;
        background-color: #0e1117; /* Fondo adaptado a modo oscuro */
        padding: 15px 10px;
        border-bottom: 1px solid #262730;
        margin-bottom: 20px;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🎯 Tablero de Gestión: Calidad, NPS y Comisiones</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Seguimiento de Satisfacción y Lealtad del Cliente: 0km, Usados Certificados y TPA</div>', unsafe_allow_html=True)

# --- BOTÓN DE ACTUALIZACIÓN MANUAL EN BARRA LATERAL ---
st.sidebar.header("🔄 Sincronización")
if st.sidebar.button("Actualizar Datos Ahora"):
    st.cache_data.clear()
    st.rerun()
st.sidebar.markdown("---")

# 2. Conexión de Datos (Hojas de Google)
SHEET_ID_VENTAS = "1PGoOlFTN2WuuiEqRk0KPrcLZL6pEcFVeNWo35shsUSA"
URL_VENTAS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID_VENTAS}/gviz/tq?tqx=out:csv&sheet=VENTAS26"
URL_USADOS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID_VENTAS}/gviz/tq?tqx=out:csv&sheet=USADO26"
URL_TPA26 = f"https://docs.google.com/spreadsheets/d/{SHEET_ID_VENTAS}/gviz/tq?tqx=out:csv&sheet=TPA26"

SHEET_ID_TPA = "1-kBeBdC60rBwsV-rUTlVLSnr2kkI4eJzvW0mA_IvtBg"
URL_TPA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID_TPA}/gviz/tq?tqx=out:csv&sheet=Base%20Datos%20Actualizada"

@st.cache_data(ttl=60)
def cargar_datos(url):
    try:
        df = pd.read_csv(url)
        df.columns = [str(col).strip() for col in df.columns]
        return df
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        return pd.DataFrame()

# Funciones de cálculo globales
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

def obtener_estado_nps(val):
    if pd.isna(val) or val == "": return 'Sin Dato'
    try:
        v = float(val)
        if v >= 9: return 'Promotor'
        elif v >= 7: return 'Neutro'
        else: return 'Detractor'
    except:
        s = str(val).lower()
        if 'promotor' in s: return 'Promotor'
        elif 'detractor' in s: return 'Detractor'
        else: return 'Neutro'

def calcular_nps_texto(serie_estado):
    s_str = serie_estado.astype(str).str.lower()
    promotores = s_str.str.contains('promotor').sum()
    detractores = s_str.str.contains('detractor').sum()
    neutros = s_str.str.contains('neutro').sum()
    
    total_validos = promotores + detractores + neutros
    
    if total_validos == 0: return np.nan
    return (promotores - detractores) / total_validos * 100.0

def crear_reloj(valor, titulo, objetivo, max_val, color_ok="#2ecc71", color_bad="#e74c3c"):
    valor = 0 if pd.isna(valor) else valor
    color_actual = color_ok if valor >= objetivo else color_bad
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta", value=valor,
        number={'suffix': "%" if "NPS" in titulo else "", 'font': {'size': 40, 'color': color_actual}},
        delta={'reference': objetivo, 'increasing': {'color': color_ok}, 'decreasing': {'color': color_bad}},
        title={'text': titulo, 'font': {'size': 18}},
        gauge={'axis': {'range': [-100 if "NPS" in titulo else 0, max_val], 'tickwidth': 1}, 'bar': {'color': color_actual},
               'steps': [{'range': [-100 if "NPS" in titulo else 0, objetivo], 'color': 'rgba(255,255,255,0.1)'}, {'range': [objetivo, max_val], 'color': 'rgba(255,255,255,0.2)'}],
               'threshold': {'line': {'color': "white", 'width': 4}, 'thickness': 0.75, 'value': objetivo}}
    ))
    fig.update_layout(height=300, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)", font={'color': "white"})
    return fig

# Cargar los dataframes
df_ventas_raw = cargar_datos(URL_VENTAS)
df_usados_raw = cargar_datos(URL_USADOS)
df_tpa_raw = cargar_datos(URL_TPA)
df_tpa26_raw = cargar_datos(URL_TPA26)

if not df_ventas_raw.empty:
    columnas_disponibles = df_ventas_raw.columns.tolist()
    
    # --- CONFIGURACIÓN ESTÁTICA 0KM (VENTAS26) ---
    col_nps = columnas_disponibles[-1] 
    col_vendedor = "Asesor de Venta"
    col_ssi = "SSI"
    col_fecha = "Fecha de encuesta"
    col_sucursal = "Boca de Venta"

    col_cliente = next((c for c in columnas_disponibles if 'cliente' in c.lower() or 'nombre' in c.lower() or 'razon' in c.lower()), columnas_disponibles[0])
    col_comentario_0km = columnas_disponibles[30] if len(columnas_disponibles) > 30 else columnas_disponibles[-1]

    df_procesado = df_ventas_raw.copy()
    
    try:
        df_procesado['Fecha_DT'] = pd.to_datetime(df_procesado[col_fecha], errors='coerce')
        df_procesado['Mes_Nombre'] = df_procesado['Fecha_DT'].dt.strftime('%B').str.lower()
        df_procesado['Mes_Num'] = df_procesado['Fecha_DT'].dt.month
        df_procesado['Mes_Período'] = df_procesado['Fecha_DT'].dt.strftime('%Y-%m')
    except:
        df_procesado['Mes_Nombre'] = df_procesado[col_fecha].astype(str)
        df_procesado['Mes_Num'] = 1
        df_procesado['Mes_Período'] = df_procesado[col_fecha].astype(str)

    df_procesado['SSI_Num'] = pd.to_numeric(df_procesado[col_ssi].astype(str).str.replace(',', '.').str.replace('%', ''), errors='coerce')
    cols_subindices = [c for c in columnas_disponibles if any(x in c for x in ['01', '02', '03', '04', '05', '08', '09', '11'])]
    for c in cols_subindices:
        df_procesado[c] = pd.to_numeric(df_procesado[c].astype(str).str.replace(',', '.').str.replace('%', ''), errors='coerce')

    col_atencion_vend = next((c for c in cols_subindices if 'atencion' in c.lower() and 'vendedor' in c.lower()), None)
    if not col_atencion_vend: col_atencion_vend = next((c for c in cols_subindices if '02' in c), None)

    meses_disp_0km = sorted(df_procesado['Mes_Período'].dropna().unique().tolist())
    bocas_disp_0km = sorted(df_procesado[col_sucursal].dropna().astype(str).unique().tolist())

    # ---------------------------------------------------------
    # PROCESAMIENTO GLOBAL DE TPA (Hoja Separada)
    # ---------------------------------------------------------
    df_t_proc = None
    if not df_tpa_raw.empty:
        columnas_tpa = df_tpa_raw.columns.tolist()
        
        col_mes_t = columnas_tpa[7] if len(columnas_tpa) > 7 else next((c for c in columnas_tpa if 'mes' in c.lower() or 'fecha' in c.lower()), columnas_tpa[0])
        col_cliente_t = columnas_tpa[9] if len(columnas_tpa) > 9 else next((c for c in columnas_tpa if 'suscriptor' in c.lower() or 'cliente' in c.lower() or 'nombre' in c.lower()), columnas_tpa[0])
        col_scoring_t = columnas_tpa[14] if len(columnas_tpa) > 14 else next((c for c in columnas_tpa if 'scoring' in c.lower()), columnas_tpa[0])
        col_suc_t = columnas_tpa[23] if len(columnas_tpa) > 23 else next((c for c in columnas_tpa if 'sucursal' in c.lower() or 'boca' in c.lower()), columnas_tpa[0])
        col_vend_t = columnas_tpa[31] if len(columnas_tpa) > 31 else next((c for c in columnas_tpa if 'vendedor' in c.lower() or 'asesor' in c.lower()), columnas_tpa[0])
        col_coment_t = columnas_tpa[36] if len(columnas_tpa) > 36 else next((c for c in columnas_tpa if 'comentario' in c.lower() or 'observaci' in c.lower()), columnas_tpa[0])
        col_estado_t = columnas_tpa[40] if len(columnas_tpa) > 40 else next((c for c in columnas_tpa if 'nps' in c.lower() or 'estado' in c.lower() or 'promotor' in c.lower() or 'detractor' in c.lower()), columnas_tpa[-1])
        
        df_t_proc = df_tpa_raw.copy()
        df_t_proc = df_t_proc.dropna(subset=[col_mes_t])
        df_t_proc['Mes_Filtro'] = df_t_proc[col_mes_t].astype(str).str.strip().str.capitalize()
        
        meses_orden = { 'Enero': 1, 'Febrero': 2, 'Marzo': 3, 'Abril': 4, 'Mayo': 5, 'Junio': 6, 'Julio': 7, 'Agosto': 8, 'Septiembre': 9, 'Octubre': 10, 'Noviembre': 11, 'Diciembre': 12 }
        df_t_proc['Mes_Num'] = df_t_proc['Mes_Filtro'].map(meses_orden).fillna(99)
        df_t_proc = df_t_proc.sort_values('Mes_Num')
        
        df_t_proc['Estado_NPS'] = df_t_proc[col_estado_t].apply(lambda x: str(x).strip().capitalize() if pd.notna(x) else 'Sin dato')
        df_t_proc['Estado_NPS'] = df_t_proc['Estado_NPS'].replace({'Promotores': 'Promotor', 'Detractores': 'Detractor', 'Neutros': 'Neutro'})

        df_t_proc['Scoring_Clean'] = df_t_proc[col_scoring_t].astype(str).str.lower().str.strip()
        df_t_proc['Scoring_Clean'] = df_t_proc['Scoring_Clean'].str.replace('í', 'i').str.replace('ó', 'o')
        
        meses_disp_tpa_com = [m for m in df_t_proc['Mes_Filtro'].unique() if str(m).lower() != 'nan']
        bocas_disp_tpa_com = sorted(df_t_proc[col_suc_t].dropna().astype(str).unique().tolist())

    # ---------------------------------------------------------
    # PROCESAMIENTO GLOBAL TPA26 (Encuestas de Marca TASA)
    # ---------------------------------------------------------
    df_tpa26_proc = None
    if not df_tpa26_raw.empty:
        cols_tpa26 = df_tpa26_raw.columns.tolist()
        
        col_estado_t26 = cols_tpa26[0] if len(cols_tpa26) > 0 else None
        col_cliente_t26 = cols_tpa26[1] if len(cols_tpa26) > 1 else None
        col_mes_t26 = cols_tpa26[4] if len(cols_tpa26) > 4 else None
        col_nota_t26 = cols_tpa26[5] if len(cols_tpa26) > 5 else None
        col_etapa_t26 = cols_tpa26[6] if len(cols_tpa26) > 6 else None
        col_coment_t26 = cols_tpa26[8] if len(cols_tpa26) > 8 else None

        if col_mes_t26 and col_nota_t26 and col_etapa_t26:
            df_tpa26_proc = df_tpa26_raw.copy()
            
            df_tpa26_proc['Fecha_DT'] = pd.to_datetime(df_tpa26_proc[col_mes_t26], errors='coerce', dayfirst=True)
            df_tpa26_proc['Mes_Num'] = df_tpa26_proc['Fecha_DT'].dt.month.fillna(99)
            meses_es_t26 = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio', 
                            7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}
            df_tpa26_proc['Mes_Filtro'] = df_tpa26_proc['Mes_Num'].map(meses_es_t26).fillna(df_tpa26_proc[col_mes_t26].astype(str))
            
            df_tpa26_proc = df_tpa26_proc.sort_values('Mes_Num')
            df_tpa26_proc['Etapa_Filtro'] = df_tpa26_proc[col_etapa_t26].astype(str).str.strip().str.capitalize()
            df_tpa26_proc['Nota_Num'] = pd.to_numeric(df_tpa26_proc[col_nota_t26], errors='coerce')
            df_tpa26_proc['Estado_NPS'] = df_tpa26_proc['Nota_Num'].apply(obtener_estado_nps)
            df_tpa26_proc['Comentario_Cliente'] = df_tpa26_proc[col_coment_t26].fillna("Sin comentarios")

    # 5. Creación de Pestañas
    tab_convencional, tab_ranking, tab_comisiones, tab_usados, tab_tpa, tab_tpa26, tab_criterios = st.tabs([
        "Venta Convencional 0km - TASA", 
        "Ranking de vendedores 0km – (TASA)", 
        "Comisiones (0KM & TPA)",
        "Usados Certificados – (TASA)",
        "Plan de Ahorro (Interno)",
        "Plan de Ahorro (TASA)",
        "Criterios de puntaje DEP"
    ])

    # --- PESTAÑA 1: VENTA CONVENCIONAL 0KM - TASA ---
    with tab_convencional:
        st.markdown('<div class="sticky-filters">', unsafe_allow_html=True)
        st.write("#### 🔍 Filtros de Visualización (0km)")
        f_col1, f_col2 = st.columns(2)
        
        with f_col1:
            meses_sel = st.multiselect("Filtrar por Mes (Período):", meses_disp_0km, default=meses_disp_0km, key="f_mes_0km")
        with f_col2:
            boca_sel = st.selectbox("Seleccionar Sucursal (Boca de Venta):", ["Todas"] + bocas_disp_0km, key="f_boca_0km")
        st.markdown('</div>', unsafe_allow_html=True)

        df_filtrado = df_procesado.copy()
        if boca_sel != "Todas": df_filtrado = df_filtrado[df_filtrado[col_sucursal].astype(str) == boca_sel]
        if meses_sel: df_filtrado = df_filtrado[df_filtrado['Mes_Período'].isin(meses_sel)]

        df_filtrado['Estado_NPS'] = df_filtrado[col_nps].apply(obtener_estado_nps)
        df_filtrado['Comentario_Cliente'] = df_filtrado[col_comentario_0km].fillna("Sin comentarios")

        st.write("### Estado Actual vs Objetivos (0km)")
        OBJETIVO_SSI = 95.6
        OBJETIVO_NPS = 87.0
        ssi_actual = df_filtrado['SSI_Num'].mean()
        nps_actual = calcular_nps(df_filtrado[col_nps])

        col1, col2 = st.columns(2)
        with col1: st.plotly_chart(crear_reloj(ssi_actual, "Indicador SSI (4,5 ptos) - Objetivo: 95.6", OBJETIVO_SSI, 100), use_container_width=True)
        with col2: st.plotly_chart(crear_reloj(nps_actual, "Indicador NPS (1,2 ptos) - Objetivo: 87%", OBJETIVO_NPS, 100), use_container_width=True)

        st.markdown("---")
        st.write(f"### Desempeño Mensual - Boca de Venta: {boca_sel}")
        
        df_mensual = df_filtrado.sort_values('Mes_Num').groupby('Mes_Nombre', sort=False) if 'Mes_Num' in df_filtrado.columns else df_filtrado.groupby('Mes_Nombre', sort=False)
        resumen_mensual = []
        for mes, grupo in df_mensual:
            fila = {'Mes': mes.capitalize(), 'Q encuestas': len(grupo), 'SSI Puro': grupo['SSI_Num'].mean(), 'NPS dealer': calcular_nps(grupo[col_nps])}
            for c in cols_subindices: fila[c] = grupo[c].mean()
            resumen_mensual.append(fila)

        df_tabla_mensual = pd.DataFrame(resumen_mensual)
        if not df_tabla_mensual.empty:
            fig_evolucion = go.Figure()
            
            fig_evolucion.add_trace(go.Bar(
                x=df_tabla_mensual['Mes'], y=df_tabla_mensual['Q encuestas'], 
                name='Cant. Encuestas', marker_color='rgba(169, 169, 169, 0.3)', 
                yaxis='y2', text=df_tabla_mensual['Q encuestas'].apply(lambda x: f"<b>{x}</b>"), textposition='auto',
                textfont=dict(color='white', size=12)
            ))
            fig_evolucion.add_trace(go.Scatter(
                x=df_tabla_mensual['Mes'], y=df_tabla_mensual['SSI Puro'], 
                mode='lines+markers+text', name='SSI Puro', line=dict(color='#3498db', width=3), 
                text=df_tabla_mensual['SSI Puro'].apply(lambda x: f"<b>{x:.1f}</b>"), textposition='top center',
                textfont=dict(color='white', size=12)
            ))
            fig_evolucion.add_trace(go.Scatter(
                x=df_tabla_mensual['Mes'], y=df_tabla_mensual['NPS dealer'], 
                mode='lines+markers+text', name='NPS dealer', line=dict(color='#2ecc71', width=3), 
                text=df_tabla_mensual['NPS dealer'].apply(lambda x: f"<b>{x:.1f}%</b>" if pd.notna(x) else ""), textposition='bottom center',
                textfont=dict(color='white', size=12)
            ))
            
            y2_max = max(10, df_tabla_mensual['Q encuestas'].max() * 1.5)
            y2_min = - (100 / 110) * y2_max
            
            fig_evolucion.update_layout(
                title="Evolución de SSI, NPS y Volumen de Encuestas",
                yaxis=dict(title="Puntaje / Porcentaje", range=[-100, 110], zeroline=True, zerolinecolor='rgba(231, 76, 60, 0.5)', zerolinewidth=2),
                yaxis2=dict(title="Cantidad de Encuestas", overlaying='y', side='right', range=[y2_min, y2_max], showgrid=False, zeroline=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_evolucion, use_container_width=True)

            totales = {'Mes': 'Total', 'Q encuestas': df_tabla_mensual['Q encuestas'].sum(), 'SSI Puro': df_filtrado['SSI_Num'].mean(), 'NPS dealer': calcular_nps(df_filtrado[col_nps])}
            for c in cols_subindices: totales[c] = df_filtrado[c].mean()
            df_tabla_mensual.loc[len(df_tabla_mensual)] = totales

            formatos = {'Q encuestas': '{:.0f}', 'SSI Puro': '{:.1f}', 'NPS dealer': '{:.1f}%'}
            for c in cols_subindices: formatos[c] = '{:.1f}'
            
            st.dataframe(
                df_tabla_mensual.style.format(formatos, na_rep="-")
                .apply(lambda x: ['font-weight: bold; border-top: 1px solid gray;' if x['Mes'] == 'Total' else '' for i in x], axis=1)
                .map(lambda val: 'color: #2ecc71; font-weight: bold;' if pd.notna(val) and val >= OBJETIVO_SSI else ('color: #e74c3c; font-weight: bold;' if pd.notna(val) else ''), subset=['SSI Puro'])
                .map(lambda val: 'color: #2ecc71; font-weight: bold;' if pd.notna(val) and val >= OBJETIVO_NPS else ('color: #e74c3c; font-weight: bold;' if pd.notna(val) else ''), subset=['NPS dealer']),
                use_container_width=True, hide_index=True
            )
            
            st.write("---")
            st.write("### 💬 Distribución y Detalle de NPS (0km)")
            
            df_nps_valid = df_filtrado[df_filtrado['Estado_NPS'] != 'Sin Dato']
            
            pie_col1, pie_col2 = st.columns(2)
            
            # --- 1. GRÁFICO GLOBAL DE TORA (0km) ---
            conteo_global_0km = df_nps_valid['Estado_NPS'].value_counts().reset_index()
            conteo_global_0km.columns = ['Estado', 'Cantidad']
            fig_pie_0km = px.pie(
                conteo_global_0km, names='Estado', values='Cantidad', title='Distribución General de NPS',
                color='Estado', color_discrete_map={'Promotor': '#2ecc71', 'Neutro': '#f1c40f', 'Detractor': '#e74c3c'}, hole=0.4
            )
            fig_pie_0km.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color='white'))
            pie_col1.plotly_chart(fig_pie_0km, use_container_width=True)
            
            # --- 2. GRÁFICO POR SUCURSAL EN BARRAS (0km) ---
            df_suc_bar_0km = df_nps_valid.groupby([col_sucursal, 'Estado_NPS']).size().reset_index(name='Cantidad')
            fig_bar_suc_0km = px.bar(
                df_suc_bar_0km, x=col_sucursal, y='Cantidad', color='Estado_NPS',
                title='Distribución de NPS por Sucursal', barmode='stack',
                color_discrete_map={'Promotor': '#2ecc71', 'Neutro': '#f1c40f', 'Detractor': '#e74c3c'}
            )
            fig_bar_suc_0km.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color='white'), xaxis_title="Sucursal", yaxis_title="Cantidad")
            pie_col2.plotly_chart(fig_bar_suc_0km, use_container_width=True)
            
            st.write("#### 📋 Registro Detallado de Clientes con Comentarios")
            columnas_tabla = [col_cliente, col_sucursal, col_vendedor, 'Mes_Período', 'Estado_NPS', col_nps]
            df_tabla_nps = df_nps_valid[columnas_tabla].copy()
            df_tabla_nps['Orden_Gravedad'] = df_tabla_nps['Estado_NPS'].map({'Detractor': 1, 'Neutro': 2, 'Promotor': 3})
            df_tabla_nps = df_tabla_nps.sort_values(by=['Orden_Gravedad', 'Mes_Período']).drop(columns=['Orden_Gravedad'])
            df_tabla_nps = df_tabla_nps.rename(columns={
                col_cliente: 'Nombre del Cliente',
                col_sucursal: 'Sucursal', col_vendedor: 'Vendedor', 'Mes_Período': 'Mes',
                'Estado_NPS': 'Clasificación', col_nps: 'Nota NPS'
            })
            
            for idx, row in df_tabla_nps.iterrows():
                comentario_texto = df_nps_valid.loc[idx, 'Comentario_Cliente'] if 'Comentario_Cliente' in df_nps_valid.columns else "Sin comentarios"
                with st.expander(f"👤 {row['Nombre del Cliente']} — Sucursal: {row['Sucursal']} — Clasificación: {row['Clasificación']}"):
                    c_info1, c_info2, c_info3 = st.columns(3)
                    c_info1.write(f"**Vendedor:** {row['Vendedor']}")
                    c_info2.write(f"**Mes:** {row['Mes']}")
                    c_info3.write(f"**Nota NPS:** {row['Nota NPS']}")
                    st.markdown(f"**💬 Comentario del Cliente:** {comentario_texto}")

    # --- PESTAÑA 2: RANKING DE VENDEDORES 0KM – (TASA) ---
    with tab_ranking:
        st.markdown('<div class="sticky-filters">', unsafe_allow_html=True)
        st.write("#### 🔍 Filtros de Ranking (0km)")
        f_rk1, f_rk2 = st.columns(2)
        with f_rk1:
            meses_sel_rk = st.multiselect("Filtrar por Mes (Período):", meses_disp_0km, default=meses_disp_0km, key="f_mes_rk")
        with f_rk2:
            boca_sel_rk = st.selectbox("Seleccionar Sucursal (Boca de Venta):", ["Todas"] + bocas_disp_0km, key="f_boca_rk")
        st.markdown('</div>', unsafe_allow_html=True)

        df_filt_rank = df_procesado.copy()
        if boca_sel_rk != "Todas": df_filt_rank = df_filt_rank[df_filt_rank[col_sucursal].astype(str) == boca_sel_rk]
        if meses_sel_rk: df_filt_rank = df_filt_rank[df_filt_rank['Mes_Período'].isin(meses_sel_rk)]

        st.write("### Ranking de Vendedores y Volumen de Encuestas")
        resumen = []
        for vend, grupo in df_filt_rank.groupby(col_vendedor):
            resumen.append({'Vendedor': vend, 'Encuestas': len(grupo), 'SSI_Promedio': grupo['SSI_Num'].mean(), 'NPS': calcular_nps(grupo[col_nps])})
            
        df_resumen = pd.DataFrame(resumen).dropna(subset=['SSI_Promedio'])
        df_resumen = df_resumen.sort_values('SSI_Promedio', ascending=True)
        
        if not df_resumen.empty:
            fig_ranking = go.Figure()
            
            fig_ranking.add_trace(go.Bar(
                y=df_resumen['Vendedor'], x=df_resumen['SSI_Promedio'], name='SSI', marker_color='#3498db', orientation='h',
                text=df_resumen['SSI_Promedio'].apply(lambda x: f"<b>{x:.1f}</b>"), textposition='auto', textfont=dict(color='white')
            ))
            fig_ranking.add_trace(go.Bar(
                y=df_resumen['Vendedor'], x=df_resumen['NPS'], name='NPS (%)', marker_color='#9b59b6', orientation='h',
                text=df_resumen['NPS'].apply(lambda x: f"<b>{x:.1f}%</b>" if pd.notna(x) else "N/D"), textposition='auto', textfont=dict(color='white')
            ))
            fig_ranking.add_trace(go.Scatter(
                y=df_resumen['Vendedor'], x=df_resumen['Encuestas'], name='Cant. Encuestas', mode='lines+markers+text', 
                xaxis='x2', marker=dict(color='#e67e22', size=12), line=dict(color='#e67e22', dash='dot'), 
                text=df_resumen['Encuestas'].apply(lambda x: f"<b>{x}</b>"), textposition='middle right', textfont=dict(color='white', size=14)
            ))
            
            x2_max_rank = max(10, df_resumen['Encuestas'].max() * 1.5)
            x2_min_rank = - (100 / 110) * x2_max_rank

            altura_dinamica = max(400, len(df_resumen) * 45)

            fig_ranking.update_layout(
                barmode='group', 
                yaxis_title="Vendedor", 
                xaxis=dict(title="Puntaje", range=[-100, 110], zeroline=True, zerolinecolor='rgba(231, 76, 60, 0.5)', zerolinewidth=2), 
                xaxis2=dict(title="Encuestas", overlaying='x', side='top', range=[x2_min_rank, x2_max_rank], showgrid=False, zeroline=False), 
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                height=altura_dinamica,
                margin=dict(l=150)
            )
            st.plotly_chart(fig_ranking, use_container_width=True)

    # --- PESTAÑA 3: COMISIONES (0KM & TPA) ---
    with tab_comisiones:
        st.markdown('<div class="sticky-filters">', unsafe_allow_html=True)
        st.write("#### 🔍 Filtros de Liquidación (Comisiones)")
        f_com1, f_com2, f_com3, f_com4 = st.columns(4)
        with f_com1:
            meses_sel_com_0km = st.multiselect("Meses (0km):", meses_disp_0km, default=meses_disp_0km, key="f_mes_com_0km")
        with f_com2:
            boca_sel_com_0km = st.selectbox("Sucursal (0km):", ["Todas"] + bocas_disp_0km, key="f_boca_com_0km")
        with f_com3:
            if df_t_proc is not None:
                meses_sel_tpa_com = st.multiselect("Meses (TPA):", meses_disp_tpa_com, default=meses_disp_tpa_com, key="f_mes_com_tpa")
        with f_com4:
            if df_t_proc is not None:
                boca_sel_tpa_com = st.multiselect("Sucursal (TPA):", bocas_disp_tpa_com, default=bocas_disp_tpa_com, key="f_boca_com_tpa")
        st.markdown('</div>', unsafe_allow_html=True)

        st.write("### 💰 Tabla de Cálculo de Comisiones SSI (0km)")
        if not col_atencion_vend: st.error("No se detectó la columna '02 Atencion Vendedor' en los datos.")
        else:
            df_com_0km_filt = df_procesado.copy()
            if meses_sel_com_0km:
                df_com_0km_filt = df_com_0km_filt[df_com_0km_filt['Mes_Período'].isin(meses_sel_com_0km)]
            if boca_sel_com_0km != "Todas":
                df_com_0km_filt = df_com_0km_filt[df_com_0km_filt[col_sucursal].astype(str) == boca_sel_com_0km]

            datos_comision = []
            for vend, grupo in df_com_0km_filt.groupby(col_vendedor):
                cant_encuestas, ssi_promedio, atencion_promedio = len(grupo), grupo['SSI_Num'].mean(), grupo[col_atencion_vend].mean()
                if pd.isna(atencion_promedio) or cant_encuestas == 0: comision = 0.00
                elif atencion_promedio*10 < 95.5: comision = -0.05
                else: comision = 0.01
                datos_comision.append({
                    'Vendedor': vend, 'Cantidad de Encuestas': cant_encuestas,
                    'Atención del Vendedor (x10)': (atencion_promedio * 10 if pd.notna(atencion_promedio) else np.nan),
                    'SSI Promedio': ssi_promedio, 'Comisión SSI': comision
                })
            df_comisiones = pd.DataFrame(datos_comision)
            if not df_comisiones.empty:
                df_comisiones = df_comisiones.sort_values('Atención del Vendedor (x10)', ascending=False)
                st.dataframe(
                    df_comisiones.style.format({'Atención del Vendedor (x10)': '{:.1f}', 'SSI Promedio': '{:.1f}', 'Comisión SSI': '{:.2f}'})
                    .map(lambda val: 'color: #e74c3c; font-weight: bold;' if val == -0.05 else ('color: #2ecc71; font-weight: bold;' if val == 0.01 else 'color: #7f8c8d;'), subset=['Comisión SSI']),
                    use_container_width=True, hide_index=True
                )
            else: st.warning("Datos insuficientes para el cálculo de comisiones de 0km en el período y sucursal seleccionados.")

        st.markdown("---")
        st.write("### 💰 Tabla de Cálculo de Comisiones NPS (Toyota Plan de Ahorro)")
        
        if df_t_proc is not None:
            df_tpa_comision = df_t_proc.copy()
            if meses_sel_tpa_com: 
                df_tpa_comision = df_tpa_comision[df_tpa_comision['Mes_Filtro'].isin(meses_sel_tpa_com)]
            if boca_sel_tpa_com:
                df_tpa_comision = df_tpa_comision[df_tpa_comision[col_suc_t].astype(str).isin(boca_sel_tpa_com)]
                
            df_nps_valid_com = df_tpa_comision[df_tpa_comision['Estado_NPS'].isin(['Promotor', 'Neutro', 'Detractor'])]
            
            datos_comision_tpa = []
            for vend, grupo in df_nps_valid_com.groupby(col_vend_t):
                cant_encuestas = len(grupo)
                if cant_encuestas == 0: continue
                
                nps_vendedor = calcular_nps_texto(grupo['Estado_NPS'])
                
                comision = 0.00
                if pd.notna(nps_vendedor):
                    if nps_vendedor >= 85.0:
                        comision = 0.01
                    else:
                        comision = -0.05
                        
                datos_comision_tpa.append({
                    'Vendedor': vend,
                    'Cantidad de Encuestas': cant_encuestas,
                    'NPS Promedio': nps_vendedor,
                    'Comisión TPA': comision
                })
                
            df_comisiones_tpa = pd.DataFrame(datos_comision_tpa)
            if not df_comisiones_tpa.empty:
                df_comisiones_tpa = df_comisiones_tpa.sort_values('NPS Promedio', ascending=False)
                st.dataframe(
                    df_comisiones_tpa.style.format({'NPS Promedio': '{:.1f}%', 'Comisión TPA': '{:.2f}'})
                    .map(lambda val: 'color: #e74c3c; font-weight: bold;' if val == -0.05 else ('color: #2ecc71; font-weight: bold;' if val == 0.01 else 'color: #7f8c8d;'), subset=['Comisión TPA']),
                    use_container_width=True, hide_index=True
                )
            else:
                st.warning("No hay encuestas válidas de TPA en el período y sucursal seleccionados para calcular comisiones.")
        else:
            st.warning("No se pudo cargar la hoja de TPA. Verifica que el enlace sea correcto.")

    # --- PESTAÑA 4: USADOS CERTIFICADOS – (TASA) ---
    with tab_usados:
        st.markdown('<div class="sticky-filters">', unsafe_allow_html=True)
        st.write("#### 🔍 Filtros de Período y Sucursal (UCT)")
        filtro_u1, filtro_u2 = st.columns(2)
        with filtro_u1:
            meses_disp_u = [m for m in df_usados_raw["Mes" if "Mes" in df_usados_raw.columns else df_usados_raw.columns[2]].astype(str).str.strip().str.capitalize().unique() if m.lower() != 'nan']
            mes_sel_u = st.multiselect("Seleccionar Meses (USADO26):", meses_disp_u, default=meses_disp_u, key="f_mes_uct")
        with filtro_u2:
            col_suc_uct_name = next((c for c in df_usados_raw.columns.tolist() if 'boca' in c.lower() or 'sucursal' in c.lower() or 'concesionario' in c.lower()), df_usados_raw.columns[0])
            bocas_disp_u = sorted(df_usados_raw[col_suc_uct_name].dropna().astype(str).unique().tolist())
            boca_sel_u = st.multiselect("Seleccionar Sucursal (USADO26):", bocas_disp_u, default=bocas_disp_u, key="f_boca_uct")
        st.markdown('</div>', unsafe_allow_html=True)

        st.write("### 🚗 Gestión de Calidad: Toyota Usados Certificados (UCT)")
        st.write("Métricas exclusivas y evolución de satisfacción para el canal de Usados.")
        
        if not df_usados_raw.empty:
            columnas_u = df_usados_raw.columns.tolist()
            col_nps_u = columnas_u[16] if len(columnas_u) > 16 else columnas_u[-1]
            col_ssi_u = next((c for c in columnas_u if 'ssi' in c.lower()), columnas_u[0])
            col_fecha_u = "Mes" if "Mes" in columnas_u else columnas_u[2]
            top_5_cols = columnas_u[5:10] if len(columnas_u) >= 10 else []
            col_cliente_u = next((c for c in columnas_u if 'cliente' in c.lower() or 'nombre' in c.lower() or 'razon' in c.lower()), columnas_u[0])
            col_comentario_uct = columnas_u[15] if len(columnas_u) > 15 else columnas_u[-1]
            col_vendedor_u = next((c for c in columnas_u if 'vendedor' in c.lower() or 'asesor' in c.lower()), columnas_u[0])
            col_sucursal_u = next((c for c in columnas_u if 'boca' in c.lower() or 'sucursal' in c.lower() or 'concesionario' in c.lower()), columnas_u[0])
            
            df_u_proc = df_usados_raw.copy()
            df_u_proc['Mes_Filtro'] = df_u_proc[col_fecha_u].astype(str).str.strip().str.capitalize()
            
            df_u_filt = df_u_proc.copy()
            if mes_sel_u: df_u_filt = df_u_filt[df_u_filt['Mes_Filtro'].isin(mes_sel_u)]
            if boca_sel_u: df_u_filt = df_u_filt[df_u_filt[col_sucursal_u].astype(str).isin(boca_sel_u)]
            
            df_u_filt['SSI_Num'] = pd.to_numeric(df_u_filt[col_ssi_u].astype(str).str.replace(',', '.').str.replace('%', ''), errors='coerce')
            for c in top_5_cols:
                df_u_filt[c] = pd.to_numeric(df_u_filt[c].astype(str).str.replace(',', '.').str.replace('%', ''), errors='coerce')
                
            df_u_filt['Estado_NPS'] = df_u_filt[col_nps_u].apply(obtener_estado_nps)
            df_u_filt['Comentario_Cliente'] = df_u_filt[col_comentario_uct].fillna("Sin comentarios")
                
            OBJ_SSI_UCT = 94.5
            OBJ_NPS_UCT = 89.0
            
            ssi_uct_actual = df_u_filt['SSI_Num'].mean()
            df_u_valid_nps = df_u_filt[df_u_filt['Estado_NPS'].isin(['Promotor', 'Neutro', 'Detractor'])]
            nps_uct_actual = calcular_nps_texto(df_u_valid_nps['Estado_NPS']) if len(df_u_valid_nps) > 0 else calcular_nps(df_u_filt[col_nps_u])
            
            st.write("#### ⏱️ Estado Actual vs Objetivos UCT")
            cu1, cu2 = st.columns(2)
            with cu1: st.plotly_chart(crear_reloj(ssi_uct_actual, "SSI UCT (0,8 ptos) - Objetivo: 94.5", OBJ_SSI_UCT, 100), use_container_width=True)
            with cu2: st.plotly_chart(crear_reloj(nps_uct_actual, "NPS UCT (0,8 ptos) - Objetivo: 89%", OBJ_NPS_UCT, 100), use_container_width=True)
            
            st.write("#### 📊 Evolución de los 5 Principales Indicadores")
            if top_5_cols:
                df_u_mensual = df_u_filt.groupby('Mes_Filtro', sort=False)
                res_u = []
                for mes, grupo in df_u_mensual:
                    grp_valid = grupo[grupo['Estado_NPS'].isin(['Promotor', 'Neutro', 'Detractor'])]
                    nps_mes = calcular_nps_texto(grp_valid['Estado_NPS']) if len(grp_valid) > 0 else np.nan
                    
                    fila = {'Mes': mes, 'Q encuestas': len(grupo), 'SSI UCT': grupo['SSI_Num'].mean(), 'NPS UCT': nps_mes}
                    for c in top_5_cols: fila[c] = grupo[c].mean()
                    res_u.append(fila)
                    
                if res_u:
                    df_res_u = pd.DataFrame(res_u)
                    fig_evo_u = go.Figure()
                    fig_evo_u.add_trace(go.Bar(
                        x=df_res_u['Mes'], y=df_res_u['Q encuestas'], 
                        name='Cant. Encuestas', marker_color='rgba(169, 169, 169, 0.3)', 
                        yaxis='y2', text=df_res_u['Q encuestas'].apply(lambda x: f"<b>{x}</b>"), textposition='auto',
                        textfont=dict(color='white', size=12)
                    ))
                    fig_evo_u.add_trace(go.Scatter(
                        x=df_res_u['Mes'], y=df_res_u['SSI UCT'], 
                        mode='lines+markers+text', name='SSI UCT', line=dict(color='#3498db', width=3), 
                        text=df_res_u['SSI UCT'].apply(lambda x: f"<b>{x:.1f}</b>"), textposition='top center',
                        textfont=dict(color='white', size=12)
                    ))
                    fig_evo_u.add_trace(go.Scatter(
                        x=df_res_u['Mes'], y=df_res_u['NPS UCT'], 
                        mode='lines+markers+text', name='NPS UCT', line=dict(color='#2ecc71', width=3), 
                        text=df_res_u['NPS UCT'].apply(lambda x: f"<b>{x:.1f}%</b>" if pd.notna(x) else ""), textposition='bottom center',
                        textfont=dict(color='white', size=12)
                    ))
                    
                    y2_max_u = max(10, df_res_u['Q encuestas'].max() * 1.5)
                    y2_min_u = - (100 / 110) * y2_max_u

                    fig_evo_u.update_layout(
                        title="Evolución de SSI, NPS y Volumen de Encuestas (UCT)",
                        yaxis=dict(title="Puntaje / Porcentaje", range=[-100, 110], zeroline=True, zerolinecolor='rgba(231, 76, 60, 0.5)', zerolinewidth=2),
                        yaxis2=dict(title="Cantidad de Encuestas", overlaying='y', side='right', range=[y2_min_u, y2_max_u], showgrid=False, zeroline=False),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
                    )
                    st.plotly_chart(fig_evo_u, use_container_width=True)

                    totales_u = {'Mes': 'Total', 'Q encuestas': df_res_u['Q encuestas'].sum(), 'SSI UCT': ssi_uct_actual, 'NPS UCT': nps_uct_actual}
                    for c in top_5_cols: totales_u[c] = df_u_filt[c].mean()
                    df_res_u.loc[len(df_res_u)] = totales_u
                    
                    formatos_u = {'Q encuestas': '{:.0f}', 'SSI UCT': '{:.1f}', 'NPS UCT': '{:.1f}%'}
                    for c in top_5_cols: formatos_u[c] = '{:.1f}'
                    
                    st.dataframe(
                        df_res_u.style.format(formatos_u, na_rep="-")
                        .apply(lambda x: ['font-weight: bold; border-top: 1px solid gray;' if x['Mes'] == 'Total' else '' for i in x], axis=1)
                        .map(lambda val: 'color: #2ecc71; font-weight: bold;' if pd.notna(val) and val >= OBJ_SSI_UCT else ('color: #e74c3c; font-weight: bold;' if pd.notna(val) else ''), subset=['SSI UCT'])
                        .map(lambda val: 'color: #2ecc71; font-weight: bold;' if pd.notna(val) and val >= OBJ_NPS_UCT else ('color: #e74c3c; font-weight: bold;' if pd.notna(val) else ''), subset=['NPS UCT']),
                        use_container_width=True, hide_index=True
                    )
                    
                    st.write("---")
                    st.write("### 💬 Distribución y Detalle de NPS (UCT)")
                    
                    df_nps_valid_u = df_u_filt[df_u_filt['Estado_NPS'] != 'Sin Dato']
                    
                    pie_u1, pie_u2 = st.columns(2)
                    
                    # --- 1. GRÁFICO GLOBAL DE TORA (UCT) ---
                    conteo_global_uct = df_nps_valid_u['Estado_NPS'].value_counts().reset_index()
                    conteo_global_uct.columns = ['Estado', 'Cantidad']
                    fig_pie_uct = px.pie(
                        conteo_global_uct, names='Estado', values='Cantidad', title='Distribución General de NPS (UCT)',
                        color='Estado', color_discrete_map={'Promotor': '#2ecc71', 'Neutro': '#f1c40f', 'Detractor': '#e74c3c'}, hole=0.4
                    )
                    fig_pie_uct.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color='white'))
                    pie_u1.plotly_chart(fig_pie_uct, use_container_width=True)
                    
                    # --- 2. GRÁFICO POR TIPO DE CLIENTE EN BARRAS (UCT) ---
                    df_tipo_bar_uct = df_nps_valid_u.groupby([col_vendedor, 'Estado_NPS']).size().reset_index(name='Cantidad')
                    fig_bar_tipo_uct = px.bar(
                        df_tipo_bar_uct, x=col_vendedor, y='Cantidad', color='Estado_NPS',
                        title='Distribución de NPS por Asesor / Tipo', barmode='stack',
                        color_discrete_map={'Promotor': '#2ecc71', 'Neutro': '#f1c40f', 'Detractor': '#e74c3c'}
                    )
                    fig_bar_tipo_uct.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color='white'), xaxis_title="Asesor / Vendedor", yaxis_title="Cantidad")
                    pie_u2.plotly_chart(fig_bar_tipo_uct, use_container_width=True)
                    
                    st.write("#### 📋 Registro Detallado de Clientes con Comentarios (UCT)")
                    columnas_tabla_u = [col_cliente_u, col_sucursal_u, col_vendedor_u, 'Mes_Filtro', 'Estado_NPS', col_nps_u]
                    df_tabla_nps_u = df_nps_valid_u[columnas_tabla_u].copy()
                    df_tabla_nps_u['Orden_Gravedad'] = df_tabla_nps_u['Estado_NPS'].map({'Detractor': 1, 'Neutro': 2, 'Promotor': 3})
                    df_tabla_nps_u = df_tabla_nps_u.sort_values(by=['Orden_Gravedad', 'Mes_Filtro']).drop(columns=['Orden_Gravedad'])
                    df_tabla_nps_u = df_tabla_nps_u.rename(columns={
                        col_cliente_u: 'Nombre del Cliente',
                        col_sucursal_u: 'Sucursal', col_vendedor_u: 'Vendedor', 'Mes_Filtro': 'Mes',
                        'Estado_NPS': 'Clasificación', col_nps_u: 'Nota NPS'
                    })
                    
                    for idx, row in df_tabla_nps_u.iterrows():
                        comentario_texto_u = df_nps_valid_u.loc[idx, 'Comentario_Cliente'] if 'Comentario_Cliente' in df_nps_valid_u.columns else "Sin comentarios"
                        with st.expander(f"👤 {row['Nombre del Cliente']} — Sucursal: {row['Sucursal']} — Clasificación: {row['Clasificación']}"):
                            c_u1, c_u2, c_u3 = st.columns(3)
                            c_u1.write(f"**Vendedor:** {row['Vendedor']}")
                            c_u2.write(f"**Mes:** {row['Mes']}")
                            c_u3.write(f"**Nota NPS:** {row['Nota NPS']}")
                            st.markdown(f"**💬 Comentario del Cliente:** {comentario_texto_u}")

                else:
                    st.warning("No hay datos para el período seleccionado.")
            else:
                st.error("No se encontraron las columnas F a J (índices 5 al 9) en la hoja de Usados.")
        else:
            st.warning("No se pudo cargar la hoja USADO26. Verifica que la URL o el nombre de la hoja sean correctos.")

    # --- PESTAÑA 5: PLAN DE AHORRO (INTERNO) ---
    with tab_tpa:
        st.markdown('<div class="sticky-filters">', unsafe_allow_html=True)
        st.write("#### 🔍 Filtros de Período y Sucursal (TPA)")
        filtro_t1, filtro_t2 = st.columns(2)
        with filtro_t1:
            meses_disp_t = [m for m in df_t_proc['Mes_Filtro'].unique() if str(m).lower() != 'nan'] if df_t_proc is not None else []
            mes_sel_t = st.multiselect("Seleccionar Meses (TPA):", meses_disp_t, default=meses_disp_t, key="f_mes_tpa")
        with filtro_t2:
            bocas_disp_t = sorted(df_t_proc[col_suc_t].dropna().astype(str).unique().tolist()) if df_t_proc is not None else []
            boca_sel_t = st.multiselect("Seleccionar Sucursal (TPA):", bocas_disp_t, default=bocas_disp_t, key="f_boca_tpa")
        st.markdown('</div>', unsafe_allow_html=True)

        st.write("### 📘 Gestión de Calidad: Toyota Plan de Ahorro (TPA)")
        st.write("Métricas y evolución de satisfacción exclusiva para TPA.")
        
        if df_t_proc is not None:
            df_t_filt = df_t_proc.copy()
            if mes_sel_t: df_t_filt = df_t_filt[df_t_filt['Mes_Filtro'].isin(mes_sel_t)]
            if boca_sel_t: df_t_filt = df_t_filt[df_t_filt[col_suc_t].astype(str).isin(boca_sel_t)]
            
            df_t_filt['Comentario_Cliente'] = df_t_filt[col_coment_t].fillna("Sin comentarios")
            df_nps_valid_t = df_t_filt[df_t_filt['Estado_NPS'].isin(['Promotor', 'Neutro', 'Detractor'])].copy()
            
            OBJETIVO_NPS_TPA = 85.0
            nps_tpa_actual = calcular_nps_texto(df_nps_valid_t['Estado_NPS'])
            
            st.write("#### ⏱️ Estado Actual vs Objetivo TPA (Global)")
            ct1, ct2 = st.columns(2)
            with ct1:
                st.plotly_chart(crear_reloj(nps_tpa_actual, "NPS Transaccional TPA (0,8 ptos)", OBJETIVO_NPS_TPA, 100), use_container_width=True)
            with ct2:
                st.markdown(f'''
                    <div style="background-color:#F8FAFC; padding:15px; border-radius:8px; border-left:5px solid #3498db; box-shadow:0 1px 3px rgba(0,0,0,0.05); text-align:center; height:100%; display:flex; flex-direction:column; justify-content:center;">
                        <span style="color:#555; font-size:16px; font-weight:bold;">TOTAL DE ENCUESTAS VÁLIDAS (TPA)</span><br>
                        <span style="font-size:48px; font-weight:bold; color:#1E3A8A;">{len(df_nps_valid_t)}</span>
                    </div>
                ''', unsafe_allow_html=True)
            
            st.markdown("---")
            st.write("#### 📊 NPS y Detalle por Sucursal")

            sucursales_validas = [s for s in df_nps_valid_t[col_suc_t].dropna().astype(str).unique() if s.strip() != '']
            if not sucursales_validas:
                st.info("No se encontraron sucursales para mostrar con las encuestas seleccionadas.")
            else:
                relojes_tpa_cols = st.columns(len(sucursales_validas))
                barras_tpa_cols = st.columns(len(sucursales_validas))

                for idx, suc in enumerate(sucursales_validas):
                    df_suc = df_nps_valid_t[df_nps_valid_t[col_suc_t].astype(str) == suc]
                    nps_suc = calcular_nps_texto(df_suc['Estado_NPS'])

                    with relojes_tpa_cols[idx]:
                        st.plotly_chart(crear_reloj(nps_suc, f"NPS - {suc}", OBJETIVO_NPS_TPA, 100), use_container_width=True)

                    with barras_tpa_cols[idx]:
                        conteo_suc = df_suc['Estado_NPS'].value_counts().reindex(['Detractor', 'Neutro', 'Promotor']).fillna(0).reset_index()
                        conteo_suc.columns = ['Tipo de cliente', 'Recuento']

                        fig_bar_tpa = px.bar(
                            conteo_suc, x='Recuento', y='Tipo de cliente', orientation='h',
                            text='Recuento', color_discrete_sequence=['#3498db']
                        )
                        fig_bar_tpa.update_layout(
                            title=f"Recuento de registros ({suc})",
                            xaxis_title="",
                            yaxis_title="Tipo de cliente",
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            height=250,
                            margin=dict(l=0, r=0, t=30, b=0),
                            xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
                        )
                        fig_bar_tpa.update_traces(textposition='outside')
                        st.plotly_chart(fig_bar_tpa, use_container_width=True)

                        with st.expander(f"Ver informe ({suc})"):
                            columnas_tabla_t = [col_cliente_t, 'Comentario_Cliente', col_vend_t, 'Mes_Filtro', 'Estado_NPS']
                            df_tabla_nps_t = df_suc[columnas_tabla_t].copy()
                            df_tabla_nps_t['Orden_Gravedad'] = df_tabla_nps_t['Estado_NPS'].map({'Detractor': 1, 'Neutro': 2, 'Promotor': 3})
                            df_tabla_nps_t = df_tabla_nps_t.sort_values(by=['Orden_Gravedad', 'Mes_Filtro']).drop(columns=['Orden_Gravedad'])
                            df_tabla_nps_t = df_tabla_nps_t.rename(columns={
                                col_cliente_t: 'Nombre del Suscriptor',
                                'Comentario_Cliente': 'Comentario del Cliente',
                                col_vend_t: 'Vendedor',
                                'Mes_Filtro': 'Mes',
                                'Estado_NPS': 'Clasificación'
                            })

                            def color_clasificacion_t(val):
                                if val == 'Detractor': return 'color: #e74c3c; font-weight: bold;'
                                elif val == 'Promotor': return 'color: #2ecc71; font-weight: bold;'
                                elif val == 'Neutro': return 'color: #f1c40f; font-weight: bold;'
                                return ''

                            st.dataframe(df_tabla_nps_t.style.map(color_clasificacion_t, subset=['Clasificación']), use_container_width=True, hide_index=True)

            st.markdown("---")
            with st.expander("📥 Ver tabla general completa y panel de alertas Scoring TPA"):
                
                # --- INDICADORES DE SCORING Y BUSCADOR AL LADO ---
                col_score_metrics, col_score_search = st.columns([3, 1])
                
                with col_score_metrics:
                    df_scoring = df_t_filt[df_t_filt['Scoring_Clean'].isin(['ok', 'pendiente', 'caido', 'caído', 'caida'])].copy()
                    total_scoring = len(df_scoring)
                    cant_ok = len(df_scoring[df_scoring['Scoring_Clean'] == 'ok'])
                    cant_pend = len(df_scoring[df_scoring['Scoring_Clean'] == 'pendiente'])
                    cant_caido = len(df_scoring[df_scoring['Scoring_Clean'].isin(['caido', 'caído', 'caida'])])
                    pct_ok = (cant_ok / total_scoring * 100) if total_scoring > 0 else 0
                    
                    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
                    sc1.metric("Total", total_scoring)
                    sc2.metric("✅ OK", cant_ok)
                    sc3.metric("⏳ Pend.", cant_pend)
                    sc4.metric("❌ Caídos", cant_caido)
                    sc5.metric("🎯 % OK", f"{pct_ok:.1f}%")

                with col_score_search:
                    busqueda_query = st.text_input("🔍 Buscar Vendedor / Cliente:", placeholder="Escriba aquí...", key="search_tpa_box")

                df_tabla_t_general = df_nps_valid_t.copy()
                if busqueda_query:
                    q = busqueda_query.lower()
                    mask = df_tabla_t_general[col_cliente_t].astype(str).str.lower().str.contains(q) | df_tabla_t_general[col_vend_t].astype(str).str.lower().str.contains(q)
                    df_tabla_t_general = df_tabla_t_general[mask]

                st.write("#### 📋 Registro Detallado de Clientes (General)")
                columnas_tabla_t_general = [col_cliente_t, 'Comentario_Cliente', col_suc_t, col_vend_t, 'Mes_Filtro', 'Estado_NPS']
                df_tabla_t_general_show = df_tabla_t_general[columnas_tabla_t_general].copy()
                df_tabla_t_general_show['Orden_Gravedad'] = df_tabla_t_general_show['Estado_NPS'].map({'Detractor': 1, 'Neutro': 2, 'Promotor': 3})
                df_tabla_t_general_show = df_tabla_t_general_show.sort_values(by=['Orden_Gravedad', 'Mes_Filtro']).drop(columns=['Orden_Gravedad'])
                df_tabla_t_general_show = df_tabla_t_general_show.rename(columns={
                    col_cliente_t: 'Nombre del Suscriptor',
                    'Comentario_Cliente': 'Comentario del Cliente',
                    col_suc_t: 'Sucursal',
                    col_vend_t: 'Vendedor',
                    'Mes_Filtro': 'Mes',
                    'Estado_NPS': 'Clasificación'
                })

                def color_clasificacion_t(val):
                    if val == 'Detractor': return 'color: #e74c3c; font-weight: bold;'
                    elif val == 'Promotor': return 'color: #2ecc71; font-weight: bold;'
                    elif val == 'Neutro': return 'color: #f1c40f; font-weight: bold;'
                    return ''

                st.dataframe(df_tabla_t_general_show.style.map(color_clasificacion_t, subset=['Clasificación']), use_container_width=True, hide_index=True)

                st.write("---")
                st.write("##### ⚠️ Detalle de Operaciones Pendientes y Caídas")
                df_alertas_scoring = df_scoring[df_scoring['Scoring_Clean'].isin(['pendiente', 'caido', 'caído', 'caida'])].copy()
                
                if not df_alertas_scoring.empty:
                    cols_to_show = [col_vend_t, col_suc_t, col_cliente_t, 'Mes_Filtro', col_scoring_t]
                    df_alertas_show = df_alertas_scoring[cols_to_show].rename(columns={
                        col_vend_t: 'Vendedor', col_suc_t: 'Sucursal', col_cliente_t: 'Cliente',
                        'Mes_Filtro': 'Mes', col_scoring_t: 'Estado Scoring'
                    })
                    
                    def color_scoring(val):
                        v = str(val).lower()
                        if 'caid' in v: return 'color: #e74c3c; font-weight: bold;'
                        if 'pend' in v: return 'color: #f1c40f; font-weight: bold;'
                        return ''
                        
                    st.dataframe(df_alertas_show.style.map(color_scoring, subset=['Estado Scoring']), use_container_width=True, hide_index=True)
                else:
                    st.success("🎉 ¡Excelente! No hay operaciones pendientes ni caídas en el período seleccionado.")

        else:
            st.warning("No se pudo cargar la hoja de TPA. Verifica que el enlace sea correcto.")

    # --- PESTAÑA 6: PLAN DE AHORRO (TASA) ---
    with tab_tpa26:
        st.markdown('<div class="sticky-filters">', unsafe_allow_html=True)
        st.write("#### 🔍 Filtros de Período y Etapa (TPA26 - Toyota)")
        filtro_t26_1, filtro_t26_2 = st.columns(2)
        with filtro_t26_1:
            meses_disp_t26 = [m for m in df_tpa26_proc['Mes_Filtro'].unique() if str(m).lower() not in ['nan', 'nat']] if df_tpa26_proc is not None else []
            mes_sel_t26 = st.multiselect("Seleccionar Meses (TPA26):", meses_disp_t26, default=meses_disp_t26, key="f_mes_tpa26")
        with filtro_t26_2:
            etapas_disp_t26 = sorted(df_tpa26_proc['Etapa_Filtro'].dropna().unique().tolist()) if df_tpa26_proc is not None else []
            etapa_sel_t26 = st.multiselect("Seleccionar Etapa:", etapas_disp_t26, default=etapas_disp_t26, key="f_etapa_tpa26")
        st.markdown('</div>', unsafe_allow_html=True)

        if df_tpa26_proc is not None:
            df_t26_filt = df_tpa26_proc.copy()
            if mes_sel_t26: df_t26_filt = df_t26_filt[df_t26_filt['Mes_Filtro'].isin(mes_sel_t26)]
            if etapa_sel_t26: df_t26_filt = df_t26_filt[df_t26_filt['Etapa_Filtro'].isin(etapa_sel_t26)]

            df_nps_valid_t26 = df_t26_filt[df_t26_filt['Estado_NPS'].isin(['Promotor', 'Neutro', 'Detractor'])].copy()

            OBJETIVO_NPS_T26 = 85.0
            nps_t26_global = calcular_nps_texto(df_nps_valid_t26['Estado_NPS'])

            st.write("### 📈 Encuestas de Marca (Toyota - TPA26)")
            st.write("Métricas de satisfacción global y por etapa.")

            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(crear_reloj(nps_t26_global, "NPS Transaccional (Global)", OBJETIVO_NPS_T26, 100), use_container_width=True)
            with c2:
                st.markdown(f'''
                    <div style="background-color:#F8FAFC; padding:15px; border-radius:8px; border-left:5px solid #3498db; box-shadow:0 1px 3px rgba(0,0,0,0.05); text-align:center; height:100%; display:flex; flex-direction:column; justify-content:center;">
                        <span style="color:#555; font-size:16px; font-weight:bold;">TOTAL DE ENCUESTAS</span><br>
                        <span style="font-size:48px; font-weight:bold; color:#1E3A8A;">{len(df_nps_valid_t26)}</span>
                    </div>
                ''', unsafe_allow_html=True)
            
            st.markdown("---")
            st.write("#### 📊 Desglose de NPS por Etapa")
            
            etapas_unicas = [e for e in df_nps_valid_t26['Etapa_Filtro'].unique() if e.lower() != 'nan']
            
            if etapas_unicas:
                relojes_cols = st.columns(len(etapas_unicas))
                barras_cols = st.columns(len(etapas_unicas))
                
                for i, etapa in enumerate(etapas_unicas):
                    df_etapa = df_nps_valid_t26[df_nps_valid_t26['Etapa_Filtro'] == etapa]
                    nps_etapa = calcular_nps_texto(df_etapa['Estado_NPS'])
                    
                    with relojes_cols[i]:
                        st.plotly_chart(crear_reloj(nps_etapa, f"NPS - {etapa}", OBJETIVO_NPS_T26, 100), use_container_width=True)
                        
                    with barras_cols[i]:
                        conteo = df_etapa['Estado_NPS'].value_counts().reindex(['Detractor', 'Neutro', 'Promotor']).fillna(0).reset_index()
                        conteo.columns = ['Tipo de cliente', 'Recuento']
                        
                        fig_bar = px.bar(
                            conteo, x='Recuento', y='Tipo de cliente', orientation='h',
                            text='Recuento', color_discrete_sequence=['#3498db']
                        )
                        fig_bar.update_layout(
                            title="Recuento de registros",
                            xaxis_title="",
                            yaxis_title="Tipo de cliente",
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            height=250,
                            margin=dict(l=0, r=0, t=30, b=0),
                            xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'),
                        )
                        fig_bar.update_traces(textposition='outside')
                        st.plotly_chart(fig_bar, use_container_width=True)
                        
                        with st.expander(f"Ver informe ({etapa})"):
                            cols_to_show_t26 = [col_cliente_t26, col_nota_t26, 'Estado_NPS', 'Comentario_Cliente']
                            df_tabla_t26 = df_etapa[cols_to_show_t26].copy()
                            
                            df_tabla_t26['Orden_Gravedad'] = df_tabla_t26['Estado_NPS'].map({'Detractor': 1, 'Neutro': 2, 'Promotor': 3})
                            df_tabla_t26 = df_tabla_t26.sort_values(by=['Orden_Gravedad'])
                            df_tabla_t26 = df_tabla_t26.drop(columns=['Orden_Gravedad'])
                            
                            df_tabla_t26 = df_tabla_t26.rename(columns={
                                col_cliente_t26: 'Nombre del Cliente',
                                col_nota_t26: 'Nota',
                                'Estado_NPS': 'Clasificación',
                                'Comentario_Cliente': 'Comentario'
                            })

                            def color_clasificacion_t26(val):
                                if val == 'Detractor': return 'color: #e74c3c; font-weight: bold;'
                                elif val == 'Promotor': return 'color: #2ecc71; font-weight: bold;'
                                elif val == 'Neutro': return 'color: #f1c40f; font-weight: bold;'
                                return ''
                                
                            st.dataframe(df_tabla_t26.style.map(color_clasificacion_t26, subset=['Clasificación']), use_container_width=True, hide_index=True)
        else:
            st.warning("No se pudo cargar la hoja TPA26. Verifica que existan las columnas indicadas.")

    # --- PESTAÑA 7: CRITERIOS DE PUNTAJE DEP ---
    with tab_criterios:
        st.write("### 📋 Criterios de puntaje DEP")
        st.write("Resumen de las métricas, puntajes máximos otorgados y porcentajes de alcance para objetivos y comisiones.")
        st.markdown("---")

        col_ventas, col_usados, col_tpa = st.columns(3)

        with col_ventas:
            st.markdown("#### 🚗 Ventas Convencional (0km)")

            st.markdown("**1. Sales Satisfaction Index (SSI) — `4,5 ptos`**")
            st.markdown("""
            | % de Alcance (SSI YTD) | % Cantidad de Encuestas | % de Puntos |
            | :--- | :--- | :--- |
            | ≥ 95,6% | ≥ % Promedio RED | 100% |
            | ≥ 95,6% | < % Promedio RED | 75% |
            | 95,6% > X ≥ 95% | ≥ % Promedio RED | 75% |
            | 95,6% > X ≥ 95% | < % Promedio RED | 50% |
            | 95% > X ≥ 94,5% | ≥ % Promedio RED | 50% |
            | 95% > X ≥ 94,5% | < % Promedio RED | 25% |
            | < 94,5% | - | 0% |
            """)

            st.markdown("**2. Net Promoter Score (NPS) — `1,2 ptos`**")
            st.markdown("""
            | % de Alcance (NPS YTD) | % de Puntos |
            | :--- | :--- |
            | ≥ 87% | 100% |
            | 82% < X ≤ 87% | 50% |
            | < 82% | 0% |
            """)

            st.markdown("**3. Índice de Contención de Quejas (ICQ) — `1,5 ptos`**")
            st.markdown("""
            | Estado (ICQ Ventas) | % de Puntos |
            | :--- | :--- |
            | ≤ 0,05 | 100% |
            | 0,05 a 0,15 | 75% |
            | 0,15 a 0,30 | 50% |
            | > 0,30 | 0% |
            """)

        with col_usados:
            st.markdown("#### 🚙 Usados Certificados (UCT)")

            st.markdown("**1. Sales Satisfaction Index (SSI) — `0,8 ptos`**")
            st.markdown("""
            | Rdo. SSI YTD | Cant. de Encuestas | % de Puntos |
            | :--- | :--- | :--- |
            | ≥ 94,5% | ≥ 30% | 100% |
            | ≥ 94,5% | 30% - 25% | 75% |
            | 94,5% - 89% | ≥ 30% | 75% |
            | 94,5% - 89% | 30% - 25% | 50% |
            | < 89% | < 25% | 0% |
            """)
            st.caption("*Superar el 89% en el SSI YTD y tener un mínimo del 25% de respuestas sobre base de clientes de UCT es condición necesaria para recibir puntaje.*")

            st.markdown("**2. Net Promoter Score (NPS) — `0,8 ptos`**")
            st.markdown("""
            | Rdo. NPS YTD | Cant. de Encuestas | % de Puntos |
            | :--- | :--- | :--- |
            | ≥ 89% | ≥ 30% | 100% |
            | ≥ 89% | 30% - 25% | 75% |
            | 89% - 84% | ≥ 30% | 75% |
            | 89% - 84% | 30% - 25% | 50% |
            | < 84% | < 25% | 0% |
            """)
            st.caption("*Superar el 84% en el NPS YTD y tener un mínimo del 25% de respuestas sobre base de clientes de UCT es condición necesaria para recibir puntaje.*")

        with col_tpa:
            st.markdown("#### 📘 Toyota Plan de Ahorro (TPA)")

            st.markdown("**1. Índice de Contención de Quejas (ICQ) — `0,8 ptos`**")
            st.markdown("""
            | ICQ | PUNTOS |
            | :--- | :--- |
            | ≤ 0,10 | 100% |
            | 0,10 < ICQ ≤ 0,30 | 75% |
            | 0,30 < ICQ ≤ 0,60 | 50% |
            | > 0,60 | 0% |
            """)
            st.caption("*Condición para Puntuar: Generar al menos 300 suscripciones anuales (evaluado mensualmente).*")

            st.markdown("**2. NPS Transaccional — `0,8 ptos`**")
            st.markdown("""
            | NPS | Puntos |
            | :--- | :--- |
            | ≥ 85% | 100% |
            | 80% - 84,99% | 75% |
            | 75% - 79,99% | 50% |
            | 70% - 74,99% | 25% |
            | < 70% | 0% |
            """)
            st.caption("*Mínimo de respuestas: Carteras ≥ 2.000 clientes (17/mes). Carteras < 2.000 clientes (8/mes).*")

else:
    st.warning("No se pudo leer la hoja VENTAS26 o está vacía.")
