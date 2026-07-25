# pages/03_settings.py
import streamlit as st
import pandas as pd
import datetime
import json
from werkzeug.security import generate_password_hash
from core.i18n import t
from core.db import get_supabase_client
from core.logger import log_error, log_event
from components.sidebar import render_sidebar, hide_sidebar

# ==========================================
# JERARQUÍA PONDERADA DE ROLES PÚBLICOS
# ==========================================
ROLE_HIERARCHY = {
    "SuperAdmin": 100,
    "admin": 100,
    "CompanyAdmin": 80,
    "ADMIN": 60,
    "SiteAdmin": 60,
    "SUPERVISOR": 40,
    "AUDITOR": 20,
    "READONLY": 10,
    "USER": 10
}

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
rol_sesion = st.session_state.get("rol_usuario", st.session_state.get("user_role", ""))
peso_sesion = ROLE_HIERARCHY.get(rol_sesion, 10)

st.markdown(f"### ⚙️ {t('settings', 'title', 'Ajustes y Configuración del Sistema')}")

# ==========================================
# 2. SELECCIÓN DE CONTEXTO (COMPAÑÍA / PLANTA)
# ==========================================
comp_id_gestion = st.session_state.get("company_id")
site_id_gestion = st.session_state.get("site_id")

if rol_sesion in ["SuperAdmin", "admin"] and not st.session_state.get("company_id"):
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
is_global_admin = rol_sesion in ["SuperAdmin", "admin"] and not st.session_state.get("company_id")
is_company_admin = rol_sesion == "CompanyAdmin" or (rol_sesion in ["SuperAdmin", "admin"] and st.session_state.get("company_id"))
is_site_admin = rol_sesion in ["ADMIN", "SiteAdmin"]

if is_global_admin:
    tabs = st.tabs([
        "🌐 " + t("settings", "tab_language", "Idioma / Language"),
        "🏢 " + t("settings", "tab_companies", "Empresas (Global)"), 
        "🔐 " + t("settings", "tab_admins", "Admins de Empresa"), 
        "🏭 " + t("settings", "tab_sites", "Plantas (Sites)"), 
        "👥 " + t("settings", "tab_users", "Gestión de Usuarios"), 
        "📍 " + t("settings", "tab_locations", "Ubicaciones de Línea"),
        "🛠️ " + t("settings", "tab_equipment", "Equipos de Medición")
    ])
    tab_lang, tab_companies, tab_admins, tab_sites, tab_usr_comp, tab_loc, tab_eq = tabs
