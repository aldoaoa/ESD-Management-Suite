# pages/03_settings.py

import streamlit as st
import pandas as pd
from core.i18n import t
from core.db import get_supabase_client

# ==========================================
# 1. BARRERA DE SEGURIDAD
# ==========================================
from core.auth import requires_auth

@requires_auth
def __ensure_auth():
    pass

__ensure_auth()

supabase = get_supabase_client()
site_id = st.session_state.site_id
company_id = st.session_state.company_id
rol = st.session_state.get("user_role", "")

st.markdown(f"### {t('settings', 'title')}")
st.caption(f"{t('settings', 'subtitle')} - **{st.session_state.site_name}**")

# ==========================================
# 2. PESTAÃ‘AS DE CONFIGURACIÃ“N
# ==========================================
tab_loc, tab_eq, tab_usr = st.tabs([
    t("settings", "tab_locations"), 
    t("settings", "tab_equipment"), 
    t("settings", "tab_users")
])

# --- PESTAÃ‘A A: UBICACIONES / LÃNEAS ---
with tab_loc:
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.markdown(f"#### {t('settings', 'loc_add')}")
        with st.form("form_add_location", clear_on_submit=True):
            loc_name = st.text_input(t("settings", "loc_name"))
            if st.form_submit_button(t("settings", "btn_save"), type="primary", use_container_width=True):
                if loc_name.strip():
                    try:
                        supabase.table("locations").insert({"site_id": site_id, "name": loc_name.strip().upper()}).execute()
                        st.success("UbicaciÃ³n guardada.")
                        st.rerun()
                    except Exception as e:
                        if "23505" in str(e): # Error de llave duplicada
                            st.error("Esta ubicaciÃ³n ya existe.")
                        else:
                            st.error(f"Error: {e}")
                            
    with col2:
        resp_loc = supabase.table("locations").select("name").eq("site_id", site_id).order("name").execute()
        if resp_loc.data:
            df_loc = pd.DataFrame(resp_loc.data)
            st.dataframe(df_loc, use_container_width=True, hide_index=True)
        else:
            st.info("No hay ubicaciones registradas.")

# --- PESTAÃ‘A B: EQUIPOS DE MEDICIÃ“N ---
with tab_eq:
    col_e1, col_e2 = st.columns([1, 2])
    
    with col_e1:
        st.markdown(f"#### {t('settings', 'eq_add')}")
        with st.form("form_add_eq", clear_on_submit=True):
            eq_id = st.text_input(t("settings", "eq_id"))
            eq_type = st.text_input(t("settings", "eq_type"))
            eq_cal = st.date_input(t("settings", "eq_cal"))
            
            if st.form_submit_button(t("settings", "btn_save"), type="primary", use_container_width=True):
                if eq_id.strip():
                    try:
                        supabase.table("measurement_equipment").insert({
                            "site_id": site_id, 
                            "custom_id": eq_id.strip().upper(),
                            "equipment_type": eq_type.strip(),
                            "next_calibration": str(eq_cal)
                        }).execute()
                        st.success("Equipo registrado.")
                        st.rerun()
                    except Exception as e:
                        st.error("Error al registrar equipo (Â¿ID duplicado?).")
                        
    with col_e2:
        resp_eq = supabase.table("measurement_equipment").select("custom_id, equipment_type, next_calibration").eq("site_id", site_id).execute()
        if resp_eq.data:
            df_eq = pd.DataFrame(resp_eq.data)
            df_eq.columns = ["ID Equipo", "Tipo", "PrÃ³xima CalibraciÃ³n"]
            st.dataframe(df_eq, use_container_width=True, hide_index=True)
        else:
            st.info("No hay equipos registrados.")

# --- PESTAÃ‘A C: GESTIÃ“N DE USUARIOS ---
with tab_usr:
    st.markdown(f"#### {t('settings', 'us_title')}")
    
    # Solo administradores pueden ver y crear usuarios
    if rol not in ["SuperAdmin", "CompanyAdmin", "SiteManager"]:
        st.warning(t("settings", "us_warning"))
    else:
        # En una arquitectura real, aquÃ­ crearÃ­as la lÃ³gica para hacer INSERT en la tabla 'users'
        # encriptando la contraseÃ±a usando `generate_password_hash` desde `core/auth.py`.
        st.write("Panel de administraciÃ³n habilitado para creaciÃ³n de cuentas y reseteo de contraseÃ±as.")
        
        try:
            # Filtramos para que un SiteManager solo vea a los usuarios de su planta, 
            # y un CompanyAdmin vea a todos los de su empresa.
            if rol == "CompanyAdmin" or rol == "SuperAdmin":
                resp_usr = supabase.table("users").select("full_name, email, role, is_active").eq("company_id", company_id).execute()
            else:
                resp_usr = supabase.table("users").select("full_name, email, role, is_active").eq("site_id", site_id).execute()
                
            if resp_usr.data:
                df_usr = pd.DataFrame(resp_usr.data)
                df_usr.columns = ["Nombre", "Email", "Rol", "Activo"]
                st.dataframe(df_usr, use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Error cargando usuarios: {e}")

