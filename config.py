import streamlit as st

def inicializar_estado_global(st):
    """
    Inicializa las variables de estado global necesarias para
    el funcionamiento de la aplicación Multi-Tenant.
    """
    defaults = {
        "modo_lectura": True,
        "usuario_nombre": None,
        "rol_usuario": None,
        "val_form_key": 0,
        "lang": "es",
        "site_id": None,
        "site_name": None,
        "company_id": None,
        "user_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
