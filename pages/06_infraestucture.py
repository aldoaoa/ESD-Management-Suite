# pages/06_infrastructure.py

import streamlit as st
import pandas as pd
from core.i18n import t
from core.db import get_supabase_client

# ==========================================
# 1. BARRERA DE SEGURIDAD MULTI-TENANT
# ==========================================
if st.session_state.get("modo_lectura", True):
    st.warning(t("auth", "login_required"))
    st.stop()

supabase = get_supabase_client()
site_id = st.session_state.site_id
user_id = st.session_state.user_id

st.markdown(f"### {t('infra', 'title')}")
st.caption(f"{t('infra', 'subtitle')} - **{st.session_state.site_name}**")

# ==========================================
# 2. PESTAÑAS DE INFRAESTRUCTURA
# ==========================================
tab_ground, tab_floor, tab_iso, tab_chk = st.tabs([
    t('infra', 'tab_ground'), 
    t('infra', 'tab_floor'), 
    t('infra', 'tab_iso'), 
    t('infra', 'tab_checkers')
])

# --- PESTAÑA A: TIERRAS Y CONEXIONES ---
with tab_ground:
    st.markdown(f"#### {t('infra', 'tab_ground')}")
    
    with st.form("form_grounding", clear_on_submit=True):
        c1, c2 = st.columns(2)
        p_type = c1.selectbox(t('infra', 'gr_type'), ["Auxiliary Ground", "Wrist Strap Point"])
        p_loc = c2.text_input(t('infra', 'gr_loc'), placeholder="SMT-01")
        
        c3, c4 = st.columns(2)
        p_id = c3.text_input(t('infra', 'gr_id'), placeholder="GND-01")
        p_ohms = c4.number_input(t('infra', 'gr_ohms'), min_value=0.0, format="%.2f", step=0.1)
        
        if st.form_submit_button(t('infra', 'gr_save'), type="primary", use_container_width=True):
            if not p_loc or not p_id:
                st.error("Ubicación e ID son obligatorios.")
            else:
                with st.spinner("Guardando..."):
                    # Lógica Normativa: Tierras auxiliares < 25 ohms, Conexiones de pulsera < 2.0 ohms
                    limit = 25.0 if p_type == "Auxiliary Ground" else 2.0
                    status = "PASS" if p_ohms < limit else "FAIL"
                    
                    try:
                        supabase.table("grounding_logs").insert({
                            "site_id": site_id,
                            "location": p_loc.strip().upper(),
                            "point_id": p_id.strip().upper(),
                            "point_type": p_type,
                            "resistance_ohms": float(p_ohms),
                            "status_result": status,
                            "auditor_id": user_id
                        }).execute()
                        
                        if status == "PASS":
                            st.success(t('infra', 'msg_pass'))
                        else:
                            st.error(t('infra', 'msg_fail'))
                    except Exception as e:
                        st.error(f"Error SQL: {e}")

# --- PESTAÑA B: PISO ESD ---
with tab_floor:
    st.markdown(f"#### {t('infra', 'tab_floor')}")
    
    with st.form("form_floor", clear_on_submit=True):
        cf1, cf2 = st.columns(2)
        f_room = cf1.text_input(t('infra', 'fl_room'), placeholder="Room 1")
        f_point = cf2.number_input(t('infra', 'fl_point'), min_value=1, step=1)
        
        cf3, cf4, cf5 = st.columns(3)
        f_temp = cf3.number_input("Temp (°C)", value=23.5)
        f_hum = cf4.number_input("Humedad (%)", value=45)
        f_ohms = cf5.number_input("Ohms", min_value=0.0, format="%.2e", step=1e6)
        
        if st.form_submit_button(t('infra', 'fl_save'), type="primary", use_container_width=True):
            if not f_room:
                st.error("El nombre del cuarto es obligatorio.")
            else:
                with st.spinner("Guardando..."):
                    # Norma: Piso < 1.0x10^9 Ohms
                    status = "PASS" if f_ohms < 1.0e9 else "FAIL"
                    try:
                        supabase.table("floor_validation_logs").insert({
                            "site_id": site_id,
                            "room_name": f_room.strip().upper(),
                            "point_number": int(f_point),
                            "resistance_ohms": float(f_ohms),
                            "temperature": float(f_temp),
                            "humidity": float(f_hum),
                            "status_result": status,
                            "auditor_id": user_id
                        }).execute()
                        st.success(f"{t('infra', 'msg_pass')} [{status}]")
                    except Exception as e:
                        st.error(f"Error SQL: {e}")

