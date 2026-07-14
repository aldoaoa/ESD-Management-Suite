# pages/03_settings.py
import streamlit as st
import pandas as pd
from werkzeug.security import generate_password_hash
from core.i18n import t
from core.db import get_supabase_client
from core.logger import log_error, log_event

# ==========================================
# 1. BARRERA DE SEGURIDAD
# ==========================================
if st.session_state.get("modo_lectura", True):
    st.warning(t("auth", "login_required"))
    st.stop()

supabase = get_supabase_client()
site_id = st.session_state.site_id
company_id = st.session_state.company_id
rol = st.session_state.get("rol_usuario", "")

st.markdown(f"### {t('settings', 'title')}")
st.caption(f"{t('settings', 'subtitle')} - **{st.session_state.site_name}**")

# ==========================================
# 2. DEFINICIÓN DE PESTAÑAS BASADO EN ROLES
# ==========================================
if rol in ["SuperAdmin", "admin"] and not company_id:
    # --- VISTA PARA SUPERADMINISTRADOR GLOBAL ---
    tab_companies, tab_admins, tab_equip = st.tabs([
        "🏢 Empresas (Companies)", 
        "🔐 Administradores de Empresa", 
        "🛠️ Equipos de Medición Globales"
    ])
    
    # --- PESTAÑA 1: GESTIÓN DE EMPRESAS ---
    with tab_companies:
        col1, col2 = st.columns([1, 1.5])
        with col1:
            st.markdown("#### ➕ Registrar Nueva Empresa")
            with st.form("form_add_company", clear_on_submit=True):
                comp_name = st.text_input("Nombre de la Empresa / Company Name")
                if st.form_submit_button(t("settings", "btn_save"), type="primary", use_container_width=True):
                    if comp_name.strip():
                        try:
                            supabase.table("companies").insert({"name": comp_name.strip()}).execute()
                            st.success(f"Empresa '{comp_name}' guardada con éxito.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar empresa: {e}")
                            log_error("pages/03_settings.py", "Error inserting company", e)
        with col2:
            st.markdown("#### 📋 Directorio de Empresas")
            try:
                resp_comps = supabase.table("companies").select("*").order("name").execute()
                if resp_comps.data:
                    df_comps = pd.DataFrame(resp_comps.data)
                    df_comps.columns = ["ID Empresa", "Nombre de Empresa", "Fecha Registro"]
                    st.dataframe(df_comps, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay empresas registradas.")
            except:
                st.info("Error al cargar empresas.")

    # --- PESTAÑA 2: ADMINISTRADORES DE EMPRESA ---
    with tab_admins:
        col_adm1, col_adm2 = st.columns([1, 1.5])
        with col_adm1:
            st.markdown("#### ➕ Crear Administrador de Empresa")
            try:
                resp_comps_sel = supabase.table("companies").select("id, name").order("name").execute()
                dict_comps = {c["id"]: c["name"] for c in resp_comps_sel.data} if resp_comps_sel.data else {}
            except:
                dict_comps = {}

            if not dict_comps:
                st.warning("Debes registrar al menos una empresa primero.")
            else:
                with st.form("form_add_company_admin", clear_on_submit=True):
                    adm_name = st.text_input("Nombre Completo")
                    adm_email = st.text_input("Email")
                    adm_pwd = st.text_input("Contraseña", type="password")
                    adm_comp = st.selectbox("Empresa Asociada", options=list(dict_comps.keys()), format_func=lambda x: dict_comps[x])
                    
                    if st.form_submit_button(t("settings", "btn_save"), type="primary", use_container_width=True):
                        if adm_name.strip() and adm_email.strip() and adm_pwd.strip():
                            try:
                                hashed_pwd = generate_password_hash(adm_pwd)
                                supabase.table("users").insert({
                                    "full_name": adm_name.strip(),
                                    "email": adm_email.strip().lower(),
                                    "password_hash": hashed_pwd,
                                    "role": "CompanyAdmin",
                                    "company_id": adm_comp,
                                    "site_id": None, # CompanyAdmin no tiene site fijo
                                    "is_active": True
                                }).execute()
                                st.success("Administrador de Empresa creado exitosamente.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al crear administrador: {e}")
                                log_error("pages/03_settings.py", "Error creating CompanyAdmin user", e)
        with col_adm2:
            st.markdown("#### 📋 Administradores de Empresa Activos")
            try:
                resp_usr = supabase.table("users").select("full_name, email, companies(name), is_active").eq("role", "CompanyAdmin").execute()
                if resp_usr.data:
                    df_usr = pd.DataFrame(resp_usr.data)
                    df_usr['Empresa'] = df_usr['companies'].apply(lambda x: x['name'] if isinstance(x, dict) else "N/D")
                    df_usr_show = df_usr[['full_name', 'email', 'Empresa', 'is_active']]
                    df_usr_show.columns = ["Nombre", "Email", "Empresa", "Activo"]
                    st.dataframe(df_usr_show, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay administradores de empresa registrados.")
            except:
                st.info("Error al cargar administradores.")

    # --- PESTAÑA 3: EQUIPOS DE MEDICIÓN GLOBALES ---
    with tab_equip:
        st.info("Como SuperAdmin ves los equipos de todas las plantas.")
        try:
            resp_eq = supabase.table("measurement_equipment").select("custom_id, equipment_type, next_calibration, sites(name)").execute()
            if resp_eq.data:
                df_eq = pd.DataFrame(resp_eq.data)
                df_eq['Planta'] = df_eq['sites'].apply(lambda x: x['name'] if isinstance(x, dict) else "N/D")
                df_eq_show = df_eq[['custom_id', 'equipment_type', 'next_calibration', 'Planta']]
                df_eq_show.columns = ["ID Equipo", "Tipo de Equipo", "Calibración", "Planta"]
                st.dataframe(df_eq_show, use_container_width=True, hide_index=True)
            else:
                st.info("No hay equipos de medición registrados.")
        except:
            st.info("Error al consultar equipos de medición.")

elif rol == "CompanyAdmin":
    # --- VISTA PARA ADMINISTRADOR DE EMPRESA ---
    tab_sites, tab_usr_comp, tab_loc, tab_eq = st.tabs([
        "🏭 Plantas (Sites)", 
        "🔐 Gestión de Usuarios", 
        "📍 Ubicaciones de Línea",
        "🛠️ Equipos de Medición"
    ])

    # --- PESTAÑA 1: GESTIÓN DE PLANTAS ---
    with tab_sites:
        col_s1, col_s2 = st.columns([1, 1.5])
        with col_s1:
            st.markdown("#### ➕ Registrar Nueva Planta")
            with st.form("form_add_site", clear_on_submit=True):
                site_name = st.text_input("Nombre de la Planta (Ej: Monterrey Plant)")
                site_tz = st.selectbox("Zona Horaria", ["America/Mexico_City", "America/Monterrey", "America/Chihuahua", "America/Tijuana"])
                
                if st.form_submit_button(t("settings", "btn_save"), type="primary", use_container_width=True):
                    if site_name.strip():
                        try:
                            supabase.table("sites").insert({
                                "company_id": company_id,
                                "name": site_name.strip(),
                                "timezone": site_tz
                            }).execute()
                            st.success("Planta registrada con éxito.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar planta: {e}")
                            log_error("pages/03_settings.py", "Error inserting site", e)
        with col_s2:
            st.markdown("#### 📋 Plantas de tu Empresa")
            try:
                resp_s = supabase.table("sites").select("*").eq("company_id", company_id).execute()
                if resp_s.data:
                    df_s = pd.DataFrame(resp_s.data)
                    df_s_show = df_s[['name', 'timezone', 'created_at']]
                    df_s_show.columns = ["Nombre Planta", "Zona Horaria", "Fecha Creación"]
                    st.dataframe(df_s_show, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay plantas registradas para tu empresa.")
            except:
                st.info("Error al cargar plantas.")

    # --- PESTAÑA 2: GESTIÓN DE USUARIOS MULTI-SITIOS ---
    with tab_usr_comp:
        col_u1, col_u2 = st.columns([1.2, 1.5])
        
        try:
            # Obtener sitios de la empresa para selección
            resp_sites_sel = supabase.table("sites").select("id, name").eq("company_id", company_id).execute()
            list_sites = resp_sites_sel.data if resp_sites_sel.data else []
        except:
            list_sites = []

        with col_u1:
            st.markdown("#### ➕ Crear Usuario de Empresa")
            if not list_sites:
                st.warning("Debes registrar al menos una Planta (Site) primero.")
            else:
                with st.form("form_add_company_user", clear_on_submit=True):
                    u_name = st.text_input("Nombre Completo")
                    u_email = st.text_input("Email")
                    u_pwd = st.text_input("Contraseña", type="password")
                    u_role = st.selectbox("Rol", ["SiteManager", "Operator", "Consulta"])
                    
                    st.markdown("**Permisos de Planta (Selecciona uno o más):**")
                    permissions = {}
                    for s in list_sites:
                        permissions[s["id"]] = st.checkbox(s["name"], value=False)
                    
                    if st.form_submit_button(t("settings", "btn_save"), type="primary", use_container_width=True):
                        if u_name.strip() and u_email.strip() and u_pwd.strip():
                            selected_site_ids = [k for k, v in permissions.items() if v]
                            if not selected_site_ids:
                                st.error("Debes asignar al menos una planta al usuario.")
                            else:
                                try:
                                    hashed_pwd = generate_password_hash(u_pwd)
                                    # Insertar en users
                                    resp_u = supabase.table("users").insert({
                                        "full_name": u_name.strip(),
                                        "email": u_email.strip().lower(),
                                        "password_hash": hashed_pwd,
                                        "role": u_role,
                                        "company_id": company_id,
                                        "site_id": selected_site_ids[0], # Default primary site
                                        "is_active": True
                                    }).execute()
                                    
                                    new_user_id = resp_u.data[0]['id']
                                    
                                    # Insertar en user_sites
                                    lote_permisos = [{"user_id": new_user_id, "site_id": sid} for sid in selected_site_ids]
                                    supabase.table("user_sites").insert(lote_permisos).execute()
                                    
                                    st.success("Usuario y permisos creados exitosamente.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error al crear usuario: {e}")
                                    log_error("pages/03_settings.py", "Error creating company user and permissions", e)
        with col_u2:
            st.markdown("#### 📋 Usuarios de tu Empresa")
            try:
                resp_users = supabase.table("users").select("id, full_name, email, role, is_active").eq("company_id", company_id).execute()
                if resp_users.data:
                    # Cargar permisos puente para mostrar
                    resp_bridge = supabase.table("user_sites").select("user_id, sites(name)").execute()
                    dict_bridge = {}
                    if resp_bridge.data:
                        for row in resp_bridge.data:
                            uid = row["user_id"]
                            sname = row["sites"]["name"] if row.get("sites") else ""
                            if uid not in dict_bridge:
                                dict_bridge[uid] = []
                            if sname:
                                dict_bridge[uid].append(sname)

                    df_users = pd.DataFrame(resp_users.data)
                    df_users['Plantas Permitidas'] = df_users['id'].apply(lambda x: ", ".join(dict_bridge.get(x, [])) if x in dict_bridge else "Ninguna")
                    df_users_show = df_users[['full_name', 'email', 'role', 'Plantas Permitidas', 'is_active']]
                    df_users_show.columns = ["Nombre", "Email", "Rol", "Plantas Permitidas", "Activo"]
                    st.dataframe(df_users_show, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay usuarios registrados en tu empresa.")
            except:
                st.info("Error al cargar usuarios.")

    # --- PESTAÑA 3: UBICACIONES DE LÍNEA ---
    with tab_loc:
        col_l1, col_l2 = st.columns([1, 1.5])
        with col_l1:
            st.markdown(f"#### {t('settings', 'loc_add')}")
            with st.form("form_add_location", clear_on_submit=True):
                loc_name = st.text_input(t("settings", "loc_name"))
                if st.form_submit_button(t("settings", "btn_save"), type="primary", use_container_width=True):
                    if loc_name.strip() and site_id:
                        try:
                            supabase.table("locations").insert({"site_id": site_id, "name": loc_name.strip().upper()}).execute()
                            st.success("Ubicación guardada.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar ubicación: {e}")
        with col_l2:
            st.markdown("#### 📋 Ubicaciones Registradas en esta Planta")
            try:
                resp_loc = supabase.table("locations").select("name").eq("site_id", site_id).order("name").execute()
                if resp_loc.data:
                    df_loc = pd.DataFrame(resp_loc.data)
                    st.dataframe(df_loc, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay ubicaciones registradas.")
            except:
                st.info("Error al cargar ubicaciones.")

    # --- PESTAÑA 4: EQUIPOS DE MEDICIÓN ---
    with tab_eq:
        col_eq1, col_eq2 = st.columns([1, 1.5])
        with col_eq1:
            st.markdown(f"#### {t('settings', 'eq_add')}")
            with st.form("form_add_eq", clear_on_submit=True):
                eq_id = st.text_input(t("settings", "eq_id"))
                eq_type = st.text_input(t("settings", "eq_type"))
                eq_cal = st.date_input(t("settings", "eq_cal"))
                if st.form_submit_button(t("settings", "btn_save"), type="primary", use_container_width=True):
                    if eq_id.strip() and site_id:
                        try:
                            supabase.table("measurement_equipment").insert({
                                "site_id": site_id,
                                "custom_id": eq_id.strip().upper(),
                                "equipment_type": eq_type.strip(),
                                "next_calibration": str(eq_cal)
                            }).execute()
                            st.success("Equipo registrado.")
                            st.rerun()
                        except:
                            st.error("Error al registrar equipo.")
        with col_eq2:
            st.markdown("#### 📋 Equipos Registrados en esta Planta")
            try:
                resp_eq = supabase.table("measurement_equipment").select("custom_id, equipment_type, next_calibration").eq("site_id", site_id).execute()
                if resp_eq.data:
                    df_eq = pd.DataFrame(resp_eq.data)
                    df_eq.columns = ["ID Equipo", "Tipo de Equipo", "Próxima Calibración"]
                    st.dataframe(df_eq, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay equipos registrados.")
            except:
                st.info("Error al cargar equipos.")

else:
    # --- VISTA PARA ROLES REGULARES (SITEMANAGER, OPERATOR, ETC.) ---
    tab_loc, tab_eq = st.tabs([t("settings", "tab_locations"), t("settings", "tab_equipment")])
    
    with tab_loc:
        col1, col2 = st.columns([1, 1.5])
        with col1:
            st.markdown(f"#### {t('settings', 'loc_add')}")
            with st.form("form_add_location", clear_on_submit=True):
                loc_name = st.text_input(t("settings", "loc_name"))
                if st.form_submit_button(t("settings", "btn_save"), type="primary", use_container_width=True):
                    if loc_name.strip() and site_id:
                        try:
                            supabase.table("locations").insert({"site_id": site_id, "name": loc_name.strip().upper()}).execute()
                            st.success("Ubicación guardada.")
                            st.rerun()
                        except:
                            st.error("Error al guardar ubicación.")
        with col2:
            st.markdown("#### 📋 Ubicaciones Registradas")
            try:
                resp_loc = supabase.table("locations").select("name").eq("site_id", site_id).order("name").execute()
                if resp_loc.data:
                    df_loc = pd.DataFrame(resp_loc.data)
                    st.dataframe(df_loc, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay ubicaciones registradas.")
            except:
                st.info("Error al cargar ubicaciones.")

    with tab_eq:
        col_eq1, col_eq2 = st.columns([1, 1.5])
        with col_eq1:
            st.markdown(f"#### {t('settings', 'eq_add')}")
            if rol not in ["SiteManager", "CompanyAdmin", "SuperAdmin"]:
                st.warning("Solo los administradores y gestores pueden agregar equipos.")
            else:
                with st.form("form_add_eq_regular", clear_on_submit=True):
                    eq_id = st.text_input(t("settings", "eq_id"))
                    eq_type = st.text_input(t("settings", "eq_type"))
                    eq_cal = st.date_input(t("settings", "eq_cal"))
                    if st.form_submit_button(t("settings", "btn_save"), type="primary", use_container_width=True):
                        if eq_id.strip() and site_id:
                            try:
                                supabase.table("measurement_equipment").insert({
                                    "site_id": site_id,
                                    "custom_id": eq_id.strip().upper(),
                                    "equipment_type": eq_type.strip(),
                                    "next_calibration": str(eq_cal)
                                }).execute()
                                st.success("Equipo registrado.")
                                st.rerun()
                            except:
                                st.error("Error al registrar equipo.")
        with col_eq2:
            st.markdown("#### 📋 Equipos Registrados")
            try:
                resp_eq = supabase.table("measurement_equipment").select("custom_id, equipment_type, next_calibration").eq("site_id", site_id).execute()
                if resp_eq.data:
                    df_eq = pd.DataFrame(resp_eq.data)
                    df_eq.columns = ["ID Equipo", "Tipo de Equipo", "Próxima Calibración"]
                    st.dataframe(df_eq, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay equipos registrados.")
            except:
                st.info("Error al cargar equipos.")
