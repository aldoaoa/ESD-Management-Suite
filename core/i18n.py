import json
import os
import streamlit as st

def load_locales():
    """Carga los diccionarios JSON en la memoria caché de Streamlit."""
    if "locales" not in st.session_state:
        locales = {}
        path = "locales"
        if not os.path.exists(path):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            path = os.path.join(base_dir, "locales")
            
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

def t(seccion, clave, default=None):
    """
    Función de traducción rápida con soporte opcional de fallback 'default'.
    Uso: t('nav', 'dashboard')
    """
    if "locales" not in st.session_state:
        load_locales()
    lang = st.session_state.get("lang", "es")
    
    locales = st.session_state.get("locales", {})
    
    if lang not in locales:
        lang = "es" if "es" in locales else ("en" if "en" in locales else None)
        
    if lang and locales:
        try:
            return locales[lang][seccion][clave]
        except (KeyError, TypeError):
            # Probar fallback en español
            try:
                return locales["es"][seccion][clave]
            except (KeyError, TypeError):
                pass

    if default is not None:
        return default
    return f"[{seccion}.{clave}]"