# --- PESTAÑA C: CONDUCTORES AISLADOS ---
with tab_iso:
    st.markdown(f"#### {t('infra', 'tab_iso')}")
    
    with st.form("form_iso_cond", clear_on_submit=True):
        ci1, ci2 = st.columns(2)
        i_loc = ci1.text_input(t('infra', 'gr_loc'))
        i_op = ci2.text_input(t('infra', 'iso_op'))
        
        ci3, ci4 = st.columns([1, 2])
        i_volt = ci3.number_input(t('infra', 'iso_volt'), min_value=0.0, format="%.1f", step=1.0)
        i_notes = ci4.text_input("Comentarios / Ubicación exacta")
        
        if st.form_submit_button(t('infra', 'iso_save'), type="primary", use_container_width=True):
            if not i_loc or not i_op:
                st.error("Línea y Operación son obligatorios.")
            else:
                with st.spinner("Guardando..."):
                    # Norma S20.20: Conductores aislados < 35V
                    if i_volt > 35.0 and not i_notes.strip():
                        st.error("⚠️ Al superar los 35V, es obligatorio especificar la ubicación exacta en los comentarios.")
                    else:
                        try:
                            supabase.table("isolated_conductors_logs").insert({
                                "site_id": site_id,
                                "location": i_loc.strip().upper(),
                                "operation_id": i_op.strip().upper(),
                                "max_voltage": float(i_volt),
                                "comments": i_notes.strip(),
                                "auditor_id": user_id
                            }).execute()
                            
                            if i_volt > 35.0:
                                st.error(f"🚨 FAIL: {i_volt}V supera el límite de 35V. Requiere Ionización.")
                            else:
                                st.success("✅ PASS: Voltaje dentro de norma.")
                        except Exception as e:
                            st.error(f"Error SQL: {e}")

# --- PESTAÑA D: CHECADORES DE INGRESO ---
with tab_chk:
    st.markdown(f"#### {t('infra', 'tab_checkers')}")
    st.info("Validación mensual cruzada con Megóhmetro (Tolerancia máxima 5%)")
    
    with st.form("form_checkers", clear_on_submit=True):
        chk_id = st.text_input("ID del Checador", placeholder="CHECADOR-01")
        
        st.markdown("##### Pie Izquierdo")
        cl1, cl2 = st.columns(2)
        ref_izq = cl1.number_input("Ref. Megóhmetro Izq (Ohms)", format="%.2e", step=1e6)
        lec_izq = cl2.number_input("Lectura Checador Izq (Ohms)", format="%.2e", step=1e6)
        
        st.markdown("##### Pie Derecho")
        cd1, cd2 = st.columns(2)
        ref_der = cd1.number_input("Ref. Megóhmetro Der (Ohms)", format="%.2e", step=1e6)
        lec_der = cd2.number_input("Lectura Checador Der (Ohms)", format="%.2e", step=1e6)
        
        if st.form_submit_button("💾 Guardar Verificación", type="primary", use_container_width=True):
            if not chk_id:
                st.error("El ID del checador es obligatorio.")
            else:
                with st.spinner("Calculando desviaciones..."):
                    desv_izq = abs(lec_izq - ref_izq) if ref_izq > 0 else 0
                    desv_der = abs(lec_der - ref_der) if ref_der > 0 else 0
                    
                    limite_desv = 1e9 * 0.05 # 5% de tolerancia sobre 1 Gigaohm
                    
                    status = "PASS" if (desv_izq <= limite_desv and desv_der <= limite_desv) else "FAIL"
                    
                    try:
                        supabase.table("entrance_checkers_logs").insert({
                            "site_id": site_id,
                            "checker_id": chk_id.strip().upper(),
                            "reference_left": float(ref_izq),
                            "reading_left": float(lec_izq),
                            "deviation_left": float(desv_izq),
                            "reference_right": float(ref_der),
                            "reading_right": float(lec_der),
                            "deviation_right": float(desv_der),
                            "status_result": status,
                            "auditor_id": user_id
                        }).execute()
                        
                        if status == "PASS":
                            st.success("✅ Verificación exitosa. Variaciones menores al 5%.")
                        else:
                            st.error("🚨 Falla de calibración: Desviación supera el 5% permitido.")
                    except Exception as e:
                        st.error(f"Error SQL: {e}")
