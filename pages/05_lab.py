# pages/05_lab.py

import streamlit as st
import pandas as pd
import re
import io
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from core.i18n import t
from core.db import get_supabase_client
from components.sidebar import render_sidebar

# ==========================================
# 1. BARRERA DE SEGURIDAD MULTI-TENANT
# ==========================================
if st.session_state.get("modo_lectura", True):
    st.warning(t("auth", "login_required"))
    st.stop()

render_sidebar()

supabase = get_supabase_client()
site_id = st.session_state.site_id
user_id = st.session_state.user_id

st.markdown(f"### {t('lab', 'title')}")
st.caption(f"{t('lab', 'subtitle')} - **{st.session_state.site_name}**")

tab_event, tab_walking = st.tabs([t('lab', 'tab_event'), t('lab', 'tab_walking')])

# ==========================================
# 2. EVENT METER (ESTUDIO DE DESCARGAS)
# ==========================================
with tab_event:
    st.markdown("#### Registro de Event Meter (PCBA)")
    st.info("Mide descargas electrostáticas y transitorios durante la operación normal de la maquinaria.")
    
    with st.form("form_event_meter", clear_on_submit=True):
        c1, c2 = st.columns(2)
        
        # En una versión completa, aquí traeríamos las "Locations" de Supabase
        linea = c1.text_input(t("lab", "em_location"))
        operacion = c2.text_input(t("lab", "em_operation"))
        
        c3, c4, c5 = st.columns([2, 1, 1])
        contacto = c3.selectbox(t("lab", "em_contact"), ["Maquinaria", "EOLT", "AOI", "Herramienta Manual", "Humano", "Otro"])
        temp = c4.number_input("Temp (°C)", value=23.5)
        hum = c5.number_input("Humedad (%)", value=45)
        
        c6, c7 = st.columns(2)
        eventos = c6.number_input(t("lab", "em_events"), min_value=0, step=1)
        voltaje = c7.number_input(t("lab", "em_voltage"), min_value=0.0, step=0.1)
        
        if st.form_submit_button(t("lab", "em_save"), type="primary", use_container_width=True):
            if not linea or not operacion:
                st.error("Línea y Operación son obligatorios.")
            else:
                with st.spinner("Guardando..."):
                    # Límite normativo típico para Event Meter
                    status = "PASS" if voltaje <= 100.0 else "FAIL"
                    
                    try:
                        supabase.table("event_meter_logs").insert({
                            "site_id": site_id,
                            "location": linea.strip().upper(),
                            "operation_id": operacion.strip().upper(),
                            "contact_type": contacto,
                            "events_count": int(eventos),
                            "max_voltage": float(voltaje),
                            "temperature": float(temp),
                            "humidity": int(hum),
                            "status_result": status,
                            "auditor_id": user_id
                        }).execute()
                        st.success(f"¡Registro guardado! Estatus: {status}")
                    except Exception as e:
                        st.error(f"Error SQL: {e}")

# ==========================================
# 3. WALKING TEST (EXTRACCIÓN OCR DE PDF)
# ==========================================
with tab_walking:
    st.markdown("#### Análisis OCR de Walking Test")
    archivo_pdf = st.file_uploader(t("lab", "wt_upload"), type=["pdf"])
    
    if archivo_pdf:
        with st.expander(f"📄 Documento: {archivo_pdf.name}", expanded=True):
            try:
                # 1. Extracción de imagen del PDF
                doc = fitz.open(stream=archivo_pdf.read(), filetype="pdf")
                pagina = doc[0]
                imagenes_pdf = pagina.get_images(full=True)
                
                if imagenes_pdf:
                    xref = imagenes_pdf[0][0]
                    base_image = doc.extract_image(xref)
                    imagen_grafica = Image.open(io.BytesIO(base_image["image"]))
                    
                    # 2. Análisis OCR
                    with st.spinner(t("lab", "wt_extracting")):
                        texto_ocr = pytesseract.image_to_string(imagen_grafica)
                    
                    # 3. Expresiones Regulares (Lógica de tu código original)
                    hum_match = re.search(r"(\d{1,3}(?:\.\d+)?)\s*%?\s*RH", texto_ocr, re.IGNORECASE)
                    humedad = float(hum_match.group(1)) if hum_match else 45.0
                    
                    temp_match = re.search(r"(\d{1,3}(?:\.\d+)?)\s*[^C]*C", texto_ocr, re.IGNORECASE)
                    temperatura = float(temp_match.group(1)) if temp_match else 23.5
                    
                    peaks_match = re.search(r"highest peaks:\s*(.*?)(?:\(|Arithmetic|\n|$)", texto_ocr, re.IGNORECASE)
                    picos = peaks_match.group(1).strip() if peaks_match else ""
                    
                    valleys_match = re.search(r"highest valleys:\s*(.*?)(?:\(|Arithmetic|\n|$)", texto_ocr, re.IGNORECASE)
                    valles = valleys_match.group(1).strip() if valleys_match else ""
                    
                    # Calcular absolutos matemáticos
                    max_abs = 0.0
                    promedio_picos = 0.0
                    try:
                        p_vals = [float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+", picos)]
                        v_vals = [float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+", valles)]
                        todos = p_vals + v_vals
                        if todos: max_abs = max(abs(x) for x in todos)
                        if p_vals: promedio_picos = sum(p_vals) / len(p_vals)
                    except: pass

                    # Mostrar extracción y gráfica
                    col_ocr1, col_ocr2 = st.columns(2)
                    col_ocr1.metric("Voltaje Máx (Absoluto)", f"{max_abs:.2f} V")
                    col_ocr2.metric("Promedio Picos", f"{promedio_picos:.2f} V")
                    st.image(imagen_grafica, use_container_width=True)
                    
                    # 4. Formulario de confirmación y guardado
                    st.divider()
                    with st.form("form_wt_save", clear_on_submit=True):
                        st.write("**Confirma y asigna los datos:**")
                        c_wt1, c_wt2 = st.columns(2)
                        
                        loc_wt = c_wt1.text_input("Ubicación / Área (Ej: SMT-01)")
                        operador_wt = c_wt2.text_input("Nombre del Operador Evaluado")
                        
                        # Permitimos editar lo extraído por si el OCR falló
                        c_wt3, c_wt4, c_wt5 = st.columns(3)
                        temp_final = c_wt3.number_input("Temp (°C)", value=temperatura)
                        hum_final = c_wt4.number_input("Humedad (%)", value=humedad)
                        vmax_final = c_wt5.number_input("Voltaje Máx (V)", value=max_abs)
                        
                        if st.form_submit_button(t("lab", "wt_save"), type="primary", use_container_width=True):
                            if not loc_wt:
                                st.error("La ubicación es requerida.")
                            else:
                                status = "PASS" if vmax_final < 100.0 else "FAIL"
                                try:
                                    supabase.table("walking_test_logs").insert({
                                        "site_id": site_id,
                                        "location": loc_wt.strip().upper(),
                                        "operator_name": operador_wt.strip(),
                                        "temperature": temp_final,
                                        "humidity": hum_final,
                                        "max_voltage_abs": vmax_final,
                                        "peak_average": promedio_picos,
                                        "status_result": status,
                                        "auditor_id": user_id
                                    }).execute()
                                    st.success(f"¡Walking Test guardado! Estatus: {status}")
                                except Exception as e:
                                    st.error(f"Error de base de datos: {e}")
                                    
                else:
                    st.error("No se encontró ninguna gráfica en la primera página del PDF.")
            except Exception as e:
                st.error(f"Error procesando el PDF: {e}")
