
import streamlit as st
from werkzeug.security import check_password_hash, generate_password_hash
# Importaremos supabase desde nuestro gestor de base de datos en el siguiente paso
from core.db import get_supabase_client

def iniciar_sesion(email, password):
    """
    Verifica las credenciales del usuario y carga sus datos de acceso.
    Retorna True si el login es exitoso, False en caso contrario.
    """
    supabase = get_supabase_client()
    
    try:
        # Buscamos al usuario por su email
        response = supabase.table("users").select("*, sites(name, timezone), companies(name)").eq("email", email).execute()
        
        if response.data and len(response.data) > 0:
            user_data = response.data[0]
            
            # Verificamos si la cuenta está activa
            if not user_data.get("is_active"):
                return False, "account_inactive"
                
            # Verificamos la contraseña hasheada
            if check_password_hash(user_data["password_hash"], password):
                
                # ¡LOGIN EXITOSO! Guardamos los datos vitales en la sesión
                st.session_state.user_id = user_data["id"]
                st.session_state.company_id = user_data["company_id"]
                st.session_state.site_id = user_data["site_id"]
                st.session_state.usuario_nombre = user_data["full_name"]
                st.session_state.rol_usuario = user_data["role"]
                st.session_state.lang = user_data.get("preferred_language", "en")
                st.session_state.modo_lectura = False
                
                # Guardamos los nombres para mostrarlos en la UI
                st.session_state.company_name = user_data["companies"]["name"] if user_data.get("companies") else "Global"
                st.session_state.site_name = user_data["sites"]["name"] if user_data.get("sites") else "All Sites"

                # Si es un usuario admin/global y no tiene site_id fijo, cargamos todas las plantas disponibles
                if not st.session_state.site_id or st.session_state.rol_usuario in ["admin", "SuperAdmin", "CompanyAdmin"]:
                    try:
                        query = supabase.table("sites").select("id, name")
                        if st.session_state.rol_usuario == "CompanyAdmin" and st.session_state.company_id:
                            query = query.eq("company_id", st.session_state.company_id)
                        
                        sites_resp = query.execute()
                        if sites_resp.data:
                            st.session_state.available_sites = sites_resp.data
                            # Inicializamos con el primer site si no tenía uno asignado o si el asignado no está en la lista
                            if not st.session_state.site_id:
                                st.session_state.site_id = sites_resp.data[0]["id"]
                                st.session_state.site_name = sites_resp.data[0]["name"]
                        else:
                            st.session_state.available_sites = []
                    except Exception as e:
                        st.session_state.available_sites = []
                        print(f"Error loading sites for admin: {e}")
                
                return True, "success"
            else:
                return False, "invalid_password"
        else:
            return False, "user_not_found"
            
    except Exception as e:
        return False, f"db_error: {str(e)}"

def cerrar_sesion():
    """Limpia la sesión de Streamlit para volver a modo lectura."""
    st.session_state.clear() # Limpia todo el diccionario
    # Forzamos los valores por defecto
    st.session_state.modo_lectura = True
    st.session_state.usuario_nombre = None
    st.session_state.rol_usuario = "Consulta"
    st.session_state.lang = "en"
    st.rerun()

def requires_auth(func):
    """
    Decorador. Envuelve una función (vista) y verifica si el usuario está logueado.
    Si no lo está, muestra un mensaje de error y detiene la ejecución.
    """
    def wrapper(*args, **kwargs):
        if st.session_state.get("modo_lectura", True):
            from core.i18n import t
            st.warning(t("auth", "login_required")) # Necesitamos agregar esto a locales
            st.stop()
        return func(*args, **kwargs)
    return wrapper
