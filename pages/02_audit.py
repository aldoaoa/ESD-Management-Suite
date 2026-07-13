# pages/02_audit.py

import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from core.i18n import t
from core.db import get_supabase_client

# ==========================================
# 1. BARRERA DE SEGURIDAD
# ==========================================
if st.session_state.get("is_read_only", True):
    st.warning(t("auth", "login_required"))
    st.stop()

supabase = get_supabase_client()
site_id = st.session_state.site_id
user_id = st.session_state.user_id

st.markdown(f"### {t('audit', 'title')}")

# ==========================================
# 2. CONTROL DE ESTADO (URL / ESCÃNER)
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
        
        # --- CÃ“DIGO HTML/JS DEL ESCÃNER QR ---
        html_code_qr = """
        <script src="https://unpkg.com/html5-qrcode"></script>
        <div id="reader_main" style="width:100%; max-width:500px; margin:auto; border-radius:10px; overflow:hidden; border: 2px solid #0052cc; background-color: #f9f9f9;"></div>
        <div style="text-align:center; margin-top:10px; display:flex; justify-content:center; gap:5px; flex-wrap:wrap;">
            <button type="button" id="cam_wide_main" style="padding:10px; background:#28a745; color:white; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">ðŸ“¸ LENTE ESTÃNDAR</button>
            <button type="button" id="cam_cycle_main" style="padding:10px; background:#555; color:white; border:none; border-radius:5px; font-weight:bold; cursor:pointer;">ðŸ”„ OTRA CÃMARA</button>
        </div>
        <p id="cam-status-main" style="text-align:center; color:#666; font-size: 14px; margin-top: 10px;">Buscando cÃ¡maras...</p>
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
                document.getElementById("cam-status-main").innerText = "Lente activo: " + (activeCam ? activeCam.label : "CÃ¡mara");
            }).catch(err => {
                document.getElementById("cam-status-main").innerText = "Error iniciando lente. Intenta 'Otra CÃ¡mara'.";
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
        }).catch(err => { document.getElementById("cam-status-main").innerText = "Permisos de cÃ¡mara denegados."; });
        </script>
        """
        components.html(html_code_qr, height=500) 
        
        # --- INPUT MANUAL ---
        id_manual = st.text_input(t("audit", "lbl_manual"), key="input_manual")
        if id_manual:
            st.query_params["qr_id"] = id_manual
            st.rerun()
            
    else:
        # --- EQUIPO ESCANEADO: BÃšSQUEDA EN BD ---
        c_info, c_btn = st.columns([0.7, 0.3])
        c_info.info(f"ðŸ” **ID:** {id_escaneado}")
        if c_btn.button(t("audit", "btn_close"), use_container_width=True):
            limpiar_url()
            st.rerun()
            
        id_limpio = str(id_escaneado).strip().upper()
        
        with st.spinner("Buscando activo..."):
            # ðŸ›¡ï¸ SEGURIDAD MULTI-TENANT: Buscamos el activo estrictamente en esta planta
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

        # --- 2. FORMULARIO DE CAPTURA RÃPIDA ---
        st.markdown(f"#### {t('audit', 'new_record')}")
        with st.form("form_audit_capture", clear_on_submit=True):
            
            c_amb1, c_amb2 = st.columns(2)
            temp = c_amb1.number_input(t("audit", "lbl_temp"), value=23.5, step=0.1)
            hum = c_amb2.number_input(t("audit", "lbl_hum"), value=45.0, step=1.0)
            
            st.divider()
            
            c_val1, c_val2 = st.columns(2)
            
            # DinÃ¡mica del formulario: Ajustamos el placeholder segÃºn si es Ionizador o no
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
                        # LÃ³gica de negocio (EvaluaciÃ³n de PASA / FALLA bÃ¡sica)
                        # Nota: En una versiÃ³n final, este lÃ­mite puede venir de la tabla assets o config.py
                        limite = 1e9 if asset_data.get("category", "") != "Maquinaria" else 1.0
                        resultado = "PASS"
                        
                        if val_res is not None and val_res > limite:
                            resultado = "FAIL"
                        if val_volts is not None and abs(val_volts) > 100:
                            resultado = "FAIL"

                        # ðŸ›¡ï¸ InserciÃ³n Multi-Tenant en historial de mediciones
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
                        st.error(f"Error al guardar mediciÃ³n: {e}")