elif is_company_admin or is_site_admin:
    tabs = st.tabs([
        "🌐 " + t("settings", "tab_language", "Idioma / Language"),
        "🏭 " + t("settings", "tab_sites", "Plantas (Sites)"), 
        "👥 " + t("settings", "tab_users", "Gestión de Usuarios"), 
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
# PESTAÑA: GESTIÓN DE PLANTAS (SITES)
# ==========================================
if is_global_admin or is_company_admin or is_site_admin:
    with tab_sites:
        st.markdown("#### 🏭 " + t("settings", "sites_title", "Gestión de Plantas (Sites), Usuarios y Permisos"))
        st.caption(t("settings", "sites_caption", "Crea plantas, asigna usuarios de tu organización a los diferentes sites y edita sus roles y permisos."))
        
        subtab_sites, subtab_users = st.tabs([
            "🏗️ " + t("settings", "subtab_sites_crud", "Plantas (Sites)"),
            "👥 " + t("settings", "subtab_user_assignments", "Asignación de Usuarios y Permisos")
        ])
        
        with subtab_sites:
            if is_global_admin or is_company_admin:
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
                if is_global_admin:
                    resp_sites = supabase.table("sites").select("*, companies(name)").order("name").execute()
                elif comp_id_gestion:
                    resp_sites = supabase.table("sites").select("*, companies(name)").eq("company_id", comp_id_gestion).order("name").execute()
                else:
                    resp_sites = supabase.table("sites").select("*, companies(name)").eq("id", site_id_gestion).order("name").execute()
                    
                if resp_sites.data and len(resp_sites.data) > 0:
                    for s in resp_sites.data:
                        s_id = s["id"]
                        s_name = s["name"]
                        s_tz = s.get("timezone", "UTC")
                        c_name = s.get("companies", {}).get("name", "N/A")
                        
                        s_tz_label = TZ_MAP.get(s_tz, s_tz)
                        idx_current_tz = TZ_CODES.index(s_tz) if s_tz in TZ_CODES else 0
                        
                        with st.expander(f"🏭 **{s_name}** ({c_name}) — TZ: `{s_tz_label}`", expanded=False):
                            if is_global_admin or is_company_admin:
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
                                st.write(f"📍 **Planta:** {s_name} | **Empresa:** {c_name} | **Zona Horaria:** {s_tz_label}")
                else:
                    st.info(t("settings", "msg_no_sites", "Sin plantas registradas para esta empresa."))
            except Exception as e:
                st.error(f"Error: {e}")

        with subtab_users:
            st.markdown(f"##### {t('settings', 'hdr_assign_heading', '👥 Asignación de Usuarios a Sites y Permisos de Acceso')}")
            
            try:
                if is_global_admin:
                    resp_s_list = supabase.table("sites").select("id, name").order("name").execute()
                elif comp_id_gestion:
                    resp_s_list = supabase.table("sites").select("id, name").eq("company_id", comp_id_gestion).order("name").execute()
                else:
                    resp_s_list = supabase.table("sites").select("id, name").eq("id", site_id_gestion).order("name").execute()
                
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
                        if is_global_admin:
                            u_resp = supabase.table("users").select("id, email, full_name, role, site_id").order("email").execute()
                        elif comp_id_gestion:
                            u_resp = supabase.table("users").select("id, email, full_name, role, site_id").eq("company_id", comp_id_gestion).order("email").execute()
                        else:
                            u_resp = supabase.table("users").select("id, email, full_name, role, site_id").eq("site_id", site_id_gestion).order("email").execute()
                        
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
# PESTAÑA: GESTIÓN DE USUARIOS (JERARQUÍA, ALTA, EDICIÓN, PASSWORD, PERMISOS Y ELIMINACIÓN)
# ==========================================
if is_global_admin or is_company_admin or is_site_admin:
    with tab_usr_comp:
        st.markdown(f"#### 👥 {t('settings', 'users_title', 'Gestión Integral de Usuarios de la Organización')}")
        st.caption(t("settings", "users_caption", "Administra usuarios registrados, otorga o edita permisos modulares granulares, restablece contraseñas y gestiona sus estados."))

        # 1. Cargar plantas/sites disponibles según alcance del usuario
        try:
            if is_global_admin:
                resp_s_u = supabase.table("sites").select("id, name").order("name").execute()
            elif comp_id_gestion:
                resp_s_u = supabase.table("sites").select("id, name").eq("company_id", comp_id_gestion).order("name").execute()
            else:
                resp_s_u = supabase.table("sites").select("id, name").eq("id", site_id_gestion).order("name").execute()
            sites_user_dict = {s["id"]: s["name"] for s in resp_s_u.data} if resp_s_u.data else {}
        except:
            sites_user_dict = {}

        # Determinar roles que el usuario actual PUEDE crear/asignar (estrictamente subordinados o iguales si es SuperAdmin)
        roles_disponibles_creacion = []
        if peso_sesion >= 100: # SuperAdmin
            roles_disponibles_creacion = ["CompanyAdmin", "ADMIN", "SUPERVISOR", "AUDITOR", "READONLY"]
        elif peso_sesion >= 80: # CompanyAdmin
            roles_disponibles_creacion = ["ADMIN", "SUPERVISOR", "AUDITOR", "READONLY"]
        elif peso_sesion >= 60: # SiteAdmin / ADMIN
            roles_disponibles_creacion = ["SUPERVISOR", "AUDITOR", "READONLY"]
        else:
            roles_disponibles_creacion = ["READONLY"]

        # --- FORMULARIO 1: ALTA DE NUEVO USUARIO ---
        with st.expander(f"➕ **{t('settings', 'btn_create_new_user', 'Registrar Nuevo Usuario')}**", expanded=False):
            with st.form("form_alta_usuario_org", clear_on_submit=True):
                col_u1, col_u2 = st.columns(2)
                with col_u1:
                    nu_nombre = st.text_input(t("settings", "lbl_full_name", "Nombre Completo"), placeholder="Ej. Juan Pérez")
                    nu_email = st.text_input(t("settings", "lbl_email", "Correo Electrónico"), placeholder="usuario@empresa.com")
                    nu_pass = st.text_input(t("settings", "lbl_password", "Contraseña"), type="password")
                
                with col_u2:
                    nu_rol = st.selectbox(
                        t("settings", "lbl_user_role", "Rol Principal:"),
                        roles_disponibles_creacion
                    )
                    
                    nu_site = None
                    if sites_user_dict:
                        nu_site = st.selectbox(
                            t("settings", "lbl_assign_site", "Planta / Site Principal:"),
                            options=list(sites_user_dict.keys()),
                            format_func=lambda x: sites_user_dict[x]
                        )
                    
                    nu_active = st.checkbox(t("settings", "chk_active_user", "Cuenta Activa"), value=True)

                st.markdown(f"##### 🔑 {t('settings', 'hdr_module_permissions', 'Permisos Modulares Granulares')}")
                p_col1, p_col2, p_col3, p_col4, p_col5 = st.columns(5)
                with p_col1:
                    p_audit = st.checkbox(t("settings", "perm_audit", "Auditorías en Piso"), value=True)
                with p_col2:
                    p_view = st.checkbox(t("settings", "perm_view", "Consultas y Tableros"), value=True)
                with p_col3:
                    p_inv = st.checkbox(t("settings", "perm_inventory", "Alta/Baja Inventario"), value=True)
                with p_col4:
                    p_rep = st.checkbox(t("settings", "perm_reports", "Generación Reportes"), value=True)
                with p_col5:
                    p_sett = st.checkbox(t("settings", "perm_settings", "Configuración Sistema"), value=False)

                if st.form_submit_button(t("settings", "btn_submit_create_user", "💾 Registrar Usuario"), type="primary"):
                    if not nu_email or not nu_pass:
                        st.warning(t("settings", "msg_fill_required", "Por favor completa el correo y la contraseña."))
                    else:
                        try:
                            dict_permisos = {
                                "audit": p_audit,
                                "view": p_view,
                                "inventory": p_inv,
                                "reports": p_rep,
                                "settings": p_sett
                            }
                            
                            nuevo_user_payload = {
                                "company_id": comp_id_gestion,
                                "site_id": nu_site,
                                "email": nu_email.strip().lower(),
                                "password_hash": generate_password_hash(nu_pass),
                                "full_name": nu_nombre.strip() if nu_nombre else nu_email.split('@')[0],
                                "role": nu_rol,
                                "is_active": nu_active,
                                "permissions": json.dumps(dict_permisos)
                            }
                            
                            res_ins = supabase.table("users").insert(nuevo_user_payload).execute()
                            if res_ins.data:
                                st.success(f"✅ {t('settings', 'msg_user_created', 'Usuario registrado exitosamente.')}")
                                st.rerun()
                        except Exception as ex:
                            if "duplicate key" in str(ex) or "23505" in str(ex):
                                st.error(t("settings", "msg_user_exists", "❌ El correo electrónico ya está registrado."))
                            else:
                                st.error(f"Error al registrar usuario: {ex}")

        st.divider()

        # --- LISTA Y EDICIÓN DE USUARIOS SEGÚN VISIBILIDAD DE ALCANCE ---
        st.markdown(f"##### 📋 {t('settings', 'hdr_user_directory', 'Directorio de Usuarios de la Organización')}")
        try:
            # 1. Filtro de Consulta según Alcance Organizacional
            if is_global_admin:
                # SuperAdmin ve TODOS los usuarios globales
                u_q = supabase.table("users").select("*, sites!users_site_id_fkey(name)").order("email").execute()
            elif is_company_admin and comp_id_gestion:
                # Admin de Empresa ve TODOS los usuarios de su empresa
                u_q = supabase.table("users").select("*, sites!users_site_id_fkey(name)").eq("company_id", comp_id_gestion).order("email").execute()
            elif site_id_gestion:
                # Admin de Site ve TODOS los usuarios de su site
                u_q = supabase.table("users").select("*, sites!users_site_id_fkey(name)").eq("site_id", site_id_gestion).order("email").execute()
            else:
                u_q = supabase.table("users").select("*, sites!users_site_id_fkey(name)").order("email").execute()
                
            list_u_data = u_q.data if u_q.data else []
        except Exception:
            try:
                if is_global_admin:
                    u_q = supabase.table("users").select("*").order("email").execute()
                elif is_company_admin and comp_id_gestion:
                    u_q = supabase.table("users").select("*").eq("company_id", comp_id_gestion).order("email").execute()
                elif site_id_gestion:
                    u_q = supabase.table("users").select("*").eq("site_id", site_id_gestion).order("email").execute()
                else:
                    u_q = supabase.table("users").select("*").order("email").execute()
                list_u_data = u_q.data if u_q.data else []
            except Exception as ex_f:
                list_u_data = []
                st.error(f"Error: {ex_f}")
            
        if list_u_data:
            for usr in list_u_data:
                usr_id = usr["id"]
                usr_email = usr.get("email", "Sin Email")
                usr_name = usr.get("full_name") or usr_email
                usr_role = usr.get("role", "USER")
                usr_active = usr.get("is_active", True)
                usr_site_id = usr.get("site_id")
                site_name_disp = usr.get("sites", {}).get("name") if isinstance(usr.get("sites"), dict) else "Sin Site"

                peso_target = ROLE_HIERARCHY.get(usr_role, 10)
                
                # REGLA DE PERMISOS: Puede modificar si mi_peso > target_peso O si soy SuperAdmin (peso=100)
                puede_modificar = (peso_sesion > peso_target) or (peso_sesion >= 100)
                
                badge_active = "🟢" if usr_active else "🔴"
                lock_icon = "✏️" if puede_modificar else "👁️ (Lectura)"
                
                with st.expander(f"{badge_active} **{usr_name}** (`{usr_email}`) | Rol: `{usr_role}` | Site: `{site_name_disp}` | {lock_icon}", expanded=False):
                    if puede_modificar:
                        tab_e1, tab_e2, tab_e3 = st.tabs([
                            "✏️ " + t("settings", "tab_edit_details", "Editar Detalles y Permisos"),
                            "🔑 " + t("settings", "tab_change_pass", "Cambiar Contraseña"),
                            "🗑️ " + t("settings", "tab_delete_user", "Eliminar / Desactivar")
                        ])
                        
                        # Sub-tab 1: Editar Detalles y Permisos
                        with tab_e1:
                            with st.form(f"form_edit_usr_{usr_id}"):
                                c_e1, c_e2 = st.columns(2)
                                with c_e1:
                                    e_fn = st.text_input(t("settings", "lbl_full_name", "Nombre Completo"), value=usr_name)
                                    
                                    # Solo mostrar roles que el usuario actual tiene derecho a asignar
                                    roles_permitidos_edit = [r for r in roles_disponibles_creacion if r in ["ADMIN", "SUPERVISOR", "AUDITOR", "READONLY", "CompanyAdmin"]]
                                    if usr_role not in roles_permitidos_edit:
                                        roles_permitidos_edit.append(usr_role)
                                        
                                    idx_r_e = roles_permitidos_edit.index(usr_role) if usr_role in roles_permitidos_edit else 0
                                    
                                    e_rl = st.selectbox(
                                        t("settings", "lbl_user_role", "Rol Principal:"),
                                        roles_permitidos_edit,
                                        index=idx_r_e
                                    )
                                with c_e2:
                                    s_idx = 0
                                    if sites_user_dict and usr_site_id in sites_user_dict:
                                        s_idx = list(sites_user_dict.keys()).index(usr_site_id)
                                    
                                    e_st = st.selectbox(
                                        t("settings", "lbl_assign_site", "Planta / Site Principal:"),
                                        options=list(sites_user_dict.keys()) if sites_user_dict else [None],
                                        format_func=lambda x: sites_user_dict.get(x, "Sin Site") if sites_user_dict else "N/A",
                                        index=s_idx
                                    )
                                    e_act = st.checkbox(t("settings", "chk_active_user", "Cuenta Activa"), value=usr_active)

                                perm_raw = usr.get("permissions")
                                p_dict = {}
                                if isinstance(perm_raw, str):
                                    try: p_dict = json.loads(perm_raw)
                                    except: pass
                                elif isinstance(perm_raw, dict):
                                    p_dict = perm_raw
                                
                                st.markdown(f"**{t('settings', 'hdr_module_permissions', 'Permisos Modulares Granulares')}:**")
                                pe1, pe2, pe3, pe4, pe5 = st.columns(5)
                                with pe1: ep_audit = st.checkbox("Auditorías", value=p_dict.get("audit", True), key=f"paud_{usr_id}")
                                with pe2: ep_view = st.checkbox("Consultas", value=p_dict.get("view", True), key=f"pvw_{usr_id}")
                                with pe3: ep_inv = st.checkbox("Inventario", value=p_dict.get("inventory", True), key=f"pinv_{usr_id}")
                                with pe4: ep_rep = st.checkbox("Reportes", value=p_dict.get("reports", True), key=f"prep_{usr_id}")
                                with pe5: ep_sett = st.checkbox("Ajustes", value=p_dict.get("settings", False), key=f"pset_{usr_id}")

                                if st.form_submit_button(t("settings", "btn_save_changes", "💾 Guardar Cambios")):
                                    if is_own_account and not e_act:
                                        st.warning("⚠️ No puedes desactivar tu propia cuenta mientras estás en sesión activa.")
                                        e_act = True
                                    try:
                                        nuevos_perms = {
                                            "audit": ep_audit,
                                            "view": ep_view,
                                            "inventory": ep_inv,
                                            "reports": ep_rep,
                                            "settings": ep_sett
                                        }
                                        supabase.table("users").update({
                                            "full_name": e_fn.strip(),
                                            "role": e_rl,
                                            "site_id": e_st,
                                            "is_active": e_act,
                                            "permissions": json.dumps(nuevos_perms)
                                        }).eq("id", usr_id).execute()
                                        st.success(f"✅ {t('settings', 'msg_user_updated', 'Usuario actualizado correctamente.')}")
                                        st.rerun()
                                    except Exception as ex:
                                        st.error(f"Error: {ex}")

                        # Sub-tab 2: Cambiar Contraseña
                        with tab_e2:
                            with st.form(f"form_reset_pass_{usr_id}"):
                                new_pass_inp = st.text_input(t("settings", "lbl_new_password", "Nueva Contraseña"), type="password")
                                if st.form_submit_button(t("settings", "btn_change_password", "🔐 Restablecer Contraseña"), type="primary"):
                                    if not new_pass_inp or len(new_pass_inp) < 4:
                                        st.warning(t("settings", "msg_pass_short", "La contraseña debe tener al menos 4 caracteres."))
                                    else:
                                        try:
                                            supabase.table("users").update({
                                                "password_hash": generate_password_hash(new_pass_inp)
                                            }).eq("id", usr_id).execute()
                                            st.success(f"✅ {t('settings', 'msg_pass_changed', 'Contraseña restablecida exitosamente.')}")
                                            st.rerun()
                                        except Exception as ex:
                                            st.error(f"Error: {ex}")

                        # Sub-tab 3: Eliminar o Desactivar Usuario
                        with tab_e3:
                            mi_email_sesion = str(st.session_state.get("usuario_email", st.session_state.get("user_email", ""))).strip().lower()
                            mi_id_sesion = str(st.session_state.get("user_id", "")).strip()
                            
                            is_own_account = (usr_id and str(usr_id).strip() == mi_id_sesion) or (usr_email and usr_email.strip().lower() == mi_email_sesion)
                            
                            if is_own_account:
                                st.info(f"🛡️ **{t('settings', 'info_own_account_title', 'Cuenta Propia en Sesión')}**: {t('settings', 'info_own_account_msg', 'Por motivos de seguridad y para prevenir el bloqueo accidental de tu acceso, no es posible eliminar o desactivar tu propia cuenta mientras estás logueado.')}")
                            else:
                                st.warning(t("settings", "warn_delete_user", "⚠️ Advertencia: Esta acción eliminará permanentemente la cuenta de usuario."))
                                if st.button(f"🗑️ {t('settings', 'btn_confirm_delete', 'Eliminar Usuario Definitivamente')}", key=f"del_u_{usr_id}", type="primary"):
                                    try:
                                        supabase.table("users").delete().eq("id", usr_id).execute()
                                        st.success(f"✅ {t('settings', 'msg_user_deleted', 'Usuario eliminado exitosamente.')}")
                                        st.rerun()
                                    except Exception as ex:
                                        st.error(f"Error al eliminar: {ex}")
                    else:
                        # Modo solo lectura para usuarios de jerarquía superior o igual
                        st.info("ℹ️ **Vista de Solo Lectura**: No cuentas con jerarquía suficiente para modificar o restablecer la contraseña de este usuario superior o de igual nivel.")
                        st.write(f"👤 **Nombre:** {usr_name}")
                        st.write(f"📧 **Email:** {usr_email}")
                        st.write(f"🛡️ **Rol:** {usr_role}")
                        st.write(f"🏭 **Planta:** {site_name_disp}")
                        st.write(f"🟢 **Estatus:** {'Activo' if usr_active else 'Inactivo'}")
        else:
            st.info(t("settings", "msg_no_users_found", "No hay usuarios registrados en la empresa."))

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
                        "company_id": comp_id_gestion,
                        "site_id": site_id_gestion,
                        "nombre_linea": nombre_linea_input.strip().upper()
                    }).execute()
                    st.success("✅ Ubicación agregada al catálogo.")
                    st.rerun()
                except Exception as e:
                    if "PGRST205" in str(e) or "catalogo_lineas" in str(e):
                        st.error("⚠️ La tabla 'catalogo_lineas' aún no existe en Supabase. Ejecuta el script SQL en Supabase Editor.")
                    else:
                        st.error(f"Error al agregar ubicación: {e}")
            else:
                st.warning("⚠️ Debes ingresar un nombre de ubicación.")
                
    st.divider()
    st.markdown("#### 📋 Ubicaciones Registradas en esta Planta")
    try:
        if site_id_gestion:
            resp_lineas = supabase.table("catalogo_lineas").select("*").eq("site_id", site_id_gestion).order("nombre_linea").execute()
        else:
            resp_lineas = supabase.table("catalogo_lineas").select("*").order("nombre_linea").execute()
            
        if resp_lineas.data:
            st.dataframe(pd.DataFrame(resp_lineas.data), use_container_width=True)
        else:
            st.info("Sin ubicaciones registradas.")
    except Exception as e:
        if "PGRST205" in str(e) or "catalogo_lineas" in str(e):
            st.info("💡 **Configuración Requerida en Supabase**: Crea la tabla `catalogo_lineas` en el SQL Editor de Supabase:")
            st.code("""CREATE TABLE IF NOT EXISTS public.catalogo_lineas (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    company_id UUID REFERENCES public.companies(id) ON DELETE CASCADE,
    site_id UUID REFERENCES public.sites(id) ON DELETE CASCADE,
    nombre_linea TEXT NOT NULL,
    CONSTRAINT unique_site_linea UNIQUE (site_id, nombre_linea)
);""", language="sql")
        else:
            st.error(f"Error al cargar ubicaciones: {e}")

with tab_eq:
    st.markdown(f"#### {t('settings', 'eq_add', '➕ Registrar Nuevo Equipo de Medición')}")
    st.info("Registra los instrumentos utilizados para auditorías (Megómetros, Voltímetros, etc.).")
