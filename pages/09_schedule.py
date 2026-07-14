# pages/09_schedule.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import base64
import time
from core.i18n import t
from core.db import get_supabase_client
from core.reports import generar_html_reporte_linea
from core.logger import log_event, log_error
from components.sidebar import render_sidebar, hide_sidebar

# Ocultar navegación nativa antes de evaluar accesos
hide_sidebar()

# ==========================================
# 1. BARRERA DE SEGURIDAD MULTI-TENANT
# ==========================================
if st.session_state.get("modo_lectura", True):
    st.warning(t("auth", "login_required"))
    st.stop()

render_sidebar()

supabase = get_supabase_client()
site_id = st.session_state.site_id

st.markdown(f"### {t('schedule', 'title')}")
st.caption(f"{t('schedule', 'subtitle')} - **{st.session_state.site_name}**")

tab_cronograma, tab_urgentes = st.tabs([
    t("schedule", "tab_general"), 
    t("schedule", "tab_urgents")
])

# --- PESTAÑA 1: CRONOGRAMA GENERAL ---
with tab_cronograma:
    st.info("Visualiza las fechas de medición y vencimiento de Equipos, Mobiliarios e Ionizadores combinados en la planta.")
    
    # 1. Cargar activos de la planta
    try:
        resp_assets = supabase.table("assets").select("*").eq("site_id", site_id).execute()
        df_assets = pd.DataFrame(resp_assets.data) if resp_assets.data else pd.DataFrame()
    except Exception as e:
        df_assets = pd.DataFrame()
        log_error("pages/09_schedule.py", "Error fetching assets for schedule", e)

    # 2. Cargar mediciones históricas
    try:
        resp_meas = supabase.table("measurements").select("*").eq("site_id", site_id).execute()
        df_meas = pd.DataFrame(resp_meas.data) if resp_meas.data else pd.DataFrame()
    except Exception as e:
        df_meas = pd.DataFrame()
        log_error("pages/09_schedule.py", "Error fetching measurements for schedule", e)

    # 3. Cargar tierras / conexiones (grounding_logs)
    try:
        resp_grounds = supabase.table("grounding_logs").select("*").eq("site_id", site_id).execute()
        df_grounds = pd.DataFrame(resp_grounds.data) if resp_grounds.data else pd.DataFrame()
    except Exception as e:
        df_grounds = pd.DataFrame()
        log_error("pages/09_schedule.py", "Error fetching grounding_logs for schedule", e)

    lista_registros = []

    # Procesar Activos y sus mediciones más recientes
    if not df_assets.empty:
        # Filtrar activos operativos
        df_assets_active = df_assets[df_assets['status'] == 'ACTIVE']
        
        # Obtener última medición por activo
        if not df_meas.empty:
            df_meas_sorted = df_meas.sort_values('measured_at', ascending=False)
            df_latest_meas = df_meas_sorted.drop_duplicates(subset=['asset_id'], keep='first')
        else:
            df_latest_meas = pd.DataFrame()

        for _, asset in df_assets_active.iterrows():
            last_meas = pd.DataFrame()
            if not df_latest_meas.empty:
                last_meas = df_latest_meas[df_latest_meas['asset_id'] == asset['id']]

            if not last_meas.empty:
                meas_row = last_meas.iloc[0]
                fecha_med = str(meas_row.get('measured_at', ''))[:10]
                estatus = str(meas_row.get('status_result', 'PENDIENTE'))
                
                # Calcular vencimiento
                try:
                    f_base = datetime.strptime(fecha_med, "%Y-%m-%d").date()
                    if asset['category'] == 'Ionizador':
                        fecha_prox = (f_base + relativedelta(months=3)).strftime("%Y-%m-%d")
                    else:
                        fecha_prox = (f_base + relativedelta(years=1)).strftime("%Y-%m-%d")
                except:
                    fecha_prox = "N/D"
            else:
                fecha_med = "N/D"
                fecha_prox = "N/D"
                estatus = "PENDIENTE"

            lista_registros.append({
                "Línea": str(asset.get('location', 'N/D')),
                "Categoría": str(asset.get('category', 'N/D')),
                "ID / Nombre": str(asset.get('custom_id', 'N/D')),
                "Clasificación": str(asset.get('classification', 'N/D')),
                "Última Medición": fecha_med,
                "Próximo Vencimiento": fecha_prox,
                "Estatus": estatus,
                "asset_uuid": asset['id'],
                "type": "asset"
            })

    # Procesar Infraestructura (Tierras y Conexiones)
    if not df_grounds.empty:
        df_grounds_latest = df_grounds.sort_values('measured_at', ascending=False).drop_duplicates(subset=['point_id'], keep='first')
        for _, ground in df_grounds_latest.iterrows():
            fecha_med = str(ground.get('measured_at', ''))[:10]
            try:
                f_base = datetime.strptime(fecha_med, "%Y-%m-%d").date()
                fecha_prox = (f_base + relativedelta(months=6)).strftime("%Y-%m-%d")
            except:
                fecha_prox = "N/D"

            lista_registros.append({
                "Línea": str(ground.get('location', 'N/D')),
                "Categoría": "Infraestructura (EPA)",
                "ID / Nombre": str(ground.get('point_id', 'N/D')),
                "Clasificación": str(ground.get('point_type', 'N/D')),
                "Última Medición": fecha_med,
                "Próximo Vencimiento": fecha_prox,
                "Estatus": str(ground.get('status_result', 'PENDIENTE')),
                "asset_uuid": None,
                "type": "ground"
            })

    df_schedule_full = pd.DataFrame(lista_registros)

    if not df_schedule_full.empty:
        df_schedule_full['Línea'] = df_schedule_full['Línea'].astype(str).str.strip().str.upper()
        lineas_disponibles = sorted([x for x in df_schedule_full['Línea'].unique() if x not in ['N/D', 'NAN', 'NONE', '']])
        
        c_filtro1, c_filtro2 = st.columns(2)
        linea_sel = c_filtro1.selectbox("📍 Selecciona la Línea / Ubicación:", ["Todas las Líneas"] + lineas_disponibles)
        categoria_sel = c_filtro2.selectbox("🏷️ Filtrar por Categoría:", ["Todas", "Maquinaria / Equipo", "Mobiliario", "Ionizador", "Piso", "Infraestructura (EPA)"])
        
        df_filtrado = df_schedule_full.copy()
        if linea_sel != "Todas las Líneas":
            df_filtrado = df_filtrado[df_filtrado['Línea'] == linea_sel]
        if categoria_sel != "Todas":
            df_filtrado = df_filtrado[df_filtrado['Categoría'].str.contains(categoria_sel, case=False, na=False)]
        
        df_filtrado['Fecha Orden'] = df_filtrado['Próximo Vencimiento'].replace('N/D', None)
        df_filtrado['Fecha Orden'] = pd.to_datetime(df_filtrado['Fecha Orden'], errors='coerce')
        df_filtrado = df_filtrado.sort_values(by=['Fecha Orden', 'Línea'], ascending=[True, True], na_position='last')
        
        # Guardar para reporte antes de agregar emojis
        df_reporte = df_filtrado.copy().drop(columns=['Fecha Orden', 'asset_uuid', 'type'])
        
        def add_emoji(val):
            val_str = str(val).upper()
            if 'VIGENTE' in val_str or 'PASS' in val_str: return f"🟢 {val}"
            if 'VENCIDO' in val_str or 'FAIL' in val_str: return f"🔴 {val}"
            if 'PENDIENTE' in val_str: return f"🟡 {val}"
            return val
            
        df_filtrado['Estatus'] = df_filtrado['Estatus'].apply(add_emoji)
        st.markdown(f"**Mostrando {len(df_filtrado)} registros:**")
        
        df_mostrar = df_filtrado.drop(columns=['Fecha Orden', 'asset_uuid', 'type'])
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
        
        # Formulario para reporte oficial
        if linea_sel != "Todas las Líneas" and not df_filtrado.empty:
            st.divider()
            st.markdown(f"#### 📄 Generar Reporte de Validación: `{linea_sel}`")
            with st.form("form_rep_linea"):
                col_r1, col_r2 = st.columns([1, 2])
                auditor_rep = col_r1.text_input("Auditor / Coordinador", value=st.session_state.usuario_nombre)
                comentarios_rep = col_r2.text_area("Observaciones Generales", placeholder="Ej: La línea cumple satisfactoriamente...")
                
                if st.form_submit_button("Generar Reporte Oficial", use_container_width=True):
                    with st.spinner("Generando documento..."):
                        try:
                            resp_log = supabase.table("log_reportes_linea").insert({
                                "linea_ubicacion": linea_sel, 
                                "auditor": auditor_rep, 
                                "comentarios": comentarios_rep
                            }).execute()
                            db_id_linea = resp_log.data[0]['id']
                            
                            html_rep_linea, año_rep = generar_html_reporte_linea(linea_sel, df_reporte, auditor_rep, comentarios_rep, db_id_linea)
                            b64_html = base64.b64encode(html_rep_linea.encode('utf-8')).decode('utf-8')
                            nombre_oficial = f"BCS-LV-{db_id_linea:03d}-{año_rep}"
                            
                            href = f'<a href="data:text/html;base64,{b64_html}" download="{nombre_oficial}.html" target="_blank" style="display: block; text-align: center; padding: 15px; background-color: #003366; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 10px; font-size: 16px;">📥 Descargar Reporte de Línea ({nombre_oficial})</a>'
                            st.markdown(href, unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"Error generando el reporte: {e}")
                            log_error("pages/09_schedule.py", "Error generating line validation report", e)
    else:
        st.warning("No hay registros disponibles para mostrar en el cronograma.")

