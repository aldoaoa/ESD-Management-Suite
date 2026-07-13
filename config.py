import json
import os
import streamlit as st
from core.i18n import load_locales


def inicializar_estado_global():
    """
    Inicializa el estado global de la aplicación.
    
    Esta función centraliza toda la inicialización necesaria:
    - Carga de locales/traducciones
    - Inicialización de variables de sesión
    - Validación de configuración crítica
    
    Se debe llamar una sola vez al inicio de app.py.
    """
    
    # Cargar locales si no existen
    if "locales" not in st.session_state:
        load_locales()
    
    # Inicializar idioma por defecto si no existe
    if "lang" not in st.session_state:
        st.session_state.lang = "es"  # Español por defecto
    
    # Inicializar variables de sesión críticas si no existen
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    
    if "user_role" not in st.session_state:
        st.session_state.user_role = None
    
    if "site" not in st.session_state:
        st.session_state.site = None
    
    # Validar que los locales se cargaron correctamente
    if not st.session_state.get("locales"):
        raise RuntimeError(
            "❌ Error crítico: No se pudieron cargar los archivos de traducción (locales)"
        )
    
    # Validar que los idiomas requeridos existen
    required_langs = ["es", "en"]
    for lang in required_langs:
        if lang not in st.session_state.locales:
            raise RuntimeError(
                f"❌ Error crítico: Falta archivo de traducción para idioma '{lang}'"
            )
    
    # Validar variables de entorno críticas (si se requieren)
    # Por ejemplo: DATABASE_URL, SECRET_KEY, etc.
    # Ejemplo comentado:
    # required_env_vars = ["DATABASE_URL", "SECRET_KEY"]
    # for var in required_env_vars:
    #     if not os.getenv(var):
    #         raise RuntimeError(f"❌ Variable de entorno requerida '{var}' no está configurada")
    
    return True


def get_config():
    """
    Retorna la configuración actual de la aplicación.
    
    Uso:
        config = get_config()
        print(config["lang"])
    """
    return {
        "lang": st.session_state.get("lang", "es"),
        "authenticated": st.session_state.get("authenticated", False),
        "user_id": st.session_state.get("user_id"),
        "user_role": st.session_state.get("user_role"),
        "site": st.session_state.get("site"),
    }
