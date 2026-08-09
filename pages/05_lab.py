# pages/05_lab.py
"""
Módulo de Laboratorio ESD: Gestión de Sensibilidad por Producto/Componente (HBM / CDM)
Mapeado a catalogo_sensibilidad y componentes_sensibilidad.
"""
import streamlit as st

# FORZAR 100% ANCHO COMPLETO EN STREAMLIT
st.markdown('''
    <style>
    .stAppViewContainer .main .block-container,
    div[data-testid="stMainBlockContainer"],
    .stMainBlockContainer,
    .block-container,
    div[data-testid="stAppViewBlockContainer"] {
        max-width: 100% !important;
        width: 100% !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        padding-top: 1.5rem !important;
    }
    [data-testid="stVerticalBlock"] {
        width: 100% !important;
    }
    </style>
''', unsafe_allow_html=True)

try:
    st.set_page_config(page_title="ESD Management Suite", page_icon="⚡", layout="wide")
except Exception:
    pass
import pandas as pd
from core.i18n import t
from core.db import get_supabase_client

# Barrera de seguridad
if st.session_state.get("modo_lectura", True):
    st.warning(t("auth", "login_required", default="Debes iniciar sesión para acceder a este módulo."))
    st.stop()

supabase = get_supabase_client()
site_id = st.session_state.site_id

st.markdown("### 🔬 Módulo de Laboratorio: Sensibilidad ESD por Componente (HBM / CDM)")
st.caption("Clasificación de nivel de sensibilidad de productos y análisis de susceptibilidad a descargas electrostáticas.")

tab1, tab2 = st.tabs(["📦 Catálogo de Productos y Sensibilidad", "🧩 Componentes Sensibles (BOM/ESD)"])

with tab1:
    st.markdown("#### Catálogo General de Productos y Nivel de Sensibilidad")
    
    with st.form("form_alta_sensibilidad", clear_on_submit=True):
        st.markdown("**Registrar Producto para Análisis de Sensibilidad**")
        col1, col2 = st.columns(2)
        with col1:
            num_parte = st.text_input("Número de Parte", placeholder="Ej. PN-998877")
            nombre_prod = st.text_input("Nombre del Producto", placeholder="Ej. Módulo Control Motor")
        with col2:
            cliente = st.text_input("Cliente / OEM", placeholder="Ej. Ford / BMW")
            nivel_sens = st.selectbox("Nivel de Sensibilidad ESD", ["Class 0 (<100V)", "Class 1A (100V-500V)", "Class 1B (500V-1000V)", "Class 1C (1000V-2000V)", "Class 2 (2000V-4000V)", "No Sensible"])
            
        if st.form_submit_button("💾 Registrar Producto"):
            if num_parte and nombre_prod:
                try:
                    supabase.table("catalogo_sensibilidad").insert({
                        "numero_parte": num_parte.strip().upper(),
                        "nombre_producto": nombre_prod.strip(),
                        "cliente": cliente.strip(),
                        "nivel_sensibilidad": nivel_sens
                    }).execute()
                    st.success("✅ Producto registrado correctamente en el catálogo de sensibilidad.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar: {e}")
            else:
                st.warning("⚠️ Completa los campos obligatorios.")

    st.divider()
    
    try:
        resp = supabase.table("catalogo_sensibilidad").select("*").order("created_at", desc=True).execute()
        if resp.data:
            df = pd.DataFrame(resp.data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Sin registros en el catálogo de sensibilidad.")
    except Exception as e:
        st.error(f"Error al cargar catálogo de sensibilidad: {e}")

with tab2:
    st.markdown("#### Detalle de Componentes Sensibles por Producto")
    try:
        resp_prods = supabase.table("catalogo_sensibilidad").select("id, numero_parte, nombre_producto").execute()
        if resp_prods.data:
            dict_prods = {f"{p['numero_parte']} - {p['nombre_producto']}": p['id'] for p in resp_prods.data}
            sel_prod_name = st.selectbox("Selecciona Producto para Ver/Agregar Componentes:", list(dict_prods.keys()))
            sel_prod_id = dict_prods[sel_prod_name]
            
            with st.form("form_alta_componente", clear_on_submit=True):
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    part_num = st.text_input("Part Number Componente", placeholder="Ej. IC-RES-100")
                    desc = st.text_input("Descripción", placeholder="Ej. Microcontrolador 32bit")
                with col_b:
                    ref_desig = st.text_input("Ref Designator", placeholder="Ej. U101 / C24")
                    qty = st.number_input("Cantidad", min_value=1, value=1)
                with col_c:
                    hbm = st.text_input("ESD HBM (Human Body Model)", placeholder="Ej. <250V")
                    cdm = st.text_input("ESD CDM (Charged Device Model)", placeholder="Ej. <500V")
                    
                comentarios = st.text_area("Comentarios / Precauciones Especiales")
                
                if st.form_submit_button("➕ Agregar Componente"):
                    if part_num:
                        try:
                            supabase.table("componentes_sensibilidad").insert({
                                "id_producto": sel_prod_id,
                                "part_number": part_num.strip(),
                                "descripcion": desc,
                                "ref_designator": ref_desig,
                                "qty": qty,
                                "esd_hbm": hbm,
                                "esd_cdm": cdm,
                                "comentarios": comentarios
                            }).execute()
                            st.success("✅ Componente guardado exitosamente.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al registrar componente: {e}")

            st.divider()
            resp_comps = supabase.table("componentes_sensibilidad").select("*").eq("id_producto", sel_prod_id).execute()
            if resp_comps.data:
                st.dataframe(pd.DataFrame(resp_comps.data), use_container_width=True)
            else:
                st.info("No hay componentes registrados para este producto.")
        else:
            st.info("Primero debes dar de alta productos en la pestaña anterior.")
    except Exception as e:
        st.error(f"Error al cargar componentes: {e}")
