# pages/07_product_routes.py
"""
Vista de Alta, Enrutamiento y Secuencia de Productos por Línea/Estación.
Integrado y modernizado desde oldcode.py al esquema modular Multi-Tenant.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from core.i18n import t
from core.db import get_supabase_client

# ==========================================
# 1. BARRERA DE SEGURIDAD MULTI-TENANT
# ==========================================
if st.session_state.get("modo_lectura", True):
    st.warning(t("auth", "login_required", default="Debes iniciar sesión para acceder a esta página."))
    st.stop()

supabase = get_supabase_client()
site_id = st.session_state.site_id

st.markdown(f"### 📦 {t('routes', 'title', default='Alta, Enrutamiento y Secuencia de Productos')}")
st.caption("Registra productos y define la secuencia estricta de las líneas y estaciones por las que transita el proceso.")

# ==========================================
# 2. OBTENER CATÁLOGO DE LÍNEAS DE LA PLANTA
# ==========================================
def obtener_catalogo_lineas():
    try:
        resp = supabase.table("catalogo_lineas").select("nombre_linea").eq("site_id", site_id).order("nombre_linea").execute()
        if resp.data:
            return [x['nombre_linea'] for x in resp.data]
    except Exception:
        pass
    return ["SMT 1", "SMT 2", "ICT 01", "Router 01", "Conformal Coating", "Final Assembly", "Empaque"]

lineas_disponibles = obtener_catalogo_lineas()

# ==========================================
# 3. FORMULARIO DE REGISTRO DE PRODUCTO Y RUTA
# ==========================================
with st.expander("➕ **Registrar Nuevo Producto y Secuencia**", expanded=False):
    with st.form("form_alta_producto", clear_on_submit=True):
        nombre_producto_input = st.text_input("Nombre / Modelo del Producto", placeholder="Ej. SCCM Ford V2")
        
        st.markdown("**Selección de Secuencia del Proceso:**")
        st.caption("💡 *Tip: Selecciona las líneas en el orden exacto de flujo del producto.*")
        
        lineas_seleccionadas = st.multiselect(
            "Selecciona y ordena la ruta de líneas:",
            options=lineas_disponibles,
            help="El orden en que selecciones las líneas determinará la secuencia oficial del proceso."
        )
        
        if lineas_seleccionadas:
            st.markdown("##### 🔍 Previsualización de la Secuencia:")
            pasos_txt = " ➡️ ".join([f"**[{i+1}] {linea}**" for i, linea in enumerate(lineas_seleccionadas)])
            st.success(pasos_txt)
            
        submit_btn = st.form_submit_button("💾 Guardar Ruta de Producto")
        
        if submit_btn:
            nombre_limpio = nombre_producto_input.strip().upper()
            if not nombre_limpio:
                st.warning("⚠️ Debes ingresar un nombre válido para el producto.")
            elif not lineas_seleccionadas:
                st.warning("⚠️ Debes seleccionar al menos una línea o estación.")
            else:
                try:
                    datos_insercion = {
                        "site_id": site_id,
                        "nombre_producto": nombre_limpio,
                        "lineas_asociadas": lineas_seleccionadas
                    }
                    respuesta = supabase.table("catalogo_productos").insert(datos_insercion).execute()
                    if respuesta.data:
                        st.success(f"✅ Producto '{nombre_limpio}' registrado exitosamente con {len(lineas_seleccionadas)} estaciones.")
                        st.rerun()
                except Exception as e:
                    if "duplicate key value" in str(e) or "23505" in str(e):
                        st.error(f"❌ El producto '{nombre_limpio}' ya está registrado.")
                    else:
                        st.error(f"❌ Error al guardar en Supabase: {e}")

st.divider()

# ==========================================
# 4. LISTADO Y DIAGRAMA DE RUTAS REGISTRADAS
# ==========================================
st.markdown("#### 🗺️ Productos y Secuencias Registradas")

try:
    resp_prod = supabase.table("catalogo_productos").select("*").eq("site_id", site_id).order("created_at", desc=True).execute()
    
    if resp_prod.data and len(resp_prod.data) > 0:
        for prod in resp_prod.data:
            nombre = prod.get("nombre_producto", "Sin Nombre")
            ruta_actual = prod.get("lineas_asociadas", [])
            
            with st.expander(f"📦 **{nombre}** ({len(ruta_actual)} Estaciones)", expanded=False):
                if isinstance(ruta_actual, list) and len(ruta_actual) > 0:
                    st.markdown("**Secuencia de Producción:**")
                    cols = st.columns(min(len(ruta_actual), 6))
                    for idx, estacion in enumerate(ruta_actual):
                        col_idx = idx % 6
                        with cols[col_idx]:
                            valor_mostrar = " / ".join(estacion) if isinstance(estacion, list) else str(estacion)
                            st.metric(label=f"Paso {idx + 1}", value=valor_mostrar)
                else:
                    st.warning("Sin ruta definida.")
    else:
        st.info("Aún no hay productos registrados en este Site.")

except Exception as e:
    st.error(f"Error al cargar productos: {e}")
