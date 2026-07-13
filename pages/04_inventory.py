# pages/03_ðŸ“¦_Inventory.py

import streamlit as st
import pandas as pd
from core.i18n import t
from core.db import get_supabase_client

# ==========================================
# 1. BARRERA DE SEGURIDAD
# ==========================================
from core.auth import requires_auth

@requires_auth
def __ensure_auth():
    pass

__ensure_auth()

# Inicializamos cliente y extraemos credenciales del usuario actual
supabase = get_supabase_client()
site_id = st.session_state.site_id

st.markdown(f"### {t('inventory', 'title')}")
st.info(f"ðŸ“ Mostrando datos exclusivos de la planta: **{st.session_state.site_name}**")

# ==========================================
# 2. ESTRUCTURA DE PESTAÃ‘AS
# ==========================================
tab_dir, tab_add, tab_retire = st.tabs([
    t("inventory", "tab_dir"), 
    t("inventory", "tab_add"), 
    t("inventory", "tab_retire")
])

# --- PESTAÃ‘A A: DIRECTORIO DE ACTIVOS ---
with tab_dir:
    st.markdown(f"#### {t('inventory', 'tab_dir')}")
    
    with st.spinner("Cargando base de datos..."):
        try:
            # ðŸ›¡ï¸ CONSULTA MULTI-TENANT: Siempre filtramos por site_id
            resp_assets = supabase.table("assets").select("*").eq("site_id", site_id).order("custom_id").execute()
            df_assets = pd.DataFrame(resp_assets.data)
            
            if not df_assets.empty:
                # Ocultamos metadatos del sistema (UUIDs internos) para la vista del usuario
                columnas_mostrar = ['custom_id', 'category', 'classification', 'location', 'status']
                df_mostrar = df_assets[columnas_mostrar].copy()
                
                # Formato visual
                df_mostrar.columns = ["ID Activo", "CategorÃ­a", "ClasificaciÃ³n", "UbicaciÃ³n", "Estatus Operativo"]
                df_mostrar["Estatus Operativo"] = df_mostrar["Estatus Operativo"].apply(
                    lambda x: f"ðŸŸ¢ {x}" if x == 'ACTIVE' else f"ðŸ”´ {x}"
                )
                
                st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
            else:
                st.info("No hay activos registrados en esta planta.")
                
        except Exception as e:
            st.error(f"Error de conexiÃ³n: {e}")

# --- PESTAÃ‘A B: REGISTRAR NUEVO ACTIVO ---
with tab_add:
    st.markdown(f"#### {t('inventory', 'tab_add')}")
    
    with st.form("form_add_asset", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        nuevo_id = col1.text_input(t("inventory", "lbl_id"))
        categoria = col2.selectbox(t("inventory", "lbl_category"), ["Mobiliario", "Maquinaria", "Ionizador", "Checador"])
        
        col3, col4 = st.columns(2)
        clasificacion = col3.text_input(t("inventory", "lbl_class"))
        ubicacion = col4.text_input(t("inventory", "lbl_location"))
        
        if st.form_submit_button(t("inventory", "btn_save"), type="primary", use_container_width=True):
            if not nuevo_id.strip():
                st.error("El ID del activo no puede estar vacÃ­o.")
            else:
                with st.spinner("Registrando..."):
                    try:
                        # ðŸ›¡ï¸ INSERCIÃ“N MULTI-TENANT: Forzamos la inyecciÃ³n del site_id del usuario
                        payload = {
                            "site_id": site_id,
                            "custom_id": nuevo_id.strip().upper(),
                            "category": categoria,
                            "classification": clasificacion.strip().title(),
                            "location": ubicacion.strip().upper(),
                            "status": "ACTIVE"
                        }
                        
                        supabase.table("assets").insert(payload).execute()
                        st.success(t("inventory", "msg_success"))
                        st.rerun() # Refresca la vista para mostrar el nuevo activo en la tabla
                        
                    except Exception as e:
                        # Si hay un error de unicidad por el UNIQUE(site_id, custom_id) de SQL
                        if "duplicate key value" in str(e).lower() or "23505" in str(e):
                            st.error(t("inventory", "msg_duplicate"))
                        else:
                            st.error(f"Error en base de datos: {e}")

# --- PESTAÃ‘A C: DAR DE BAJA ---
with tab_retire:
    st.markdown(f"#### {t('inventory', 'tab_retire')}")
    st.caption("Cambia el estatus de un activo a inactivo sin eliminar su historial de auditorÃ­as.")
    
    if 'df_assets' in locals() and not df_assets.empty:
        # Solo mostrar equipos que estÃ¡n activos actualmente
        activos_disponibles = df_assets[df_assets['status'] == 'ACTIVE']['custom_id'].tolist()
        
        if activos_disponibles:
            with st.form("form_retire_asset"):
                activo_baja = st.selectbox("Selecciona el Activo a dar de baja:", activos_disponibles)
                
                if st.form_submit_button("ðŸ—‘ï¸ Desactivar Activo", type="secondary"):
                    with st.spinner("Actualizando estatus..."):
                        try:
                            # ðŸ›¡ï¸ UPDATE SEGURO: Doble candado con site_id y custom_id
                            supabase.table("assets").update({"status": "INACTIVE"}).match({
                                "site_id": site_id, 
                                "custom_id": activo_baja
                            }).execute()
                            
                            st.success(f"Activo {activo_baja} dado de baja exitosamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al desactivar: {e}")
        else:
            st.success("No hay equipos activos disponibles para dar de baja.")

