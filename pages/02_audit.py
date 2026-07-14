# pages/02_audit.py

import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import json
from core.i18n import t
from core.db import get_supabase_client
from components.reports import generate_esd_html_report
from components.sidebar import render_sidebar, hide_sidebar

# Ocultar navegación nativa antes de evaluar accesos
hide_sidebar()

# ==========================================
# 1. BARRERA DE SEGURIDAD
# ==========================================
if st.session_state.get("modo_lectura", True):
    st.warning(t("auth", "login_required"))
    st.stop()

render_sidebar()

supabase = get_supabase_client()
site_id = st.session_state.site_id
user_id = st.session_state.user_id

st.markdown(f"### {t('audit', 'title')}")

# ==========================================
# 2. CONTROL DE ESTADO (URL / ESCÁNER)
# ==========================================
id_escaneado = st.query_params.get("qr_id", "")

def limpiar_url():
    if "qr_id" in st.query_params:
        del st.query_params["qr_id"]

# ==========================================
# 3. LAYOUT DE PANTALLA DIVIDIDA (SPLIT SCREEN)
# ==========================================
col_izq, col_der = st.columns([1.2, 2])

asset_data = None
asset_db_id = None

with col_izq:
    if not id_escaneado:
        st.markdown(f"#### {t('audit', 'lbl_scan')}")
        
        # --- CÓDIGO HTML/JS DEL ESCÁNER QR ---
        html_code_qr = """
        <script src="https://unpkg.com/html5-qrcode"></script>
        <div id="reader_main" style="width:100%; max-width:500px; margin:auto; border-radius:10px; overflow:hidden; border: 2px solid #0052cc; background-color: #f9f9f9;"></div>
        <div style="text-align:center; margin-top:10px; display:flex; justify-content:center; gap:5px; flex-wrap:wrap;">
            <button type="button" id="cam_wide_main" style="padding:10px; background:#28a745; color:white; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">📸 LENTE ESTÁNDAR</button>
            <button type="button" id="cam_cycle_main" style="padding:10px; background:#555; color:white; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">🔄 OTRA CÁMARA</button>
        </div>
        <p id="cam-status-main" style="text-align:center; color:#666; font-size: 14px; margin-top: 10px;">Buscando cámaras...</p>
        <script>
        let html5QrCodeMain;
        let rearCamsMain = [];
        let currentIdxMain = 0;
        let wideIdMain = null;

        function startScannerMain(camId) {
            if(!html5QrCodeMain) html5QrCodeMain = new Html5Qrcode("reader_main");
            if (html5QrCodeMain.isScanning) {
                html5QrCodeMain.stop().then(() => { runScanMain(camId); }).catch(e => console.log(e));
            } else {
                runScanMain(camId);
            }
        }

        function runScanMain(camId) {
            html5QrCodeMain.start(
                camId, { fps: 15, qrbox: { width: 250, height: 250 }, aspectRatio: 1.0 },
                (decodedText) => {
                    html5QrCodeMain.stop();
                    const url = new URL(window.parent.location.href);
                    url.searchParams.set("qr_id", decodedText);
                    window.parent.history.replaceState({}, "", url);
                    window.parent.location.reload();
                }, (err) => {} 
            ).then(() => { 
                let activeCam = rearCamsMain.find(c => c.id === camId);
                document.getElementById("cam-status-main").innerText = "Lente activo: " + (activeCam ? activeCam.label : "Cámara");
            }).catch(err => {
                document.getElementById("cam-status-main").innerText = "Error iniciando lente. Intenta 'Otra Cámara'.";
            });
        }

        Html5Qrcode.getCameras().then(devices => {
            if (devices && devices.length) {
                rearCamsMain = devices.filter(c => c.label.toLowerCase().includes('back') || c.label.toLowerCase().includes('trasera') || c.label.toLowerCase().includes('environment'));
                if(rearCamsMain.length === 0) rearCamsMain = devices;

                wideIdMain = rearCamsMain[0].id;
                for (let c of rearCamsMain) {
                    let lbl = c.label.toLowerCase();
                    if (lbl.includes('wide') && !lbl.includes('ultra')) {
                        wideIdMain = c.id; break;
                    }
                }
                currentIdxMain = rearCamsMain.findIndex(c => c.id === wideIdMain);
                if(currentIdxMain === -1) currentIdxMain = 0;

                startScannerMain(wideIdMain);

                document.getElementById('cam_wide_main').addEventListener('click', () => {
                    currentIdxMain = rearCamsMain.findIndex(c => c.id === wideIdMain);
                    startScannerMain(wideIdMain);
                });

                document.getElementById('cam_cycle_main').addEventListener('click', () => {
                    currentIdxMain = (currentIdxMain + 1) % rearCamsMain.length;
                    startScannerMain(rearCamsMain[currentIdxMain].id);
                });
            }
        }).catch(err => { document.getElementById("cam-status-main").innerText = "Permisos de cámara denegados."; });
        </script>
        """
        components.html(html_code_qr, height=500) 
        
        # --- INPUT MANUAL ---
        id_manual = st.text_input(t("audit", "lbl_manual"), key="input_manual")
        if id_manual:
            st.query_params["qr_id"] = id_manual
            st.rerun()
            
    else:
        # --- EQUIPO ESCANEADO: BÚSQUEDA EN BD ---
        c_info, c_btn = st.columns([0.7, 0.3])
        c_info.info(f"🔍 **ID:** {id_escaneado}")
        if c_btn.button(t("audit", "btn_close"), use_container_width=True):
            limpiar_url()
            st.rerun()
            
        id_limpio = str(id_escaneado).strip().upper()
        
        with st.spinner("Buscando activo..."):
            # 🛡️ SEGURIDAD MULTI-TENANT: Buscamos el activo estrictamente en esta planta
            resp_asset = supabase.table("assets").select("*").eq("site_id", site_id).eq("custom_id", id_limpio).execute()
            
            if resp_asset.data and len(resp_asset.data) > 0:
                asset_data = resp_asset.data[0]
                asset_db_id = asset_data["id"] # UUID interno real de la base de datos
                
                st.markdown(f"#### {t('audit', 'asset_info')}")
                with st.container(border=True):
                    c_loc, c_class = st.columns(2)
                    c_loc.metric(t("audit", "loc"), asset_data.get("location", "N/A"))
                    c_class.metric(t("audit", "class"), asset_data.get("classification", "N/A"))
                    
                    estatus = asset_data.get("status", "UNKNOWN")
                    color = "green" if estatus == "ACTIVE" else "red"
                    st.markdown(f"**{t('audit', 'status')}:** :{color}[{estatus}]")
            else:
                st.error(t("audit", "msg_not_found"))

