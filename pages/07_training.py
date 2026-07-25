# pages/07_training.py
"""
Módulo de Capacitación, Exámenes y Entrenamientos ESD.
Conectado a la tabla entrenamientos_esd y empleados_batas.
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime
from core.i18n import t
from core.db import get_supabase_client

# Barrera de Seguridad
if st.session_state.get("modo_lectura", True):
    st.warning(t("auth", "login_required", default="Debes iniciar sesión para acceder."))
    st.stop()

supabase = get_supabase_client()
site_id = st.session_state.site_id

st.markdown("### 🎓 Módulo de Capacitación y Evaluación ESD")
st.caption("Evaluación de conocimientos sobre normatividad ANSI/ESD S20.20 y certificación de personal.")

tab1, tab2 = st.tabs(["📝 Aplicar Evaluación ESD", "📊 Historial de Certificaciones"])

with tab1:
    st.markdown("#### Formulario de Examen / Evaluación ESD")
    
    with st.form("form_evaluacion_esd", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            num_emp = st.text_input("Número de Empleado", placeholder="Ej. EMP-1002")
        with col2:
            nombre_emp = st.text_input("Nombre Completo del Empleado", placeholder="Ej. Ana Martínez")
            
        st.divider()
        st.markdown("**Preguntas de Evaluación:**")
        
        q1 = st.radio("1. ¿Cuál es el límite máximo permitido de resistencia para una pulsera antiestática (ANSI/ESD TR53)?", 
                      ["< 3.5 x 10^7 ohms", "< 1.0 x 10^9 ohms", "< 10 ohms"], index=0)
        
        q2 = st.radio("2. ¿A qué distancia mínima deben mantenerse los materiales aislantes de componentes sensibles (ESDS)?", 
                      ["> 30 cm (12 pulgadas)", "> 5 cm", "No importa la distancia"], index=0)
                      
        q3 = st.radio("3. ¿Cuál es la función principal de los ionizadores en un área protegida (EPA)?", 
                      ["Neutralizar cargas en materiales aislantes no conductores", "Enfriar la tarjeta electrónica", "Limpiar el polvo de la mesa"], index=0)
                      
        submit_exam = st.form_submit_button("📤 Enviar Examen y Calificar", type="primary")
        
        if submit_exam:
            if not num_emp or not nombre_emp:
                st.warning("⚠️ Debes ingresar el número y nombre del empleado.")
            else:
                try:
                    # Calificación
                    aciertos = 0
                    if q1 == "< 3.5 x 10^7 ohms": aciertos += 1
                    if q2 == "> 30 cm (12 pulgadas)": aciertos += 1
                    if q3 == "Neutralizar cargas en materiales aislantes no conductores": aciertos += 1
                    
                    nota_intento = round((aciertos / 3.0) * 100.0, 1)
                except Exception as e:
                    nota_intento = 0.0

                try:
                    resp_json = {
                        "q1": q1,
                        "q2": q2,
                        "q3": q3,
                        "score": nota_intento
                    }
                    
                    supabase.table("entrenamientos_esd").insert({
                        "num_empleado": num_emp.strip().upper(),
                        "nombre_empleado": nombre_emp.strip(),
                        "fecha_entrenamiento": str(datetime.now()),
                        "calificacion_total": nota_intento,
                        "detalle_respuestas": resp_json
                    }).execute()
                    
                    if nota_intento >= 80.0:
                        st.balloons()
                        st.success(f"🎉 ¡Aprobado! Calificación obtenida: **{nota_intento}%**")
                    else:
                        st.error(f"❌ No Aprobado. Calificación obtenida: **{nota_intento}%** (Mínimo requerido: 80%)")
                except Exception as ex:
                    st.error(f"Error al registrar la evaluación: {ex}")

with tab2:
    st.markdown("#### Historial Registrado de Exámenes")
    try:
        resp = supabase.table("entrenamientos_esd").select("*").order("created_at", desc=True).execute()
        if resp.data:
            st.dataframe(pd.DataFrame(resp.data), use_container_width=True)
        else:
            st.info("Sin evaluaciones registradas.")
    except Exception as e:
        st.error(f"Error al consultar historial: {e}")
