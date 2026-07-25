# pages/03_settings.py
import streamlit as st
import pandas as pd
from werkzeug.security import generate_password_hash
from core.i18n import t
from core.db import get_supabase_client
from core.logger import log_error, log_event
from components.sidebar import render_sidebar, hide_sidebar

# Cargar lista completa de zonas horarias mundiales IANA
try:
    import zoneinfo
    ALL_TIMEZONES = sorted([tz for tz in zoneinfo.available_timezones() if '/' in tz or tz == 'UTC'])
except Exception:
    ALL_TIMEZONES = ["UTC", "America/Mexico_City", "America/Tijuana", "America/New_York", "Europe/London", "Asia/Tokyo"]

# Ocultar navegación nativa antes de evaluar accesos
hide_sidebar()

# ==========================================
# 1. BARRERA DE SEGURIDAD
# ==========================================
if st.session_state.get("modo_lectura", True):
    st.warning(t("auth", "login_required"))
    st.stop()

render_sidebar()

supabase = get_supabase_client()
rol = st.session_state.get("rol_usuario", st.session_state.get("user_role", ""))

st.markdown(f"### ⚙️ {t('settings', 'title', default='Ajustes y Configuración del Sistema')}")

# ==========================================
# 2. SELECCIÓN DE CONTEXTO (COMPAÑÍA / PLANTA)
# ==========================================
comp_id_gestion = st.session_state.get("company_id")
site_id_gestion = st.session_state.get("site_id")

if rol in ["SuperAdmin", "admin"] and not st.session_state.get("company_id"):
    try:
        resp_comps_ctx = supabase.table("companies").select("id, name").order("name").execute()
        dict_comps_ctx = {c["id"]: c["name"] for c in resp_comps_ctx.data} if resp_comps_ctx.data else {}
    except:
        dict_comps_ctx = {}
else:
    dict_comps_ctx = {}

# ==========================================
# 3. CONSTRUCCIÓN DE PESTAÑAS SEGÚN ROL
# ==========================================
is_global_admin = rol in ["SuperAdmin", "admin"] and not st.session_state.get("company_id")
is_company_admin = rol == "CompanyAdmin" or (rol in ["SuperAdmin", "admin"] and st.session_state.get("company_id"))

if is_global_admin:
    tabs = st.tabs([
        "🌐 " + t("settings", "tab_language", default="Idioma / Language"),
        "🏢 " + t("settings", "tab_companies", default="Empresas (Global)"), 
        "🔐 " + t("settings", "tab_admins", default="Admins de Empresa"), 
        "🏭 " + t("settings", "tab_sites", default="Plantas (Sites)"), 
        "🔐 " + t("settings", "tab_users", default="Usuarios de Planta"), 
        "📍 " + t("settings", "tab_locations", default="Ubicaciones de Línea"),
        "🛠️ " + t("settings", "tab_equipment", default="Equipos de Medición")
    ])
    tab_lang, tab_companies, tab_admins, tab_sites, tab_usr_comp, tab_loc, tab_eq = tabs
elif is_company_admin:
    tabs = st.tabs([
        "🌐 " + t("settings", "tab_language", default="Idioma / Language"),
        "🏭 " + t("settings", "tab_sites", default="Plantas (Sites)"), 
        "🔐 " + t("settings", "tab_users", default="Gestión de Usuarios"), 
        "📍 " + t("settings", "tab_locations", default="Ubicaciones de Línea"),
        "🛠️ " + t("settings", "tab_equipment", default="Equipos de Medición")
    ])
    tab_lang, tab_sites, tab_usr_comp, tab_loc, tab_eq = tabs
else:
    tabs = st.tabs([
        "🌐 " + t("settings", "tab_language", default="Idioma / Language"),
        "📍 " + t("settings", "tab_locations", default="Ubicaciones de Línea"), 
        "🛠️ " + t("settings", "tab_equipment", default="Equipos de Medición")
    ])
    tab_lang, tab_loc, tab_eq = tabs

# ==========================================
# PESTAÑA: PREFERENCIAS DE IDIOMA
# ==========================================
with tab_lang:
    st.markdown("#### 🌐 " + t("settings", "lang_heading", default="Preferencias de Idioma / Language Settings"))
    st.caption(t("settings", "lang_caption", default="Selecciona el idioma preferido para la interfaz y todos los textos del sistema."))
    
    lang_actual = st.session_state.get("lang", "es")
    
    opciones_idioma = {
        "es": "Español (Spanish)",
        "en": "English (Inglés)"
    }
    
    sel_lang = st.radio(
        t("settings", "lbl_select_lang", default="Idioma de la plataforma / Platform Language:"),
        options=["es", "en"],
        format_func=lambda x: opciones_idioma[x],
        index=0 if lang_actual == "es" else 1
    )
    
    if sel_lang != lang_actual:
        st.session_state["lang"] = sel_lang
        st.success(t("settings", "lang_updated", default="✅ Idioma actualizado correctamente."))
        st.rerun()

