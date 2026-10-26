# components/sidebar.py
import streamlit as st
from core.i18n import t
from core.auth import cerrar_sesion

def hide_sidebar():
    st.markdown(
        """
        <style>
        [data-testid="sidebar-nav"] {
            display: none !important;
        }
        div[data-testid="stSidebarNav"] {
            display: none !important;
        }

        div[data-testid="stMainBlockContainer"],
        .stMainBlockContainer,
        .block-container,
        div[data-testid="stAppViewBlockContainer"],
        .stAppViewContainer .main .block-container {
            max-width: 100% !important;
            width: 100% !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            padding-top: 1rem !important;
            margin: 0 !important;
        }
        div[data-testid="stVerticalBlock"] {
            width: 100% !important;
        }

        div[data-testid="stMainBlockContainer"],
        .stMainBlockContainer,
        .block-container,
        div[data-testid="stAppViewBlockContainer"],
        .stAppViewContainer .main .block-container {
            max-width: 100% !important;
            width: 100% !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            padding-top: 1.5rem !important;
        }
        div[data-testid="stVerticalBlock"] {
            width: 100% !important;
        }

        .stAppViewContainer .main .block-container,
        [data-testid="stMainBlockContainer"],
        .block-container,
        div[data-testid="stAppViewBlockContainer"] {
            max-width: 96% !important;
            width: 96% !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            padding-top: 1.5rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    from config import inicializar_estado_global
    from core.i18n import load_locales
    inicializar_estado_global(st)
    load_locales()

def render_sidebar():
    from core.db import sync_company_logo_in_session
    sync_company_logo_in_session()

    with st.sidebar:
        st.markdown(
            """
            <style>
            [data-testid="sidebar-nav"] {
                display: none !important;
            }
            .sidebar-category {
                font-size: 11px;
                font-weight: 800;
                color: #888888;
                margin-top: 15px;
                margin-bottom: 5px;
                letter-spacing: 1px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        # --- RENDERIZADO DE LOGOTIPO DINÁMICO POR EMPRESA ---
        rol_actual = st.session_state.get("rol_usuario", st.session_state.get("user_role", ""))
        can_manage_logo = not st.session_state.get("modo_lectura", True) and rol_actual in ["SuperAdmin", "admin", "CompanyAdmin"]
        company_logo = st.session_state.get("company_logo") or st.session_state.get("site_logo")
        
        if company_logo:
            st.image(company_logo, use_container_width=True)
        else:
            placeholder_text = t("sidebar", "placeholder_logo", "Coloca logotipo aquí")
            st.markdown(
                f"""
                <div style="
                    border: 2px dashed #ff4b4b;
                    border-radius: 10px;
                    padding: 14px 10px;
                    text-align: center;
                    background-color: rgba(255, 75, 75, 0.08);
                    margin-bottom: 8px;
                ">
                    <span style="font-size: 13px; font-weight: 700; color: #ff4b4b;">{placeholder_text}</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            if can_manage_logo:
                if st.button("🖼️ " + placeholder_text, use_container_width=True, type="secondary", key="btn_sidebar_logo_placeholder"):
                    st.session_state.open_logo_uploader = True
                    try:
                        st.switch_page("pages/03_settings.py")
                    except Exception:
                        pass

        st.divider()

        # --- INFORMACIÓN DEL USUARIO ---
        if not st.session_state.get("modo_lectura", True):
            st.success(f"👤 {st.session_state.get('usuario_nombre', st.session_state.get('user_name', 'Usuario'))}")
            
            # --- SELECTOR DE PLANTA (PARA ADMINS / MULTI-TENANT) ---
            available_sites = st.session_state.get("available_sites", [])
            if available_sites:
                site_names = [s["name"] for s in available_sites]
                current_site_id = st.session_state.get("site_id")
                
                idx = 0
                for i, s in enumerate(available_sites):
                    if s["id"] == current_site_id:
                        idx = i
                        break
                
                selected_site_name = st.selectbox(
                    "🏭 Site / Planta",
                    options=site_names,
                    index=idx
                )
                
                selected_site = available_sites[site_names.index(selected_site_name)]
                if selected_site["id"] != current_site_id:
                    st.session_state.site_id = selected_site["id"]
                    st.session_state.site_name = selected_site["name"]
                    if selected_site.get("company_id"):
                        st.session_state.company_id = selected_site["company_id"]
                    if selected_site.get("company_name"):
                        st.session_state.company_name = selected_site["company_name"]
                    sync_company_logo_in_session(force=True)
                    st.rerun()
                st.caption(f"🏢 {st.session_state.get('company_name', 'Global')} | 📍 {st.session_state.get('site_name', 'Site Principal')}")
            else:
                st.caption(f"🏢 {st.session_state.get('company_name', 'Global')} | 📍 {st.session_state.get('site_name', 'Site Principal')}")
            
            st.divider()

            # --- MENÚ DE NAVEGACIÓN AGRUPADO CON TRADUCCIÓN COMPLETA ---
            st.markdown(f'<div class="sidebar-category">{t("nav", "cat_monitoring", "MONITOREO Y MÉTRICAS")}</div>', unsafe_allow_html=True)
            st.page_link("pages/01_dashboard.py", label=t("nav", "dashboard", "Dashboard general"), icon="📊")

            st.markdown(f'<div class="sidebar-category">{t("nav", "cat_verification", "VERIFICACIÓN Y PISO")}</div>', unsafe_allow_html=True)
            st.page_link("pages/02_audit.py", label=t("nav", "audit", "Auditoría en piso"), icon="🔍")
            st.page_link("pages/11_findings.py", label=t("nav", "findings", "Seguimiento de hallazgos"), icon="🎯")
            st.page_link("pages/09_schedule.py", label=t("nav", "schedule", "Cronograma de verificación"), icon="📅")

            st.markdown(f'<div class="sidebar-category">{t("nav", "cat_assets_training", "ACTIVOS Y CAPACITACIÓN")}</div>', unsafe_allow_html=True)
            st.page_link("pages/04_inventory.py", label=t("nav", "inventory", "Directorio de activos"), icon="📦")
            st.page_link("pages/05_lab.py", label=t("nav", "lab", "Laboratorio de pruebas"), icon="🧪")
            st.page_link("pages/06_infraestucture.py", label=t("nav", "infrastructure", "Infraestructura (EPA)"), icon="⚡")
            st.page_link("pages/07_training.py", label=t("nav", "training", "Entrenamiento y certificación"), icon="🎓")
            st.page_link("pages/08_sensibilidad.py", label=t("nav", "sensitivity", "Análisis de sensibilidad"), icon="🔌")
            st.page_link("pages/10_routes.py", label=t("nav", "routes", "Rutas de productos"), icon="📦")

            st.markdown(f'<div class="sidebar-category">{t("nav", "cat_settings", "CONFIGURACIÓN")}</div>', unsafe_allow_html=True)
            st.page_link("pages/03_settings.py", label=t("nav", "settings", "Ajustes del sistema"), icon="⚙️")

            st.divider()
            if st.button("🚪 " + t("nav", "logout", "Cerrar Sesión"), use_container_width=True, type="secondary"):
                cerrar_sesion()
                st.rerun()

        try:
            import os
            ver_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "VERSION")
            if os.path.exists(ver_path):
                with open(ver_path, "r", encoding="utf-8") as vf:
                    ver_str = vf.read().strip().split("-")[0]
                    st.caption(f"🔖 Versión: `{ver_str}`")
        except Exception:
            pass
