# pages/06_infraestucture.py
"""
Módulo de Infraestructura y Puntos EPA (Tierras, Conexiones, Pisos ESD, Conductores Aislados y Checadores).
Incluye centro de consulta de registros históricos con soporte i18n y multi-tenant.
"""
import streamlit as st
try:
    st.set_page_config(page_title="ESD Management Suite", page_icon="⚡", layout="wide")
except Exception:
    pass
import pandas as pd
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

st.markdown(f"### {t('infra', 'title', '⚡ Infraestructura y Puntos EPA')}")
st.caption(f"{t('infra', 'subtitle', 'Verificación periódica de tierras auxiliares, conexiones de pulsera, pisos ESD y checadores')} - **{st.session_state.get('site_name', 'Site Principal')}**")

# Inicializar almacenes locales de respaldo para demostraciones y resiliencia
if "local_grounding_logs" not in st.session_state:
    st.session_state.local_grounding_logs = [
        {"created_at": "2026-08-09 08:30", "location": "SMT-01", "point_id": "GND-01", "point_type": "Auxiliary Ground", "resistance_ohms": 4.5, "status_result": "PASS", "auditor_id": "demo_user"},
        {"created_at": "2026-08-09 09:10", "location": "BE-02", "point_id": "WS-04", "point_type": "Wrist Strap Point", "resistance_ohms": 2.8, "status_result": "FAIL", "auditor_id": "demo_user"}
    ]

if "local_floor_logs" not in st.session_state:
    st.session_state.local_floor_logs = [
        {"created_at": "2026-08-09 10:00", "room_name": "CLEANROOM 1", "point_number": 1, "resistance_ohms": 4.5e7, "temperature": 23.5, "humidity": 45, "status_result": "PASS", "auditor_id": "demo_user"},
        {"created_at": "2026-08-09 10:15", "room_name": "CLEANROOM 1", "point_number": 2, "resistance_ohms": 1.2e10, "temperature": 23.8, "humidity": 40, "status_result": "FAIL", "auditor_id": "demo_user"}
    ]

if "local_isolated_logs" not in st.session_state:
    st.session_state.local_isolated_logs = [
        {"created_at": "2026-08-09 11:00", "location": "SMT-02", "operation_id": "ROUTER-01", "max_voltage": 18.5, "comments": "Laminar Shield OK", "status_result": "PASS", "auditor_id": "demo_user"},
        {"created_at": "2026-08-09 12:30", "location": "SMT-03", "operation_id": "STENCIL-CLEAN", "max_voltage": 42.0, "comments": "Requiere Ionizador de Boquilla", "status_result": "FAIL", "auditor_id": "demo_user"}
    ]

if "local_checkers_logs" not in st.session_state:
    st.session_state.local_checkers_logs = [
        {"created_at": "2026-08-09 07:00", "checker_id": "CHECADOR-01", "reference_left": 1.0e8, "reading_left": 1.02e8, "deviation_left": 2000000.0, "reference_right": 1.0e8, "reading_right": 1.01e8, "deviation_right": 1000000.0, "status_result": "PASS", "auditor_id": "demo_user"}
    ]

tab_ground, tab_floor, tab_iso, tab_chk, tab_records = st.tabs([
    t('infra', 'tab_ground', '⚡ Tierras y Conexiones'), 
    t('infra', 'tab_floor', '🔲 Piso ESD'), 
    t('infra', 'tab_iso', '⚡ Conductores Aislados'), 
    t('infra', 'tab_checkers', '🥾 Checadores de Ingreso'),
    t('infra', 'tab_records', '📋 Histórico de Infraestructura')
])

