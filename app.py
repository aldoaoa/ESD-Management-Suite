# Full Reboot Trigger testing 2026-08-09 10:38
# app.py
import streamlit as st
from config import inicializar_estado_global
from core.i18n import load_locales, t
from core.auth import iniciar_sesion
from components.sidebar import render_sidebar, hide_sidebar
from core.logger import log_event, log_error

# Hide native Streamlit navigation lists globally
hide_sidebar()

# 1. Configuración de página (Debe ser el primer comando de Streamlit)
st.set_page_config(
    page_title="ESD Management Suite", 
    page_icon="🛡️", 
    layout="wide"
)

try:
    # 2. Inicializar estado global y cargar diccionarios de idioma
    inicializar_estado_global(st)
    load_locales()

    # 3. Renderizar el menú lateral
    render_sidebar()

    # 4. Lógica de Enrutamiento (Router)
    if st.session_state.get("modo_lectura", True):
        # --- PANTALLA DE LOGIN ---
        st.title(t("login", "title", "ESD Management Suite - Acceso al Sistema"))
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.container(border=True):
                with st.form("login_form"):
                    st.subheader(f"🔒 {t('login', 'account_access', 'Acceso de Usuario')}")
                    email_input = st.text_input(t("login", "email_ph", "Correo Electrónico"))
                    pwd_input = st.text_input(t("login", "pwd_ph", "Contraseña"), type="password")
                    
                    if st.form_submit_button(t("login", "btn_submit", "Iniciar Sesión"), use_container_width=True, type="primary"):
                        if email_input and pwd_input:
                            with st.spinner(t("login", "authenticating", "Autenticando...")):
                                success, msg = iniciar_sesion(email_input, pwd_input)
                                if success:
                                    log_event("INFO", "app.py", f"Successful login for user: {email_input}")
                                    st.rerun()
                                else:
                                    log_event("WARNING", "app.py", f"Failed login attempt for email: {email_input} (Reason: {msg})")
                                    st.error(t("login", "error_creds", "❌ Credenciales incorrectas. Verifica tu correo y contraseña."))
                        else:
                            st.warning(t("login", "fill_all", "Por favor completa todos los campos."))
    else:
        # --- PANTALLA DE INICIO (USUARIO LOGUEADO) ---
        st.title(f"👋 {t('login', 'welcome', 'Bienvenido')}, {st.session_state.usuario_nombre}")
        st.info(f"👈 {t('login', 'select_module', 'Por favor selecciona un módulo del menú lateral para comenzar.')}")
        
        c1, c2, c3 = st.columns(3)
        c1.metric(t("settings", "tab_companies", "Empresa"), st.session_state.get('company_name', 'N/A'))
        c2.metric(t("settings", "tab_sites", "Site Activo"), st.session_state.get('site_name', 'N/A'))
        c3.metric(t("settings", "lbl_user_role", "Rol"), st.session_state.get('rol_usuario', 'N/A'))

except Exception as e:
    st.error("⚠️ An unexpected error occurred. The system administrator has been notified.")
    log_error("app.py", "Unhandled exception in application router/startup", e)
