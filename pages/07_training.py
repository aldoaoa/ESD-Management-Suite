# pages/07_training.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
import time
from core.i18n import t
from core.db import get_supabase_client
from core.logger import log_event, log_error
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

st.markdown(f"### {t('training', 'title')}")
st.caption(f"{t('training', 'subtitle')} - **{st.session_state.site_name}**")

tab_dash, tab_historico, tab_semanal, tab_auditoria = st.tabs([
    t("training", "tab_dash"), 
    t("training", "tab_historical"), 
    t("training", "tab_weekly"),
    t("training", "tab_audit")
])

# --- PESTAÑA 1: DASHBOARD Y ANÁLISIS ---
with tab_dash:
    st.markdown("#### 📊 Dashboard de Certificación y Cumplimiento ESD")
    st.write("Monitoreo en tiempo real de vigencias. El sistema calcula los vencimientos **exclusivamente** a partir de la última evaluación del personal activo.")
    
    hoy = datetime.today().date()
    limite_365 = hoy + timedelta(days=365)
    
    primer_dia_mes = hoy.replace(day=1)
    if hoy.month == 12:
        ultimo_dia_mes = hoy.replace(year=hoy.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        ultimo_dia_mes = hoy.replace(month=hoy.month + 1, day=1) - timedelta(days=1)

    try:
        # Cargar padrón maestro filtrado por site_id para seguridad multi-tenant
        resp_maestro = supabase.table("empleados_batas").select("num_empleado, nombre, fecha_ingreso, fecha_ultimo_entrenamiento, fecha_proximo_entrenamiento").eq("estatus_empleado", "Activo").eq("site_id", site_id).execute()
        df_maestro = pd.DataFrame(resp_maestro.data)
    except Exception as e:
        df_maestro = pd.DataFrame()
        st.error(f"Error al conectar con la base maestra de personal: {e}")
        log_error("pages/07_training.py", "Error fetching empleados_batas", e)

    # Cargar historial completo de exámenes
    try:
        resp_todo_train = supabase.table("entrenamientos_esd").select("num_empleado, fecha_entrenamiento, calificacion_total, detalle_respuestas").execute()
        df_todo_train = pd.DataFrame(resp_todo_train.data)
    except Exception as e:
        df_todo_train = pd.DataFrame()
        log_error("pages/07_training.py", "Error fetching entrenamientos_esd", e)

    if not df_maestro.empty:
        df_maestro['num_empleado'] = df_maestro['num_empleado'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
        df_maestro = df_maestro.drop_duplicates(subset=['num_empleado'], keep='first')
        
        df_maestro['fecha_entrenamiento_oficial'] = pd.to_datetime(df_maestro['fecha_ultimo_entrenamiento'], errors='coerce').dt.date
        df_maestro['fecha_proximo'] = pd.to_datetime(df_maestro['fecha_proximo_entrenamiento'], errors='coerce').dt.date
        
        if not df_todo_train.empty:
            df_todo_train['num_empleado'] = df_todo_train['num_empleado'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
            df_todo_train['fecha_entrenamiento'] = pd.to_datetime(df_todo_train['fecha_entrenamiento'], errors='coerce')
            
            df_recientes = df_todo_train.sort_values('fecha_entrenamiento', ascending=False).drop_duplicates(subset=['num_empleado'], keep='first')
            df_recientes = df_recientes[['num_empleado', 'fecha_entrenamiento', 'calificacion_total', 'detalle_respuestas']]
        else:
            df_recientes = pd.DataFrame(columns=['num_empleado', 'fecha_entrenamiento', 'calificacion_total', 'detalle_respuestas'])

        # Unir padrón maestro con su última calificación
        df_merged = pd.merge(df_maestro, df_recientes, on='num_empleado', how='left')
        
        # Auto-sanidad de datos
        if 'fecha_entrenamiento' in df_merged.columns:
            df_merged['ingreso_dt'] = pd.to_datetime(df_merged['fecha_ingreso'], errors='coerce')
            f_oficial_dt = pd.to_datetime(df_merged['fecha_entrenamiento_oficial'], errors='coerce')
            
            cond1 = df_merged['fecha_entrenamiento_oficial'].isna() & df_merged['fecha_entrenamiento'].notna()
            cond2 = df_merged['fecha_entrenamiento'].notna() & f_oficial_dt.notna() & (f_oficial_dt.dt.date < df_merged['fecha_entrenamiento'].dt.date)
            mask_rescate = cond1 | cond2
            mask_valida = df_merged['ingreso_dt'].isna() | (df_merged['fecha_entrenamiento'] >= df_merged['ingreso_dt'])
            mask_rescate = mask_rescate & mask_valida

            if mask_rescate.any():
                df_merged.loc[mask_rescate, 'fecha_entrenamiento_oficial'] = df_merged.loc[mask_rescate, 'fecha_entrenamiento'].dt.date
                df_merged.loc[mask_rescate, 'fecha_proximo'] = (df_merged.loc[mask_rescate, 'fecha_entrenamiento'] + pd.DateOffset(years=1)).dt.date
        
        # Calcular nota real base 10
        def calcular_nota_real(row):
            detalle = row.get('detalle_respuestas', {})
            if isinstance(detalle, dict) and len(detalle) > 0:
                total_r = len(detalle)
                aciertos = sum([1.0 for v in detalle.values() if float(v) > 0])
                return round((aciertos / total_r) * 10.0, 2)
            else:
                try:
                    return min(float(row['calificacion_total']), 10.0)
                except:
                    return 0.0
                    
        df_merged['nota_real_base_10'] = df_merged.apply(calcular_nota_real, axis=1)

        # Segmentación para métricas
        mask_sin_vigencia = df_merged['fecha_proximo'].isna() | (df_merged['fecha_proximo'] < hoy)
        df_sin_vigencia = df_merged[mask_sin_vigencia]

        mask_proximos_365 = (df_merged['fecha_proximo'] >= hoy) & (df_merged['fecha_proximo'] <= limite_365)
        df_vencen_anio = df_merged[mask_proximos_365]

        mask_mes = (df_merged['fecha_proximo'] >= hoy) & (df_merged['fecha_proximo'] <= ultimo_dia_mes)
        df_vencen_mes = df_merged[mask_mes]

        mask_tiene_examen = df_merged['fecha_entrenamiento_oficial'].notna()
        df_bajos = df_merged[mask_tiene_examen & (df_merged['nota_real_base_10'] <= 7.0)]

        # KPI Cards
        c_kpi1, c_kpi2, c_kpi3, c_kpi4 = st.columns(4)
        c_kpi1.metric("🚨 Sin Vigencia / Vencidos", len(df_sin_vigencia), delta="Acción Requerida", delta_color="inverse" if len(df_sin_vigencia) > 0 else "normal")
        c_kpi2.metric("📌 Vencen este Mes", len(df_vencen_mes), delta=f"Límite: {ultimo_dia_mes.strftime('%d-%b')}")
        c_kpi3.metric("📅 Proyección 365", len(df_vencen_anio), delta="Próximos 12 Meses", delta_color="off")
        c_kpi4.metric("⚠️ Notas ≤ 80%", len(df_bajos), delta="Requieren Capacitación", delta_color="inverse" if len(df_bajos) > 0 else "normal")

        st.divider()

        # Tablas Operacionales
        col_tablas1, col_tablas2 = st.columns(2)
        
        with col_tablas1:
            st.markdown("##### 🚨 Personal SIN Entrenamiento Vigente")
            if not df_sin_vigencia.empty:
                df_sin_vigencia_show = df_sin_vigencia[['num_empleado', 'nombre', 'fecha_proximo']].copy()
                df_sin_vigencia_show['fecha_proximo'] = df_sin_vigencia_show['fecha_proximo'].fillna("Sin Registro / Nunca Evaluado")
                df_sin_vigencia_show.columns = ['No. Empleado', 'Nombre', 'Estatus Vigencia']
                st.dataframe(df_sin_vigencia_show, use_container_width=True, hide_index=True)
            else:
                st.success("🎉 Óptimo: Todo el personal activo cuenta con entrenamiento vigente.")

            st.markdown("##### 🔴 Notas Críticas Activas (≤ 80%)")
            if not df_bajos.empty:
                df_bajos_show = df_bajos[['num_empleado', 'nombre', 'nota_real_base_10', 'fecha_entrenamiento_oficial']].copy()
                df_bajos_show['fecha_entrenamiento_oficial'] = pd.to_datetime(df_bajos_show['fecha_entrenamiento_oficial']).dt.strftime('%d-%b-%Y')
                df_bajos_show.columns = ['No. Empleado', 'Nombre', 'Calificación Real', 'Último Examen']
                st.dataframe(df_bajos_show, use_container_width=True, hide_index=True)
            else:
                st.success("🎉 Ningún usuario activo tiene calificación reprobatoria en su evaluación más reciente.")

        with col_tablas2:
            st.markdown("##### 📅 Cronograma de Reentrenamientos")
            opciones_tiempo = {
                "Próximo Mes": 1, 
                "Próximos 3 Meses": 3, 
                "Próximos 6 Meses": 6, 
                "Próximos 12 Meses": 12
            }
            filtro_meses = st.selectbox("⏳ Rango de proyección:", options=list(opciones_tiempo.keys()), index=3)
            
            meses_delta = opciones_tiempo[filtro_meses]
            limite_dinamico = hoy + relativedelta(months=meses_delta)
            
            mask_dinamica = (df_merged['fecha_proximo'] >= hoy) & (df_merged['fecha_proximo'] <= limite_dinamico)
            df_vencen_dinamico = df_merged[mask_dinamica]

            if not df_vencen_dinamico.empty:
                df_vencen_show = df_vencen_dinamico[['num_empleado', 'nombre', 'fecha_proximo']].copy()
                df_vencen_show = df_vencen_show.sort_values('fecha_proximo')
                df_vencen_show.columns = ['No. Empleado', 'Nombre', 'Próximo Reentrenamiento']
                
                st.dataframe(df_vencen_show, use_container_width=True, hide_index=True)
                st.caption(f"Mostrando {len(df_vencen_show)} vencimientos proyectados hasta el {limite_dinamico.strftime('%d-%b-%Y')}.")
            else:
                st.info(f"No hay reentrenamientos proyectados para el rango de '{filtro_meses}'.")

        # Resumen Semanal
        st.divider()
        st.markdown("#### 📅 Resumen de Calificaciones por Semana")
        st.caption("Filtra por rango de fechas para visualizar la distribución y el porcentaje de aprobación semanal.")
        
        c_f1, c_f2 = st.columns(2)
        fecha_inicio_filtro = c_f1.date_input("Fecha de Inicio", date(hoy.year, 1, 1))
        fecha_fin_filtro = c_f2.date_input("Fecha de Fin", hoy)

        if not df_todo_train.empty:
            df_semanal = df_todo_train.copy()
            df_semanal['fecha_entrenamiento'] = pd.to_datetime(df_semanal['fecha_entrenamiento'], errors='coerce')
            
            # Filtrar por el rango de fechas seleccionado
            mask_fechas = (df_semanal['fecha_entrenamiento'].dt.date >= fecha_inicio_filtro) & (df_semanal['fecha_entrenamiento'].dt.date <= fecha_fin_filtro)
            df_semanal = df_semanal[mask_fechas]

            # Cruzar con df_maestro para que solo muestre datos del site activo
            df_semanal = df_semanal[df_semanal['num_empleado'].isin(df_maestro['num_empleado'])]

            if not df_semanal.empty:
                df_semanal['Nota'] = df_semanal.apply(calcular_nota_real, axis=1)
                df_semanal['Mes'] = df_semanal['fecha_entrenamiento'].dt.month
                df_semanal['Semana'] = "WK " + df_semanal['fecha_entrenamiento'].dt.isocalendar().week.astype(str)

                df_semanal['Reprobados'] = (df_semanal['Nota'] < 8.0).astype(int)
                df_semanal['Calif_8'] = ((df_semanal['Nota'] >= 8.0) & (df_semanal['Nota'] < 9.0)).astype(int)
                df_semanal['Calif_9'] = ((df_semanal['Nota'] >= 9.0) & (df_semanal['Nota'] < 10.0)).astype(int)
                df_semanal['Calif_10'] = (df_semanal['Nota'] >= 10.0).astype(int)

                agrupado = df_semanal.groupby(['Mes', 'Semana']).agg(
                    Examenes_aplicados=('num_empleado', 'count'),
                    No_aprobados=('Reprobados', 'sum'),
                    Calif_8=('Calif_8', 'sum'),
                    Calif_9=('Calif_9', 'sum'),
                    Calif_10=('Calif_10', 'sum')
                ).reset_index()

                agrupado['Aprobación de examenes %'] = agrupado.apply(
                    lambda x: round((x['Examenes_aplicados'] - x['No_aprobados']) / x['Examenes_aplicados'] * 100, 2) if x['Examenes_aplicados'] > 0 else 0.0, 
                    axis=1
                )

                agrupado.columns = ['Mes', 'Semana', 'Exámenes aplicados', 'Exámenes no aprobados <8', 'Calificación 8', 'Calificación 9', 'Calificación 10', 'Aprobación de examenes %']

                def estilar_aprobacion(val):
                    try:
                        v = float(val)
                        if v >= 90: return 'background-color: #28a745; color: white; font-weight: bold;'
                        elif v >= 80: return 'background-color: #a3cfbb; color: black; font-weight: bold;'
                        elif v >= 70: return 'background-color: #ffc107; color: black; font-weight: bold;'
                        elif v >= 60: return 'background-color: #fd7e14; color: black; font-weight: bold;'
                        else: return 'background-color: #dc3545; color: white; font-weight: bold;'
                    except:
                        return ''

                df_estilado_semanal = agrupado.style.map(estilar_aprobacion, subset=['Aprobación de examenes %']).format({
                    "Aprobación de examenes %": "{:.2f}"
                })
                
                st.dataframe(df_estilado_semanal, use_container_width=True, hide_index=True)
            else:
                st.info("No hay exámenes registrados en el rango de fechas seleccionado para esta planta.")
        else:
            st.info("La base de datos de entrenamientos está vacía.")
        
        # Análisis de Reactivos
        st.divider()
        st.markdown("#### 🧠 Análisis de Reactivos Críticos (Áreas de Oportunidad Técnica)")
        
        # Filtrar historial completo para la planta activa
        if not df_todo_train.empty:
            df_train_site = df_todo_train[df_todo_train['num_empleado'].isin(df_maestro['num_empleado'])]
            todas_respuestas = []
            
            for _, row in df_train_site.iterrows():
                resp_json = row.get('detalle_respuestas', {})
                if isinstance(resp_json, dict):
                    for pregunta, puntaje in resp_json.items():
                        palabras_filtro = [
                            'qué te pareció', 'que te parecio', 'qué le mejorarías', 'que le mejorarias',
                            'desempeño del capacitador', 'desempeño del', 'capacitador', 'instructor', 'curso',
                            'comentarios', 'sugerencias', 'evaluación', 'evaluacion del', 'entrenador', 'entrenamiento', 
                            'instalaciones', 'recomendarías', 'recomendar', 'satisfacción', 'material didáctico', 'rh', 
                            'recursos humanos', 'utilidad', 'fomento', 'trabajo', 'conocimientos', 'cambiarías', 'presentaciones', 'califica'
                        ]
                        
                        if any(x in pregunta.lower() for x in palabras_filtro):
                            continue
                            
                        try:
                            p = float(puntaje)
                            acertada = 1 if p > 0 else 0
                        except:
                            acertada = 0
                        todas_respuestas.append({"Pregunta": pregunta, "Acertada": acertada})
            
            if todas_respuestas:
                df_resp = pd.DataFrame(todas_respuestas)
                resumen_preguntas = df_resp.groupby('Pregunta').agg(
                    Total_Intentos=('Acertada', 'count'),
                    Aciertos=('Acertada', 'sum')
                ).reset_index()
                
                resumen_preguntas['Porcentaje_Falla'] = ((resumen_preguntas['Total_Intentos'] - resumen_preguntas['Aciertos']) / resumen_preguntas['Total_Intentos']) * 100
                resumen_preguntas = resumen_preguntas.sort_values('Porcentaje_Falla', ascending=False)
                resumen_preguntas['Concepto Técnico'] = resumen_preguntas['Pregunta'].str.replace('Puntos: ', '', regex=False).str.strip()
                df_preguntas_reales = resumen_preguntas[~resumen_preguntas['Concepto Técnico'].str.contains('Nombre|Puesto|Número|Fecha|Turno|Exámen|Examen', case=False, na=False)].head(5)
                
                if not df_preguntas_reales.empty:
                    fig = px.bar(
                        df_preguntas_reales, 
                        x='Porcentaje_Falla', 
                        y='Concepto Técnico', 
                        orientation='h',
                        text_auto='.1f',
                        labels={'Porcentaje_Falla': '% de Fallas Globales', 'Concepto Técnico': 'Reactivo Evaluado'},
                        title="Top 5 Conceptos Técnicos con Mayor Frecuencia de Error",
                        color='Porcentaje_Falla',
                        color_continuous_scale='Reds'
                    )
                    fig.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False, height=320, margin=dict(l=0, r=0, t=30, b=0))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No se localizaron reactivos de conocimiento técnico puro.")
        
        # Búsqueda Individual
        st.divider()
        st.markdown("#### 🔍 Consultar Historial Individual de Entrenamiento")
        if "empleado_consultado" not in st.session_state:
            st.session_state.empleado_consultado = ""

        with st.form("form_busqueda_individual"):
            c_search1, c_search2 = st.columns([3, 1])
            c_search1.text_input("ID de Empleado / Personnel ID:", key="texto_busqueda_empleado", autocomplete="off")
            btn_buscar = c_search2.form_submit_button("🔍 Buscar Historial", use_container_width=True)

        if btn_buscar:
            st.session_state.empleado_consultado = st.session_state.texto_busqueda_empleado.strip()

        if st.session_state.empleado_consultado:
            with st.spinner(f"Consultando expediente para el ID {st.session_state.empleado_consultado}..."):
                try:
                    resp_individual = supabase.table("entrenamientos_esd")\
                                              .select("fecha_entrenamiento, nombre_empleado, calificacion_total, archivo_origen, detalle_respuestas")\
                                              .eq("num_empleado", st.session_state.empleado_consultado)\
                                              .order("fecha_entrenamiento", desc=True)\
                                              .execute()
                    
                    if resp_individual.data:
                        df_individual = pd.DataFrame(resp_individual.data)
                        df_individual = df_individual.drop_duplicates(subset=['fecha_entrenamiento'], keep='first')
                        df_individual['fecha_entrenamiento'] = pd.to_datetime(df_individual['fecha_entrenamiento']).dt.strftime('%d-%b-%Y %H:%M')
                        nombre_detectado = df_individual.iloc[0]['nombre_empleado']
                        
                        puesto_detectado = "N/D"
                        ingreso_detectado = "N/D"
                        
                        try:
                            # Validar que el empleado pertenezca al site actual por seguridad
                            resp_ficha = supabase.table("empleados_batas").select("departamento, fecha_ingreso").eq("num_empleado", st.session_state.empleado_consultado).eq("site_id", site_id).execute()
                            if resp_ficha.data:
                                ficha_usuario = resp_ficha.data[0]
                                puesto_detectado = str(ficha_usuario.get('departamento', 'N/D'))
                                ingreso_detectado = str(ficha_usuario.get('fecha_ingreso', 'N/D'))[:10]
                            else:
                                st.warning("El empleado no se encuentra asignado a la planta activa.")
                                st.stop()
                        except:
                            pass
                        
                        st.markdown(f"##### 📋 Ficha de Identificación de Personal")
                        c_emp1, c_emp2, c_emp3 = st.columns(3)
                        c_emp1.metric("Empleado", nombre_detectado)
                        c_emp2.metric("Puesto", puesto_detectado)
                        c_emp3.metric("Fecha de Ingreso", ingreso_detectado)
                        st.write("")
                        
                        df_individual['Calificación (Base 10)'] = df_individual['detalle_respuestas'].apply(lambda d: round((sum([1.0 for v in d.values() if float(v) > 0]) / len(d)) * 10.0, 2) if isinstance(d, dict) and len(d) > 0 else 0.0)
                        
                        df_tabla_individual = df_individual[['fecha_entrenamiento', 'Calificación (Base 10)', 'archivo_origen']].copy()
                        df_tabla_individual.columns = ['Fecha de Aplicación', 'Calificación (Base 10)', 'Reporte de Origen']

                        def estilar_calificaciones(val):
                            try:
                                return 'background-color: #f8d7da; color: #721c24; font-weight: bold;' if float(val) <= 7.0 else 'background-color: #d4edda; color: #155724;'
                            except:
                                return ''

                        df_estilado = df_tabla_individual.style.map(estilar_calificaciones, subset=['Calificación (Base 10)'])
                        st.dataframe(df_estilado, use_container_width=True, hide_index=True)

                        st.markdown("##### 📜 Desglose de preguntas por examen")
                        for idx, row in df_individual.iterrows():
                            fecha_intento = row['fecha_entrenamiento']
                            detalle_json = row.get('detalle_respuestas', {})
                            
                            if isinstance(detalle_json, dict) and len(detalle_json) > 0:
                                nota_intento = round((sum([1.0 for v in detalle_json.values() if float(v) > 0]) / len(detalle_json)) * 10.0, 2)
                            else:
                                try: nota_intento = min(float(row['calificacion_total']), 10.0)
                                catch: nota_intento = 0.0
                            
                            icono_intento = "🟢" if nota_intento > 7.0 else "🔴"
                            
                            with st.expander(f"{icono_intento} Evaluación del {fecha_intento} — Calificación: {nota_intento} / 10.0"):
                                if isinstance(detalle_json, dict) and len(detalle_json) > 0:
                                    lista_reactivos = [{"Reactivo Evaluado": preg.replace('Puntos: ', '', 1).strip(), "Puntaje Obtenido": "✔️ Correcta (1.0)" if float(puntaje) > 0 else "❌ Incorrecta (0.0)"} for preg, puntaje in detalle_json.items()]
                                    st.dataframe(pd.DataFrame(lista_reactivos), use_container_width=True, hide_index=True)
                                else:
                                    st.info("Este registro histórico no cuenta con desglose de reactivos.")
                    else:
                        st.warning(f"🔍 No se localizaron registros para el ID: **{st.session_state.empleado_consultado}**.")
                except Exception as e:
                    st.error(f"Error consultando base de datos: {e}")
    else:
        st.info("No hay personal activo registrado en el sistema para esta planta.")

# --- PESTAÑA 2: CARGAR HISTÓRICOS ---
with tab_historico:
    st.markdown("#### 📥 Importar Excel/CSV Histórico (Forms)")
    st.write("Sube archivos antiguos. El sistema detectará automáticamente los datos clave.")
    
    archivos_hist = st.file_uploader("Seleccionar archivos históricos", type=["csv", "xlsx"], accept_multiple_files=True, key="up_hist")
    
    if archivos_hist:
        for archivo in archivos_hist:
            with st.expander(f"⚙️ Procesando: {archivo.name}", expanded=True):
                try:
                    df_raw = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo)
                    cols = df_raw.columns
                    col_num = next((c for c in cols if 'número de empleado' in str(c).lower() or 'numero de empleado' in str(c).lower()), None)
                    col_nom = next((c for c in cols if 'nombre' in str(c).lower() and 'completo' in str(c).lower()), None) or next((c for c in cols if str(c).lower() == 'nombre'), None)
                    col_calif = next((c for c in cols if 'total de puntos' in str(c).lower()), None)
                    col_fecha = next((c for c in cols if 'hora de finalización' in str(c).lower() or 'fecha de aplicación' in str(c).lower()), None)
                    
                    if not col_num or not col_calif:
                        st.error(f"❌ Columnas requeridas no encontradas en {archivo.name}.")
                    else:
                        cols_preguntas = [c for c in cols if str(c).strip().startswith('Puntos:')]
                        df_clean = df_raw.dropna(subset=[col_num]).copy()
                        df_clean[col_num] = df_clean[col_num].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                        
                        st.success(f"Se detectaron {len(df_clean)} registros y {len(cols_preguntas)} preguntas.")
                        
                        if st.button(f"🚀 Guardar datos de {archivo.name}", key=f"btn_{archivo.name}"):
                            with st.spinner("Registrando exámenes..."):
                                try:
                                    resp_ex = supabase.table("entrenamientos_esd").select("num_empleado, fecha_entrenamiento").execute()
                                    set_existentes = {f"{str(x.get('num_empleado')).strip()}|{str(x.get('fecha_entrenamiento'))[:10]}" for x in resp_ex.data}
                                except:
                                    set_existentes = set()
                                
                                if col_fecha:
                                    df_clean = df_clean.drop_duplicates(subset=[col_num, col_fecha], keep='first')

                                lote_insercion = []
                                registros_omitidos = 0
                                
                                palabras_filtro = [
                                    'nombre', 'puesto', 'empleado', 'fecha', 'exámen', 'examen', 'qué te pareció', 'que te parecio',
                                    'qué le mejorarías', 'que le mejorarias', 'desempeño del capacitador', 'desempeño del', 'capacitador',
                                    'instructor', 'curso', 'comentarios', 'sugerencias', 'evaluación', 'evaluacion del', 'entrenador',
                                    'entrenamiento', 'instalaciones', 'recomendarías', 'recomendar', 'satisfacción', 'material didáctico',
                                    'rh', 'recursos humanos', 'utilidad', 'fomento', 'trabajo', 'conocimientos', 'cambiarías', 'presentaciones', 'califica'
                                ]

                                for _, row in df_clean.iterrows():
                                    emp_id = str(row[col_num]).strip()
                                    nombre_emp = str(row.get(col_nom, "N/D"))[:100]
                                    
                                    fecha_raw = row.get(col_fecha, datetime.now())
                                    try:
                                        fecha_dt = pd.to_datetime(fecha_raw)
                                        fecha_val_str = fecha_dt.strftime('%Y-%m-%d')
                                        fecha_proximo_str = (fecha_dt + relativedelta(years=1)).strftime('%Y-%m-%d')
                                    except:
                                        fecha_dt = datetime.now()
                                        fecha_val_str = fecha_dt.strftime('%Y-%m-%d')
                                        fecha_proximo_str = (fecha_dt + relativedelta(years=1)).strftime('%Y-%m-%d')
                                        
                                    llave_unica = f"{emp_id}|{fecha_val_str}"
                                    if llave_unica in set_existentes:
                                        registros_omitidos += 1
                                        continue

                                    detalle = {}
                                    for cp in cols_preguntas:
                                        if any(x in cp.lower() for x in palabras_filtro):
                                            continue 
                                        val_raw = row.get(cp)
                                        if pd.isna(val_raw) or str(val_raw).strip() == '':
                                            continue
                                        try:
                                            detalle[cp] = float(val_raw)
                                        except:
                                            pass 
                                    
                                    total_reactivos = len(detalle)
                                    calif_total = round((sum([1.0 for v in detalle.values() if float(v) > 0]) / total_reactivos) * 10.0, 2) if total_reactivos > 0 else 0.0
                                    
                                    lote_insercion.append({
                                        "num_empleado": emp_id,
                                        "nombre_empleado": nombre_emp,
                                        "fecha_entrenamiento": fecha_dt.isoformat(),
                                        "calificacion_total": calif_total,
                                        "detalle_respuestas": detalle,
                                        "archivo_origen": archivo.name
                                    })
                                    
                                    # Actualizar ficha con site_id activo
                                    try:
                                        supabase.table("empleados_batas").update({
                                            "fecha_ultimo_entrenamiento": fecha_val_str,
                                            "fecha_proximo_entrenamiento": fecha_proximo_str,
                                            "site_id": site_id
                                        }).eq("num_empleado", emp_id).execute()
                                    except:
                                        pass

                                if lote_insercion:
                                    for i in range(0, len(lote_insercion), 300):
                                        supabase.table("entrenamientos_esd").insert(lote_insercion[i:i+300]).execute()
                                    st.success(f"🎉 ¡{len(lote_insercion)} exámenes archivados!")
                                    st.cache_data.clear()
                                    st.rerun()
                                elif registros_omitidos > 0:
                                    st.warning("No se agregaron registros nuevos (ya existían).")
                except Exception as e:
                    st.error(f"Error procesando {archivo.name}: {e}")

# --- PESTAÑA 3: ACTUALIZACIÓN SEMANAL ---
with tab_semanal:
    st.markdown("#### 🔄 Cargar Formato Semanal de Inducción")
    archivo_sem = st.file_uploader("Subir archivo semanal (Inducción)", type=["csv", "xlsx"], key="up_sem")

    if archivo_sem:
        with st.expander(f"⚙️ Procesando: {archivo_sem.name}", expanded=True):
            try:
                df_raw = pd.read_csv(archivo_sem) if archivo_sem.name.endswith('.csv') else pd.read_excel(archivo_sem)
                cols = [str(c).strip() for c in df_raw.columns]
                df_raw.columns = cols
                
                col_examen = next((c for c in cols if 'exámen va a presentar' in c.lower() or 'examen va a presentar' in c.lower()), None)
                col_num = next((c for c in cols if 'número de empleado' in c.lower() or 'numero de empleado' in c.lower()), None)
                col_nom = 'Nombre Completo'
                col_calif = next((c for c in cols if 'total de puntos' in c.lower()), None)
                col_fecha = next((c for c in cols if 'hora de finalización' in c.lower() or 'fecha que se realiza' in c.lower()), None)

                if col_nom not in cols:
                    st.error(f"❌ No se encontró la columna exacta '{col_nom}'.")
                elif not col_examen or not col_num or not col_calif:
                    st.error("❌ No se encontraron columnas de control.")
                else:
                    df_esd = df_raw[df_raw[col_examen].astype(str).str.contains('ESD', case=False, na=False)].copy()
                    df_esd['num_emp_str'] = df_esd[col_num].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                    mask_sin_id = df_esd['num_emp_str'].isin(['nan', '', 'None', 'N/A', '0']) | df_esd[col_num].isna()
                    df_sin_id = df_esd[mask_sin_id]
                    df_clean = df_esd[~mask_sin_id]

                    st.success(f"Exámenes ESD detectados: **{len(df_esd)}** | Listos: **{len(df_clean)}**")

                    if not df_sin_id.empty:
                        st.warning(f"⚠️ **{len(df_sin_id)}** exámenes sin ID:")
                        df_sin_id_show = df_sin_id.copy()
                        df_sin_id_show[col_nom] = df_sin_id_show[col_nom].fillna("Sin Nombre")
                        df_mostrar_sin_id = df_sin_id_show[[col_fecha, col_nom, col_calif, col_examen]]
                        df_mostrar_sin_id.columns = ['Fecha / Hora', 'Nombre', 'Calificación', 'Examen']
                        st.dataframe(df_mostrar_sin_id, use_container_width=True, hide_index=True)

                    if not df_clean.empty:
                        cols_preguntas = [c for c in cols if str(c).strip().startswith('Puntos:')]
                        if st.button("🚀 Guardar Exámenes Semanales", key="btn_semanal_guardar", type="primary"):
                            with st.spinner("Guardando..."):
                                try:
                                    resp_ex = supabase.table("entrenamientos_esd").select("num_empleado, fecha_entrenamiento").execute()
                                    set_existentes = {f"{str(x.get('num_empleado')).strip()}|{str(x.get('fecha_entrenamiento'))[:10]}" for x in resp_ex.data}
                                except:
                                    set_existentes = set()

                                lote_insercion = []
                                registros_omitidos = 0
                                palabras_filtro = [
                                    'nombre', 'puesto', 'empleado', 'fecha', 'exámen', 'examen', 'qué te pareció', 'que te parecio',
                                    'qué le mejorarías', 'que le mejorarias', 'desempeño del capacitador', 'desempeño del', 'capacitador',
                                    'instructor', 'curso', 'comentarios', 'sugerencias', 'evaluación', 'evaluacion del', 'entrenador',
                                    'entrenamiento', 'instalaciones', 'recomendarías', 'recomendar', 'satisfacción', 'material didáctico',
                                    'rh', 'recursos humanos', 'utilidad', 'fomento', 'trabajo', 'conocimientos', 'cambiarías', 'presentaciones', 'califica'
                                ]

                                for _, row in df_clean.iterrows():
                                    emp_id = str(row['num_emp_str'])
                                    fecha_raw = row.get(col_fecha, datetime.now())
                                    try:
                                        fecha_dt = pd.to_datetime(fecha_raw)
                                        fecha_val_str = fecha_dt.strftime('%Y-%m-%d')
                                        fecha_proximo_str = (fecha_dt + relativedelta(years=1)).strftime('%Y-%m-%d')
                                    except:
                                        fecha_dt = datetime.now()
                                        fecha_val_str = fecha_dt.strftime('%Y-%m-%d')
                                        fecha_proximo_str = (fecha_dt + relativedelta(years=1)).strftime('%Y-%m-%d')

                                    llave_unica = f"{emp_id}|{fecha_val_str}"
                                    if llave_unica in set_existentes:
                                        registros_omitidos += 1
                                        continue

                                    raw_nombre = row.get(col_nom)
                                    nombre_emp = "Sin Nombre" if pd.isna(raw_nombre) else str(raw_nombre).strip()[:100]

                                    detalle = {}
                                    for cp in cols_preguntas:
                                        if any(x in cp.lower() for x in palabras_filtro):
                                            continue 
                                        col_resp = cp.replace("Puntos: ", "", 1).strip()
                                        if col_resp in df_raw.columns and pd.isna(row.get(col_resp)):
                                            continue
                                        detalle[cp] = float(row.get(cp, 0))

                                    total_reactivos = len(detalle)
                                    calif_total = round((sum([1.0 for v in detalle.values() if float(v) > 0]) / total_reactivos) * 10.0, 2) if total_reactivos > 0 else 0.0

                                    lote_insercion.append({
                                        "num_empleado": emp_id,
                                        "nombre_empleado": nombre_emp,
                                        "fecha_entrenamiento": fecha_dt.isoformat(),
                                        "calificacion_total": calif_total,
                                        "detalle_respuestas": detalle,
                                        "archivo_origen": archivo_sem.name
                                    })

                                    try:
                                        supabase.table("empleados_batas").update({
                                            "fecha_ultimo_entrenamiento": fecha_val_str,
                                            "fecha_proximo_entrenamiento": fecha_proximo_str,
                                            "site_id": site_id
                                        }).eq("num_empleado", emp_id).execute()
                                    except:
                                        pass

                                if lote_insercion:
                                    for i in range(0, len(lote_insercion), 300):
                                        supabase.table("entrenamientos_esd").insert(lote_insercion[i:i+300]).execute()
                                    st.success(f"🎉 Sincronización exitosa: **{len(lote_insercion)}** exámenes.")
                                    st.cache_data.clear()
                                    st.rerun()
                                elif registros_omitidos > 0:
                                    st.warning("No hay registros nuevos (ya existían).")
            except Exception as e:
                st.error(f"Error: {e}")

# --- PESTAÑA 4: AUDITORÍA CRONOLÓGICA ---
with tab_auditoria:
    st.markdown("#### 🕵️ Auditoría de Cumplimiento (Gaps y Reentrenamientos)")
    st.info("Detecta brechas mayores a 365 días y reentrenamientos que tardaron más de 2 días tras reprobar (< 8.0).")

    if "anomalias_entrenamiento" not in st.session_state:
        st.session_state.anomalias_entrenamiento = None

    if st.button("🔍 Escanear Historial Completo", type="secondary", use_container_width=True):
        with st.spinner("Analizando historial..."):
            try:
                resp_emp = supabase.table("empleados_batas").select("num_empleado, fecha_ingreso").eq("site_id", site_id).execute()
                df_emp = pd.DataFrame(resp_emp.data)
                
                dict_ingreso = {}
                if not df_emp.empty:
                    df_emp['num_empleado'] = df_emp['num_empleado'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
                    if 'fecha_ingreso' in df_emp.columns:
                        dict_ingreso = dict(zip(df_emp['num_empleado'], df_emp['fecha_ingreso']))
                        
                resp_train = supabase.table("entrenamientos_esd").select("id, num_empleado, nombre_empleado, fecha_entrenamiento, calificacion_total").order("fecha_entrenamiento").execute()
                df_train = pd.DataFrame(resp_train.data)
                
                anomalias_encontradas = []
                if not df_train.empty:
                    df_train['fecha_dt'] = pd.to_datetime(df_train['fecha_entrenamiento'], errors='coerce')
                    df_train['num_empleado'] = df_train['num_empleado'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
                    df_train = df_train.dropna(subset=['fecha_dt'])
                    
                    # Filtrar sólo para empleados de este site
                    df_train = df_train[df_train['num_empleado'].isin(dict_ingreso.keys())]
                    df_train = df_train.sort_values(by=['num_empleado', 'fecha_dt'])
                    
                    for emp, group in df_train.groupby('num_empleado'):
                        group = group.reset_index(drop=True)
                        f_ingreso_raw = dict_ingreso.get(emp)
                        f_ingreso_str = str(f_ingreso_raw)[:10] if pd.notna(f_ingreso_raw) and f_ingreso_raw else "N/D"
                        
                        for i in range(len(group)):
                            row_actual = group.iloc[i]
                            if i > 0:
                                row_prev = group.iloc[i-1]
                                dias_transcurridos = (row_actual['fecha_dt'].date() - row_prev['fecha_dt'].date()).days
                                es_primer_examen = "Sí" if (i - 1) == 0 else "No"
                                
                                try: nota_previa = float(row_prev['calificacion_total'])
                                except: nota_previa = 10.0
                                try: nota_siguiente = float(row_actual['calificacion_total'])
                                except: nota_siguiente = 0.0
                                
                                registro_base = {
                                    "id_bd_actual": row_actual['id'],
                                    "id_bd_previo": row_prev['id'],
                                    "No. Empleado": emp,
                                    "Nombre": row_actual['nombre_empleado'],
                                    "Fecha Ingreso": f_ingreso_str,
                                    "Es Primer Examen?": es_primer_examen,
                                    "Fecha Examen Previo": row_prev['fecha_dt'].strftime('%Y-%m-%d'),
                                    "Nueva Fecha Previa": row_prev['fecha_dt'].strftime('%Y-%m-%d'),
                                    "Nota Previa": nota_previa,
                                    "Días Gap": dias_transcurridos,
                                    "Fecha Siguiente Examen": row_actual['fecha_dt'].strftime('%Y-%m-%d'),
                                    "Nueva Fecha (Correcta)": row_actual['fecha_dt'].strftime('%Y-%m-%d'),
                                    "Nota Siguiente Examen": nota_siguiente
                                }

                                if nota_previa < 8.0 and dias_transcurridos > 2:
                                    reg_falla = registro_base.copy()
                                    reg_falla["Motivo de Alerta"] = "Reentrenamiento Tardío"
                                    anomalias_encontradas.append(reg_falla)
                                    continue 
                                        
                                if dias_transcurridos > 365:
                                    reg_brecha = registro_base.copy()
                                    reg_brecha["Motivo de Alerta"] = "Brecha Anual Excedida"
                                    anomalias_encontradas.append(reg_brecha)

                st.session_state.anomalias_entrenamiento = anomalias_encontradas
            except Exception as e:
                st.error(f"Error al analizar el historial: {e}")

    if st.session_state.anomalias_entrenamiento is not None:
        lista_anomalias = st.session_state.anomalias_entrenamiento
        st.divider()
        
        if len(lista_anomalias) == 0:
            st.success("✨ ¡Cumplimiento cronológico perfecto!")
            st.session_state.anomalias_entrenamiento = None
        else:
            st.warning(f"⚠️ Se encontraron {len(lista_anomalias)} anomalías:")
            df_anomalias = pd.DataFrame(lista_anomalias)
            columnas_maestras = [
                "id_bd_actual", "id_bd_previo", "No. Empleado", "Nombre", "Fecha Ingreso", 
                "Motivo de Alerta", "Es Primer Examen?", "Fecha Examen Previo", 
                "Nota Previa", "Días Gap", "Fecha Siguiente Examen", "Nota Siguiente Examen"
            ]

            for col in columnas_maestras:
                if col not in df_anomalias.columns:
                    df_anomalias[col] = None

            df_anomalias['Nueva Fecha Previa'] = pd.to_datetime(df_anomalias['Fecha Examen Previo'], errors='coerce')
            df_anomalias['Nueva Fecha (Correcta)'] = pd.to_datetime(df_anomalias['Fecha Siguiente Examen'], errors='coerce')

            cols_ordenadas = [
                "id_bd_actual", "id_bd_previo", "No. Empleado", "Nombre", "Fecha Ingreso", 
                "Motivo de Alerta", "Es Primer Examen?", "Fecha Examen Previo", "Nueva Fecha Previa", 
                "Nota Previa", "Días Gap", "Fecha Siguiente Examen", "Nueva Fecha (Correcta)", "Nota Siguiente Examen"
            ]
            df_anomalias = df_anomalias[[c for c in cols_ordenadas if c in df_anomalias.columns]]

            editor_train = st.data_editor(
                df_anomalias,
                column_config={
                    "id_bd_actual": None, "id_bd_previo": None,
                    "No. Empleado": st.column_config.TextColumn("No. Empleado", disabled=True),
                    "Nombre": st.column_config.TextColumn("Nombre", disabled=True),
                    "Fecha Ingreso": st.column_config.TextColumn("Ingreso", disabled=True),
                    "Motivo de Alerta": st.column_config.TextColumn("Motivo", disabled=True),
                    "Es Primer Examen?": st.column_config.TextColumn("1er Examen?", disabled=True),
                    "Fecha Examen Previo": st.column_config.TextColumn("Examen Previo", disabled=True),
                    "Nueva Fecha Previa": st.column_config.DateColumn("Edita Fecha Previa"),
                    "Nota Previa": st.column_config.NumberColumn("Nota Previa", disabled=True),
                    "Días Gap": st.column_config.NumberColumn("Días Gap", disabled=True),
                    "Fecha Siguiente Examen": st.column_config.TextColumn("Sig. Examen", disabled=True),
                    "Nueva Fecha (Correcta)": st.column_config.DateColumn("Edita Fecha Sig."),
                    "Nota Siguiente Examen": st.column_config.NumberColumn("Nota Sig.", disabled=True),
                },
                hide_index=True,
                width='stretch',
                key="editor_train_audit"
            )
            
            if st.button("💾 Guardar Correcciones", type="primary", use_container_width=True):
                cambios = st.session_state.editor_train_audit.get("edited_rows", {})
                if not cambios:
                    st.info("No hay cambios pendientes.")
                else:
                    with st.spinner("Sincronizando..."):
                        errores = 0
                        for idx_str, edits in cambios.items():
                            idx = int(idx_str)
                            fila = df_anomalias.iloc[idx]
                            
                            if "Nueva Fecha (Correcta)" in edits:
                                try:
                                    supabase.table("entrenamientos_esd").update({"fecha_entrenamiento": str(edits["Nueva Fecha (Correcta)"]) + "T00:00:00"}).eq("id", fila['id_bd_actual']).execute()
                                except: errores += 1
                            if "Nueva Fecha Previa" in edits:
                                try:
                                    supabase.table("entrenamientos_esd").update({"fecha_entrenamiento": str(edits["Nueva Fecha Previa"]) + "T00:00:00"}).eq("id", fila['id_bd_previo']).execute()
                                except: errores += 1
                        
                        if errores == 0:
                            st.success("✅ ¡Registros actualizados!")
                            st.session_state.anomalias_entrenamiento = None
                            st.rerun()
