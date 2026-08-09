from components.sidebar import render_sidebar, hide_sidebar
# pages/01_dashboard.py
import streamlit as st
from components.sidebar import render_sidebar, hide_sidebar


# FORZAR 100% ANCHO COMPLETO EN STREAMLIT

try:
    st.set_page_config(page_title="ESD Management Suite", page_icon="⚡", layout="wide")
except Exception:
    pass
import pandas as pd
import plotly.express as px
from core.i18n import t
from core.db import get_supabase_client

# Barrera de Seguridad
if st.session_state.get("modo_lectura", True):
    st.warning(t("auth", "login_required", default="Debes iniciar sesión para acceder."))
    st.stop()

render_sidebar()

supabase = get_supabase_client()
site_id = st.session_state.site_id

st.markdown(f"### 📊 {t('dashboard', 'title', default='Overview de Cumplimiento ESD')}")
st.caption(f"{t('dashboard', 'subtitle', default='Estado global de cumplimiento normativo ANSI/ESD S20.20')} - **{st.session_state.site_name}**")

# Cargar métricas clave
with st.spinner("Cargando métricas de la planta..."):
    col1, col2, col3, col4 = st.columns(4)
    
    # Total de Activos
    total_assets = 0
    try:
        r_assets = supabase.table("assets").select("id", count="exact").eq("site_id", site_id).execute()
        total_assets = r_assets.count or 0
    except Exception: pass
    
    # Auditorías de Piso
    total_floors = 0
    try:
        r_floors = supabase.table("floor_validation_logs").select("id", count="exact").eq("site_id", site_id).execute()
        total_floors = r_floors.count or 0
    except Exception: pass
    
    # Tierras Físicas
    total_grounding = 0
    try:
        r_grounding = supabase.table("grounding_logs").select("id", count="exact").eq("site_id", site_id).execute()
        total_grounding = r_grounding.count or 0
    except Exception: pass

    # Checadores de Entrada
    total_entrance = 0
    try:
        r_entrance = supabase.table("entrance_checkers_logs").select("id", count="exact").eq("site_id", site_id).execute()
        total_entrance = r_entrance.count or 0
    except Exception: pass

    col1.metric("📦 Activos ESD Registrados", total_assets)
    col2.metric("🧹 Verificaciones de Piso ESD", total_floors)
    col3.metric("⚡ Tierras Físicas Auditadas", total_grounding)
    col4.metric("🚪 Lecturas de Checadores", total_entrance)

st.divider()
st.markdown("#### 🔍 Estado Operativo por Categoría de Activo")

try:
    resp = supabase.table("assets").select("category, status").eq("site_id", site_id).execute()
    if resp.data:
        df = pd.DataFrame(resp.data)
        fig = px.histogram(df, x="category", color="status", barmode="group", title="Distribución de Activos por Categoría y Estatus")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay activos registrados en este Site.")
except Exception as e:
    st.error(f"Error al cargar visualización de activos: {e}")
