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
from core.db import (
    get_supabase_client,
    optimize_logo_image,
    save_company_logo,
    delete_company_logo,
    get_company_logo,
    sync_company_logo_in_session,
)
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

is_super_admin = rol_sesion in ["SuperAdmin", "admin"]
is_global_admin = is_super_admin and not st.session_state.get("company_id")
is_company_admin = rol_sesion == "CompanyAdmin" or (is_super_admin and bool(st.session_state.get("company_id")))
is_site_admin = rol_sesion in ["ADMIN", "SiteAdmin", "SUPERVISOR"]
can_manage_logo = is_super_admin or (rol_sesion == "CompanyAdmin")

tab_logo = None
tab_companies = None
tab_admins = None
tab_sites = None
tab_usr = None

# ==========================================
# 2. DEFINICIÓN DE PESTAÑAS DE CONFIGURACIÓN POR ROL
# ==========================================
if is_super_admin:
    tabs = st.tabs([
        "🌐 " + t("settings", "tab_language", "Idioma / Language"),
        "🖼️ " + t("settings", "tab_logo", "Identidad y Logotipo de Empresa"),
        "🏢 " + t("settings", "tab_companies", "Empresas (Global)"), 
        "🔐 " + t("settings", "tab_admins", "Admins de Empresa"), 
        "🏭 " + t("settings", "tab_sites", "Plantas (Sites)"), 
        "👥 " + t("settings", "tab_users", "Gestión de Usuarios")
    ])
    tab_lang, tab_logo, tab_companies, tab_admins, tab_sites, tab_usr = tabs
elif rol_sesion == "CompanyAdmin":
    tabs = st.tabs([
        "🌐 " + t("settings", "tab_language", "Idioma / Language"),
        "🖼️ " + t("settings", "tab_logo", "Identidad y Logotipo de Empresa"),
        "🏭 " + t("settings", "tab_sites", "Plantas (Sites)"), 
        "👥 " + t("settings", "tab_users", "Gestión de Usuarios")
    ])
    tab_lang, tab_logo, tab_sites, tab_usr = tabs
elif is_site_admin:
    tabs = st.tabs([
        "🌐 " + t("settings", "tab_language", "Idioma / Language"),
        "🏭 " + t("settings", "tab_sites", "Plantas (Sites)"), 
        "👥 " + t("settings", "tab_users", "Gestión de Usuarios")
    ])
    tab_lang, tab_sites, tab_usr = tabs
