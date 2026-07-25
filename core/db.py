# core/db.py
import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client() -> Client:
    """Inicializa y retorna la conexión a Supabase usando los secrets de Streamlit."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def log_app_event(page: str, level: str, message: str, details: str = None):
    """Registra eventos del sistema en la tabla app_logs."""
    try:
        supabase = get_supabase_client()
        user_id = st.session_state.get("user_id")
        site_id = st.session_state.get("site_id")
        
        supabase.table("app_logs").insert({
            "page": page,
            "level": level,
            "message": message,
            "details": details,
            "user_id": user_id,
            "site_id": site_id
        }).execute()
    except Exception as e:
        print(f"Error logging to app_logs: {e}")

# --- WRAPPERS MULTI-TENANT POR SITE_ID ---

def get_site_assets(site_id: str = None):
    """Retorna los activos de la planta desde la tabla assets."""
    target_site = site_id or st.session_state.get("site_id")
    if not target_site:
        return []
    supabase = get_supabase_client()
    resp = supabase.table("assets").select("*").eq("site_id", target_site).execute()
    return resp.data or []

def get_grounding_logs(site_id: str = None):
    """Retorna bitácora de tierras físicas."""
    target_site = site_id or st.session_state.get("site_id")
    if not target_site:
        return []
    supabase = get_supabase_client()
    resp = supabase.table("grounding_logs").select("*").eq("site_id", target_site).order("measured_at", desc=True).execute()
    return resp.data or []

def get_floor_validation_logs(site_id: str = None):
    """Retorna bitácora de pisos ESD."""
    target_site = site_id or st.session_state.get("site_id")
    if not target_site:
        return []
    supabase = get_supabase_client()
    resp = supabase.table("floor_validation_logs").select("*").eq("site_id", target_site).order("measured_at", desc=True).execute()
    return resp.data or []

def get_event_meter_logs(site_id: str = None):
    """Retorna mediciones de Event Meter."""
    target_site = site_id or st.session_state.get("site_id")
    if not target_site:
        return []
    supabase = get_supabase_client()
    resp = supabase.table("event_meter_logs").select("*").eq("site_id", target_site).order("measured_at", desc=True).execute()
    return resp.data or []

def get_entrance_checkers_logs(site_id: str = None):
    """Retorna bitácora de checadores de calzado/pulsera."""
    target_site = site_id or st.session_state.get("site_id")
    if not target_site:
        return []
    supabase = get_supabase_client()
    resp = supabase.table("entrance_checkers_logs").select("*").eq("site_id", target_site).order("measured_at", desc=True).execute()
    return resp.data or []

def get_empleados_batas(site_id: str = None):
    """Retorna empleados y control de batas/entrenamiento."""
    target_site = site_id or st.session_state.get("site_id")
    if not target_site:
        return []
    supabase = get_supabase_client()
    resp = supabase.table("empleados_batas").select("*").eq("site_id", target_site).execute()
    return resp.data or []
