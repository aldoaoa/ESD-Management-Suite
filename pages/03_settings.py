# pages/03_settings.py
import streamlit as st
import pandas as pd
import datetime
from werkzeug.security import generate_password_hash
from core.i18n import t
from core.db import get_supabase_client
from core.logger import log_error, log_event
from components.sidebar import render_sidebar, hide_sidebar

# ==========================================
# GENERAR LISTA DE ZONAS HORARIAS CON UTC OFFSET
# ==========================================
@st.cache_data
def get_formatted_timezones():
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    formatted = []
    
    try:
        import zoneinfo
        tz_names = sorted([tz for tz in zoneinfo.available_timezones() if '/' in tz or tz == 'UTC'])
    except Exception:
        tz_names = ["UTC", "America/Mexico_City", "America/Tijuana", "America/New_York", "Europe/London", "Asia/Tokyo"]

    for tz_name in tz_names:
        try:
            import zoneinfo
            dt = now_utc.astimezone(zoneinfo.ZoneInfo(tz_name))
            offset = dt.strftime('%z')
            offset_str = f"UTC{offset[:3]}:{offset[3:]}" if offset else "UTC+00:00"
            formatted.append({"code": tz_name, "label": f"{tz_name} ({offset_str})"})
        except Exception:
            formatted.append({"code": tz_name, "label": tz_name})
            
    return formatted

TIMEZONE_DATA = get_formatted_timezones()
TZ_CODES = [item["code"] for item in TIMEZONE_DATA]
TZ_MAP = {item["code"]: item["label"] for item in TIMEZONE_DATA}

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

st.markdown(f"### ⚙️ {t('settings', 'title', 'Ajustes y Configuración del Sistema')}")

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
        "🌐 " + t("settings", "tab_language", "Idioma / Language"),
        "🏢 " + t("settings", "tab_companies", "Empresas (Global)"), 
        "🔐 " + t("settings", "tab_admins", "Admins de Empresa"), 
        "🏭 " + t("settings", "tab_sites", "Plantas (Sites)"), 
        "🔐 " + t("settings", "tab_users", "Usuarios de Planta"), 
        "📍 " + t("settings", "tab_locations", "Ubicaciones de Línea"),
        "🛠️ " + t("settings", "tab_equipment", "Equipos de Medición")
    ])
    tab_lang, tab_companies, tab_admins, tab_sites, tab_usr_comp, tab_loc, tab_eq = tabs
elif is_company_admin:
    tabs = st.tabs([
        "🌐 " + t("settings", "tab_language", "Idioma / Language"),
        "🏭 " + t("settings", "tab_sites", "Plantas (Sites)"), 
        "🔐 " + t("settings", "tab_users", "Gestión de Usuarios"), 
        "📍 " + t("settings", "tab_locations", "Ubicaciones de Línea"),
        "🛠️ " + t("settings", "tab_equipment", "Equipos de Medición")
    ])
    tab_lang, tab_sites, tab_usr_comp, tab_loc, tab_eq = tabs
else:
    tabs = st.tabs([
        "🌐 " + t("settings", "tab_language", "Idioma / Language"),
        "📍 " + t("settings", "tab_locations", "Ubicaciones de Línea"), 
        "🛠️ " + t("settings", "tab_equipment", "Equipos de Medición")
    ])
    tab_lang, tab_loc, tab_eq = tabs

# ==========================================
# PESTAÑA: PREFERENCIAS DE IDIOMA
# ==========================================
with tab_lang:
    st.markdown("#### 🌐 " + t("settings", "lang_heading", "Preferencias de Idioma / Language Settings"))
    st.caption(t("settings", "lang_caption", "Selecciona el idioma preferido para la interfaz y todos los textos del sistema."))
    
    lang_actual = st.session_state.get("lang", "es")
    
    opciones_idioma = {
        "es": "Español (Spanish)",
        "en": "English (Inglés)",
        "zh": "中文 (Chinese / Chino)",
        "de": "Deutsch (German / Alemán)",
        "it": "Italiano (Italian / Italiano)",
        "ro": "Română (Romanian / Rumano)"
    }
    
    opciones_keys = list(opciones_idioma.keys())
    idx_lang = opciones_keys.index(lang_actual) if lang_actual in opciones_keys else 0
    
    sel_lang = st.radio(
        t("settings", "lbl_select_lang", "Idioma de la plataforma / Platform Language:"),
        options=opciones_keys,
        format_func=lambda x: opciones_idioma[x],
        index=idx_lang
    )
    
    if sel_lang != lang_actual:
        st.session_state["lang"] = sel_lang
        from core.i18n import load_locales
        load_locales(force=True)
        st.success(t("settings", "lang_updated", "✅ Idioma actualizado correctamente."))
        st.rerun()