else:
    tabs = st.tabs([
        "🌐 " + t("settings", "tab_language", "Idioma / Language")
    ])
    tab_lang = tabs[0]

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
# PESTAÑA 2: IDENTIDAD Y LOGOTIPO DE EMPRESA (SOLO COMPANY ADMIN Y SUPERADMIN)
# ==========================================
if tab_logo is not None and can_manage_logo:
    with tab_logo:
        st.markdown(f"#### 🖼️ {t('settings', 'logo_title', 'Identidad y Logotipo de Empresa')}")
        st.caption(
            t(
                'settings',
                'logo_subtitle',
                'Carga el logotipo oficial de la empresa en formato PNG o JPG. Se mantendrá guardado por empresa y actualizará automáticamente el menú lateral según la empresa asignada.',
            )
        )

        if st.session_state.get("open_logo_uploader"):
            st.info(f"👉 {t('settings', 'logo_prompt', 'Has accedido desde el enlace del Sidebar. Carga la imagen de tu logotipo a continuación.')}")
            st.session_state.open_logo_uploader = False

        # Determinar la empresa objetivo a configurar (SuperAdmin puede elegir empresa; CompanyAdmin configura su empresa asignada)
        active_company_id = st.session_state.get("company_id")
        active_company_name = st.session_state.get("company_name") or "Empresa Principal"

        target_company_id = active_company_id or "global"
        target_company_name = active_company_name

        if is_super_admin:
            empresas_catalogo = []
            try:
                resp_comp = supabase.table("companies").select("id, name").order("name").execute()
                if resp_comp and resp_comp.data:
                    empresas_catalogo = resp_comp.data
            except Exception:
                pass

            # Asegurar que las empresas de available_sites y la activa estén en la lista
            ids_vistos = {str(c["id"]) for c in empresas_catalogo if c.get("id")}
            if active_company_id and str(active_company_id) not in ids_vistos:
                empresas_catalogo.insert(0, {"id": active_company_id, "name": active_company_name})
                ids_vistos.add(str(active_company_id))
            for s_item in st.session_state.get("available_sites", []):
                s_cid = s_item.get("company_id")
                s_cname = s_item.get("company_name")
                if s_cid and str(s_cid) not in ids_vistos:
                    empresas_catalogo.append({"id": s_cid, "name": s_cname or f"Empresa ({s_item.get('name')})"})
                    ids_vistos.add(str(s_cid))

            if empresas_catalogo:
                mapa_empresas = {str(c["id"]): c.get("name") or str(c["id"]) for c in empresas_catalogo}
                lista_cids = list(mapa_empresas.keys())
                idx_comp = lista_cids.index(str(active_company_id)) if str(active_company_id) in lista_cids else 0
                sel_cid = st.selectbox(
                    "🏢 Empresa a configurar (SuperAdmin):",
                    options=lista_cids,
                    index=idx_comp,
                    format_func=lambda cid: f"{mapa_empresas[cid]}",
                )
                target_company_id = sel_cid
                target_company_name = mapa_empresas[sel_cid]
            else:
                st.info(f"🏢 Configurando Identidad Corporativa para: **{target_company_name}**")
        else:
            st.info(f"🏢 Empresa Asignada: **{target_company_name}** *(Solo CompanyAdmin y SuperAdmin pueden modificar esta identidad)*")

        st.divider()

        if st.session_state.get("_logo_saved_toast"):
            st.success(st.session_state.pop("_logo_saved_toast"))

        c_logo1, c_logo2 = st.columns([1.5, 1])

        with c_logo1:
            st.markdown(f"**{t('settings', 'lbl_upload_logo', 'Selecciona una imagen de logotipo (PNG, JPG, JPEG):')}**")
            uploaded_logo = st.file_uploader(
                "Archivo de Logotipo",
                type=["png", "jpg", "jpeg"],
                key=f"settings_logo_file_input_{target_company_id}",
                label_visibility="collapsed",
            )

            if uploaded_logo is not None:
                raw_bytes = uploaded_logo.getvalue()
                opt_bytes, opt_mime, data_uri = optimize_logo_image(raw_bytes, uploaded_logo.type or "image/png")

                st.image(data_uri, caption=f"Previsualización para {target_company_name}", width=260)

                if st.button(
                    t("settings", "btn_save_logo", "💾 Guardar Nuevo Logotipo"),
                    type="primary",
                    use_container_width=True,
                    key=f"btn_save_company_logo_{target_company_id}",
                ):
                    with st.spinner("Guardando logotipo oficial de la empresa en la nube..."):
                        save_company_logo(
                            company_id=target_company_id,
                            data_uri=data_uri,
                            file_bytes=opt_bytes,
                            mime_type=opt_mime,
                        )
                        # Si la empresa editada es la empresa activa en sesión, actualizar inmediatamente el Sidebar
                        if str(target_company_id) == str(st.session_state.get("company_id") or "global"):
                            st.session_state["company_logo"] = data_uri
                            st.session_state["site_logo"] = data_uri
                            st.session_state["_logo_loaded_for_company"] = str(target_company_id)

                        log_event("INFO", "pages/03_settings.py", f"Company logo updated for company_id={target_company_id}")
                        st.session_state["_logo_saved_toast"] = f"✅ Logotipo de **{target_company_name}** guardado permanentemente y actualizado en el menú lateral."
                        st.rerun()

        with c_logo2:
            st.markdown(f"**Logotipo Activo de {target_company_name}:**")
            current_logo = get_company_logo(target_company_id)
            if current_logo:
                st.image(current_logo, caption=f"Logotipo Oficial — {target_company_name}", use_container_width=True)
                st.divider()
                if st.button(
                    t("settings", "btn_remove_logo", "🗑️ Eliminar Logotipo Personalizado"),
                    type="secondary",
                    use_container_width=True,
                    key=f"btn_del_company_logo_{target_company_id}",
                ):
                    delete_company_logo(target_company_id)
                    if str(target_company_id) == str(st.session_state.get("company_id") or "global"):
                        st.session_state["company_logo"] = None
                        st.session_state["site_logo"] = None
                    log_event("INFO", "pages/03_settings.py", f"Company logo removed for company_id={target_company_id}")
                    st.session_state["_logo_saved_toast"] = f"🗑️ Logotipo de **{target_company_name}** eliminado. Se restableció el estado predeterminado."
                    st.rerun()
            else:
                st.info(f"ℹ️ {t('sidebar', 'placeholder_logo', 'Coloca logotipo aquí')}")
                st.caption(f"Aún no se ha configurado un logotipo oficial para **{target_company_name}**.")

# ==========================================
# PESTAÑAS ADMINISTRATIVAS
# ==========================================
if is_super_admin and tab_companies is not None and tab_admins is not None:
    with tab_companies:
        st.markdown("#### 🏢 Gestión Global de Empresas")
        st.info("Administra las organizaciones clientes de la suite.")

    with tab_admins:
        st.markdown("#### 🔐 Asignación de Administradores")
        st.info("Asigna cuentas principales a cada empresa registrada.")

if (is_super_admin or is_company_admin or is_site_admin) and tab_sites is not None and tab_usr is not None:
    with tab_sites:
        st.markdown("#### 🏭 Gestión de Plantas (Sites)")
        st.caption("Configura zonas horarias y parámetros de planta.")
        
    with tab_usr:
        st.markdown("#### 👥 Gestión de Usuarios y Permisos")
        st.caption("Administración de usuarios de la planta.")
