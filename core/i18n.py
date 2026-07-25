# core/i18n.py
import json
import os
import streamlit as st

def load_locales():
    """Carga los diccionarios JSON de traducción en la memoria caché de Streamlit."""
    if "locales" not in st.session_state:
        locales = {}
        # Intentar buscar la carpeta locales en el directorio actual o ruta absoluta
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, "locales")
        
        if not os.path.exists(path):
            path = "locales"

        if os.path.exists(path):
            for file in os.listdir(path):
                if file.endswith(".json"):
                    lang_code = file.split(".")[0]
                    file_path = os.path.join(path, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            locales[lang_code] = json.load(f)
                    except Exception as e:
                        print(f"Error al cargar locale {file}: {e}")
        
        st.session_state["locales"] = locales

def t(section: str, key: str, default: str = None) -> str:
    """
    Retorna la traducción para la sección y clave indicadas según el idioma seleccionado.
    """
    lang = st.session_state.get("lang", "es")
    locales = st.session_state.get("locales", {})

    dict_lang = locales.get(lang, locales.get("es", {}))
    section_dict = dict_lang.get(section, {})
    
    val = section_dict.get(key)
    if val is not None:
        return val

    # Fallback a español si no se encontró en el idioma actual
    if lang != "es" and "es" in locales:
        val_es = locales["es"].get(section, {}).get(key)
        if val_es is not None:
            return val_es

    return default if default is not None else key.replace("_", " ").title()
