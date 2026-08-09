# Full Reboot Trigger main 2026-08-09 10:38
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
inicializar_estado_global(st)
load_locales()

# 3. Renderizar la barra lateral
render_sidebar()

# FORZAR 100% ANCHO COMPLETO EN STREAMLIT
st.markdown('''
    <style>
    .stAppViewContainer .main .block-container,
    div[data-testid="stMainBlockContainer"],
    .stMainBlockContainer,
    .block-container,
    div[data-testid="stAppViewBlockContainer"] {
        max-width: 100% !important;
        width: 100% !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        padding-top: 1.5rem !important;
    }
    [data-testid="stVerticalBlock"] {
        width: 100% !important;
    }
    </style>
''', unsafe_allow_html=True)


# 4. Lógica de Enrutamiento (Login vs Sistema Principal)
if st.session_state.get("modo_lectura", True):
    # --- PANTALLA DE LOGIN ---
    st.title("🛡️ " + t("login", "title", default="ESD Management Suite - Acceso al Sistema"))
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.container(border=True):
            st.subheader("🔒 " + t("login", "account_access", default="Acceso de Usuario"))
            with st.form("login_form"):
                email_input = st.text_input(t("login", "email", default="Correo Electrónico"), placeholder="usuario@empresa.com")
                password_input = st.text_input(t("login", "password", default="Contraseña"), type="password")
                submit_btn = st.form_submit_button(t("login", "submit", default="Iniciar Sesión"), use_container_width=True, type="primary")
                
                if submit_btn:
                    if email_input and password_input:
                        success, res = iniciar_sesion(email_input, password_input)
                        if success:
                            st.success("✅ Acceso autorizado. Cargando sistema...")
                            st.rerun()
                        else:
                            msg = t("login", res, default=f"Error de inicio de sesión: {res}")
                            st.error(f"❌ {msg}")
                    else:
                        st.warning("⚠️ Ingresa correo y contraseña.")
else:
    # --- SISTEMA PRINCIPAL LOGUEADO ---
    st.markdown(f"## 🛡️ ESD Management Suite - **{st.session_state.get('site_name', 'Site')}**")
    st.caption("Selecciona un módulo en la navegación lateral para operar.")
