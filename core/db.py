import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client() -> Client:
    """Inicializa y retorna la conexión a Supabase usando los secrets de Streamlit."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# --- FUNCIONES WRAPPER MULTI-TENANT ---
# Estas funciones aseguran que siempre se consulte la información correcta

def get_site_assets():
    """Retorna todos los activos (Mobiliario, Maquinaria, etc.) del Site actual."""
    if not st.session_state.get("site_id"):
        return [] # O manejar el caso de un SuperAdmin que ve todo
        
    supabase = get_supabase_client()
    try:
        response = supabase.table("assets").select("*").eq("site_id", st.session_state.site_id).execute()
        return response.data
    except Exception as e:
        st.error(f"Error fetching assets: {e}")
        return []

def get_site_measurements(limit=1000):
    """Retorna el historial de mediciones del Site actual."""
    if not st.session_state.get("site_id"):
        return []
        
    supabase = get_supabase_client()
    try:
        response = supabase.table("measurements").select("*, assets(custom_id, category, classification)").eq("site_id", st.session_state.site_id).order("measured_at", desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        st.error(f"Error fetching measurements: {e}")
        return []
