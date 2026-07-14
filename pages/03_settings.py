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

render_sidebar()

supabase = get_supabase_client()
rol = st.session_state.get("rol_usuario", "")

st.markdown(f"### {t('settings', 'title')}")

# ==========================================
# 2. SELECCIÓN DE CONTEXTO (COMPAÑÍA / PLANTA)
# ==========================================
comp_id_gestion = st.session_state.company_id
site_id_gestion = st.session_state.site_id

if rol in ["SuperAdmin", "admin"] and not st.session_state.company_id:
    # El SuperAdmin gestiona de manera global, cargamos todas las empresas
    try:
        resp_comps_ctx = supabase.table("companies").select("id, name").order("name").execute()
        dict_comps_ctx = {c["id"]: c["name"] for c in resp_comps_ctx.data} if resp_comps_ctx.data else {}
    except:
        dict_comps_ctx = {}
    
    if dict_comps_ctx:
        col_ctx1, col_ctx2 = st.columns(2)
        comp_id_gestion = col_ctx1.selectbox(
            "🏢 Empresa a Gestionar (Modo SuperAdmin)",
            options=list(dict_comps_ctx.keys()),
            format_func=lambda x: dict_comps_ctx[x]
        )
        
        # Cargar plantas de la empresa seleccionada
        try:
            resp_sites_ctx = supabase.table("sites").select("id, name").eq("company_id", comp_id_gestion).order("name").execute()
            dict_sites_ctx = {s["id"]: s["name"] for s in resp_sites_ctx.data} if resp_sites_ctx.data else {}
        except:
            dict_sites_ctx = {}
            
        if dict_sites_ctx:
            site_id_gestion = col_ctx2.selectbox(
                "🏭 Planta a Gestionar (Modo SuperAdmin)",
                options=list(dict_sites_ctx.keys()),
                format_func=lambda x: dict_sites_ctx[x]
            )
        else:
            col_ctx2.warning("Esta empresa no tiene plantas registradas.")
            site_id_gestion = None
    else:
        st.warning("No hay empresas registradas en el sistema global.")

elif rol == "CompanyAdmin":
    # El Administrador de Empresa puede seleccionar de entre las plantas de su propia empresa
    try:
        resp_sites_ctx = supabase.table("sites").select("id, name").eq("company_id", comp_id_gestion).order("name").execute()
        dict_sites_ctx = {s["id"]: s["name"] for s in resp_sites_ctx.data} if resp_sites_ctx.data else {}
    except:
        dict_sites_ctx = {}
        
    if dict_sites_ctx:
        col_ctx = st.columns(1)[0]
        site_id_gestion = col_ctx.selectbox(
            "🏭 Planta Activa para Gestión",
            options=list(dict_sites_ctx.keys()),
            format_func=lambda x: dict_sites_ctx[x]
        )
    else:
        st.warning("Registra una planta en la pestaña 'Plantas' para comenzar la administración de ubicaciones y equipos.")
        site_id_gestion = None

st.divider()

# ==========================================
# 3. CONSTRUCCIÓN DE PESTAÑAS SEGÚN ROL
# ==========================================
if rol in ["SuperAdmin", "admin"] and not st.session_state.company_id:
    # Pestañas disponibles para SuperAdmin
    tabs = st.tabs([
        "🏢 Empresas (Global)", 
        "🔐 Admins de Empresa", 
        "🏭 Plantas (Sites)", 
        "🔐 Usuarios de Planta", 
        "📍 Ubicaciones de Línea",
        "🛠️ Equipos de Medición"
    ])
    tab_companies, tab_admins, tab_sites, tab_usr_comp, tab_loc, tab_eq = tabs
else:
    # Pestañas para Administrador de Empresa y SiteManager
    if rol == "CompanyAdmin":
        tabs = st.tabs([
            "🏭 Plantas (Sites)", 
            "🔐 Gestión de Usuarios", 
            "📍 Ubicaciones de Línea",
            "🛠️ Equipos de Medición"
        ])
        tab_sites, tab_usr_comp, tab_loc, tab_eq = tabs
    else:
        # SiteManager y regular
        tabs = st.tabs([
            t("settings", "tab_locations"), 
            t("settings", "tab_equipment")
        ])
        tab_loc, tab_eq = tabs

