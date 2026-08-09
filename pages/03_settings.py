# pages/03_settings.py
"""
Módulo de Ajustes y Configuración del Sistema ESD Management Suite.
Soporte Multi-Tenant, Control de Roles, Selección de Idioma y Personalización del Logotipo.
"""
import streamlit as st
try:
    st.set_page_config(page_title="ESD Management Suite", page_icon="⚡", layout="wide")
except Exception:
    pass
import pandas as pd
import datetime
import json
import base64
from werkzeug.security import generate_password_hash
from core.i18n import t
from core.db import get_supabase_client
from core.logger import log_error, log_event
from components.sidebar import render_sidebar, hide_sidebar

# ==========================================
# JERARQUÍA PONDERADA DE ROLES
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

hide_sidebar()

# ==========================================
# 1. BARRERA DE SEGURIDAD MULTI-TENANT
# ==========================================
if st.session_state.get("modo_lectura", True):
    from core.auth import render_login_screen
    render_login_screen(t("auth", "login_required", "🔒 Por favor inicia sesión para acceder a este módulo."))
    st.stop()

render_sidebar()

supabase = get_supabase_client()
rol_sesion = st.session_state.get("rol_usuario", st.session_state.get("user_role", "SuperAdmin"))
peso_sesion = ROLE_HIERARCHY.get(rol_sesion, 100)

st.markdown(f"### ⚙️ {t('settings', 'title', 'Ajustes y Configuración del Sistema')}")

is_global_admin = rol_sesion in ["SuperAdmin", "admin"] and not st.session_state.get("company_id")
is_company_admin = rol_sesion == "CompanyAdmin" or (rol_sesion in ["SuperAdmin", "admin"] and st.session_state.get("company_id"))
is_site_admin = rol_sesion in ["ADMIN", "SiteAdmin", "SUPERVISOR"]

# ==========================================
# 2. DEFINICIÓN DE PESTAÑAS DE CONFIGURACIÓN
# ==========================================
if is_global_admin:
    tabs = st.tabs([
        "🌐 " + t("settings", "tab_language", "Idioma / Language"),
        "🖼️ " + t("settings", "tab_logo", "Logotipo"),
        "🏢 " + t("settings", "tab_companies", "Empresas (Global)"), 
        "🔐 " + t("settings", "tab_admins", "Admins de Empresa"), 
        "🏭 " + t("settings", "tab_sites", "Plantas (Sites)"), 
        "👥 " + t("settings", "tab_users", "Gestión de Usuarios")
    ])
    tab_lang, tab_logo, tab_companies, tab_admins, tab_sites, tab_usr = tabs
elif is_company_admin or is_site_admin:
    tabs = st.tabs([
        "🌐 " + t("settings", "tab_language", "Idioma / Language"),
        "🖼️ " + t("settings", "tab_logo", "Logotipo"),
        "🏭 " + t("settings", "tab_sites", "Plantas (Sites)"), 
        "👥 " + t("settings", "tab_users", "Gestión de Usuarios")
    ])
    tab_lang, tab_logo, tab_sites, tab_usr = tabs
else:
    tabs = st.tabs([
        "🌐 " + t("settings", "tab_language", "Idioma / Language"),
        "🖼️ " + t("settings", "tab_logo", "Logotipo")
    ])
    tab_lang, tab_logo = tabs

# ==========================================
# PESTAÑA 1: PREFERENCIAS DE IDIOMA
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
# PESTAÑA 2: PERSONALIZACIÓN DE LOGOTIPO
# ==========================================
with tab_logo:
    st.markdown(f"#### 🖼️ {t('settings', 'logo_title', 'Personalización del Logotipo de la Empresa / Planta')}")
    st.caption(t('settings', 'logo_subtitle', 'Carga el logotipo oficial de tu empresa en formato PNG o JPG. Se mostrará en la parte superior del menú lateral.'))
    
    if st.session_state.get("open_logo_uploader"):
        st.info(f"👉 {t('settings', 'logo_prompt', 'Has accedido desde el enlace del Sidebar. Carga la imagen de tu logotipo a continuación.')}")
        st.session_state.open_logo_uploader = False
        
    st.divider()
    
    c_logo1, c_logo2 = st.columns([1.5, 1])
    
    with c_logo1:
        st.markdown(f"**{t('settings', 'lbl_upload_logo', 'Selecciona una imagen de logotipo (PNG, JPG, JPEG):')}**")
        uploaded_logo = st.file_uploader(
            "Archivo de Logotipo",
            type=["png", "jpg", "jpeg"],
            key="settings_logo_file_input",
            label_visibility="collapsed"
        )
        
        if uploaded_logo is not None:
            bytes_data = uploaded_logo.read()
            b64_img = base64.b64encode(bytes_data).decode("utf-8")
            mime_type = uploaded_logo.type or "image/png"
            data_uri = f"data:{mime_type};base64,{b64_img}"
            
            st.image(data_uri, caption="Previsualización del archivo seleccionado", width=260)
            
            if st.button(t("settings", "btn_save_logo", "💾 Guardar Nuevo Logotipo"), type="primary", use_container_width=True):
                st.session_state.site_logo = data_uri
                st.session_state.company_logo = data_uri
                
                try:
                    site_id = st.session_state.get("site_id")
                    if site_id:
                        supabase.table("site_settings").upsert({
                            "site_id": site_id,
                            "logo_base64": data_uri,
                            "updated_at": datetime.datetime.now().isoformat()
                        }).execute()
                except Exception:
                    pass
                    
                st.success("✅ Logotipo actualizado exitosamente. El menú lateral se ha actualizado.")
                st.rerun()
                
    with c_logo2:
        st.markdown("**Logotipo Configurado Actualmente:**")
        current_logo = st.session_state.get("site_logo") or st.session_state.get("company_logo")
        if current_logo:
            st.image(current_logo, caption="Logotipo Activo", use_container_width=True)
            st.divider()
            if st.button(t("settings", "btn_remove_logo", "🗑️ Eliminar Logotipo Personalizado"), type="secondary", use_container_width=True):
                st.session_state.site_logo = None
                st.session_state.company_logo = None
                try:
                    site_id = st.session_state.get("site_id")
                    if site_id:
                        supabase.table("site_settings").delete().eq("site_id", site_id).execute()
                except Exception:
                    pass
                st.success("Logotipo eliminado. Se restableció el estado predeterminado.")
                st.rerun()
        else:
            st.info(f"ℹ️ {t('sidebar', 'placeholder_logo', 'Coloca logotipo aquí')}")
            st.caption("Aún no se ha cargado una imagen oficial de logotipo para esta planta.")

# ==========================================
# PESTAÑAS ADMINISTRATIVAS
# ==========================================
if is_global_admin:
    with tab_companies:
        st.markdown("#### 🏢 Gestión Global de Empresas")
        st.info("Administra las organizaciones clientes de la suite.")

    with tab_admins:
        st.markdown("#### 🔐 Asignación de Administradores")
        st.info("Asigna cuentas principales a cada empresa registrada.")

if is_global_admin or is_company_admin or is_site_admin:
    with tab_sites:
        st.markdown("#### 🏭 Gestión de Plantas (Sites)")
        st.caption("Configura zonas horarias y parámetros de planta.")
        
    with tab_usr:
        st.markdown("#### 👥 Gestión de Usuarios y Permisos")
        st.caption("Administración de usuarios de la planta.")
