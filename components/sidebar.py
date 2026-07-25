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
        </style>
        """,
        unsafe_allow_html=True
    )
    from config import inicializar_estado_global
    from core.i18n import load_locales
    inicializar_estado_global(st)
    load_locales()

def render_sidebar():
    with st.sidebar:
        # --- LOGOTIPO Y ESTILOS CSS PARA OCULTAR MENÚ NATIVO ---
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
        
        st.image("https://raw.githubusercontent.com/aldoaoa/Visualizador-BCS-IDS/refs/heads/main/Logo_BCS_transparent%20(1).png", use_container_width=True)
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
                    st.rerun()
            else:
                st.caption(f"🏢 {st.session_state.get('company_name', 'Global')} | 📍 {st.session_state.get('site_name', 'Site Principal')}")
            
            st.divider()

            # --- MENÚ DE NAVEGACIÓN AGRUPADO CON TRADUCCIÓN COMPLETA ---
            # MONITOREO Y MÉTRICAS
            st.markdown(f'<div class="sidebar-category">{t("nav", "cat_monitoring", default="MONITOREO Y MÉTRICAS")}</div>', unsafe_allow_html=True)
            st.page_link("pages/01_dashboard.py", label=t("nav", "dashboard", default="Dashboard general"), icon="📊")

            # VERIFICACIÓN Y PISO
            st.markdown(f'<div class="sidebar-category">{t("nav", "cat_verification", default="VERIFICACIÓN Y PISO")}</div>', unsafe_allow_html=True)
            st.page_link("pages/02_audit.py", label=t("nav", "audit", default="Auditoría en piso"), icon="🔍")
            st.page_link("pages/09_schedule.py", label=t("nav", "schedule", default="Cronograma de verificación"), icon="📅")

            # ACTIVOS Y CAPACITACIÓN
            st.markdown(f'<div class="sidebar-category">{t("nav", "cat_assets_training", default="ACTIVOS Y CAPACITACIÓN")}</div>', unsafe_allow_html=True)
            st.page_link("pages/04_inventory.py", label=t("nav", "inventory", default="Directorio de activos"), icon="📦")
            st.page_link("pages/05_lab.py", label=t("nav", "lab", default="Laboratorio de pruebas"), icon="🧪")
            st.page_link("pages/06_infraestucture.py", label=t("nav", "infrastructure", default="Infraestructura (EPA)"), icon="⚡")
            st.page_link("pages/07_training.py", label=t("nav", "training", default="Entrenamiento y certificación"), icon="🎓")
            st.page_link("pages/08_sensibilidad.py", label=t("nav", "sensitivity", default="Análisis de sensibilidad"), icon="🔌")
            st.page_link("pages/10_routes.py", label=t("nav", "routes", default="Rutas de productos"), icon="📦")

            # CONFIGURACIÓN
            st.markdown(f'<div class="sidebar-category">{t("nav", "cat_settings", default="CONFIGURACIÓN")}</div>', unsafe_allow_html=True)
            st.page_link("pages/03_settings.py", label=t("nav", "settings", default="Ajustes del sistema"), icon="⚙️")

            st.divider()
            if st.button("🚪 " + t("nav", "logout", default="Cerrar Sesión"), use_container_width=True, type="secondary"):
                cerrar_sesion()
                st.rerun()
