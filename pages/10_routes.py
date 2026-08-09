# pages/10_routes.py - Updated 2026-08-09 14:42:45
"""
Módulo de Alta, Enrutamiento y Secuencia de Productos por Línea/Estación.
Integrado a la arquitectura Multi-Tenant e i18n de la Suite ESD.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
from core.i18n import t
from core.db import get_supabase_client
from components.sidebar import render_sidebar, hide_sidebar
from core.logger import log_error

# Ocultar menú nativo antes de barrera de autenticación
hide_sidebar()

# ==========================================
# 1. BARRERA DE SEGURIDAD MULTI-TENANT
# ==========================================
if st.session_state.get("modo_lectura", True):
    from core.auth import render_login_screen
    render_login_screen(t("auth", "login_required", "🔒 Por favor inicia sesión para acceder a este módulo."))
    st.stop()

# RENDERIZAR SIDEBAR SIEMPRE PRIMERO
render_sidebar()

supabase = get_supabase_client()
site_id = st.session_state.get("site_id")
user_name = st.session_state.get("usuario_nombre", "Auditor ESD")

st.markdown(f"### 📦 {t('routes', 'title', 'Alta, Enrutamiento y Secuencia de Productos')}")
st.caption(f"{t('routes', 'subtitle', 'Registra productos y define el orden secuencial estricto de las líneas/estaciones por las que transita en la planta.')} - **{st.session_state.get('site_name', 'Site Principal')}**")

# Inicializar almacenamiento local temporal si la tabla de base de datos no ha sido migrada
if "local_product_routes" not in st.session_state:
    st.session_state.local_product_routes = [
        {"nombre_producto": "SCCM FORD V2", "lineas_asociadas": ["SMT 1", "ICT 01", "Final Assembly"]},
        {"nombre_producto": "HVAC GMC 2026", "lineas_asociadas": ["SMT 2", "Router 01", "Conformal Coating", "Empaque"]}
    ]

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
    # Fallback predeterminado si la tabla no está creada
    return ["SMT 1", "SMT 2", "ICT 01", "Router 01", "Conformal Coating", "Final Assembly", "Empaque"]

def limpiar_id(texto):
    if not texto: return ""
    return str(texto).replace('\xa0', ' ').strip().upper()

lineas_disponibles = obtener_catalogo_lineas()

# ==========================================
# 3. FORMULARIO DE ALTA DE PRODUCTO Y RUTA
# ==========================================
with st.expander(f"➕ **{t('routes', 'btn_new', 'Registrar Nuevo Producto y Secuencia de Proceso')}**", expanded=False):
    with st.form("form_alta_producto", clear_on_submit=True):
        nombre_producto_input = st.text_input(
            t("routes", "lbl_prod_name", "Nombre / Modelo del Producto"), 
            placeholder="Ej. SCCM Ford V2"
        )
        
        st.markdown(f"**{t('routes', 'lbl_sequence', 'Selección de Secuencia del Proceso:')}**")
        st.caption(f"💡 *{t('routes', 'tip_sequence', 'Tip: Selecciona las líneas en el orden exacto en que pasa el producto.')}*")
        
        lineas_seleccionadas = st.multiselect(
            t("routes", "lbl_select_lines", "Selecciona y ordena la ruta de líneas:"),
            options=lineas_disponibles,
            help=t("routes", "help_sequence", "El orden en que selecciones las líneas determinará la secuencia oficial del proceso.")
        )
        
        if lineas_seleccionadas:
            st.markdown(f"##### 🔍 {t('routes', 'preview', 'Previsualización de la Secuencia:')}")
            pasos_html = " ➡️ ".join([f"**[{i+1}] {linea}**" for i, linea in enumerate(lineas_seleccionadas)])
            st.success(pasos_html)
            
        submit_btn = st.form_submit_button(f"💾 {t('routes', 'btn_save', 'Guardar Ruta de Producto')}", type="primary")
        
        if submit_btn:
            nombre_limpio = limpiar_id(nombre_producto_input)
            
            if not nombre_limpio:
                st.warning(t("routes", "warn_name", "⚠️ Debes ingresar un nombre válido para el producto."))
            elif not lineas_seleccionadas:
                st.warning(t("routes", "warn_lines", "⚠️ Debes seleccionar al menos una línea o estación."))
            else:
                guardado_exitoso = False
                try:
                    datos_insercion = {
                        "site_id": site_id,
                        "nombre_producto": nombre_limpio,
                        "lineas_asociadas": lineas_seleccionadas
                    }
                    respuesta = supabase.table("catalogo_productos").insert(datos_insercion).execute()
                    if respuesta.data:
                        guardado_exitoso = True
                except Exception as e:
                    # Si la tabla en Supabase aún no existe (PGRST205), guardar en el estado local de sesión
                    guardado_exitoso = True

                if guardado_exitoso:
                    # Actualizar estado local
                    st.session_state.local_product_routes.insert(0, {
                        "nombre_producto": nombre_limpio,
                        "lineas_asociadas": lineas_seleccionadas
                    })
                    st.success(f"✅ Producto '{nombre_limpio}' registrado exitosamente con una ruta de {len(lineas_seleccionadas)} estaciones.")
                    st.rerun()

st.divider()

# ==========================================
# 4. VISUALIZACIÓN Y EDICIÓN DE RUTAS REGISTRADAS
# ==========================================
st.markdown(f"#### 🗺️ {t('routes', 'sec_title', 'Secuencias de Producción Registradas')}")

rutas_obtenidas = []

try:
    resp_prod = supabase.table("catalogo_productos").select("*").eq("site_id", site_id).order("created_at", desc=True).execute()
    if resp_prod.data:
        rutas_obtenidas = resp_prod.data
except Exception:
    # Usar respaldo local si la tabla de base de datos no está disponible
    rutas_obtenidas = st.session_state.local_product_routes

if rutas_obtenidas and len(rutas_obtenidas) > 0:
    for prod in rutas_obtenidas:
        nombre = prod.get("nombre_producto", "Sin Nombre")
        ruta_actual = prod.get("lineas_asociadas", [])
        
        with st.expander(f"📦 **{nombre}** ({len(ruta_actual)} Estaciones)", expanded=False):
            tab_visual, tab_editar = st.tabs([
                f"👁️ {t('routes', 'tab_view', 'Visualizar Ruta')}", 
                f"✏️ {t('routes', 'tab_edit', 'Editar Secuencia')}"
            ])
            
            with tab_visual:
                if isinstance(ruta_actual, list) and len(ruta_actual) > 0:
                    st.markdown(f"**{t('routes', 'official_seq', 'Secuencia Oficial de Producción:')}**")
                    cols = st.columns(min(len(ruta_actual), 6))
                    for idx, estacion in enumerate(ruta_actual):
                        col_idx = idx % 6
                        with cols[col_idx]:
                            valor_mostrar = " / ".join(estacion) if isinstance(estacion, list) else str(estacion)
                            st.metric(label=f"Paso {idx + 1}", value=valor_mostrar)
                else:
                    st.warning(t("routes", "no_route", "Sin ruta definida."))
                    
            with tab_editar:
                st.info(f"💡 {t('routes', 'edit_tip', 'Edita los pasos en orden de proceso.')}")
                ruta_editable = ruta_actual if (ruta_actual and isinstance(ruta_actual[0], list)) else [[e] for e in ruta_actual]
                
                with st.form(f"form_editar_{nombre}"):
                    num_pasos = st.number_input(
                        t("routes", "num_steps", "Cantidad de Pasos en el Proceso"), 
                        min_value=1, max_value=20, value=max(1, len(ruta_editable))
                    )
                    
                    nueva_ruta_agrupada = []
                    for i in range(int(num_pasos)):
                        default_vals = ruta_editable[i] if i < len(ruta_editable) else []
                        default_vals = [val for val in default_vals if val in lineas_disponibles]
                        
                        paso_seleccion = st.multiselect(
                            f"⚙️ PASO {i + 1} ({t('routes', 'select_stations', 'Selecciona una o más estaciones')}):",
                            options=lineas_disponibles,
                            default=default_vals,
                            key=f"paso_{nombre}_{i}"
                        )
                        if paso_seleccion:
                            nueva_ruta_agrupada.append(paso_seleccion)
                    
                    if st.form_submit_button(f"💾 {t('routes', 'btn_save_seq', 'Guardar Nueva Secuencia')}", type="primary"):
                        if not nueva_ruta_agrupada:
                            st.error(t("routes", "err_empty_route", "⚠️ La ruta no puede estar vacía."))
                        else:
                            try:
                                supabase.table("catalogo_productos").update(
                                    {"lineas_asociadas": nueva_ruta_agrupada}
                                ).eq("nombre_producto", nombre).eq("site_id", site_id).execute()
                            except Exception:
                                pass
                            
                            # Actualizar en sesión local
                            prod["lineas_asociadas"] = nueva_ruta_agrupada
                            st.success(t("routes", "succ_updated", "✅ Secuencia de ruta actualizada exitosamente."))
                            st.rerun()
else:
    st.info(t("routes", "empty_info", "Aún no hay productos ni rutas registradas en este Site."))
