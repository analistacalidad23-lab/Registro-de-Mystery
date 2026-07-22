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
    .main-title { font-size: 28px; font-weight: bold; color: #1E3A8A; margin-bottom: 5px; }
    .subtitle { font-size: 14px; color: #555555; margin-bottom: 25px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🎯 Tablero de Gestión: Calidad, NPS y Comisiones</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Seguimiento de Satisfacción y Lealtad del Cliente - 0km y Usados Certificados</div>', unsafe_allow_html=True)

# 2. Conexión de Datos (Ambas Hojas)
SHEET_ID = "1PGoOlFTN2WuuiEqRk0KPrcLZL6pEcFVeNWo35shsUSA"
URL_VENTAS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=VENTAS26"
URL_USADOS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USADO26"

@st.cache_data(ttl=600)
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

# Cargar ambos dataframes
df_ventas_raw = cargar_datos(URL_VENTAS)
df_usados_raw = cargar_datos(URL_USADOS)

if not df_ventas_raw.empty:
    columnas_disponibles = df_ventas_raw.columns.tolist()
    
    # 3. Detección Inteligente de Columnas (VENTAS)
    st.sidebar.header("⚙️ Configuración 0km (VENTAS26)")
    
    col_nps = columnas_disponibles[-1]
    col_vend_detectada = next((c for c in columnas_disponibles if 'vendedor' in c.lower() or 'asesor' in c.lower()), columnas_disponibles[0])
    col_vendedor = st.sidebar.selectbox("Columna Vendedor:", columnas_disponibles, index=columnas_disponibles.index(col_vend_detectada))
    
    col_ssi_detectada = next((c for c in columnas_disponibles if 'ssi' in c.lower()), columnas_disponibles[0])
    col_ssi = st.sidebar.selectbox("Columna SSI:", columnas_disponibles, index=columnas_disponibles.index(col_ssi_detectada))
    
    col_fecha_detectada = next((c for c in columnas_disponibles if 'fecha' in c.lower() or 'mes' in c.lower() or 'periodo' in c.lower()), columnas_disponibles[0])
    col_fecha = st.sidebar.selectbox("Columna Fecha:", columnas_disponibles, index=columnas_disponibles.index(col_fecha_detectada))

    col_sucursal_detectada = next((c for c in columnas_disponibles if 'boca' in c.lower() or 'sucursal' in c.lower() or 'concesionario' in c.lower()), columnas_disponibles[0])
    col_sucursal = st.sidebar.selectbox("Columna Boca de Venta:", columnas_disponibles, index=columnas_disponibles.index(col_sucursal_detectada))

    df_procesado = df_ventas_raw.copy()
    
    # Preparar Fechas 0km
    try:
        df_procesado['Fecha_DT'] = pd.to_datetime(df_procesado[col_fecha], errors='coerce')
        df_procesado['Mes_Nombre'] = df_procesado['Fecha_DT'].dt.strftime('%B').str.lower()
        df_procesado['Mes_Num'] = df_procesado['Fecha_DT'].dt.month
        df_procesado['Año'] = df_procesado['Fecha_DT'].dt.year.fillna(0).astype(int).astype(str)
        df_procesado['Mes_Período'] = df_procesado['Fecha_DT'].dt.strftime('%Y-%m')
    except:
        df_procesado['Mes_Nombre'] = df_procesado[col_fecha].astype(str)
        df_procesado['Mes_Num'] = 1
        df_procesado['Año'] = "N/D"
        df_procesado['Mes_Período'] = df_procesado[col_fecha].astype(str)

    # Limpieza de SSI y Subíndices 0km
    df_procesado['SSI_Num'] = pd.to_numeric(df_procesado[col_ssi].astype(str).str.replace(',', '.').str.replace('%', ''), errors='coerce')
    cols_subindices = [c for c in columnas_disponibles if any(x in c for x in ['01', '02', '03', '04', '05', '08', '09', '11'])]
    for c in cols_subindices:
        df_procesado[c] = pd.to_numeric(df_procesado[c].astype(str).str.replace(',', '.').str.replace('%', ''), errors='coerce')

    col_atencion_vend = next((c for c in cols_subindices if 'atencion' in c.lower() and 'vendedor' in c.lower()), None)
    if not col_atencion_vend: col_atencion_vend = next((c for c in cols_subindices if '02' in c), None)

    # 4. Filtros Globales en Barra Lateral (0km)
    st.sidebar.header("🔍 Filtros Generales 0km")
    años_disp = sorted([a for a in df_procesado['Año'].unique() if a != "0"], reverse=True)
    año_sel = st.sidebar.selectbox("Año:", ["Todos"] + años_disp)
    
    meses_disp = sorted(df_procesado['Mes_Período'].dropna().unique().tolist())
    meses_sel = st.sidebar.multiselect("Filtrar por Mes (Período):", meses_disp, default=meses_disp)

    bocas_disp = sorted(df_procesado[col_sucursal].dropna().astype(str).unique().tolist())
    boca_sel = st.sidebar.selectbox("Seleccionar Boca de Venta:", ["Todas"] + bocas_disp)

    df_filtrado = df_procesado.copy()
    if año_sel != "Todos": df_filtrado = df_filtrado[df_filtrado['Año'] == año_sel]
    if boca_sel != "Todas": df_filtrado = df_filtrado[df_filtrado[col_sucursal].astype(str) == boca_sel]
    if meses_sel: df_filtrado = df_filtrado[df_filtrado['Mes_Período'].isin(meses_sel)]

    # 5. Creación de Pestañas
    tab_resumen, tab_ranking, tab_evolucion, tab_comisiones, tab_usados = st.tabs([
        "⏱️ Relojes (0km)", 
        "🏆 Ranking Vendedores", 
        "📅 Evolución Mensual",
        "💰 Comisiones SSI",
        "🚗 Usados Certificados"
    ])

    # --- PESTAÑA 1: RELOJES 0KM ---
    with tab_resumen:
        st.write("### Estado Actual vs Objetivos (0km)")
        OBJETIVO_SSI = 95.6
        OBJETIVO_NPS = 87.0
        ssi_actual = df_filtrado['SSI_Num'].mean()
        nps_actual = calcular_nps(df_filtrado[col_nps])

        col1, col2 = st.columns(2)
        with col1: st.plotly_chart(crear_reloj(ssi_actual, "Indicador SSI (Objetivo: 95.6)", OBJETIVO_SSI, 100), use_container_width=True)
        with col2: st.plotly_chart(crear_reloj(nps_actual, "Indicador NPS (Objetivo: 87%)", OBJETIVO_NPS, 100), use_container_width=True)

    # --- PESTAÑA 2: RANKING 0KM ---
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

    # --- PESTAÑA 3: EVOLUCIÓN MENSUAL 0KM ---
    with tab_evolucion:
        st.write(f"### Desempeño Mensual - Boca de Venta: {boca_sel} | Año: {año_sel}")
        df_mensual = df_filtrado.sort_values('Mes_Num').groupby('Mes_Nombre', sort=False) if 'Mes_Num' in df_filtrado.columns else df_filtrado.groupby('Mes_Nombre', sort=False)
        resumen_mensual = []
        for mes, grupo in df_mensual:
            fila = {'Mes': mes.capitalize(), 'Q encuestas': len(grupo), 'SSI Puro': grupo['SSI_Num'].mean(), 'NPS dealer': calcular_nps(grupo[col_nps])}
            for c in cols_subindices: fila[c] = grupo[c].mean()
            resumen_mensual.append(fila)

        df_tabla_mensual = pd.DataFrame(resumen_mensual)
        if not df_tabla_mensual.empty:
            fig_evolucion = go.Figure()
            fig_evolucion.add_trace(go.Scatter(x=df_tabla_mensual['Mes'], y=df_tabla_mensual['SSI Puro'], mode='lines+markers+text', name='SSI Puro', line=dict(color='#1E3A8A', width=3), text=df_tabla_mensual['SSI Puro'].apply(lambda x: f"{x:.1f}"), textposition='top center'))
            fig_evolucion.add_trace(go.Scatter(x=df_tabla_mensual['Mes'], y=df_tabla_mensual['NPS dealer'], mode='lines+markers+text', name='NPS dealer', line=dict(color='#2ecc71', width=3), text=df_tabla_mensual['NPS dealer'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else ""), textposition='bottom center'))
            fig_evolucion.update_layout(title="Evolución de SSI y NPS", yaxis_range=[0, 110], template="plotly_white")
            st.plotly_chart(fig_evolucion, use_container_width=True)

            totales = {'Mes': 'Total', 'Q encuestas': df_tabla_mensual['Q encuestas'].sum(), 'SSI Puro': df_filtrado['SSI_Num'].mean(), 'NPS dealer': calcular_nps(df_filtrado[col_nps])}
            for c in cols_subindices: totales[c] = df_filtrado[c].mean()
            df_tabla_mensual.loc[len(df_tabla_mensual)] = totales

            formatos = {'Q encuestas': '{:.0f}', 'SSI Puro': '{:.1f}', 'NPS dealer': '{:.1f}%'}
            for c in cols_subindices: formatos[c] = '{:.1f}'
            
            # Formato Condicional para Tabla 0km
            st.dataframe(
                df_tabla_mensual.style.format(formatos, na_rep="-")
                .apply(lambda x: ['font-weight: bold; background-color: #f0f2f6' if x['Mes'] == 'Total' else '' for i in x], axis=1)
                .map(lambda val: 'color: #2ecc71; font-weight: bold;' if pd.notna(val) and val >= OBJETIVO_SSI else ('color: #e74c3c; font-weight: bold;' if pd.notna(val) else ''), subset=['SSI Puro'])
                .map(lambda val: 'color: #2ecc71; font-weight: bold;' if pd.notna(val) and val >= OBJETIVO_NPS else ('color: #e74c3c; font-weight: bold;' if pd.notna(val) else ''), subset=['NPS dealer']),
                use_container_width=True, hide_index=True
            )

    # --- PESTAÑA 4: COMISIONES 0KM ---
    with tab_comisiones:
        st.write("### 💰 Tabla de Cálculo de Comisiones SSI")
        if not col_atencion_vend: st.error("No se detectó la columna '02 Atencion Vendedor' en los datos.")
        else:
            datos_comision = []
            for vend, grupo in df_filtrado.groupby(col_vendedor):
                cant_encuestas, ssi_promedio, atencion_promedio = len(grupo), grupo['SSI_Num'].mean(), grupo[col_atencion_vend].mean()
                if pd.isna(atencion_promedio) or cant_encuestas == 0: comision = 0.00
                elif atencion_promedio < 95.6: comision = -0.05
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
            else: st.warning("Datos insuficientes para el cálculo de comisiones.")

    # --- PESTAÑA 5: USADOS CERTIFICADOS (UCT) ---
    with tab_usados:
        st.write("### 🚗 Gestión de Calidad: Toyota Usados Certificados (UCT)")
        st.write("Métricas exclusivas y evolución de satisfacción para el canal de Usados.")
        
        if not df_usados_raw.empty:
            columnas_u = df_usados_raw.columns.tolist()
            
            # Coordenadas exactas indicadas para UCT
            col_nps_u = columnas_u[-1]
            col_ssi_u = next((c for c in columnas_u if 'ssi' in c.lower()), columnas_u[0])
            col_fecha_u = "Mes" if "Mes" in columnas_u else columnas_u[2]
            top_5_cols = columnas_u[5:10] if len(columnas_u) >= 10 else []
            
            df_u_proc = df_usados_raw.copy()
            df_u_proc['Mes_Filtro'] = df_u_proc[col_fecha_u].astype(str).str.strip().str.capitalize()
            
            # Filtro por mes local exclusivo para esta pestaña
            st.write("#### 🔍 Filtro de Período (UCT)")
            meses_disp_u = [m for m in df_u_proc['Mes_Filtro'].unique() if m.lower() != 'nan']
            mes_sel_u = st.multiselect("Seleccionar Meses (USADO26):", meses_disp_u, default=meses_disp_u)
            
            df_u_filt = df_u_proc[df_u_proc['Mes_Filtro'].isin(mes_sel_u)] if mes_sel_u else df_u_proc.copy()
            
            # Limpieza Numérica
            df_u_filt['SSI_Num'] = pd.to_numeric(df_u_filt[col_ssi_u].astype(str).str.replace(',', '.').str.replace('%', ''), errors='coerce')
                
            for c in top_5_cols:
                df_u_filt[c] = pd.to_numeric(df_u_filt[c].astype(str).str.replace(',', '.').str.replace('%', ''), errors='coerce')
                
            # Relojes UCT
            OBJ_SSI_UCT = 94.5
            OBJ_NPS_UCT = 89.0
            
            ssi_uct_actual = df_u_filt['SSI_Num'].mean()
            nps_uct_actual = calcular_nps(df_u_filt[col_nps_u])
            
            st.write("#### ⏱️ Estado Actual vs Objetivos UCT")
            cu1, cu2 = st.columns(2)
            with cu1: st.plotly_chart(crear_reloj(ssi_uct_actual, "SSI UCT (Objetivo: 94.5)", OBJ_SSI_UCT, 100), use_container_width=True)
            with cu2: st.plotly_chart(crear_reloj(nps_uct_actual, "NPS UCT (Objetivo: 89%)", OBJ_NPS_UCT, 100), use_container_width=True)
            
            # Tabla 5 principales indicadores por mes (Cols F a J)
            st.write("#### 📊 Evolución de los 5 Principales Indicadores")
            
            if top_5_cols:
                df_u_mensual = df_u_filt.groupby('Mes_Filtro', sort=False)
                res_u = []
                for mes, grupo in df_u_mensual:
                    fila = {
                        'Mes': mes,
                        'Q encuestas': len(grupo),
                        'SSI UCT': grupo['SSI_Num'].mean(),
                        'NPS UCT': calcular_nps(grupo[col_nps_u])
                    }
                    for c in top_5_cols: fila[c] = grupo[c].mean()
                    res_u.append(fila)
                    
                if res_u:
                    df_res_u = pd.DataFrame(res_u)
                    
                    # Fila de Totales
                    totales_u = {'Mes': 'Total', 'Q encuestas': df_res_u['Q encuestas'].sum(), 'SSI UCT': ssi_uct_actual, 'NPS UCT': nps_uct_actual}
                    for c in top_5_cols: totales_u[c] = df_u_filt[c].mean()
                    df_res_u.loc[len(df_res_u)] = totales_u
                    
                    formatos_u = {'Q encuestas': '{:.0f}', 'SSI UCT': '{:.1f}', 'NPS UCT': '{:.1f}%'}
                    for c in top_5_cols: formatos_u[c] = '{:.1f}'
                    
                    # Formato Condicional para Tabla UCT
                    st.dataframe(
                        df_res_u.style.format(formatos_u, na_rep="-")
                        .apply(lambda x: ['font-weight: bold; background-color: #f0f2f6' if x['Mes'] == 'Total' else '' for i in x], axis=1)
                        .map(lambda val: 'color: #2ecc71; font-weight: bold;' if pd.notna(val) and val >= OBJ_SSI_UCT else ('color: #e74c3c; font-weight: bold;' if pd.notna(val) else ''), subset=['SSI UCT'])
                        .map(lambda val: 'color: #2ecc71; font-weight: bold;' if pd.notna(val) and val >= OBJ_NPS_UCT else ('color: #e74c3c; font-weight: bold;' if pd.notna(val) else ''), subset=['NPS UCT']),
                        use_container_width=True, hide_index=True
                    )
                else:
                    st.warning("No hay datos para el período seleccionado.")
            else:
                st.error("No se encontraron las columnas F a J (índices 5 al 9) en la hoja de Usados.")
        else:
            st.warning("No se pudo cargar la hoja USADO26. Verifica que la URL o el nombre de la hoja sean correctos.")

else:
    st.warning("No se pudo leer la hoja VENTAS26 o está vacía.")