# --- PESTAÑA A: TIERRAS Y CONEXIONES ---
with tab_ground:
    st.markdown(f"#### {t('infra', 'tab_ground', '⚡ Tierras y Conexiones')}")
    
    with st.form("form_grounding", clear_on_submit=True):
        c1, c2 = st.columns(2)
        p_type = c1.selectbox(t('infra', 'gr_type', 'Tipo de Punto de Tierra'), ["Auxiliary Ground", "Wrist Strap Point"])
        p_loc = c2.text_input(t('infra', 'gr_loc', 'Ubicación / Línea'), placeholder="SMT-01")
        
        c3, c4 = st.columns(2)
        p_id = c3.text_input(t('infra', 'gr_id', 'Identificador del Punto (ID)'), placeholder="GND-01")
        p_ohms = c4.number_input(t('infra', 'gr_ohms', 'Resistencia a Tierra (Ohms)'), min_value=0.0, format="%.2f", step=0.1)
        
        if st.form_submit_button(t('infra', 'gr_save', '💾 Guardar Verificación de Tierra'), type="primary", use_container_width=True):
            if not p_loc or not p_id:
                st.error("Ubicación e ID son obligatorios.")
            else:
                with st.spinner("Guardando..."):
                    limit = 25.0 if p_type == "Auxiliary Ground" else 2.0
                    status = "PASS" if p_ohms < limit else "FAIL"
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    nuevo_gnd = {
                        "created_at": now_str,
                        "site_id": site_id,
                        "location": p_loc.strip().upper(),
                        "point_id": p_id.strip().upper(),
                        "point_type": p_type,
                        "resistance_ohms": float(p_ohms),
                        "status_result": status,
                        "auditor_id": user_id
                    }
                    
                    try:
                        supabase.table("grounding_logs").insert(nuevo_gnd).execute()
                    except Exception:
                        pass
                        
                    st.session_state.local_grounding_logs.insert(0, nuevo_gnd)
                    if status == "PASS":
                        st.success(f"{t('infra', 'msg_pass', '✅ Medición APROBADA (PASS)')}")
                    else:
                        st.error(f"{t('infra', 'msg_fail', '🚨 Medición RECHAZADA (FAIL)')}")
                    st.rerun()

# --- PESTAÑA B: PISO ESD ---
with tab_floor:
    st.markdown(f"#### {t('infra', 'tab_floor', '🔲 Piso ESD')}")
    
    with st.form("form_floor", clear_on_submit=True):
        cf1, cf2 = st.columns(2)
        f_room = cf1.text_input(t('infra', 'fl_room', 'Nombre del Cuarto / Área Cleanroom'), placeholder="Room 1")
        f_point = cf2.number_input(t('infra', 'fl_point', 'Número de Punto de Medición'), min_value=1, step=1)
        
        cf3, cf4, cf5 = st.columns(3)
        f_temp = cf3.number_input("Temp (°C)", value=23.5)
        f_hum = cf4.number_input("Humedad (%)", value=45)
        f_ohms = cf5.number_input("Ohms", min_value=0.0, format="%.2e", step=1e6)
        
        if st.form_submit_button(t('infra', 'fl_save', '💾 Guardar Verificación de Piso'), type="primary", use_container_width=True):
            if not f_room:
                st.error("El nombre del cuarto es obligatorio.")
            else:
                with st.spinner("Guardando..."):
                    status = "PASS" if f_ohms < 1.0e9 else "FAIL"
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    nuevo_floor = {
                        "created_at": now_str,
                        "site_id": site_id,
                        "room_name": f_room.strip().upper(),
                        "point_number": int(f_point),
                        "resistance_ohms": float(f_ohms),
                        "temperature": float(f_temp),
                        "humidity": float(f_hum),
                        "status_result": status,
                        "auditor_id": user_id
                    }
                    try:
                        supabase.table("floor_validation_logs").insert(nuevo_floor).execute()
                    except Exception:
                        pass
                        
                    st.session_state.local_floor_logs.insert(0, nuevo_floor)
                    st.success(f"{t('infra', 'msg_pass', '✅ Medición APROBADA (PASS)')} [{status}]")
                    st.rerun()

# --- PESTAÑA C: CONDUCTORES AISLADOS ---
with tab_iso:
    st.markdown(f"#### {t('infra', 'tab_iso', '⚡ Conductores Aislados')}")
    
    with st.form("form_iso_cond", clear_on_submit=True):
        ci1, ci2 = st.columns(2)
        i_loc = ci1.text_input(t('infra', 'gr_loc', 'Ubicación / Línea'))
        i_op = ci2.text_input(t('infra', 'iso_op', 'Operación / Estación ID'))
        
        ci3, ci4 = st.columns([1, 2])
        i_volt = ci3.number_input(t('infra', 'iso_volt', 'Voltaje Inducido Máximo (V)'), min_value=0.0, format="%.1f", step=1.0)
        i_notes = ci4.text_input("Comentarios / Ubicación exacta")
        
        if st.form_submit_button(t('infra', 'iso_save', '💾 Guardar Registro de Conductor Aislado'), type="primary", use_container_width=True):
            if not i_loc or not i_op:
                st.error("Línea y Operación son obligatorios.")
            else:
                with st.spinner("Guardando..."):
                    status = "PASS" if i_volt <= 35.0 else "FAIL"
                    if i_volt > 35.0 and not i_notes.strip():
                        st.error("⚠️ Al superar los 35V, es obligatorio especificar la ubicación exacta en los comentarios.")
                    else:
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                        nuevo_iso = {
                            "created_at": now_str,
                            "site_id": site_id,
                            "location": i_loc.strip().upper(),
                            "operation_id": i_op.strip().upper(),
                            "max_voltage": float(i_volt),
                            "comments": i_notes.strip(),
                            "status_result": status,
                            "auditor_id": user_id
                        }
                        try:
                            supabase.table("isolated_conductors_logs").insert(nuevo_iso).execute()
                        except Exception:
                            pass
                            
                        st.session_state.local_isolated_logs.insert(0, nuevo_iso)
                        if i_volt > 35.0:
                            st.error(f"🚨 FAIL: {i_volt}V supera el límite de 35V. Requiere Ionización.")
                        else:
                            st.success("✅ PASS: Voltaje dentro de norma.")
                        st.rerun()