# --- PESTAÑA 2: EDICIÓN DIRECTA ---
with tab_urgentes:
    st.markdown("#### 🚨 Mesa de Control y Actualización")
    filtro_urgentes = st.radio(
        "Selecciona el modo de visualización:", 
        ["🚨 Solo Vencidos y Pendientes (Acción Inmediata)", "⚠️ Próximos a Vencer (7 días)"],
        horizontal=True
    )
    st.caption("Introduce la nueva lectura en la tabla interactiva y presiona Guardar. El sistema recalculará los estatus de verificación.")

    hoy = datetime.today().date()
    limite_alerta = hoy + timedelta(days=7) if "Próximos" in filtro_urgentes else hoy

    lista_urgentes = []
    
    # Mapear desde df_schedule_full
    if not df_schedule_full.empty:
        for _, r in df_schedule_full.iterrows():
            f_prox_str = r['Próximo Vencimiento']
            est = r['Estatus'].upper()
            es_nulo = f_prox_str == "N/D" or est in ["PENDIENTE", ""]
            
            vencido_por_fecha = False
            f_prox_date = None
            if f_prox_str != "N/D":
                try:
                    f_prox_date = datetime.strptime(f_prox_str, "%Y-%m-%d").date()
                    if f_prox_date <= limite_alerta:
                        vencido_por_fecha = True
                except:
                    pass

            if est in ["VENCIDO", "PENDIENTE", "FAIL"] or es_nulo or vencido_por_fecha:
                lista_urgentes.append({
                    "type": r['type'],
                    "asset_uuid": r['asset_uuid'],
                    "ID Activo": r['ID / Nombre'],
                    "Categoría": r['Categoría'],
                    "Clasificación": r['Clasificación'],
                    "Ubicación": r['Línea'],
                    "Vencimiento": f_prox_str,
                    "_fecha_sort": f_prox_date if f_prox_date else datetime.min.date(),
                    "Nueva Resistencia (Ω)": "",
                    "Nuevo Voltaje (V)": 0.0,
                    "Fecha Medición": hoy.strftime("%Y-%m-%d"),
                    "Notas": ""
                })

    if not lista_urgentes:
        st.success("🎉 ¡Excelente! No hay activos urgentes en este filtro.")
    else:
        df_urgentes_edit = pd.DataFrame(lista_urgentes).sort_values('_fecha_sort')
        
        df_editor = st.data_editor(
            df_urgentes_edit,
            column_config={
                "type": None,
                "asset_uuid": None,
                "_fecha_sort": None,
                "ID Activo": st.column_config.TextColumn("ID Activo", disabled=True),
                "Categoría": st.column_config.TextColumn("Categoría", disabled=True),
                "Clasificación": st.column_config.TextColumn("Clasificación", disabled=True),
                "Ubicación": st.column_config.TextColumn("Ubicación", disabled=True),
                "Vencimiento": st.column_config.TextColumn("Vencimiento", disabled=True),
                "Nueva Resistencia (Ω)": st.column_config.TextColumn("Resistencia (Ω) / Descarga", help="Ej: 1e9, 5e6, 12.5"),
                "Nuevo Voltaje (V)": st.column_config.NumberColumn("Voltaje / Balance (V)", format="%.1f"),
                "Fecha Medición": st.column_config.TextColumn("Fecha (YYYY-MM-DD)"),
                "Notas": st.column_config.TextColumn("Comentarios")
            },
            hide_index=True,
            use_container_width=True,
            key="live_editor_urgentes"
        )
        
        if st.button("💾 Guardar Mediciones en Base de Datos", type="primary", use_container_width=True):
            cambios = st.session_state.live_editor_urgentes.get("edited_rows", {})
            if not cambios:
                st.info("No hay cambios para guardar.")
            else:
                with st.spinner("Guardando en Supabase..."):
                    actualizaciones = 0
                    errores = 0
                    
                    for idx_str, edits in cambios.items():
                        idx = int(idx_str)
                        fila = df_urgentes_edit.iloc[idx]
                        
                        id_activo = fila["ID Activo"]
                        tipo_activo = fila["type"]
                        asset_uuid = fila["asset_uuid"]
                        
                        res_val = edits.get("Nueva Resistencia (Ω)", "")
                        volt_val = float(edits.get("Nuevo Voltaje (V)", 0.0))
                        fecha_med = edits.get("Fecha Medición", hoy.strftime("%Y-%m-%d"))
                        notas = edits.get("Notas", "")
                        
                        if not res_val.strip() and volt_val == 0.0:
                            continue  # Saltar celdas vacías
                        
                        try:
                            val_r_float = float(res_val) if res_val.strip() else None
                        except ValueError:
                            st.error(f"Valor de resistencia inválido para {id_activo}.")
                            errores += 1
                            continue

                        # Evaluar normativas
                        estatus_calc = "PASS"
                        if val_r_float is not None:
                            if fila["Categoría"] == "Maquinaria":
                                estatus_calc = "PASS" if val_r_float <= 1.0 else "FAIL"
                            elif fila["Categoría"] == "Ionizador":
                                # Ionizadores usan tiempo de descarga y balance, no resistencia pura, pero evaluamos
                                estatus_calc = "PASS" if val_r_float < 10.0 else "FAIL"
                            else:
                                estatus_calc = "PASS" if val_r_float < 1.0e9 else "FAIL"

                        try:
                            if tipo_activo == "asset":
                                # Insertar medición en tabla measurements
                                supabase.table("measurements").insert({
                                    "site_id": site_id,
                                    "asset_id": asset_uuid,
                                    "auditor_id": st.session_state.user_id,
                                    "resistance_value": val_r_float,
                                    "static_field_value": volt_val if volt_val != 0.0 else None,
                                    "status_result": estatus_calc,
                                    "temperatura": "23.5",
                                    "humedad": "45.0",
                                    "observaciones": notas,
                                    "measured_at": fecha_med + "T12:00:00Z"
                                }).execute()
                                actualizaciones += 1
                            else:
                                # Insertar en grounding_logs
                                limit_ground = 25.0 if fila["Clasificación"] == "Auxiliary Ground" else 2.0
                                est_ground = "PASS" if val_r_float and val_r_float < limit_ground else "FAIL"
                                
                                supabase.table("grounding_logs").insert({
                                    "site_id": site_id,
                                    "location": fila["Ubicación"],
                                    "point_id": id_activo,
                                    "point_type": fila["Clasificación"],
                                    "resistance_ohms": val_r_float,
                                    "status_result": est_ground,
                                    "auditor_id": st.session_state.user_id,
                                    "measured_at": fecha_med + "T12:00:00Z"
                                }).execute()
                                actualizaciones += 1
                        except Exception as e:
                            st.error(f"Error guardando {id_activo}: {e}")
                            log_error("pages/09_schedule.py", f"Error saving direct edit measurement for {id_activo}", e)
                            errores += 1
                            
                    if actualizaciones > 0 and errores == 0:
                        st.success(f"🎉 ¡{actualizaciones} mediciones guardadas exitosamente!")
                        st.cache_data.clear()
                        time.sleep(1.5)
                        st.rerun()
