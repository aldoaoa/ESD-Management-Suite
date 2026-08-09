# pages/05_lab.py
"""
Módulo de Laboratorio de Pruebas ESD (Event Meter & Walking Test).
Incluye centro interactivo de consulta de registros históricos con i18n y soporte multi-tenant.
"""
import streamlit as st
try:
    st.set_page_config(page_title="ESD Management Suite", page_icon="⚡", layout="wide")
except Exception:
    pass
import pandas as pd
import re
import io
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from datetime import datetime
from core.i18n import t
from core.db import get_supabase_client
from components.sidebar import render_sidebar, hide_sidebar

# Ocultar navegación nativa antes de evaluar accesos
hide_sidebar()

# ==========================================
# 1. BARRERA DE SEGURIDAD MULTI-TENANT
# ==========================================
if st.session_state.get("modo_lectura", True):
    from core.auth import render_login_screen
    render_login_screen(t("auth", "login_required", "🔒 Por favor inicia sesión para acceder a este módulo."))
    st.stop()

render_sidebar()

supabase = get_supabase_client()
site_id = st.session_state.get("site_id")
user_id = st.session_state.get("user_id")

st.markdown(f"### {t('lab', 'title', '🧪 Laboratorio de Pruebas ESD')}")
st.caption(f"{t('lab', 'subtitle', 'Evaluación de descargas transitorias (Event Meter) y ensayos de caminata (Walking Test)')} - **{st.session_state.get('site_name', 'Site Principal')}**")

# Inicializar almacenamiento local temporal para demostraciones
if "local_event_meter_logs" not in st.session_state:
    st.session_state.local_event_meter_logs = [
        {
            "created_at": "2026-08-09 10:15",
            "location": "SMT-01",
            "operation_id": "LINE-SMT1-AOI",
            "contact_type": "Maquinaria",
            "events_count": 3,
            "max_voltage": 45.2,
            "temperature": 23.5,
            "humidity": 45,
            "status_result": "PASS",
            "auditor_id": "demo_user"
        },
        {
            "created_at": "2026-08-09 11:30",
            "location": "BE-02",
            "operation_id": "EOLT-TEST-02",
            "contact_type": "Herramienta Manual",
            "events_count": 12,
            "max_voltage": 120.8,
            "temperature": 24.0,
            "humidity": 42,
            "status_result": "FAIL",
            "auditor_id": "demo_user"
        }
    ]

if "local_walking_test_logs" not in st.session_state:
    st.session_state.local_walking_test_logs = [
        {
            "created_at": "2026-08-09 09:45",
            "location": "CLEANROOM-01",
            "operator_name": "Juan Pérez",
            "temperature": 22.8,
            "humidity": 48,
            "max_voltage_abs": 38.5,
            "peak_average": 24.2,
            "status_result": "PASS",
            "auditor_id": "demo_user"
        },
        {
            "created_at": "2026-08-09 14:20",
            "location": "SMT-02",
            "operator_name": "María Gómez",
            "temperature": 24.1,
            "humidity": 39,
            "max_voltage_abs": 115.0,
            "peak_average": 88.4,
            "status_result": "FAIL",
            "auditor_id": "demo_user"
        }
    ]

tab_event, tab_walking, tab_records = st.tabs([
    t('lab', 'tab_event', '⚡ Event Meter'), 
    t('lab', 'tab_walking', '👣 Walking Test'),
    t('lab', 'tab_records', '📊 Consulta de Ensayos')
])

