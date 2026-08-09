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
    Auto-refresca el caché si la llave es nueva.
    """
    locales = load_locales()
    lang = st.session_state.get("lang", "en")
    
    # 1. Intento directo en idioma activo
    if lang in locales and seccion in locales[lang] and clave in locales[lang][seccion]:
        return locales[lang][seccion][clave]

    # 2. Si no se encuentra, forzamos recarga de disco por si fue actualizado en caliente
    locales = load_locales(force=True)
    if lang in locales and seccion in locales[lang] and clave in locales[lang][seccion]:
        return locales[lang][seccion][clave]

    # 3. Fallback a inglés
    if "en" in locales and seccion in locales["en"] and clave in locales["en"][seccion]:
        return locales["en"][seccion][clave]

    # 4. Fallback a español
    if "es" in locales and seccion in locales["es"] and clave in locales["es"][seccion]:
        return locales["es"][seccion][clave]

    if default is not None:
        return default
    return f"[{seccion}.{clave}]"