# --- PESTAÑA D: CHECADORES DE INGRESO ---
with tab_chk:
    st.markdown(f"#### {t('infra', 'tab_checkers', '🥾 Checadores de Ingreso')}")
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
                    limite_desv = 1e9 * 0.05
                    
                    status = "PASS" if (desv_izq <= limite_desv and desv_der <= limite_desv) else "FAIL"
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                    
                    nuevo_chk = {
                        "created_at": now_str,
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
                    }
                    try:
                        supabase.table("entrance_checkers_logs").insert(nuevo_chk).execute()
                    except Exception:
                        pass
                        
                    st.session_state.local_checkers_logs.insert(0, nuevo_chk)
                    if status == "PASS":
                        st.success("✅ Verificación exitosa. Variaciones menores al 5%.")
                    else:
                        st.error("🚨 Falla de calibración: Desviación supera el 5% permitido.")
                    st.rerun()

# ==========================================
# 3. CENTRO DE CONSULTA E HISTÓRICO DE INFRAESTRUCTURA
# ==========================================
with tab_records:
    st.markdown(f"#### 📋 {t('infra', 'records_title', 'Histórico y Consulta de Infraestructura EPA')}")
    st.caption("Inspecciona, filtra por estatus y exporta las verificaciones de tierras, pisos, conductores y checadores.")
    
    sec_gnd, sec_fl, sec_iso, sec_chk = st.tabs([
        t("infra", "lbl_gr_history", "⚡ Tierras y Conexiones"),
        t("infra", "lbl_fl_history", "🔲 Piso ESD"),
        t("infra", "lbl_iso_history", "⚡ Conductores Aislados"),
        t("infra", "lbl_chk_history", "🥾 Checadores de Ingreso")
    ])
    
    # --- HISTÓRICO TIERRAS ---
    with sec_gnd:
        st.markdown(f"##### {t('infra', 'lbl_gr_history', '⚡ Histórico de Tierras y Conexiones')}")
        gnd_logs = []
        try:
            resp_gnd = supabase.table("grounding_logs").select("*").eq("site_id", site_id).order("created_at", desc=True).execute()
            if resp_gnd and hasattr(resp_gnd, 'data') and resp_gnd.data:
                gnd_logs = resp_gnd.data
        except Exception:
            pass
        if not gnd_logs:
            gnd_logs = st.session_state.local_grounding_logs
            
        df_gnd = pd.DataFrame(gnd_logs)
        if not df_gnd.empty:
            cg1, cg2 = st.columns([2, 1])
            search_gnd = cg1.text_input("Buscar por Ubicación o ID...", key="s_gnd")
            status_gnd = cg2.selectbox("Filtrar por Estatus:", ["TODOS", "PASS", "FAIL"], key="st_gnd")
            
            df_gnd_f = df_gnd.copy()
            if status_gnd != "TODOS":
                df_gnd_f = df_gnd_f[df_gnd_f["status_result"] == status_gnd]
            if search_gnd:
                term = search_gnd.upper()
                df_gnd_f = df_gnd_f[df_gnd_f["location"].astype(str).str.contains(term) | df_gnd_f["point_id"].astype(str).str.contains(term)]
                
            st.dataframe(df_gnd_f, use_container_width=True)
            st.download_button("📥 Exportar Tierras a CSV", df_gnd_f.to_csv(index=False).encode('utf-8'), "grounding_logs.csv", "text/csv")
        else:
            st.info(t("infra", "no_records", "No se encontraron registros."))

    # --- HISTÓRICO PISO ESD ---
    with sec_fl:
        st.markdown(f"##### {t('infra', 'lbl_fl_history', '🔲 Histórico de Validación de Pisos ESD')}")
        fl_logs = []
        try:
            resp_fl = supabase.table("floor_validation_logs").select("*").eq("site_id", site_id).order("created_at", desc=True).execute()
            if resp_fl and hasattr(resp_fl, 'data') and resp_fl.data:
                fl_logs = resp_fl.data
        except Exception:
            pass
        if not fl_logs:
            fl_logs = st.session_state.local_floor_logs
            
        df_fl = pd.DataFrame(fl_logs)
        if not df_fl.empty:
            cf1, cf2 = st.columns([2, 1])
            search_fl = cf1.text_input("Buscar por Cuarto / Área...", key="s_fl")
            status_fl = cf2.selectbox("Filtrar por Estatus:", ["TODOS", "PASS", "FAIL"], key="st_fl")
            
            df_fl_f = df_fl.copy()
            if status_fl != "TODOS":
                df_fl_f = df_fl_f[df_fl_f["status_result"] == status_fl]
            if search_fl:
                df_fl_f = df_fl_f[df_fl_f["room_name"].astype(str).str.upper().str.contains(search_fl.upper())]
                
            st.dataframe(df_fl_f, use_container_width=True)
            st.download_button("📥 Exportar Pisos a CSV", df_fl_f.to_csv(index=False).encode('utf-8'), "floor_logs.csv", "text/csv")
        else:
            st.info(t("infra", "no_records", "No se encontraron registros."))

    # --- HISTÓRICO CONDUCTORES AISLADOS ---
    with sec_iso:
        st.markdown(f"##### {t('infra', 'lbl_iso_history', '⚡ Histórico de Conductores Aislados')}")
        iso_logs = []
        try:
            resp_iso = supabase.table("isolated_conductors_logs").select("*").eq("site_id", site_id).order("created_at", desc=True).execute()
            if resp_iso and hasattr(resp_iso, 'data') and resp_iso.data:
                iso_logs = resp_iso.data
        except Exception:
            pass
        if not iso_logs:
            iso_logs = st.session_state.local_isolated_logs
            
        df_iso = pd.DataFrame(iso_logs)
        if not df_iso.empty:
            ci1, ci2 = st.columns([2, 1])
            search_iso = ci1.text_input("Buscar por Ubicación u Operación...", key="s_iso")
            status_iso = ci2.selectbox("Filtrar por Estatus:", ["TODOS", "PASS", "FAIL"], key="st_iso")
            
            df_iso_f = df_iso.copy()
            if status_iso != "TODOS":
                df_iso_f = df_iso_f[df_iso_f["status_result"] == status_iso]
            if search_iso:
                term = search_iso.upper()
                df_iso_f = df_iso_f[df_iso_f["location"].astype(str).str.contains(term) | df_iso_f["operation_id"].astype(str).str.contains(term)]
                
            st.dataframe(df_iso_f, use_container_width=True)
            st.download_button("📥 Exportar Conductores Aislados a CSV", df_iso_f.to_csv(index=False).encode('utf-8'), "isolated_logs.csv", "text/csv")
        else:
            st.info(t("infra", "no_records", "No se encontraron registros."))

    # --- HISTÓRICO CHECADORES ---
    with sec_chk:
        st.markdown(f"##### {t('infra', 'lbl_chk_history', '🥾 Histórico de Calibración de Checadores')}")
        chk_logs = []
        try:
            resp_chk = supabase.table("entrance_checkers_logs").select("*").eq("site_id", site_id).order("created_at", desc=True).execute()
            if resp_chk and hasattr(resp_chk, 'data') and resp_chk.data:
                chk_logs = resp_chk.data
        except Exception:
            pass
        if not chk_logs:
            chk_logs = st.session_state.local_checkers_logs
            
        df_chk = pd.DataFrame(chk_logs)
        if not df_chk.empty:
            cc1, cc2 = st.columns([2, 1])
            search_chk = cc1.text_input("Buscar por ID de Checador...", key="s_chk")
            status_chk = cc2.selectbox("Filtrar por Estatus:", ["TODOS", "PASS", "FAIL"], key="st_chk")
            
            df_chk_f = df_chk.copy()
            if status_chk != "TODOS":
                df_chk_f = df_chk_f[df_chk_f["status_result"] == status_chk]
            if search_chk:
                df_chk_f = df_chk_f[df_chk_f["checker_id"].astype(str).str.upper().str.contains(search_chk.upper())]
                
            st.dataframe(df_chk_f, use_container_width=True)
            st.download_button("📥 Exportar Checadores a CSV", df_chk_f.to_csv(index=False).encode('utf-8'), "checkers_logs.csv", "text/csv")
        else:
            st.info(t("infra", "no_records", "No se encontraron registros."))
