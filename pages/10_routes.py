# pages/10_routes.py
"""
Módulo de Alta, Enrutamiento y Secuencia de Productos por Línea/Estación.
Integrado desde oldcode.py y adaptado a la arquitectura Multi-Tenant de la Suite.
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
site_id = st.session_state.get("site_id")
user_name = st.session_state.get("user_name", "Auditor ESD")

st.markdown(f"### 📦 {t('routes', 'title', default='Alta, Enrutamiento y Secuencia de Productos')}")
st.caption("Registra productos y define el orden secuencial estricto de las líneas/estaciones por las que transita en la planta.")

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
    # Fallback si no hay catálogo registrado
    return ["SMT 1", "SMT 2", "ICT 01", "Router 01", "Conformal Coating", "Final Assembly", "Empaque"]

def limpiar_id(texto):
    if not texto: return ""
    return str(texto).replace('\xa0', ' ').strip().upper()

lineas_disponibles = obtener_catalogo_lineas()

# ==========================================
# 3. FORMULARIO DE ALTA DE PRODUCTO Y RUTA
# ==========================================
with st.expander("➕ **Registrar Nuevo Producto y Secuencia de Proceso**", expanded=False):
    with st.form("form_alta_producto", clear_on_submit=True):
        nombre_producto_input = st.text_input("Nombre / Modelo del Producto", placeholder="Ej. SCCM Ford V2")
        
        st.markdown("**Selección de Secuencia del Proceso:**")
        st.caption("💡 *Tip: Selecciona las líneas en el orden exacto en que pasa el producto (de la primera operación a la última).*")
        
        lineas_seleccionadas = st.multiselect(
            "Selecciona y ordena la ruta de líneas:",
            options=lineas_disponibles,
            help="El orden en que selecciones las líneas determinará la secuencia oficial del proceso."
        )
        
        if lineas_seleccionadas:
            st.markdown("##### 🔍 Previsualización de la Secuencia:")
            pasos_html = " ➡️ ".join([f"**[{i+1}] {linea}**" for i, linea in enumerate(lineas_seleccionadas)])
            st.success(pasos_html)
            
        submit_btn = st.form_submit_button("💾 Guardar Ruta de Producto", type="primary")
        
        if submit_btn:
            nombre_limpio = limpiar_id(nombre_producto_input)
            
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
                        st.success(f"✅ Producto '{nombre_limpio}' registrado exitosamente con una ruta de {len(lineas_seleccionadas)} estaciones.")
                        st.rerun()
                except Exception as e:
                    if "duplicate key value" in str(e) or "23505" in str(e):
                        st.error(f"❌ El producto '{nombre_limpio}' ya está registrado.")
                    else:
                        st.error(f"❌ Error al guardar en la base de datos: {e}")

st.divider()

# ==========================================
# 4. VISUALIZACIÓN Y EDICIÓN DE RUTAS REGISTRADAS
# ==========================================
st.markdown("#### 🗺️ Secuencias de Producción Registradas")

try:
    resp_prod = supabase.table("catalogo_productos").select("*").eq("site_id", site_id).order("created_at", desc=True).execute()
    
    if resp_prod.data and len(resp_prod.data) > 0:
        for prod in resp_prod.data:
            nombre = prod.get("nombre_producto", "Sin Nombre")
            ruta_actual = prod.get("lineas_asociadas", [])
            
            with st.expander(f"📦 **{nombre}** ({len(ruta_actual)} Estaciones)", expanded=False):
                tab_visual, tab_editar = st.tabs(["👁️ Visualizar Ruta", "✏️ Editar Secuencia"])
                
                with tab_visual:
                    if isinstance(ruta_actual, list) and len(ruta_actual) > 0:
                        st.markdown("**Secuencia Oficial de Producción:**")
                        cols = st.columns(min(len(ruta_actual), 6))
                        for idx, estacion in enumerate(ruta_actual):
                            col_idx = idx % 6
                            with cols[col_idx]:
                                valor_mostrar = " / ".join(estacion) if isinstance(estacion, list) else str(estacion)
                                st.metric(label=f"Paso {idx + 1}", value=valor_mostrar)
                    else:
                        st.warning("Sin ruta definida.")
                        
                with tab_editar:
                    st.info("💡 Edita los pasos en orden de proceso.")
                    ruta_editable = ruta_actual if (ruta_actual and isinstance(ruta_actual[0], list)) else [[e] for e in ruta_actual]
                    
                    with st.form(f"form_editar_{nombre}"):
                        num_pasos = st.number_input("Cantidad de Pasos en el Proceso", min_value=1, max_value=20, value=max(1, len(ruta_editable)))
                        
                        nueva_ruta_agrupada = []
                        for i in range(int(num_pasos)):
                            default_vals = ruta_editable[i] if i < len(ruta_editable) else []
                            default_vals = [val for val in default_vals if val in lineas_disponibles]
                            
                            paso_seleccion = st.multiselect(
                                f"⚙️ PASO {i + 1} (Selecciona una o más estaciones):",
                                options=lineas_disponibles,
                                default=default_vals,
                                key=f"paso_{nombre}_{i}"
                            )
                            if paso_seleccion:
                                nueva_ruta_agrupada.append(paso_seleccion)
                        
                        if st.form_submit_button("💾 Guardar Nueva Secuencia", type="primary"):
                            if not nueva_ruta_agrupada:
                                st.error("⚠️ La ruta no puede estar vacía.")
                            else:
                                try:
                                    supabase.table("catalogo_productos").update(
                                        {"lineas_asociadas": nueva_ruta_agrupada}
                                    ).eq("nombre_producto", nombre).eq("site_id", site_id).execute()
                                    st.success("✅ Secuencia de ruta actualizada exitosamente.")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error al actualizar: {e}")
    else:
        st.info("Aún no hay productos ni rutas registradas en este Site.")

except Exception as e:
    st.error(f"Error al cargar las rutas de productos: {e}")
