# pages/08_sensibilidad.py
import streamlit as st
import pandas as pd
import plotly.express as px
from core.i18n import t
from core.db import get_supabase_client
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

st.markdown(f"### {t('sensitivity', 'title')}")
st.caption(f"{t('sensitivity', 'subtitle')} - **{st.session_state.site_name}**")

tab_overview_sen, tab_consulta, tab_importar = st.tabs([
    t("sensitivity", "tab_overview"), 
    t("sensitivity", "tab_query"), 
    t("sensitivity", "tab_import")
])

# --- PESTAÑA: OVERVIEW GLOBAL ---
with tab_overview_sen:
    st.markdown("#### 🌍 Resumen Global de Sensibilidad en Planta")
    
    try:
        resp_cat_ov = supabase.table("catalogo_sensibilidad").select("id, nombre_producto, numero_parte, cliente, nivel_sensibilidad").execute()
        df_cat_ov = pd.DataFrame(resp_cat_ov.data)
        
        resp_comp_ov = supabase.table("componentes_sensibilidad").select("id_producto, esd_hbm, esd_cdm").execute()
        df_comp_ov = pd.DataFrame(resp_comp_ov.data)
        
        if not df_cat_ov.empty and not df_comp_ov.empty:
            df_comp_ov['esd_hbm_num'] = pd.to_numeric(df_comp_ov['esd_hbm'].replace('-', pd.NA), errors='coerce')
            df_comp_ov['esd_cdm_num'] = pd.to_numeric(df_comp_ov['esd_cdm'].replace('-', pd.NA), errors='coerce')
            
            minimos_por_producto = df_comp_ov.groupby('id_producto').agg({
                'esd_hbm_num': 'min', 
                'esd_cdm_num': 'min'
            }).reset_index()
            
            df_consolidado = pd.merge(df_cat_ov, minimos_por_producto, left_on='id', right_on='id_producto', how='inner')
            
            if not df_consolidado.empty:
                min_hbm_global = df_consolidado['esd_hbm_num'].min()
                min_cdm_global = df_consolidado['esd_cdm_num'].min()
                
                df_consolidado['min_absoluto'] = df_consolidado[['esd_hbm_num', 'esd_cdm_num']].min(axis=1)
                idx_mas_sensible = df_consolidado['min_absoluto'].idxmin()
                proyecto_critico = df_consolidado.loc[idx_mas_sensible]
                
                st.markdown("##### 🚨 Proyecto Más Crítico (Mayor Riesgo ESD)")
                c_crit1, c_crit2, c_crit3 = st.columns(3)
                
                nombre_critico = f"{proyecto_critico['nombre_producto']} ({proyecto_critico['cliente']})"
                voltaje_critico = f"{proyecto_critico['min_absoluto']:g} V" if pd.notna(proyecto_critico['min_absoluto']) else "N/D"
                
                c_crit1.metric("Proyecto Más Sensible", nombre_critico, delta="Requiere máxima atención", delta_color="inverse")
                c_crit2.metric("Mínimo Global HBM", f"{min_hbm_global:g} V" if pd.notna(min_hbm_global) else "N/D")
                c_crit3.metric("Mínimo Global CDM", f"{min_cdm_global:g} V" if pd.notna(min_cdm_global) else "N/D")
                
                st.divider()
                
                st.markdown("##### 🏢 Sensibilidad Mínima por Cliente")
                df_validos = df_consolidado.dropna(subset=['min_absoluto'])
                
                if not df_validos.empty:
                    idx_min_por_cliente = df_validos.groupby('cliente')['min_absoluto'].idxmin()
                    resumen_cliente = df_validos.loc[idx_min_por_cliente, ['cliente', 'nombre_producto', 'esd_hbm_num', 'esd_cdm_num']].copy()
                    resumen_cliente.columns = ['Cliente', 'Producto Más Crítico', 'Mínimo HBM (V)', 'Mínimo CDM (V)']
                    resumen_cliente['Mínimo HBM (V)'] = resumen_cliente['Mínimo HBM (V)'].apply(lambda x: f"{x:g}" if pd.notna(x) else "N/D")
                    resumen_cliente['Mínimo CDM (V)'] = resumen_cliente['Mínimo CDM (V)'].apply(lambda x: f"{x:g}" if pd.notna(x) else "N/D")
                    
                    st.dataframe(resumen_cliente, use_container_width=True, hide_index=True)
                else:
                    st.info("No hay datos suficientes para generar el resumen por cliente.")
                
                st.markdown("##### 📊 Comparativa Visual de Riesgo (Voltaje Mínimo Absoluto por Producto)")
                df_grafica = df_consolidado.dropna(subset=['min_absoluto']).copy()
                if not df_grafica.empty:
                    df_grafica = df_grafica.sort_values('min_absoluto')
                    fig = px.bar(
                        df_grafica, 
                        x='nombre_producto', 
                        y='min_absoluto', 
                        color='cliente',
                        labels={'nombre_producto': 'Producto', 'min_absoluto': 'Límite de Soporte (Volts)', 'cliente': 'Cliente'},
                        text_auto='.0f'
                    )
                    fig.update_traces(textposition='outside')
                    fig.update_layout(yaxis_title="Volts (Menor = Más Crítico)", xaxis_title="")
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No se pudieron consolidar los datos de catálogo y componentes.")
        else:
            st.info("Aún no hay suficientes datos procesados para generar el Overview.")
    except Exception as e:
        st.error(f"Error generando el Overview: {e}")
        log_error("pages/08_sensibilidad.py", "Error compiling global overview data", e)

