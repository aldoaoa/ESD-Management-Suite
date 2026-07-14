# pages/01_dashboard.py

import streamlit as st
import pandas as pd
import plotly.express as px
from core.i18n import t
from core.db import get_supabase_client

# ==========================================
# 1. BARRERA DE SEGURIDAD MULTI-TENANT
# ==========================================
if st.session_state.get("modo_lectura", True):
    st.warning(t("auth", "login_required"))
    st.stop()

supabase = get_supabase_client()
site_id = st.session_state.site_id

st.markdown(f"### {t('dashboard', 'title')}")
st.caption(f"{t('dashboard', 'subtitle')} - **{st.session_state.site_name}**")

from core.logger import log_error

# ==========================================
# 2. EXTRACCIÓN DE DATOS
# ==========================================
try:
    with st.spinner("Procesando métricas..."):
        # Extraer todos los activos de la planta
        resp_assets = supabase.table("assets").select("id, custom_id, category, status").eq("site_id", site_id).execute()
        df_assets = pd.DataFrame(resp_assets.data)

        # Extraer el historial de mediciones de la planta
        resp_meas = supabase.table("measurements").select("asset_id, status_result, measured_at").eq("site_id", site_id).order("measured_at", desc=True).execute()
        df_meas = pd.DataFrame(resp_meas.data)
except Exception as e:
    st.error("Error al cargar los datos del Dashboard. Por favor, intente de nuevo más tarde.")
    log_error("pages/01_dashboard.py", "Error fetching assets or measurements from Supabase", e)
    st.stop()

# ==========================================
# 3. CÁLCULO DE KPIs
# ==========================================
if not df_assets.empty:
    # Filtrar solo activos operativos
    activos_operativos = df_assets[df_assets['status'] == 'ACTIVE'].copy()
    total_activos = len(activos_operativos)

    activos_aprobados = 0
    activos_fallidos = 0
    alertas_criticas = []

    if not df_meas.empty:
        # Obtener la medición más reciente por cada activo
        df_latest_meas = df_meas.drop_duplicates(subset=['asset_id'], keep='first')
        
        # Cruzar los activos con su última medición
        df_kpi = pd.merge(activos_operativos, df_latest_meas, left_on='id', right_on='asset_id', how='left')
        
        # Contar estatus (Si no tiene medición, se considera como PENDIENTE/FALLO para el compliance)
        df_kpi['status_result'] = df_kpi['status_result'].fillna('PENDING')
        
        activos_aprobados = len(df_kpi[df_kpi['status_result'] == 'PASS'])
        activos_fallidos = total_activos - activos_aprobados
        
        # Identificar las alertas críticas (FALLA o PENDIENTE)
        df_alertas = df_kpi[df_kpi['status_result'] != 'PASS'].copy()
        
    else:
        # Si no hay mediciones, todo está pendiente
        activos_fallidos = total_activos
        df_kpi = activos_operativos.copy()
        df_kpi['status_result'] = 'PENDING'
        df_alertas = df_kpi.copy()

    cumplimiento_pct = (activos_aprobados / total_activos) * 100 if total_activos > 0 else 100.0

    # --- RENDERIZADO DE TARJETAS KPI ---
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric(t("dashboard", "kpi_total"), total_activos)
    kpi2.metric(t("dashboard", "kpi_comp"), f"{cumplimiento_pct:.1f}%", f"{-activos_fallidos} req. action" if activos_fallidos > 0 else "100%", delta_color="inverse" if activos_fallidos > 0 else "normal")
    kpi3.metric(t("dashboard", "kpi_pass"), activos_aprobados)
    kpi4.metric(t("dashboard", "kpi_fail"), activos_fallidos)

    st.divider()

    # ==========================================
    # 4. GRÁFICOS INTERACTIVOS (Plotly)
    # ==========================================
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.markdown(f"**{t('dashboard', 'chart_status')}**")
        df_status_count = df_kpi['status_result'].value_counts().reset_index()
        df_status_count.columns = ['Status', 'Count']
        
        fig_status = px.pie(
            df_status_count, 
            values='Count', 
            names='Status', 
            hole=0.4,
            color='Status',
            color_discrete_map={'PASS': '#28a745', 'FAIL': '#dc3545', 'PENDING': '#ffc107'}
        )
        fig_status.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)
        st.plotly_chart(fig_status, use_container_width=True)

    with col_chart2:
        st.markdown(f"**{t('dashboard', 'chart_category')}**")
        df_cat_count = df_kpi['category'].value_counts().reset_index()
        df_cat_count.columns = ['Category', 'Count']
        
        fig_cat = px.bar(
            df_cat_count, 
            x='Count', 
            y='Category', 
            orientation='h',
            text_auto=True,
            color='Category'
        )
        fig_cat.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300, showlegend=False, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_cat, use_container_width=True)

    # ==========================================
    # 5. TABLA DE ALERTAS CRÍTICAS
    # ==========================================
    st.divider()
    st.markdown(f"#### {t('dashboard', 'alerts_title')}")
    
    if not df_alertas.empty:
        df_show_alerts = df_alertas[['custom_id', 'category', 'status_result']].copy()
        df_show_alerts.columns = [t("dashboard", "col_asset"), t("dashboard", "col_category"), t("dashboard", "col_status")]
        
        # Formato visual
        df_show_alerts[t("dashboard", "col_status")] = df_show_alerts[t("dashboard", "col_status")].apply(
            lambda x: f"🔴 {x}" if x == 'FAIL' else f"🟡 {x}"
        )
        
        st.dataframe(df_show_alerts, use_container_width=True, hide_index=True)
    else:
        st.success("🎉 Todo el equipamiento se encuentra en cumplimiento normativo.")

else:
    st.info("No hay activos registrados en el sistema para esta planta.")
