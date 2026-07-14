
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

                # Si es un usuario global (SuperAdmin/admin), cargamos todos los sitios del sistema
                if st.session_state.rol_usuario in ["SuperAdmin", "admin"]:
                    try:
                        sites_resp = supabase.table("sites").select("id, name").execute()
                        st.session_state.available_sites = sites_resp.data if sites_resp.data else []
                    except Exception as e:
                        st.session_state.available_sites = []
                        print(f"Error loading all sites for SuperAdmin: {e}")
                
                # Si es administrador de empresa (CompanyAdmin), cargamos todos los sitios de su empresa
                elif st.session_state.rol_usuario == "CompanyAdmin":
                    try:
                        if st.session_state.company_id:
                            sites_resp = supabase.table("sites").select("id, name").eq("company_id", st.session_state.company_id).execute()
                            st.session_state.available_sites = sites_resp.data if sites_resp.data else []
                        else:
                            st.session_state.available_sites = []
                    except Exception as e:
                        st.session_state.available_sites = []
                        print(f"Error loading company sites for CompanyAdmin: {e}")
                
                # Para roles regulares, cargamos las plantas asignadas en la tabla puente user_sites
                else:
                    try:
                        user_sites_resp = supabase.table("user_sites").select("site_id, sites(name)").eq("user_id", st.session_state.user_id).execute()
                        if user_sites_resp.data:
                            st.session_state.available_sites = [
                                {"id": x["site_id"], "name": x["sites"]["name"]} 
                                for x in user_sites_resp.data if x.get("sites")
                            ]
                        else:
                            st.session_state.available_sites = []
                    except Exception as e:
                        st.session_state.available_sites = []
                        print(f"Error loading user_sites for regular user: {e}")

                # Inicializamos la planta activa por defecto en base a los accesos cargados
                if st.session_state.available_sites:
                    # Validar si el site_id de la cuenta está dentro de sus accesos permitidos
                    site_ids = [s["id"] for s in st.session_state.available_sites]
                    if st.session_state.site_id in site_ids:
                        # Encontrar el nombre del sitio correspondiente
                        for s in st.session_state.available_sites:
                            if s["id"] == st.session_state.site_id:
                                st.session_state.site_name = s["name"]
                                break
                    else:
                        # Si no coincide o es nulo, forzamos el primero de la lista
                        st.session_state.site_id = st.session_state.available_sites[0]["id"]
                        st.session_state.site_name = st.session_state.available_sites[0]["name"]
                else:
                    st.session_state.site_id = None
                    st.session_state.site_name = "Sin Planta Asignada"
                
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
