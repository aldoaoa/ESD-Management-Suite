# components/sidebar.py
import streamlit as st
from core.i18n import t
from core.auth import cerrar_sesion

def render_sidebar():
    with st.sidebar:
        # Logotipo GenÃ©rico (Puede ser dinÃ¡mico por empresa en el futuro)
        st.image("https://raw.githubusercontent.com/aldoaoa/Visualizador-BCS-IDS/refs/heads/main/Logo_BCS_transparent%20(1).png", use_container_width=True)
        st.divider()

        # --- SELECTOR DE IDIOMA ---
        lang_actual = st.session_state.get("lang", "en")
        nuevo_lang = st.selectbox(
            "ðŸŒ Language / Idioma", 
            options=["en", "es"], 
            format_func=lambda x: "English" if x == "en" else "EspaÃ±ol",
            index=0 if lang_actual == "en" else 1
        )
        
        if nuevo_lang != lang_actual:
            st.session_state.lang = nuevo_lang
            st.rerun()
            
        st.divider()

        # --- INFORMACIÃ“N DEL USUARIO Y MENÃš ---
        if not st.session_state.get("is_read_only", True):
            st.success(f"ðŸ‘¤ {st.session_state.get('user_name', 'User')}")
            st.caption(f"ðŸ¢ {st.session_state.get('company_name', 'Global')} | ðŸ“ {st.session_state.get('site_name', 'All Sites')}")
            
            st.markdown(f"### ðŸ§­ {t('sidebar', 'menu')}")
            
            # Streamlit renderiza los enlaces de la carpeta /pages automÃ¡ticamente aquÃ­.
            # Por ahora, solo colocamos el botÃ³n de salida al fondo.
            
            st.write("") # Espaciador
            if st.button(f"ðŸšª {t('sidebar', 'logout')}", use_container_width=True):
                cerrar_sesion()

