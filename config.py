import json
import os
import streamlit as st
import logging
from core.i18n import load_locales

logger = logging.getLogger(__name__)

REQUIRED_SECRETS = ["SUPABASE_URL", "SUPABASE_KEY"]


def validar_secrets():
    """
    Valida que los secrets requeridos estén configurados.
    
    Raises:
        RuntimeError: Si falta algún secret requerido
    """
    missing_secrets = []
    for secret in REQUIRED_SECRETS:
        try:
            _ = st.secrets[secret]
        except KeyError:
            missing_secrets.append(secret)
    
    if missing_secrets:
        error_msg = f"Secrets faltantes: {', '.join(missing_secrets)}"
        logger.error(error_msg)
        raise RuntimeError(f"❌ {error_msg}. Configura estos valores en .streamlit/secrets.toml")


def inicializar_estado_global():
    """
    Inicializa el estado global de la aplicación.
    
    Esta función centraliza toda la inicialización necesaria:
    - Validación de secrets
    - Carga de locales/traducciones
    - Inicialización de variables de sesión
    - Validación de configuración crítica
    
    Se debe llamar una sola vez al inicio de app.py.
    """
    
    try:
        # Validar secrets requeridos
        validar_secrets()
        logger.debug("Secrets validated successfully")
    except RuntimeError as e:
        st.error(str(e))
        st.stop()
    
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
    
    if "site_id" not in st.session_state:
        st.session_state.site_id = None
    
    if "is_read_only" not in st.session_state:
        st.session_state.is_read_only = True
    
    # Validar que los locales se cargaron correctamente
    if not st.session_state.get("locales"):
        error_msg = "No se pudieron cargar los archivos de traducción (locales)"
        logger.error(error_msg)
        raise RuntimeError(f"❌ Error crítico: {error_msg}")
    
    # Validar que los idiomas requeridos existen
    required_langs = ["es", "en"]
    for lang in required_langs:
        if lang not in st.session_state.locales:
            error_msg = f"Falta archivo de traducción para idioma '{lang}'"
            logger.error(error_msg)
            raise RuntimeError(f"❌ Error crítico: {error_msg}")
    
    logger.info("Global state initialized successfully")
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
        "site_id": st.session_state.get("site_id"),
    }
