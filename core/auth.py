
import streamlit as st
import logging
from werkzeug.security import check_password_hash, generate_password_hash
from core.db import get_supabase_client

logger = logging.getLogger(__name__)

def iniciar_sesion(email, password):
    """
    Verifica las credenciales del usuario y carga sus datos de acceso.
    Retorna tupla (success: bool, message: str).
    """
    # Validar entrada
    if not email or not password:
        logger.warning("Login attempt with empty credentials")
        return False, "invalid_credentials"
    
    if not isinstance(email, str) or not isinstance(password, str):
        logger.warning("Login attempt with invalid input types")
        return False, "invalid_input"
    
    try:
        supabase = get_supabase_client()
        
        # Buscamos al usuario por su email
        response = supabase.table("users").select("*, sites(name, timezone), companies(name)").eq("email", email).execute()
        
        if response.data and len(response.data) > 0:
            user_data = response.data[0]
            
            # Verificamos si la cuenta está activa
            if not user_data.get("is_active"):
                logger.warning(f"Login attempt for inactive account: {email}")
                return False, "account_inactive"
                
            # Verificamos la contraseña hasheada
            if check_password_hash(user_data["password_hash"], password):
                
                # ¡LOGIN EXITOSO! Guardamos los datos vitales en la sesión
                st.session_state.user_id = user_data["id"]
                st.session_state.company_id = user_data["company_id"]
                st.session_state.site_id = user_data["site_id"]
                st.session_state.user_name = user_data["full_name"]
                st.session_state.user_role = user_data["role"]
                st.session_state.lang = user_data.get("preferred_language", "en")
                st.session_state.is_read_only = False
                
                # Guardamos los nombres para mostrarlos en la UI
                st.session_state.company_name = user_data["companies"]["name"] if user_data.get("companies") else "Global"
                st.session_state.site_name = user_data["sites"]["name"] if user_data.get("sites") else "All Sites"
                
                logger.info(f"Successful login: {email}")
                return True, "success"
            else:
                logger.warning(f"Invalid password attempt: {email}")
                return False, "invalid_password"
        else:
            logger.warning(f"Login attempt for non-existent user: {email}")
            return False, "user_not_found"
            
    except Exception as e:
        logger.error(f"Database error during login: {str(e)}")
        return False, "db_error"

def cerrar_sesion():
    """Limpia la sesión de Streamlit para volver a modo lectura."""
    try:
        st.session_state.clear()
        # Forzamos los valores por defecto
        st.session_state.is_read_only = True
        st.session_state.user_name = None
        st.session_state.user_role = "Viewer"
        st.session_state.lang = "en"
        logger.info("Session cleared successfully")
        st.rerun()
    except Exception as e:
        logger.error(f"Error closing session: {str(e)}")
        st.error("❌ Error al cerrar sesión. Intenta de nuevo.")

def requires_auth(func):
    """
    Decorador. Envuelve una función (vista) y verifica si el usuario está logueado.
    Si no lo está, muestra un mensaje de error y detiene la ejecución.
    """
    def wrapper(*args, **kwargs):
        if st.session_state.get("is_read_only", True):
            from core.i18n import t
            st.warning(t("auth", "login_required"))
            st.stop()
        return func(*args, **kwargs)
    return wrapper
