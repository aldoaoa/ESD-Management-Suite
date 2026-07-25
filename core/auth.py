# core/auth.py
import streamlit as st
from werkzeug.security import check_password_hash, generate_password_hash
from core.db import get_supabase_client

def iniciar_sesion(email, password):
    """
    Verifica las credenciales del usuario y carga sus datos de acceso.
    Retorna (True, user_data) si el login es exitoso, (False, error_key) en caso contrario.
    """
    supabase = get_supabase_client()
    
    try:
        # Buscamos al usuario por su email incluyendo relaciones de site y company
        response = supabase.table("users").select("*, sites(name, timezone), companies(name)").eq("email", email.strip().lower()).execute()
        
        if response.data and len(response.data) > 0:
            user_data = response.data[0]
            
            # Verificamos si la cuenta está activa
            if not user_data.get("is_active", True):
                return False, "account_inactive"
                
            # Verificamos la contraseña hasheada
            stored_hash = user_data.get("password_hash", "")
            if check_password_hash(stored_hash, password):
                # LOGIN EXITOSO - Guardar variables clave en la sesión
                st.session_state["modo_lectura"] = False
                st.session_state["user_id"] = user_data.get("id")
                st.session_state["user_email"] = user_data.get("email")
                st.session_state["user_role"] = user_data.get("role", "AUDITOR")
                st.session_state["user_name"] = user_data.get("full_name", user_data.get("email"))
                
                # Datos de tenant
                st.session_state["site_id"] = user_data.get("site_id")
                st.session_state["company_id"] = user_data.get("company_id")
                
                site_info = user_data.get("sites") or {}
                company_info = user_data.get("companies") or {}
                
                st.session_state["site_name"] = site_info.get("name", "Site Principal")
                st.session_state["company_name"] = company_info.get("name", "ESD Enterprise")
                
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
