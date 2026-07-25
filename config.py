# config.py
import streamlit as st

def inicializar_estado_global(st_instance):
    """
    Inicializa todas las variables de sesión globales requeridas por el sistema.
    """
    if "modo_lectura" not in st_instance.session_state:
        st_instance.session_state["modo_lectura"] = True

    if "user" not in st_instance.session_state:
        st_instance.session_state["user"] = None

    if "user_id" not in st_instance.session_state:
        st_instance.session_state["user_id"] = None

    if "user_email" not in st_instance.session_state:
        st_instance.session_state["user_email"] = None

    if "user_role" not in st_instance.session_state:
        st_instance.session_state["user_role"] = None

    if "site_id" not in st_instance.session_state:
        st_instance.session_state["site_id"] = None

    if "site_name" not in st_instance.session_state:
        st_instance.session_state["site_name"] = None

    if "company_id" not in st_instance.session_state:
        st_instance.session_state["company_id"] = None

    if "company_name" not in st_instance.session_state:
        st_instance.session_state["company_name"] = None

    if "lang" not in st_instance.session_state:
        st_instance.session_state["lang"] = "es"

    if "vista_actual" not in st_instance.session_state:
        st_instance.session_state["vista_actual"] = "Dashboard"
