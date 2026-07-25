# pages/03_settings.py
import streamlit as st
import pandas as pd
from werkzeug.security import generate_password_hash
from core.i18n import t
from core.db import get_supabase_client
from core.logger import log_error, log_event
from components.sidebar import render_sidebar, hide_sidebar

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
