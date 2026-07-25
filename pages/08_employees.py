# pages/08_employees.py
"""
Módulo de Gestión de Empleados, Batas, Calzado y Entrenamientos ESD.
Mapeado a las tablas empleados_batas y entrenamientos_esd.
"""
import streamlit as st
import pandas as pd
from core.i18n import t
from core.db import get_supabase_client

if st.session_state.get("modo_lectura", True):
    st.warning(t("auth", "login_required", default="Debes iniciar sesión para acceder a este módulo."))
    st.stop()

supabase = get_supabase_client()
site_id = st.session_state.site_id

st.markdown("### 👥 Control de Personal, Batas y Entrenamientos ESD")
st.caption("Seguimiento de vigencia de capacitaciones ESD y asignación de equipo personal ESD.")

tab1, tab2 = st.tabs(["👔 Padrón de Empleados y Equipo", "📜 Historial de Capacitaciones ESD"])

with tab1:
    st.markdown("#### Registro y Control de Batas / Calzado")
    with st.form("form_empleado", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            num_emp = st.text_input("Número de Empleado", placeholder="Ej. EMP-1049")
            nombre_emp = st.text_input("Nombre Completo", placeholder="Ej. Juan Pérez")
        with col2:
            depto = st.text_input("Departamento / Área", placeholder="Ej. SMT Línea 2")
            estatus = st.selectbox("Estatus del Empleado", ["ACTIVO", "INACTIVO", "PERMISO"])
        with col3:
            f_ultimo = st.date_input("Fecha Último Entrenamiento")
            f_proximo = st.date_input("Fecha Próximo Entrenamiento")
            
        if st.form_submit_button("💾 Guardar Empleado"):
            if num_emp and nombre_emp:
                try:
                    supabase.table("empleados_batas").upsert({
                        "num_empleado": num_emp.strip().upper(),
                        "nombre": nombre_emp.strip(),
                        "departamento": depto,
                        "estatus_empleado": estatus,
                        "fecha_ultimo_entrenamiento": str(f_ultimo),
                        "fecha_proximo_entrenamiento": str(f_proximo),
                        "site_id": site_id
                    }, on_conflict="num_empleado").execute()
                    st.success("✅ Registro de empleado actualizado correctamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al guardar empleado: {e}")

    st.divider()
    try:
        resp = supabase.table("empleados_batas").select("*").eq("site_id", site_id).execute()
        if resp.data:
            st.dataframe(pd.DataFrame(resp.data), use_container_width=True)
        else:
            st.info("No hay empleados registrados para este Site.")
    except Exception as e:
        st.error(f"Error al consultar empleados: {e}")

with tab2:
    st.markdown("#### Historial de Entrenamientos y Calificaciones")
    try:
        resp_entrenamientos = supabase.table("entrenamientos_esd").select("*").order("created_at", desc=True).execute()
        if resp_entrenamientos.data:
            st.dataframe(pd.DataFrame(resp_entrenamientos.data), use_container_width=True)
        else:
            st.info("Sin registros de entrenamiento.")
    except Exception as e:
        st.error(f"Error al cargar entrenamientos: {e}")
