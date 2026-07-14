# components/sidebar.py
import streamlit as st
from core.i18n import t
from core.auth import cerrar_sesion

def render_sidebar():
    with st.sidebar:
        # Logotipo Genérico (Puede ser dinámico por empresa en el futuro)
        st.image("https://raw.githubusercontent.com/aldoaoa/Visualizador-BCS-IDS/refs/heads/main/Logo_BCS_transparent%20(1).png", use_container_width=True)
        st.divider()

        # --- SELECTOR DE IDIOMA ---
        lang_actual = st.session_state.get("lang", "en")
        nuevo_lang = st.selectbox(
            "🌐 Language / Idioma", 
            options=["en", "es"], 
            format_func=lambda x: "English" if x == "en" else "Español",
            index=0 if lang_actual == "en" else 1
        )
        
        if nuevo_lang != lang_actual:
            st.session_state.lang = nuevo_lang
            st.rerun()
            
        st.divider()

        # --- INFORMACIÓN DEL USUARIO Y MENÚ ---
        if not st.session_state.get("modo_lectura", True):
            st.success(f"👤 {st.session_state.get('usuario_nombre', 'User')}")
            
            # --- SELECTOR DE PLANTA (PARA ADMINS) ---
            available_sites = st.session_state.get("available_sites", [])
            if available_sites:
                site_names = [s["name"] for s in available_sites]
                current_site_id = st.session_state.get("site_id")
                
                idx = 0
                for i, s in enumerate(available_sites):
                    if s["id"] == current_site_id:
                        idx = i
                        break
                
                selected_site_name = st.selectbox(
                    "🏭 Active Site / Planta",
                    options=site_names,
                    index=idx
                )
                
                selected_site = available_sites[site_names.index(selected_site_name)]
                if selected_site["id"] != current_site_id:
                    st.session_state.site_id = selected_site["id"]
                    st.session_state.site_name = selected_site["name"]
                    st.rerun()
            else:
                st.caption(f"🏢 {st.session_state.get('company_name', 'Global')} | 📍 {st.session_state.get('site_name', 'All Sites')}")
            
            st.markdown(f"### 🧭 {t('sidebar', 'menu')}")
            
            # Streamlit renderiza los enlaces de la carpeta /pages automáticamente aquí.
            # Por ahora, solo colocamos el botón de salida al fondo.
            
            st.write("") # Espaciador
            if st.button(f"🚪 {t('sidebar', 'logout')}", use_container_width=True):
                cerrar_sesion()