# --- PESTAÑA: GESTIÓN DE EMPRESAS (SUPERADMIN) ---
if rol in ["SuperAdmin", "admin"] and not st.session_state.company_id:
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
                resp_comps = supabase.table("companies").select("id, name, created_at").order("name").execute()
                if resp_comps.data:
                    df_comps = pd.DataFrame(resp_comps.data)
                    df_comps = df_comps[['id', 'name', 'created_at']]
                    df_comps.columns = ["ID Empresa", "Nombre de Empresa", "Fecha Registro"]
                    st.dataframe(df_comps, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay empresas registradas.")
            except Exception as e:
                st.info("Error al cargar empresas.")
                log_error("pages/03_settings.py", "Error fetching companies", e)

    # --- PESTAÑA: ADMINISTRADORES DE EMPRESA (SUPERADMIN) ---
    with tab_admins:
        col_adm1, col_adm2 = st.columns([1, 1.5])
        with col_adm1:
            st.markdown("#### ➕ Crear Administrador de Empresa")
            if not dict_comps_ctx:
                st.warning("Debes registrar al menos una empresa primero.")
            else:
                with st.form("form_add_company_admin", clear_on_submit=True):
                    adm_name = st.text_input("Nombre Completo")
                    adm_email = st.text_input("Email")
                    adm_pwd = st.text_input("Contraseña", type="password")
                    adm_comp = st.selectbox("Empresa Asociada", options=list(dict_comps_ctx.keys()), format_func=lambda x: dict_comps_ctx[x])
                    
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
                                    "site_id": None,
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
            except Exception as e:
                st.info("Error al cargar administradores.")
                log_error("pages/03_settings.py", "Error fetching CompanyAdmin list", e)

# --- PESTAÑA: PLANTAS (SITES) (SUPERADMIN & COMPANYADMIN) ---
if rol in ["SuperAdmin", "admin", "CompanyAdmin"]:
    with tab_sites:
        col_s1, col_s2 = st.columns([1, 1.5])
        with col_s1:
            st.markdown("#### ➕ Registrar Nueva Planta")
            if not comp_id_gestion:
                st.warning("Selecciona una empresa arriba para agregar plantas.")
            else:
                with st.form("form_add_site", clear_on_submit=True):
                    site_name_inp = st.text_input("Nombre de la Planta (Ej: Monterrey Plant)")
                    site_tz = st.selectbox("Zona Horaria", ["America/Mexico_City", "America/Monterrey", "America/Chihuahua", "America/Tijuana"])
                    
                    if st.form_submit_button(t("settings", "btn_save"), type="primary", use_container_width=True):
                        if site_name_inp.strip():
                            try:
                                supabase.table("sites").insert({
                                    "company_id": comp_id_gestion,
                                    "name": site_name_inp.strip(),
                                    "timezone": site_tz
                                }).execute()
                                st.success("Planta registrada con éxito.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al guardar planta: {e}")
                                log_error("pages/03_settings.py", "Error inserting site", e)
        with col_s2:
            st.markdown("#### 📋 Plantas Registradas")
            if comp_id_gestion:
                try:
                    resp_s = supabase.table("sites").select("*").eq("company_id", comp_id_gestion).execute()
                    if resp_s.data:
                        df_s = pd.DataFrame(resp_s.data)
                        df_s_show = df_s[['name', 'timezone', 'created_at']]
                        df_s_show.columns = ["Nombre Planta", "Zona Horaria", "Fecha Creación"]
                        st.dataframe(df_s_show, use_container_width=True, hide_index=True)
                    else:
                        st.info("No hay plantas registradas para esta empresa.")
                except Exception as e:
                    st.info("Error al cargar plantas.")
                    log_error("pages/03_settings.py", "Error fetching sites list", e)

    # --- PESTAÑA: GESTIÓN DE USUARIOS (SUPERADMIN & COMPANYADMIN) ---
    with tab_usr_comp:
        col_u1, col_u2 = st.columns([1.2, 1.5])
        
        try:
            # Obtener sitios de la empresa para selección
            resp_sites_sel = supabase.table("sites").select("id, name").eq("company_id", comp_id_gestion).execute()
            list_sites = resp_sites_sel.data if resp_sites_sel.data else []
        except:
            list_sites = []

        with col_u1:
            st.markdown("#### ➕ Crear Usuario de Empresa")
            if not comp_id_gestion:
                st.warning("Selecciona una empresa para gestionar usuarios.")
            elif not list_sites:
                st.warning("Debes registrar al menos una Planta (Site) primero para esta empresa.")
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
                                    resp_u = supabase.table("users").insert({
                                        "full_name": u_name.strip(),
                                        "email": u_email.strip().lower(),
                                        "password_hash": hashed_pwd,
                                        "role": u_role,
                                        "company_id": comp_id_gestion,
                                        "site_id": selected_site_ids[0],
                                        "is_active": True
                                    }).execute()
                                    
                                    new_user_id = resp_u.data[0]['id']
                                    lote_permisos = [{"user_id": new_user_id, "site_id": sid} for sid in selected_site_ids]
                                    supabase.table("user_sites").insert(lote_permisos).execute()
                                    
                                    st.success("Usuario y permisos creados exitosamente.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error al crear usuario: {e}")
                                    log_error("pages/03_settings.py", "Error creating company user and permissions", e)
        with col_u2:
            st.markdown("#### 📋 Usuarios Registrados")
            if comp_id_gestion:
                try:
                    resp_users = supabase.table("users").select("id, full_name, email, role, is_active").eq("company_id", comp_id_gestion).execute()
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
                except Exception as e:
                    st.info("Error al cargar usuarios.")
                    log_error("pages/03_settings.py", "Error listing users", e)

# --- PESTAÑA: UBICACIONES DE LÍNEA ---
with tab_loc:
    col_l1, col_l2 = st.columns([1, 1.5])
    with col_l1:
        st.markdown(f"#### {t('settings', 'loc_add')}")
        if not site_id_gestion:
            st.warning("Selecciona una Planta (Site) arriba para agregar ubicaciones.")
        else:
            with st.form("form_add_location", clear_on_submit=True):
                loc_name = st.text_input(t("settings", "loc_name"))
                if st.form_submit_button(t("settings", "btn_save"), type="primary", use_container_width=True):
                    if loc_name.strip():
                        try:
                            supabase.table("locations").insert({"site_id": site_id_gestion, "name": loc_name.strip().upper()}).execute()
                            st.success("Ubicación guardada.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al guardar ubicación: {e}")
    with col_l2:
        st.markdown("#### 📋 Ubicaciones Registradas en esta Planta")
        if site_id_gestion:
            try:
                resp_loc = supabase.table("locations").select("name").eq("site_id", site_id_gestion).order("name").execute()
                if resp_loc.data:
                    df_loc = pd.DataFrame(resp_loc.data)
                    st.dataframe(df_loc, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay ubicaciones registradas.")
            except:
                st.info("Error al cargar ubicaciones.")

# --- PESTAÑA: EQUIPOS DE MEDICIÓN ---
with tab_eq:
    col_eq1, col_eq2 = st.columns([1, 1.5])
    with col_eq1:
        st.markdown(f"#### {t('settings', 'eq_add')}")
        if not site_id_gestion:
            st.warning("Selecciona una Planta (Site) arriba para agregar equipos.")
        elif rol not in ["SiteManager", "CompanyAdmin", "SuperAdmin", "admin"]:
            st.warning("Solo los administradores y gestores pueden agregar equipos.")
        else:
            with st.form("form_add_eq", clear_on_submit=True):
                eq_id = st.text_input(t("settings", "eq_id"))
                eq_type = st.text_input(t("settings", "eq_type"))
                eq_cal = st.date_input(t("settings", "eq_cal"))
                if st.form_submit_button(t("settings", "btn_save"), type="primary", use_container_width=True):
                    if eq_id.strip():
                        try:
                            supabase.table("measurement_equipment").insert({
                                "site_id": site_id_gestion,
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
        if site_id_gestion:
            try:
                resp_eq = supabase.table("measurement_equipment").select("custom_id, equipment_type, next_calibration").eq("site_id", site_id_gestion).execute()
                if resp_eq.data:
                    df_eq = pd.DataFrame(resp_eq.data)
                    df_eq.columns = ["ID Equipo", "Tipo de Equipo", "Próxima Calibración"]
                    st.dataframe(df_eq, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay equipos registrados.")
            except:
                st.info("Error al cargar equipos.")
