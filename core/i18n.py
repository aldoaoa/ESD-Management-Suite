import json
import os
import streamlit as st

def load_locales():
    """Carga los diccionarios JSON en la memoria caché de Streamlit."""
    if "locales" not in st.session_state:
        locales = {}
        path = "locales"
        if os.path.exists(path):
            for file in os.listdir(path):
                if file.endswith(".json"):
                    lang_code = file.split(".")[0]
                    with open(os.path.join(path, file), "r", encoding="utf-8") as f:
                        locales[lang_code] = json.load(f)
        st.session_state.locales = locales

def t(seccion, clave):
    """
    Función de traducción rápida.
    Uso: t('login', 'btn_submit')
    """
    if "locales" not in st.session_state:
        load_locales()
    lang = st.session_state.get("lang", "en") # Inglés por defecto
    
    # Si el idioma no existe, usa inglés
    if lang not in st.session_state.locales:
        lang = "en"
        
    try:
        return st.session_state.locales[lang][seccion][clave]
    except KeyError:
        return f"[{seccion}.{clave}]" # Muestra un error visible si falta la traducción