# ==========================================
# PESTAÑA: GESTIÓN DE PLANTAS (SITES), USUARIOS Y PERMISOS
# ==========================================
if is_global_admin or is_company_admin:
    with tab_sites:
        st.markdown("#### 🏭 " + t("settings", "sites_title", default="Gestión de Plantas (Sites), Usuarios y Permisos"))
        st.caption("Crea plantas, asigna usuarios de tu organización a los diferentes sites y edita sus roles y permisos.")
        
        subtab_sites, subtab_users = st.tabs([
            "🏗️ " + t("settings", "subtab_sites_crud", default="Plantas (Sites)"),
            "👥 " + t("settings", "subtab_user_assignments", default="Asignación de Usuarios y Permisos")
        ])
        
        with subtab_sites:
            with st.expander("➕ **Registrar Nueva Planta (Site)**", expanded=True):
                with st.form("form_alta_site", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        nombre_site_input = st.text_input("Nombre de la Planta / Sucursal", placeholder="Ej. Planta Guadalajara / Site Norte")
                    with col2:
                        idx_tz_default = ALL_TIMEZONES.index("America/Mexico_City") if "America/Mexico_City" in ALL_TIMEZONES else 0
                        timezone_input = st.selectbox(
                            "Zona Horaria (Mundial IANA)",
                            options=ALL_TIMEZONES,
                            index=idx_tz_default,
                            help="Soporta todas las zonas horarias del mundo (América, Europa, Asia, África, Oceanía, etc.)"
                        )
                    
                    empresa_target_id = comp_id_gestion
                    if is_global_admin and dict_comps_ctx:
                        empresa_target_id = st.selectbox(
                            "Empresa a la que pertenece:",
                            options=list(dict_comps_ctx.keys()),
                            format_func=lambda x: dict_comps_ctx[x]
                        )
                    
                    if st.form_submit_button("💾 Guardar Planta", type="primary"):
                        if nombre_site_input and empresa_target_id:
                            try:
                                supabase.table("sites").insert({
                                    "company_id": empresa_target_id,
                                    "name": nombre_site_input.strip(),
                                    "timezone": timezone_input
                                }).execute()
                                st.success(f"✅ Planta '{nombre_site_input}' creada exitosamente.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al registrar la planta: {e}")
                        else:
                            st.warning("⚠️ Completa los campos obligatorios.")

            st.divider()
            st.markdown("##### 📋 Directores y Plantas Registradas")
            try:
                if comp_id_gestion:
                    resp_sites = supabase.table("sites").select("*, companies(name)").eq("company_id", comp_id_gestion).order("name").execute()
                else:
                    resp_sites = supabase.table("sites").select("*, companies(name)").order("name").execute()
                    
                if resp_sites.data and len(resp_sites.data) > 0:
                    for s in resp_sites.data:
                        s_id = s["id"]
                        s_name = s["name"]
                        s_tz = s.get("timezone", "UTC")
                        c_name = s.get("companies", {}).get("name", "N/A")
                        
                        idx_current_tz = ALL_TIMEZONES.index(s_tz) if s_tz in ALL_TIMEZONES else 0
                        
                        with st.expander(f"🏭 **{s_name}** ({c_name}) — TZ: `{s_tz}`", expanded=False):
                            with st.form(f"form_edit_site_{s_id}"):
                                edit_name = st.text_input("Nombre de Planta", value=s_name)
                                edit_tz = st.selectbox(
                                    "Zona Horaria (Mundial IANA)",
                                    options=ALL_TIMEZONES,
                                    index=idx_current_tz
                                )
                                if st.form_submit_button("💾 Actualizar Planta"):
                                    try:
                                        supabase.table("sites").update({
                                            "name": edit_name.strip(),
                                            "timezone": edit_tz
                                        }).eq("id", s_id).execute()
                                        st.success("✅ Planta actualizada.")
                                        st.rerun()
                                    except Exception as ex:
                                        st.error(f"Error al actualizar: {ex}")
                else:
                    st.info("Sin plantas registradas para esta empresa.")
            except Exception as e:
                st.error(f"Error al cargar las plantas: {e}")

        with subtab_users:
            st.markdown("##### 👥 Asignación de Usuarios a Sites y Permisos de Acceso")
            
            try:
                if comp_id_gestion:
                    resp_s_list = supabase.table("sites").select("id, name").eq("company_id", comp_id_gestion).order("name").execute()
                else:
                    resp_s_list = supabase.table("sites").select("id, name").order("name").execute()
                
                sites_dict = {s["id"]: s["name"] for s in resp_s_list.data} if resp_s_list.data else {}
            except:
                sites_dict = {}
                
            if not sites_dict:
                st.warning("⚠️ Primero debes crear al menos una planta (Site) en la pestaña anterior para asignar usuarios.")
            else:
                site_sel_id = st.selectbox(
                    "🏭 Selecciona Planta a gestionar:",
                    options=list(sites_dict.keys()),
                    format_func=lambda x: sites_dict[x]
                )
                
                with st.expander(f"➕ **Asignar / Editar Permisos de Usuario en '{sites_dict[site_sel_id]}'**", expanded=True):
                    try:
                        if comp_id_gestion:
                            u_resp = supabase.table("users").select("id, email, full_name, role, site_id").eq("company_id", comp_id_gestion).order("email").execute()
                        else:
                            u_resp = supabase.table("users").select("id, email, full_name, role, site_id").order("email").execute()
                        
                        users_list = u_resp.data if u_resp.data else []
                    except:
                        users_list = []
                        
                    if users_list:
                        with st.form("form_assign_user_site", clear_on_submit=True):
                            dict_users_fmt = {u["id"]: f"{u.get('full_name') or u['email']} ({u['email']})" for u in users_list}
                            
                            user_sel_id = st.selectbox(
                                "Usuario de la Organización:",
                                options=list(dict_users_fmt.keys()),
                                format_func=lambda x: dict_users_fmt[x]
                            )
                            
                            rol_sel = st.selectbox(
                                "Rol y Permisos en esta Planta:",
                                ["ADMIN", "SUPERVISOR", "AUDITOR", "READONLY"],
                                help="ADMIN: Control total de la planta | SUPERVISOR: Gestión de auditorías y catálogo | AUDITOR: Captura de auditorías | READONLY: Solo visualización"
                            )
                            
                            act_status = st.checkbox("Cuenta Activa", value=True)
                            
                            if st.form_submit_button("💾 Guardar Asignación de Usuario", type="primary"):
                                try:
                                    supabase.table("users").update({
                                        "site_id": site_sel_id,
                                        "role": rol_sel,
                                        "is_active": act_status
                                    }).eq("id", user_sel_id).execute()
                                    st.success("✅ Asignación y permisos de usuario actualizados correctamente.")
                                    st.rerun()
                                except Exception as ex:
                                    st.error(f"Error al asignar usuario: {ex}")
                    else:
                        st.info("No hay usuarios registrados en la empresa para asignar.")
                
                st.divider()
                st.markdown(f"##### 📋 Usuarios Asignados a **'{sites_dict[site_sel_id]}'**")
                try:
                    resp_site_users = supabase.table("users").select("*").eq("site_id", site_sel_id).order("email").execute()
                    if resp_site_users.data and len(resp_site_users.data) > 0:
                        df_u = pd.DataFrame(resp_site_users.data)
                        cols_show = ["email", "full_name", "role", "is_active", "created_at"]
                        cols_exist = [c for c in cols_show if c in df_u.columns]
                        st.dataframe(df_u[cols_exist], use_container_width=True)
                    else:
                        st.info("Sin usuarios asignados a esta planta actualmente.")
                except Exception as e:
                    st.error(f"Error al listar usuarios de la planta: {e}")

# ==========================================
# GESTIÓN DE UBICACIONES Y EQUIPOS (PARA TODOS LOS ROLES)
# ==========================================
with tab_loc:
    st.markdown(f"#### {t('settings', 'loc_add', default='➕ Registrar Nueva Ubicación')}")
    with st.form("form_alta_ubicacion", clear_on_submit=True):
        nombre_linea_input = st.text_input("Nombre de la Línea / Estación", placeholder="Ej. SMT Línea 3")
        if st.form_submit_button("💾 Guardar Ubicación", type="primary"):
            if nombre_linea_input:
                try:
                    supabase.table("catalogo_lineas").insert({
                        "site_id": site_id_gestion,
                        "nombre_linea": nombre_linea_input.strip().upper()
                    }).execute()
                    st.success("✅ Ubicación agregada al catálogo.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al agregar ubicación: {e}")
            else:
                st.warning("⚠️ Debes ingresar un nombre de ubicación.")
                
    st.divider()
    st.markdown("#### 📋 Ubicaciones Registradas en esta Planta")
    try:
        resp_lineas = supabase.table("catalogo_lineas").select("*").eq("site_id", site_id_gestion).order("nombre_linea").execute()
        if resp_lineas.data:
            st.dataframe(pd.DataFrame(resp_lineas.data), use_container_width=True)
        else:
            st.info("Sin ubicaciones registradas.")
    except Exception as e:
        st.error(f"Error al cargar ubicaciones: {e}")

with tab_eq:
    st.markdown(f"#### {t('settings', 'eq_add', default='➕ Registrar Nuevo Equipo de Medición')}")
    st.info("Registra los instrumentos utilizados para auditorías (Megómetros, Voltímetros, etc.).")
