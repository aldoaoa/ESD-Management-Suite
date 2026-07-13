import streamlit as st
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

@st.cache_resource
def get_supabase_client() -> Client:
    """Inicializa y retorna la conexión a Supabase usando los secrets de Streamlit."""
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in secrets")
        
        return create_client(url, key)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        st.error("❌ Database connection failed. Please check configuration.")
        st.stop()

# --- FUNCIONES WRAPPER MULTI-TENANT ---
# Estas funciones aseguran que siempre se consulte la información correcta

def get_site_assets():
    """Retorna todos los activos (Mobiliario, Maquinaria, etc.) del Site actual."""
    if not st.session_state.get("site_id"):
        logger.debug("No site_id in session state")
        return []
        
    try:
        supabase = get_supabase_client()
        response = supabase.table("assets").select("*").eq("site_id", st.session_state.site_id).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching assets: {e}")
        st.error("❌ Error al obtener activos. Intenta de nuevo.")
        return []

def get_site_measurements(limit=1000):
    """Retorna el historial de mediciones del Site actual."""
    if not st.session_state.get("site_id"):
        logger.debug("No site_id in session state")
        return []
        
    try:
        supabase = get_supabase_client()
        response = supabase.table("measurements").select("*, assets(custom_id, category, classification)").eq("site_id", st.session_state.site_id).order("measured_at", desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        logger.error(f"Error fetching measurements: {e}")
        st.error("❌ Error al obtener mediciones. Intenta de nuevo.")
        return []
