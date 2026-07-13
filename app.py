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
            import re
            from datetime import datetime, timedelta

            def validate_email(email):
                pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                return re.match(pattern, email) is not None

            def validate_password(password):
                return len(password) >= 8

            with st.form("login_form"):
                st.subheader(t("login_ui", "account_access"))
                email_input = st.text_input(t("login", "email_ph"))
                pwd_input = st.text_input(t("login", "pwd_ph"), type="password")
                
                if st.form_submit_button(t("login", "btn_submit"), use_container_width=True, type="primary"):
                    # Validaciones de input
                    if not email_input or not pwd_input:
                        st.warning(t("login_ui", "fields_required"))
                    elif not validate_email(email_input):
                        st.warning(t("login", "invalid_email"))
                    elif not validate_password(pwd_input):
                        st.warning(t("login", "weak_password"))
                    else:
                        # Rate limiting
                        if "login_attempts" not in st.session_state:
                            st.session_state.login_attempts = []
                        recent_attempts = [
                            t for t in st.session_state.login_attempts 
                            if datetime.now() - t < timedelta(minutes=15)
                        ]
                        if len(recent_attempts) >= 5:
                            st.error(t("login", "too_many_attempts"))
                            st.stop()

                        with st.spinner(t("login_ui", "authenticating")):
                            success, msg = iniciar_sesion(email_input, pwd_input)
                            if success:
                                st.session_state.login_attempts = []
                                st.rerun()
                            else:
                                # Registrar intento fallido
                                st.session_state.login_attempts.append(datetime.now())
                                st.error(t("login", "error_creds"))
else:
    # --- PANTALLA DE INICIO (USUARIO LOGUEADO) ---
    st.title(f"👋 {t('login_ui', 'welcome')}, {st.session_state.user_name}")
    st.info(t("common", "select_module"))
    
    # Aquí puedes colocar métricas de alto nivel a futuro
    c1, c2, c3 = st.columns(3)
    c1.metric("Company", st.session_state.get('company_name', 'N/A'))
    c2.metric("Active Site", st.session_state.get('site_name', 'N/A'))
    c3.metric("Role", st.session_state.get('user_role', 'N/A'))
