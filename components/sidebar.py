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
    # Inicialización forzada para enlaces directos/actualizaciones
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

        # --- SELECTOR DE IDIOMA ---
        lang_actual = st.session_state.get("lang", "en")
        nuevo_lang = st.selectbox(
            "🌐 Language / Idioma", 
            options=["en", "es"], 
            format_func=lambda x: "English" if x == "en" else "Español",
            index=0 if lang_actual == "en" else 1
        )
        
        if nuevo_lang != lang_actual:
            st.session_state.lang = nuevo_lang
            st.rerun()
            
        st.divider()

        # --- INFORMACIÓN DEL USUARIO ---
        if not st.session_state.get("modo_lectura", True):
            st.success(f"👤 {st.session_state.get('usuario_nombre', 'User')}")
            
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
                    "🏭 Active Site / Planta",
                    options=site_names,
                    index=idx
                )
                
                selected_site = available_sites[site_names.index(selected_site_name)]
                if selected_site["id"] != current_site_id:
                    st.session_state.site_id = selected_site["id"]
                    st.session_state.site_name = selected_site["name"]
                    st.rerun()
            else:
                st.caption(f"🏢 {st.session_state.get('company_name', 'Global')} | 📍 {st.session_state.get('site_name', 'All Sites')}")
            
            st.divider()

            # --- MENÚ DE NAVEGACIÓN AGRUPADO ---
            # MONITOREO Y MÉTRICAS
            st.markdown('<div class="sidebar-category">MONITOREO Y MÉTRICAS</div>', unsafe_allow_html=True)
            st.page_link("pages/01_dashboard.py", label="Dashboard general", icon="📊")

            # VERIFICACIÓN Y PISO
            st.markdown('<div class="sidebar-category">VERIFICACIÓN Y PISO</div>', unsafe_allow_html=True)
            st.page_link("pages/02_audit.py", label="Auditoría en piso", icon="🔍")
            st.page_link("pages/09_schedule.py", label="Cronograma de verificación", icon="📅")

            # ACTIVOS Y CAPACITACIÓN
            st.markdown('<div class="sidebar-category">ACTIVOS Y CAPACITACIÓN</div>', unsafe_allow_html=True)
            st.page_link("pages/04_inventory.py", label="Directorio de activos", icon="📦")
            st.page_link("pages/05_lab.py", label="Laboratorio de pruebas", icon="🧪")
            st.page_link("pages/06_infraestucture.py", label="Infraestructura (EPA)", icon="⚡")
            st.page_link("pages/07_training.py", label="Entrenamiento y certificación", icon="🎓")
            st.page_link("pages/08_sensibilidad.py", label="Análisis de sensibilidad", icon="🔌")

            # CONFIGURACIÓN
            st.markdown('<div class="sidebar-category">CONFIGURACIÓN</div>', unsafe_allow_html=True)
            st.page_link("pages/03_settings.py", label="Ajustes del sistema", icon="⚙️")

            st.divider()
            if st.button("🚪 Logout / Cerrar Sesión", use_container_width=True, type="secondary"):
                cerrar_sesion()
                st.rerun()
