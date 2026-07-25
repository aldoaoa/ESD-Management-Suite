import json
import os
import streamlit as st

def get_locales_dir():
    """Obtiene la ruta absoluta segura de la carpeta locales/."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    possible_paths = [
        os.path.join(parent_dir, "locales"),
        os.path.join(os.getcwd(), "locales"),
        "locales"
    ]
    for p in possible_paths:
        if os.path.exists(p) and os.path.isdir(p):
            return p
    return "locales"

def load_locales(force=False):
    """Carga los diccionarios JSON de todos los idiomas disponibles en la memoria de la sesión."""
    if force or "locales" not in st.session_state or not st.session_state.get("locales"):
        locales = {}
        path = get_locales_dir()
        if os.path.exists(path):
            for file in os.listdir(path):
                if file.endswith(".json"):
                    lang_code = file.split(".")[0]
                    file_path = os.path.join(path, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            locales[lang_code] = json.load(f)
                    except Exception as e:
                        print(f"Error loading locale {file}: {e}")
        st.session_state.locales = locales
        return locales
    return st.session_state.locales

def t(seccion, clave, default=None):
    """
    Función de traducción rápida con soporte dinámico de todos los idiomas registrados.
    Uso: t('nav', 'dashboard')
    """
    locales = load_locales()
    lang = st.session_state.get("lang", "es")
    
    # Si el idioma solicitado no está en la memoria caché, forzar recarga de locales/
    if lang not in locales:
        locales = load_locales(force=True)
        
    if lang in locales and seccion in locales[lang] and clave in locales[lang][seccion]:
        return locales[lang][seccion][clave]

    # Fallback al idioma español si la clave no existe en el idioma seleccionado
    if "es" in locales and seccion in locales["es"] and clave in locales["es"][seccion]:
        return locales["es"][seccion][clave]

    # Fallback al idioma inglés si tampoco está en español
    if "en" in locales and seccion in locales["en"] and clave in locales["en"][seccion]:
        return locales["en"][seccion][clave]

    if default is not None:
        return default
    return f"[{seccion}.{clave}]"