# ==========================================
# 2. EVENT METER (ESTUDIO DE DESCARGAS)
# ==========================================
with tab_event:
    st.markdown(f"#### {t('lab', 'em_title', 'Registro de Event Meter (PCBA)')}")
    st.info(t('lab', 'em_info', 'Mide descargas electrostáticas y transitorios durante la operación normal de la maquinaria.'))
    
    with st.form("form_event_meter", clear_on_submit=True):
        c1, c2 = st.columns(2)
        linea = c1.text_input(t("lab", "em_location", "Ubicación / Línea"), placeholder="Ej. SMT-01")
        operacion = c2.text_input(t("lab", "em_operation", "Operación / Estación ID"), placeholder="Ej. AOI-01")
        
        c3, c4, c5 = st.columns([2, 1, 1])
        contacto = c3.selectbox(t("lab", "em_contact", "Tipo de Contacto"), ["Maquinaria", "EOLT", "AOI", "Herramienta Manual", "Humano", "Otro"])
        temp = c4.number_input("Temp (°C)", value=23.5)
        hum = c5.number_input("Humedad (%)", value=45)
        
        c6, c7 = st.columns(2)
        eventos = c6.number_input(t("lab", "em_events", "Número de Eventos Detectados"), min_value=0, step=1)
        voltaje = c7.number_input(t("lab", "em_voltage", "Voltaje Máximo Detectado (V)"), min_value=0.0, step=0.1)
        
        if st.form_submit_button(t("lab", "em_save", "💾 Guardar Registro de Event Meter"), type="primary", use_container_width=True):
            if not linea or not operacion:
                st.error("Línea y Operación son obligatorios.")
            else:
                with st.spinner("Guardando..."):
                    status = "PASS" if voltaje <= 100.0 else "FAIL"
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    nuevo_registro = {
                        "created_at": now_str,
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
                    }
                    
                    try:
                        supabase.table("event_meter_logs").insert(nuevo_registro).execute()
                    except Exception:
                        pass
                        
                    st.session_state.local_event_meter_logs.insert(0, nuevo_registro)
                    st.success(f"✅ Registro de Event Meter guardado exitosamente. Estatus: **{status}**")
                    st.rerun()