with col_der:
    if not asset_data:
        st.info(t("audit", "waiting"))
    else:
        # --- 1. HISTORIAL DEL ACTIVO ---
        with st.expander(t("audit", "history"), expanded=False):
            # Extraemos el historial usando el UUID interno del activo
            resp_hist = supabase.table("measurements").select("*").eq("asset_id", asset_db_id).order("measured_at", desc=True).limit(5).execute()
            df_hist = pd.DataFrame(resp_hist.data)
            
            if not df_hist.empty:
                df_mostrar = df_hist[['measured_at', 'resistance_value', 'static_field_value', 'status_result']].copy()
                df_mostrar['measured_at'] = pd.to_datetime(df_mostrar['measured_at']).dt.strftime('%Y-%m-%d %H:%M')
                st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
            else:
                st.write("No hay registros previos.")

        # --- 2. MODO DE INSPECCIÓN ---
        st.markdown(f"#### {t('audit', 'new_record')}")
        
        # Obtenemos los strings traducidos con fallbacks por si no existen aún
        str_quick = t("audit", "mode_quick") if t("audit", "mode_quick") != "[audit.mode_quick]" else "Inspección Rápida (1 Punto)"
        str_integral = t("audit", "mode_integral") if t("audit", "mode_integral") != "[audit.mode_integral]" else "Validación Integral S20.20"
        
        modo_inspeccion = st.radio("Selecciona el modo:", [str_quick, str_integral], horizontal=True, label_visibility="collapsed")
        
        if modo_inspeccion == str_quick:
            with st.form("form_audit_capture", clear_on_submit=True):
                
                c_amb1, c_amb2 = st.columns(2)
                temp = c_amb1.number_input(t("audit", "lbl_temp"), value=23.5, step=0.1)
                hum = c_amb2.number_input(t("audit", "lbl_hum"), value=45.0, step=1.0)
                
                st.divider()
                
                c_val1, c_val2 = st.columns(2)
                
                if asset_data.get("category", "").upper() == "IONIZADOR":
                    val_res = None
                    val_volts = c_val2.number_input(t("audit", "lbl_volts"), format="%.1f", placeholder="0.0")
                else:
                    val_res = c_val1.number_input(t("audit", "lbl_res"), format="%.2e", min_value=0.0, placeholder="0.0e0")
                    val_volts = c_val2.number_input(t("audit", "lbl_volts"), format="%.1f", placeholder="0.0")
                    
                obs = st.text_area("Observaciones")
                
                if st.form_submit_button(t("audit", "btn_save"), type="primary", use_container_width=True):
                    with st.spinner("Guardando..."):
                        try:
                            limite = 1e9 if asset_data.get("category", "") != "Maquinaria" else 1.0
                            resultado = "PASS"
                            
                            if val_res is not None and val_res > limite:
                                resultado = "FAIL"
                            if val_volts is not None and abs(val_volts) > 100:
                                resultado = "FAIL"

                            supabase.table("measurements").insert({
                                "site_id": site_id,
                                "asset_id": asset_db_id,
                                "auditor_id": user_id,
                                "temperatura": temp,
                                "humedad": hum,
                                "resistance_value": val_res,
                                "static_field_value": val_volts,
                                "status_result": resultado,
                                "observaciones": obs
                            }).execute()
                            
                            st.success(t("audit", "msg_success"))
                            
                        except Exception as e:
                            st.error(f"Error al guardar medición: {e}")
                            
        else:
            # --- MODO INTEGRAL ---
            num_meds = st.number_input("Cantidad de Puntos a Medir", min_value=1, max_value=50, value=5)
            
            with st.form("form_audit_integral", clear_on_submit=False):
                c_amb1, c_amb2 = st.columns(2)
                temp = c_amb1.number_input(t("audit", "lbl_temp"), value=23.5, step=0.1)
                hum = c_amb2.number_input(t("audit", "lbl_hum"), value=45.0, step=1.0)
                st.divider()
                
                st.markdown("**Captura de Puntos de Prueba (Ohms)**")
                mediciones_dict = {}
                cols = st.columns(3)
                for i in range(num_meds):
                    col_idx = i % 3
                    val = cols[col_idx].number_input(f"Punto {i+1}", format="%.2e", min_value=0.0, step=1e5, key=f"med_int_{i}")
                    mediciones_dict[f"m{i+1}"] = val
                    
                obs = st.text_area("Observaciones")
                
                str_save_int = t("audit", "btn_save_integral") if t("audit", "btn_save_integral") != "[audit.btn_save_integral]" else "💾 Guardar y Generar Reporte"
                submitted = st.form_submit_button(str_save_int, type="primary", use_container_width=True)
                
                if submitted:
                    with st.spinner("Evaluando y guardando..."):
                        try:
                            # Calcular promedio de resistencia
                            valores_validos = [v for v in mediciones_dict.values() if v > 0]
                            promedio_res = sum(valores_validos) / len(valores_validos) if valores_validos else 0.0
                            
                            limite = 1e9 if asset_data.get("category", "") != "Maquinaria" else 1.0
                            resultado = "PASS" if promedio_res <= limite and promedio_res > 0 else "FAIL"
                            
                            # Insert en Base de Datos
                            meas_data = {
                                "site_id": site_id,
                                "asset_id": asset_db_id,
                                "auditor_id": user_id,
                                "temperatura": temp,
                                "humedad": hum,
                                "resistance_value": promedio_res,
                                "status_result": resultado,
                                "observaciones": obs,
                                "extra_data": mediciones_dict
                            }
                            
                            supabase.table("measurements").insert(meas_data).execute()
                            st.success("✅ Validación Integral guardada en base de datos.")
                            
                            # Generar Reporte HTML
                            auditor_name = st.session_state.get("usuario_nombre", "Auditor")
                            site_name = st.session_state.get("site_name", "Planta")
                            html_report = generate_esd_html_report(asset_data, meas_data, site_name, auditor_name)
                            
                            # Guardar HTML en session_state para mostrar el botón de descarga
                            st.session_state.last_report_html = html_report
                            st.session_state.last_report_id = asset_data.get("custom_id", "000")
                            
                        except Exception as e:
                            st.error(f"Error al guardar: {e}")
                            
            # Fuera del form, si existe un reporte recién generado, lo mostramos para descargar
            if st.session_state.get("last_report_html"):
                st.divider()
                st.markdown("### 📄 Reporte Generado")
                components.html(st.session_state.last_report_html, height=400, scrolling=True)
                
                st.download_button(
                    label="📥 Descargar HTML del Reporte",
                    data=st.session_state.last_report_html,
                    file_name=f"BCS-PV-{st.session_state.last_report_id}.html",
                    mime="text/html",
                    use_container_width=True,
                    type="primary"
                )