# --- PESTAÑA: CONSULTA Y EXPORTACIÓN ---
with tab_consulta:
    try:
        resp_cat = supabase.table("catalogo_sensibilidad").select("*").execute()
        df_cat = pd.DataFrame(resp_cat.data)
    except Exception as e:
        df_cat = pd.DataFrame()
        st.error(f"Error conectando a la base de datos: {e}")
        log_error("pages/08_sensibilidad.py", "Error fetching catalogo_sensibilidad", e)

    if not df_cat.empty:
        c_filtro1, c_filtro2 = st.columns(2)
        clientes_disp = sorted(df_cat['cliente'].dropna().unique())
        cliente_sel = c_filtro1.selectbox("🏢 Selecciona el Cliente:", ["Todos"] + list(clientes_disp))
        
        df_filtrado_cli = df_cat if cliente_sel == "Todos" else df_cat[df_cat['cliente'] == cliente_sel]
        
        opciones_prod = {row['id']: f"{row['nombre_producto']} (PN: {row['numero_parte']})" for _, row in df_filtrado_cli.iterrows()}
        
        if opciones_prod:
            prod_id_sel = c_filtro2.selectbox("📦 Selecciona el Producto:", options=list(opciones_prod.keys()), format_func=lambda x: opciones_prod[x])
            
            prod_info = df_filtrado_cli[df_filtrado_cli['id'] == prod_id_sel].iloc[0]
            numero_parte = str(prod_info['numero_parte']).strip()
            nombre_prod = str(prod_info['nombre_producto']).strip()
            
            id_reporte_unico = f"BCS-SEN-{numero_parte.replace(' ', '')}-{nombre_prod.replace(' ', '_')}".upper()
            
            try:
                resp_comp = supabase.table("componentes_sensibilidad").select("*").eq("id_producto", prod_id_sel).execute()
                df_comp = pd.DataFrame(resp_comp.data)
            except Exception as e:
                df_comp = pd.DataFrame()
                log_error("pages/08_sensibilidad.py", "Error fetching components for product selection", e)
            
            if not df_comp.empty:
                df_comp['esd_hbm_num'] = pd.to_numeric(df_comp['esd_hbm'].replace('-', pd.NA), errors='coerce')
                df_comp['esd_cdm_num'] = pd.to_numeric(df_comp['esd_cdm'].replace('-', pd.NA), errors='coerce')
                
                min_hbm = df_comp['esd_hbm_num'].min()
                min_cdm = df_comp['esd_cdm_num'].min()
                
                comp_hbm = df_comp.loc[df_comp['esd_hbm_num'] == min_hbm, 'part_number'].iloc[0] if pd.notna(min_hbm) else "N/D"
                comp_cdm = df_comp.loc[df_comp['esd_cdm_num'] == min_cdm, 'part_number'].iloc[0] if pd.notna(min_cdm) else "N/D"

                st.markdown(f"#### 📄 ID Reporte: `{id_reporte_unico}`")
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Cliente", prod_info['cliente'])
                m2.metric("Nivel Sensibilidad", prod_info['nivel_sensibilidad'])
                m3.metric("Voltaje Mín. HBM", f"{min_hbm:g} V" if pd.notna(min_hbm) else "N/D", comp_hbm, delta_color="off")
                m4.metric("Voltaje Mín. CDM", f"{min_cdm:g} V" if pd.notna(min_cdm) else "N/D", comp_cdm, delta_color="off")
                
                st.markdown("##### 🧩 Desglose de Componentes")
                df_mostrar = df_comp[['part_number', 'descripcion', 'ref_designator', 'qty', 'esd_cdm', 'esd_hbm', 'comentarios']].copy()
                df_mostrar.columns = ['Part Number', 'Descripción', 'Ref Designator', 'Qty', 'CDM (V)', 'HBM (V)', 'Comentarios']
                st.dataframe(df_mostrar.fillna("-"), use_container_width=True, hide_index=True)

                csv_sen = df_mostrar.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Descargar Análisis en CSV",
                    data=csv_sen,
                    file_name=f"{id_reporte_unico}.csv",
                    mime="text/csv",
                    type="primary"
                )
            else:
                st.warning("No hay componentes registrados para este producto.")
        else:
            st.warning("No hay productos para este cliente.")
    else:
        st.info("Aún no hay reportes de sensibilidad en el sistema. Utiliza la pestaña 'Importar Histórico'.")

