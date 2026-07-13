# app.py
import streamlit as st
from config import inicializar_estado_global
from core.i18n import load_locales, t
from core.auth import iniciar_sesion
from components.sidebar import render_sidebar

# 1. Configuración de página (Debe ser el primer comando de Streamlit)
st.set_page_config(
    page_title="ESD Management Suite", 
    page_icon="🛡️", 
    layout="wide"
)

# 2. Inicializar estado global y cargar diccionarios de idioma
inicializar_estado_global()

# 3. Renderizar el menú lateral
render_sidebar()

# 4. Lógica de Enrutamiento (Router)
if st.session_state.get("is_read_only", True):
    # --- PANTALLA DE LOGIN ---
    st.title(t("login", "title"))
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            with st.form("login_form"):
                st.subheader("🔒 Account Access")
                email_input = st.text_input(t("login", "email_ph"))
                pwd_input = st.text_input(t("login", "pwd_ph"), type="password")
                
                if st.form_submit_button(t("login", "btn_submit"), use_container_width=True, type="primary"):
                    if email_input and pwd_input:
                        with st.spinner("Authenticating..."):
                            success, msg = iniciar_sesion(email_input, pwd_input)
                            if success:
                                st.rerun()
                            else:
                                st.error(t("login", "error_creds"))
                    else:
                        st.warning("Please fill in all fields.")
else:
    # --- PANTALLA DE INICIO (USUARIO LOGUEADO) ---
    st.title(f"👋 Welcome, {st.session_state.user_name}")
    st.info("👈 Please select a module from the sidebar to begin.")
    
    # Aquí puedes colocar métricas de alto nivel a futuro
    c1, c2, c3 = st.columns(3)
    c1.metric("Company", st.session_state.get('company_name', 'N/A'))
    c2.metric("Active Site", st.session_state.get('site_name', 'N/A'))
    c3.metric("Role", st.session_state.get('user_role', 'N/A'))
