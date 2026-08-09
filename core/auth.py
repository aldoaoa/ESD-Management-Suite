# core/auth.py
import streamlit as st
from werkzeug.security import check_password_hash
from core.db import get_supabase_client

def iniciar_sesion(email, password):
    """
    Verifica las credenciales del usuario y carga sus datos de acceso.
    """
    supabase = get_supabase_client()
    clean_email = email.strip().lower()
    
    try:
        # Consulta limpia a la tabla usuarios
        response = supabase.table("users").select("*").eq("email", clean_email).execute()

        if response.data and len(response.data) > 0:
            user_data = response.data[0]
            
            # Verificamos si la cuenta está activa
            if not user_data.get("is_active", True):
                return False, "account_inactive"
                
            # Verificamos la contraseña hasheada
            stored_hash = user_data.get("password_hash", "")
            if check_password_hash(stored_hash, password):
                # LOGIN EXITOSO
                st.session_state["modo_lectura"] = False
                st.session_state["user_id"] = user_data.get("id")
                st.session_state["user_email"] = user_data.get("email")
                st.session_state["user_role"] = user_data.get("role", "AUDITOR")
                st.session_state["user_name"] = user_data.get("full_name", user_data.get("email"))
                
                # Datos de tenant
                st.session_state["site_id"] = user_data.get("site_id")
                st.session_state["company_id"] = user_data.get("company_id")
                
                # Cargar nombre de site de forma segura
                site_name = "Planta Principal"
                if user_data.get("site_id"):
                    try:
                        s_resp = supabase.table("sites").select("name").eq("id", user_data["site_id"]).execute()
                        if s_resp.data and len(s_resp.data) > 0:
                            site_name = s_resp.data[0].get("name", site_name)
                    except Exception: pass

                # Cargar nombre de empresa de forma segura
                company_name = "ESD Enterprise"
                if user_data.get("company_id"):
                    try:
                        c_resp = supabase.table("companies").select("name").eq("id", user_data["company_id"]).execute()
                        if c_resp.data and len(c_resp.data) > 0:
                            company_name = c_resp.data[0].get("name", company_name)
                    except Exception: pass
                
                st.session_state["site_name"] = site_name
                st.session_state["company_name"] = company_name
                
                return True, user_data
            else:
                return False, "invalid_password"
        else:
            return False, "user_not_found"
            
    except Exception as e:
        print(f"Error en iniciar_sesion: {e}")
        return False, str(e)

def cerrar_sesion():
    """
    Limpia la sesión activa y regresa al modo de lectura/login.
    """
    st.session_state["modo_lectura"] = True
    st.session_state["user"] = None
    st.session_state["user_id"] = None
    st.session_state["user_email"] = None
    st.session_state["user_role"] = None
    st.session_state["site_id"] = None
    st.session_state["site_name"] = None
    st.session_state["company_id"] = None
    st.session_state["company_name"] = None
    st.rerun()