# --- PESTAÑA: IMPORTACIÓN ---
with tab_importar:
    st.markdown("#### 📂 Cargar Archivos de Sensibilidad")
    st.write("Sube uno o varios archivos CSV o Excel. El sistema buscará la tabla automáticamente a partir de la cabecera 'Part Number'.")
    
    archivos_sen = st.file_uploader("Select files", type=["csv", "xlsx"], accept_multiple_files=True, key="sens_uploader")
    
    if archivos_sen:
        for idx, archivo_sen in enumerate(archivos_sen):
            with st.expander(f"📄 Procesando: {archivo_sen.name}", expanded=True):
                try:
                    df_raw = pd.read_csv(archivo_sen, header=None) if archivo_sen.name.endswith('.csv') else pd.read_excel(archivo_sen, header=None)
                    
                    fila_inicio = None
                    for i in range(min(20, len(df_raw))):
                        if df_raw.iloc[i].astype(str).str.contains("Part Number", case=False, na=False).any():
                            fila_inicio = i
                            break
                    
                    if fila_inicio is not None:
                        df_tabla = df_raw.iloc[fila_inicio+1:].copy()
                        columnas_texto = [str(c) for c in df_raw.iloc[fila_inicio].tolist()]
                        df_tabla.columns = columnas_texto
                        
                        col_pn_real = next((c for c in df_tabla.columns if 'part number' in c.lower()), df_tabla.columns[1])
                        df_tabla = df_tabla.dropna(subset=[col_pn_real])
                        df_tabla = df_tabla[df_tabla[col_pn_real].astype(str).str.strip() != '']
                        df_tabla = df_tabla[df_tabla[col_pn_real].astype(str).str.strip().str.lower() != 'nan']
                        
                        st.success(f"✅ Tabla detectada ({len(df_tabla)} componentes encontrados).")
                        
                        with st.form(f"form_guardar_sensibilidad_{idx}"):
                            st.markdown("##### 📝 Confirma los Datos Generales del Producto")
                            sug_pn = df_raw.iloc[4, 4] if len(df_raw) > 4 and len(df_raw.columns) > 4 else ""
                            sug_cliente = df_raw.iloc[5, 8] if len(df_raw) > 5 and len(df_raw.columns) > 8 else ""
                            sug_prod = df_raw.iloc[7, 4] if len(df_raw) > 7 and len(df_raw.columns) > 4 else "" 
                            sug_lvl = df_raw.iloc[7, 8] if len(df_raw) > 7 and len(df_raw.columns) > 8 else ""

                            col_f1, col_f2 = st.columns(2)
                            num_parte_imp = col_f1.text_input("Número de Parte", value=str(sug_pn).replace('nan','').strip())
                            nom_prod_imp = col_f2.text_input("Nombre del Producto", value=str(sug_prod).replace('nan','').strip())
                            
                            col_f3, col_f4 = st.columns(2)
                            cliente_imp = col_f3.text_input("Cliente", value=str(sug_cliente).replace('nan','').strip())
                            nivel_imp = col_f4.text_input("Nivel de Sensibilidad", value=str(sug_lvl).replace('nan','').strip())

                            if st.form_submit_button("💾 Guardar Reporte en Base de Datos", use_container_width=True):
                                if num_parte_imp and nom_prod_imp and cliente_imp:
                                    with st.spinner("Registrando producto y componentes..."):
                                        try:
                                            resp_ins_prod = supabase.table("catalogo_sensibilidad").insert({
                                                "numero_parte": num_parte_imp.upper(),
                                                "nombre_producto": nom_prod_imp.upper(),
                                                "cliente": cliente_imp.upper(),
                                                "nivel_sensibilidad": nivel_imp
                                            }).execute()
                                            
                                            id_nuevo_prod = resp_ins_prod.data[0]['id']
                                            
                                            componentes_a_insertar = []
                                            cols = df_tabla.columns.tolist()
                                            pn_col = next((c for c in cols if 'part number' in c.lower()), cols[0])
                                            desc_col = next((c for c in cols if 'description' in c.lower()), cols[1])
                                            ref_col = next((c for c in cols if 'ref' in c.lower()), cols[3] if len(cols)>3 else None)
                                            qty_col = next((c for c in cols if 'qty' in c.lower()), cols[4] if len(cols)>4 else None)
                                            cdm_col = next((c for c in cols if 'cdm' in c.lower()), cols[5] if len(cols)>5 else None)
                                            hbm_col = next((c for c in cols if 'hbm' in c.lower()), cols[6] if len(cols)>6 else None)
                                            com_col = next((c for c in cols if 'comentario' in c.lower()), cols[7] if len(cols)>7 else None)

                                            for _, fila in df_tabla.iterrows():
                                                val_cdm = str(fila[cdm_col]) if cdm_col and pd.notna(fila[cdm_col]) else "-"
                                                val_hbm = str(fila[hbm_col]) if hbm_col and pd.notna(fila[hbm_col]) else "-"
                                                
                                                componentes_a_insertar.append({
                                                    "id_producto": id_nuevo_prod,
                                                    "part_number": str(fila[pn_col]) if pd.notna(fila[pn_col]) else "N/D",
                                                    "descripcion": str(fila[desc_col]) if pd.notna(fila[desc_col]) else "N/D",
                                                    "ref_designator": str(fila[ref_col]) if ref_col and pd.notna(fila[ref_col]) else "",
                                                    "qty": int(fila[qty_col]) if qty_col and pd.notna(fila[qty_col]) and str(fila[qty_col]).isnumeric() else 1,
                                                    "esd_cdm": val_cdm,
                                                    "esd_hbm": val_hbm,
                                                    "comentarios": str(fila[com_col]) if com_col and pd.notna(fila[com_col]) else ""
                                                })
                                            
                                            supabase.table("componentes_sensibilidad").insert(componentes_a_insertar).execute()
                                            
                                            st.success(f"✅ ¡Producto {nom_prod_imp} guardado con éxito!")
                                            time.sleep(1.5)
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error guardando producto en base de datos: {e}")
                                            log_error("pages/08_sensibilidad.py", "Error inserting sensitivity records", e)
                                else:
                                    st.error("Por favor completa Número de Parte, Nombre y Cliente.")
                    else:
                        st.error("❌ No se encontró la cabecera 'Part Number' en este archivo.")
                except Exception as e:
                    st.error(f"Error: {e}")
