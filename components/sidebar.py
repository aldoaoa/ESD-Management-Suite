# components/sidebar.py
import streamlit as st
from core.i18n import t
from core.auth import cerrar_sesion

def render_sidebar():
    with st.sidebar:
        # Logotipo Genérico / Empresa
        st.image("https://raw.githubusercontent.com/aldoaoa/Visualizador-BCS-IDS/refs/heads/main/Logo_BCS_transparent%20(1).png", use_container_width=True)
        
        # Información de Empresa y Site Activo si ha iniciado sesión
        if not st.session_state.get("modo_lectura", True):
            st.markdown(f"**🏢 {st.session_state.get('company_name', 'ESD Enterprise')}**")
            st.caption(f"📍 Site: **{st.session_state.get('site_name', 'Site Principal')}**")
            st.caption(f"👤 Auditor: **{st.session_state.get('user_name', 'Usuario')}** ({st.session_state.get('user_role', 'AUDITOR')})")
        
        st.divider()

        # --- SELECTOR DE IDIOMA ---
        lang_actual = st.session_state.get("lang", "es")
        nuevo_lang = st.selectbox(
            "🌐 Language / Idioma", 
            options=["es", "en"], 
            format_func=lambda x: "Español" if x == "es" else "English",
            index=0 if lang_actual == "es" else 1
        )
        
        if nuevo_lang != lang_actual:
            st.session_state["lang"] = nuevo_lang
            st.rerun()

        st.divider()

        # Botón de Cerrar Sesión si está logueado
        if not st.session_state.get("modo_lectura", True):
            if st.button("🚪 " + t("auth", "logout", default="Cerrar Sesión"), use_container_width=True, type="secondary"):
                cerrar_sesion()