# ==========================================
# 3. WALKING TEST (EXTRACCIÓN OCR DE PDF)
# ==========================================
with tab_walking:
    st.markdown(f"#### {t('lab', 'wt_title', 'Análisis OCR de Walking Test')}")
    archivo_pdf = st.file_uploader(t("lab", "wt_upload", "Cargar Gráfica PDF de Walking Test"), type=["pdf"])
    
    if archivo_pdf:
        with st.expander(f"📄 Documento: {archivo_pdf.name}", expanded=True):
            try:
                doc = fitz.open(stream=archivo_pdf.read(), filetype="pdf")
                pagina = doc[0]
                imagenes_pdf = pagina.get_images(full=True)
                
                if imagenes_pdf:
                    xref = imagenes_pdf[0][0]
                    base_image = doc.extract_image(xref)
                    imagen_grafica = Image.open(io.BytesIO(base_image["image"]))
                    
                    with st.spinner(t("lab", "wt_extracting", "Extrayendo gráfica y texto con OCR...")):
                        texto_ocr = pytesseract.image_to_string(imagen_grafica)
                    
                    hum_match = re.search(r"(\d{1,3}(?:\.\d+)?)\s*%?\s*RH", texto_ocr, re.IGNORECASE)
                    humedad = float(hum_match.group(1)) if hum_match else 45.0
                    
                    temp_match = re.search(r"(\d{1,3}(?:\.\d+)?)\s*[^C]*C", texto_ocr, re.IGNORECASE)
                    temperatura = float(temp_match.group(1)) if temp_match else 23.5
                    
                    peaks_match = re.search(r"highest peaks:\s*(.*?)(?:\(|Arithmetic|\n|$)", texto_ocr, re.IGNORECASE)
                    picos = peaks_match.group(1).strip() if peaks_match else ""
                    
                    valleys_match = re.search(r"highest valleys:\s*(.*?)(?:\(|Arithmetic|\n|$)", texto_ocr, re.IGNORECASE)
                    valles = valleys_match.group(1).strip() if valleys_match else ""
                    
                    max_abs = 0.0
                    promedio_picos = 0.0
                    try:
                        p_vals = [float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+", picos)]
                        v_vals = [float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+", valles)]
                        todos = p_vals + v_vals
                        if todos: max_abs = max(abs(x) for x in todos)
                        if p_vals: promedio_picos = sum(p_vals) / len(p_vals)
                    except: pass

                    col_ocr1, col_ocr2 = st.columns(2)
                    col_ocr1.metric("Voltaje Máx (Absoluto)", f"{max_abs:.2f} V")
                    col_ocr2.metric("Promedio Picos", f"{promedio_picos:.2f} V")
                    st.image(imagen_grafica, use_container_width=True)
                    
                    st.divider()
                    with st.form("form_wt_save", clear_on_submit=True):
                        st.write("**Confirma y asigna los datos:**")
                        c_wt1, c_wt2 = st.columns(2)
                        
                        loc_wt = c_wt1.text_input("Ubicación / Área (Ej: SMT-01)")
                        operador_wt = c_wt2.text_input("Nombre del Operador Evaluado")
                        
                        c_wt3, c_wt4, c_wt5 = st.columns(3)
                        temp_final = c_wt3.number_input("Temp (°C)", value=temperatura)
                        hum_final = c_wt4.number_input("Humedad (%)", value=humedad)
                        vmax_final = c_wt5.number_input("Voltaje Máx (V)", value=max_abs)
                        
                        if st.form_submit_button(t("lab", "wt_save", "💾 Guardar Registro de Walking Test"), type="primary", use_container_width=True):
                            if not loc_wt:
                                st.error("La ubicación es requerida.")
                            else:
                                status = "PASS" if vmax_final < 100.0 else "FAIL"
                                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                                nuevo_wt = {
                                    "created_at": now_str,
                                    "site_id": site_id,
                                    "location": loc_wt.strip().upper(),
                                    "operator_name": operador_wt.strip(),
                                    "temperature": temp_final,
                                    "humidity": hum_final,
                                    "max_voltage_abs": vmax_final,
                                    "peak_average": promedio_picos,
                                    "status_result": status,
                                    "auditor_id": user_id
                                }
                                try:
                                    supabase.table("walking_test_logs").insert(nuevo_wt).execute()
                                except Exception:
                                    pass
                                
                                st.session_state.local_walking_test_logs.insert(0, nuevo_wt)
                                st.success(f"✅ Walking Test guardado exitosamente. Estatus: **{status}**")
                                st.rerun()
                else:
                    st.error("No se encontró ninguna gráfica en la primera página del PDF.")
            except Exception as e:
                st.error(f"Error procesando el PDF: {e}")

# ==========================================
# 4. CENTRO DE CONSULTA Y AUDITORÍA DE ENSAYOS
# ==========================================
with tab_records:
    st.markdown(f"#### 📊 {t('lab', 'records_title', 'Centro de Consulta de Registros de Laboratorio')}")
    st.caption("Filtra, audita y exporta las mediciones registradas de Event Meter y Walking Test.")
    
    subtab_em, subtab_wt = st.tabs([
        t("lab", "lbl_em_history", "⚡ Histórico Event Meter"),
        t("lab", "lbl_wt_history", "👣 Histórico Walking Test")
    ])
    
    # --- SUBTAB: EVENT METER HISTORY ---
    with subtab_em:
        st.markdown(f"##### {t('lab', 'lbl_em_history', '⚡ Histórico de Mediciones Event Meter (PCBA)')}")
        
        # Obtener datos de Supabase o respaldo local
        em_logs = []
        try:
            resp_em = supabase.table("event_meter_logs").select("*").eq("site_id", site_id).order("created_at", desc=True).execute()
            if resp_em and hasattr(resp_em, 'data') and resp_em.data:
                em_logs = resp_em.data
        except Exception:
            pass
        
        if not em_logs:
            em_logs = st.session_state.local_event_meter_logs
            
        df_em = pd.DataFrame(em_logs)
        
        if not df_em.empty:
            # Filtros dinámicos
            col_f1, col_f2 = st.columns([2, 1])
            search_em = col_f1.text_input(t("lab", "lbl_search_lab", "Buscar por Ubicación, Operación u Operador..."), key="search_em")
            status_em = col_f2.selectbox(t("lab", "lbl_filter_status", "Filtrar por Estatus:"), ["TODOS", "PASS", "FAIL"], key="status_em")
            
            # Aplicar filtros
            df_filtered = df_em.copy()
            if status_em != "TODOS":
                df_filtered = df_filtered[df_filtered["status_result"] == status_em]
            if search_em:
                s_term = search_em.upper()
                df_filtered = df_filtered[
                    df_filtered["location"].astype(str).str.contains(s_term) | 
                    df_filtered["operation_id"].astype(str).str.contains(s_term)
                ]
            
            # Métricas
            m1, m2, m3, m4 = st.columns(4)
            total_em = len(df_filtered)
            pass_em = len(df_filtered[df_filtered["status_result"] == "PASS"])
            rate_em = (pass_em / total_em * 100) if total_em > 0 else 0.0
            max_v_em = df_filtered["max_voltage"].max() if total_em > 0 and "max_voltage" in df_filtered else 0.0
            
            m1.metric("Total Mediciones", total_em)
            m2.metric("Aprobados (PASS)", pass_em)
            m3.metric("Tasa de Cumplimiento", f"{rate_em:.1f}%")
            m4.metric("Voltaje Máx Registrado", f"{max_v_em:.1f} V")
            
            st.divider()
            st.dataframe(df_filtered, use_container_width=True)
            
            csv_em = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"📥 {t('lab', 'btn_export_csv', 'Exportar Tabla a CSV')}",
                data=csv_em,
                file_name=f"event_meter_logs_{site_id}.csv",
                mime="text/csv"
            )
        else:
            st.info(t("lab", "no_records", "No se encontraron registros guardados en esta categoría."))

    # --- SUBTAB: WALKING TEST HISTORY ---
    with subtab_wt:
        st.markdown(f"##### {t('lab', 'lbl_wt_history', '👣 Histórico de Ensayos Walking Test (OCR)')}")
        
        wt_logs = []
        try:
            resp_wt = supabase.table("walking_test_logs").select("*").eq("site_id", site_id).order("created_at", desc=True).execute()
            if resp_wt and hasattr(resp_wt, 'data') and resp_wt.data:
                wt_logs = resp_wt.data
        except Exception:
            pass
            
        if not wt_logs:
            wt_logs = st.session_state.local_walking_test_logs
            
        df_wt = pd.DataFrame(wt_logs)
        
        if not df_wt.empty:
            col_wf1, col_wf2 = st.columns([2, 1])
            search_wt = col_wf1.text_input(t("lab", "lbl_search_lab", "Buscar por Ubicación, Operación u Operador..."), key="search_wt")
            status_wt = col_wf2.selectbox(t("lab", "lbl_filter_status", "Filtrar por Estatus:"), ["TODOS", "PASS", "FAIL"], key="status_wt")
            
            df_wt_filtered = df_wt.copy()
            if status_wt != "TODOS":
                df_wt_filtered = df_wt_filtered[df_wt_filtered["status_result"] == status_wt]
            if search_wt:
                s_term = search_wt.upper()
                df_wt_filtered = df_wt_filtered[
                    df_wt_filtered["location"].astype(str).str.contains(s_term) | 
                    df_wt_filtered["operator_name"].astype(str).str.upper().str.contains(s_term)
                ]
            
            w1, w2, w3, w4 = st.columns(4)
            total_wt = len(df_wt_filtered)
            pass_wt = len(df_wt_filtered[df_wt_filtered["status_result"] == "PASS"])
            rate_wt = (pass_wt / total_wt * 100) if total_wt > 0 else 0.0
            max_v_wt = df_wt_filtered["max_voltage_abs"].max() if total_wt > 0 and "max_voltage_abs" in df_wt_filtered else 0.0
            
            w1.metric("Total Ensayos", total_wt)
            w2.metric("Aprobados (PASS)", pass_wt)
            w3.metric("Tasa de Cumplimiento", f"{rate_wt:.1f}%")
            w4.metric("Voltaje Abs. Máx", f"{max_v_wt:.1f} V")
            
            st.divider()
            st.dataframe(df_wt_filtered, use_container_width=True)
            
            csv_wt = df_wt_filtered.to_csv(index=False).encode('utf-8')
            st.download_button(
                label=f"📥 {t('lab', 'btn_export_csv', 'Exportar Tabla a CSV')}",
                data=csv_wt,
                file_name=f"walking_test_logs_{site_id}.csv",
                mime="text/csv"
            )
        else:
            st.info(t("lab", "no_records", "No se encontraron registros guardados en esta categoría."))