# ==========================================
# PESTAÑA: GESTIÓN DE PLANTAS (SITES), USUARIOS Y PERMISOS
# ==========================================
if is_global_admin or is_company_admin:
    with tab_sites:
        st.markdown("#### 🏭 " + t("settings", "sites_title", "Gestión de Plantas (Sites), Usuarios y Permisos"))
        st.caption(t("settings", "sites_caption", "Crea plantas, asigna usuarios de tu organización a los diferentes sites y edita sus roles y permisos."))
        
        subtab_sites, subtab_users = st.tabs([
            "🏗️ " + t("settings", "subtab_sites_crud", "Plantas (Sites)"),
            "👥 " + t("settings", "subtab_user_assignments", "Asignación de Usuarios y Permisos")
        ])
        
        with subtab_sites:
            with st.expander(t("settings", "expander_add_site", "➕ Registrar Nueva Planta (Site)"), expanded=True):
                with st.form("form_alta_site", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        nombre_site_input = st.text_input(
                            t("settings", "lbl_site_name", "Nombre de la Planta / Sucursal"), 
                            placeholder=t("settings", "ph_site_name", "Ej. Planta Guadalajara / Site Norte")
                        )
                    with col2:
                        idx_tz_default = TZ_CODES.index("America/Mexico_City") if "America/Mexico_City" in TZ_CODES else 0
                        timezone_input_code = st.selectbox(
                            t("settings", "lbl_timezone", "Zona Horaria (Mundial IANA)"),
                            options=TZ_CODES,
                            format_func=lambda x: TZ_MAP.get(x, x),
                            index=idx_tz_default,
                            help=t("settings", "help_timezone", "Soporta todas las zonas horarias del mundo con desfase UTC")
                        )
                    
                    empresa_target_id = comp_id_gestion
                    if is_global_admin and dict_comps_ctx:
                        empresa_target_id = st.selectbox(
                            t("settings", "lbl_belongs_company", "Empresa a la que pertenece:"),
                            options=list(dict_comps_ctx.keys()),
                            format_func=lambda x: dict_comps_ctx[x]
                        )
                    
                    if st.form_submit_button(t("settings", "btn_save_site", "💾 Guardar Planta"), type="primary"):
                        if nombre_site_input and empresa_target_id:
                            try:
                                supabase.table("sites").insert({
                                    "company_id": empresa_target_id,
                                    "name": nombre_site_input.strip(),
                                    "timezone": timezone_input_code
                                }).execute()
                                st.success(f"✅ {t('settings', 'msg_site_created', 'Planta creada exitosamente.')}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                        else:
                            st.warning(f"⚠️ {t('settings', 'msg_fill_required', 'Completa los campos obligatorios.')}")

            st.divider()
            st.markdown(f"##### {t('settings', 'hdr_registered_sites', '📋 Directores y Plantas Registradas')}")
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
                        
                        s_tz_label = TZ_MAP.get(s_tz, s_tz)
                        idx_current_tz = TZ_CODES.index(s_tz) if s_tz in TZ_CODES else 0
                        
                        with st.expander(f"🏭 **{s_name}** ({c_name}) — TZ: `{s_tz_label}`", expanded=False):
                            with st.form(f"form_edit_site_{s_id}"):
                                edit_name = st.text_input(t("settings", "lbl_site_name", "Nombre de Planta"), value=s_name)
                                edit_tz_code = st.selectbox(
                                    t("settings", "lbl_timezone", "Zona Horaria (Mundial IANA)"),
                                    options=TZ_CODES,
                                    format_func=lambda x: TZ_MAP.get(x, x),
                                    index=idx_current_tz
                                )
                                if st.form_submit_button(t("settings", "btn_update_site", "💾 Actualizar Planta")):
                                    try:
                                        supabase.table("sites").update({
                                            "name": edit_name.strip(),
                                            "timezone": edit_tz_code
                                        }).eq("id", s_id).execute()
                                        st.success(f"✅ {t('settings', 'msg_site_updated', 'Planta actualizada.')}")
                                        st.rerun()
                                    except Exception as ex:
                                        st.error(f"Error: {ex}")
                else:
                    st.info(t("settings", "msg_no_sites", "Sin plantas registradas para esta empresa."))
            except Exception as e:
                st.error(f"Error: {e}")

        with subtab_users:
            st.markdown(f"##### {t('settings', 'hdr_assign_heading', '👥 Asignación de Usuarios a Sites y Permisos de Acceso')}")
            
            try:
                if comp_id_gestion:
                    resp_s_list = supabase.table("sites").select("id, name").eq("company_id", comp_id_gestion).order("name").execute()
                else:
                    resp_s_list = supabase.table("sites").select("id, name").order("name").execute()
                
                sites_dict = {s["id"]: s["name"] for s in resp_s_list.data} if resp_s_list.data else {}
            except:
                sites_dict = {}
                
            if not sites_dict:
                st.warning(f"⚠️ {t('settings', 'msg_create_site_first', 'Primero debes crear al menos una planta (Site) en la pestaña anterior para asignar usuarios.')}")
            else:
                site_sel_id = st.selectbox(
                    t("settings", "lbl_select_site_manage", "🏭 Selecciona Planta a gestionar:"),
                    options=list(sites_dict.keys()),
                    format_func=lambda x: sites_dict[x]
                )
                
                with st.expander(f"{t('settings', 'expander_assign_user', '➕ Asignar / Editar Permisos de Usuario en')} '{sites_dict[site_sel_id]}'", expanded=True):
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
                                t("settings", "lbl_org_user", "Usuario de la Organización:"),
                                options=list(dict_users_fmt.keys()),
                                format_func=lambda x: dict_users_fmt[x]
                            )
                            
                            rol_sel = st.selectbox(
                                t("settings", "lbl_role_permissions", "Rol y Permisos en esta Planta:"),
                                ["ADMIN", "SUPERVISOR", "AUDITOR", "READONLY"],
                                help=t("settings", "help_role", "ADMIN: Control total | SUPERVISOR: Gestión de auditorías | AUDITOR: Captura | READONLY: Solo lectura")
                            )
                            
                            act_status = st.checkbox(t("settings", "chk_active_account", "Cuenta Activa"), value=True)
                            
                            if st.form_submit_button(t("settings", "btn_save_assignment", "💾 Guardar Asignación de Usuario"), type="primary"):
                                try:
                                    supabase.table("users").update({
                                        "site_id": site_sel_id,
                                        "role": rol_sel,
                                        "is_active": act_status
                                    }).eq("id", user_sel_id).execute()
                                    st.success(f"✅ {t('settings', 'msg_assignment_saved', 'Asignación y permisos de usuario actualizados correctamente.')}")
                                    st.rerun()
                                except Exception as ex:
                                    st.error(f"Error: {ex}")
                    else:
                        st.info(t("settings", "msg_no_users_org", "No hay usuarios registrados en la empresa para asignar."))
                
                st.divider()
                st.markdown(f"##### {t('settings', 'hdr_users_assigned_to', '📋 Usuarios Asignados a')} **'{sites_dict[site_sel_id]}'**")
                try:
                    resp_site_users = supabase.table("users").select("*").eq("site_id", site_sel_id).order("email").execute()
                    if resp_site_users.data and len(resp_site_users.data) > 0:
                        df_u = pd.DataFrame(resp_site_users.data)
                        cols_show = ["email", "full_name", "role", "is_active", "created_at"]
                        cols_exist = [c for c in cols_show if c in df_u.columns]
                        st.dataframe(df_u[cols_exist], use_container_width=True)
                    else:
                        st.info(t("settings", "msg_no_assigned_users", "Sin usuarios asignados a esta planta actualmente."))
                except Exception as e:
                    st.error(f"Error: {e}")

# ==========================================
# GESTIÓN DE UBICACIONES Y EQUIPOS (PARA TODOS LOS ROLES)
# ==========================================
with tab_loc:
    st.markdown(f"#### {t('settings', 'loc_add', '➕ Registrar Nueva Ubicación')}")
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
    st.markdown(f"#### {t('settings', 'eq_add', '➕ Registrar Nuevo Equipo de Medición')}")
    st.info("Registra los instrumentos utilizados para auditorías (Megómetros, Voltímetros, etc.).")
