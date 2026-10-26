# pages/11_findings.py
"""
Módulo de Seguimiento de Hallazgos (EASE Audit Mitigation Tracking),
Control de Tiempos de Respuesta y Cierre (SLA), Acciones Correctivas (CAPA),
Evidencias en Supabase Storage Bucket y Lessons Learned Globales de la Compañía (Yokoten).
"""
import streamlit as st
try:
    st.set_page_config(page_title="ESD Management Suite", page_icon="⚡", layout="wide")
except Exception:
    pass

import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
import json

from core.i18n import t
from core.db import (
    get_supabase_client,
    upload_finding_evidence,
    get_site_findings,
    get_company_lessons_learned,
)
from core.constants import INFO_ELEMENTOS_ESD
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
site_name = st.session_state.get("site_name", "Planta Principal")
company_id = st.session_state.get("company_id")
company_name = st.session_state.get("company_name", "Corporativo Global")
user_id = st.session_state.get("user_id")
user_name = st.session_state.get("usuario_nombre", "Auditor ESD")

# ==========================================
# 2. CONSTANTES Y CONFIGURACIÓN ESTILO EASE AUDIT
# ==========================================
EASE_ASSESSMENT_TYPES = [
    "LPA Layer 1 - Supervisor Diario",
    "LPA Layer 2 - Ingeniería ESD / Calidad",
    "LPA Layer 3 - Gerencia / Staff",
    "Auditoría Normativa ANSI/ESD S20.20 (TR53)",
    "Recorrido EPA / 5S + ESD",
    "Auditoría de Proceso SMT / Final Assembly",
    "Auditoría Externa / Cliente",
]

EASE_SEVERITY_SLA = {
    "Critical": {"label": "🔴 Critical (Crítico - Riesgo directo ESDS)", "resp_hours": 4, "close_days": 3, "color": "#dc3545"},
    "Major": {"label": "🟠 Major (Mayor - Incumplimiento S20.20)", "resp_hours": 24, "close_days": 7, "color": "#fd7e14"},
    "Minor": {"label": "🟡 Minor (Menor - Desviación puntual)", "resp_hours": 48, "close_days": 14, "color": "#ffc107"},
    "Observation": {"label": "🔵 Observation / OFI (Mejora Continua)", "resp_hours": 72, "close_days": 30, "color": "#0d6efd"},
}

EASE_MITIGATION_TYPES = [
    "Action Required (Short-Term)",
    "CAPA / 8D (Root Cause & Systemic)",
    "Fix Now / Point of Cause",
]

EASE_STATUS_OPTIONS = [
    "Open",
    "In Progress / Containment",
    "Pending Verification",
    "Past Due / Escalated",
    "Closed / Completed",
    "Fix Now (Point of Cause)",
    "Rejected / Reopened",
]

ROOT_CAUSE_6M = [
    "Sin Clasificar",
    "Método / Proceso (Method)",
    "Máquina / Equipo / Herramienta (Machine)",
    "Mano de Obra / Entrenamiento (People)",
    "Material / Empaque ESD (Material)",
    "Medio Ambiente / Humedad / EPA (Environment)",
    "Medición / Calibración (Measurement)",
]

# ==========================================
# 3. ALMACENES LOCALES DE RESPALDO (RESILIENCIA)
# ==========================================
if "local_esd_findings" not in st.session_state:
    hoy_dt = datetime.now()
    st.session_state.local_esd_findings = [
        {
            "finding_code": "EASE-2026-0101",
            "site_id": site_id,
            "site_name": site_name,
            "company_id": company_id,
            "assessment_type": "LPA Layer 2 - Ingeniería ESD / Calidad",
            "question_title": "Monitor Continuo",
            "location": "SMT-01",
            "station_or_asset": "MON-SMT01-04",
            "severity": "Critical",
            "mitigation_type": "CAPA / 8D (Root Cause & Systemic)",
            "status": "Past Due / Escalated",
            "opened_by": "Carlos Mendoza (Auditor ESD)",
            "responsible_party": "Ing. Roberto Sánchez (Mantenimiento SMT)",
            "escalation_owner": "Gerencia de Calidad",
            "opened_at": (hoy_dt - timedelta(days=5, hours=3)).strftime("%Y-%m-%d %H:%M"),
            "response_sla_hours": 4,
            "first_response_at": (hoy_dt - timedelta(days=5, hours=1)).strftime("%Y-%m-%d %H:%M"),
            "due_date": (hoy_dt - timedelta(days=2)).strftime("%Y-%m-%d"),
            "closed_at": None,
            "measured_value": "4.8 Ohms (Límite < 2.0 Ohms)",
            "finding_description": "Monitor continuo de estación de retoque presenta resistencia a tierra de 4.8 Ohms y desconexión intermitente en el jack de operador.",
            "containment_action": "Se bloqueó la estación de retoque #4 y se instaló pulsera en punto auxiliar verificado (< 0.8 Ohms).",
            "root_cause_6m": "Máquina / Equipo / Herramienta (Machine)",
            "root_cause_detail": "1. ¿Por qué dio 4.8 Ohms? Sulfatación y desgaste mecánico del cable de tierra del monitor. 2. ¿Por qué no se detectó antes? Tensión mecánica al mover el banco.",
            "corrective_action": "Reemplazo de cableado de tierra con terminal ojillo soldado y reubicación con alivio de tensión.",
            "preventive_action": "Incluir revisión de alivio de tensión mecánico en el checklist trimestral de monitores continuos.",
            "verification_comments": "",
            "evidence_before_url": "",
            "evidence_after_url": "",
            "storage_bucket": "evidencias_hallazgos",
            "is_lesson_learned": False,
        },
        {
            "finding_code": "EASE-2026-0102",
            "site_id": site_id,
            "site_name": site_name,
            "company_id": company_id,
            "assessment_type": "LPA Layer 1 - Supervisor Diario",
            "question_title": "Ionizador",
            "location": "ROUTER-01",
            "station_or_asset": "ION-RTR-02",
            "severity": "Major",
            "mitigation_type": "Action Required (Short-Term)",
            "status": "In Progress / Containment",
            "opened_by": "Laura Torres",
            "responsible_party": "Ing. Miguel Ángel Ruiz",
            "escalation_owner": "Supervisión Producción",
            "opened_at": (hoy_dt - timedelta(days=2, hours=6)).strftime("%Y-%m-%d %H:%M"),
            "response_sla_hours": 24,
            "first_response_at": (hoy_dt - timedelta(days=2, hours=2)).strftime("%Y-%m-%d %H:%M"),
            "due_date": (hoy_dt + timedelta(days=5)).strftime("%Y-%m-%d"),
            "closed_at": None,
            "measured_value": "Tiempo descarga +1000V a +100V = 14.5s (Límite < 10s)",
            "finding_description": "Ionizador de banco en estación de depanelizado (Router) excede el tiempo máximo de descarga en polaridad positiva y presenta acumulación de polvo en agujas emisoras.",
            "containment_action": "Limpieza inmediata de agujas emisoras con alcohol isopropílico y ajuste de ángulo hacia el fixture del router.",
            "root_cause_6m": "Medio Ambiente / Humedad / EPA (Environment)",
            "root_cause_detail": "El polvo de fibra de vidrio del ruteo de PCB se deposita aceleradamente sobre los emisores del ionizador.",
            "corrective_action": "Cambio de filtro y recalibración de balance offset (+4V).",
            "preventive_action": "Aumentar frecuencia de limpieza de emisores en área de Router de mensual a semanal.",
            "verification_comments": "",
            "evidence_before_url": "",
            "evidence_after_url": "",
            "storage_bucket": "evidencias_hallazgos",
            "is_lesson_learned": False,
        },
        {
            "finding_code": "EASE-2026-0098",
            "site_id": site_id,
            "site_name": site_name,
            "company_id": company_id,
            "assessment_type": "Auditoría Normativa ANSI/ESD S20.20 (TR53)",
            "question_title": "Aislantes - EPA (General)",
            "location": "FINAL ASSEMBLY",
            "station_or_asset": "LINEA-FA-EST03",
            "severity": "Major",
            "mitigation_type": "CAPA / 8D (Root Cause & Systemic)",
            "status": "Closed / Completed",
            "opened_by": "Carlos Mendoza (Auditor ESD)",
            "responsible_party": "Sup. Diana Flores",
            "escalation_owner": "Gerencia de Operaciones",
            "opened_at": (hoy_dt - timedelta(days=9, hours=4)).strftime("%Y-%m-%d %H:%M"),
            "response_sla_hours": 24,
            "first_response_at": (hoy_dt - timedelta(days=9, hours=1)).strftime("%Y-%m-%d %H:%M"),
            "due_date": (hoy_dt - timedelta(days=2)).strftime("%Y-%m-%d"),
            "closed_at": (hoy_dt - timedelta(days=4, hours=2)).strftime("%Y-%m-%d %H:%M"),
            "measured_value": "+2,450 Volts a 10 cm de PCBA (Límite < 2000V / >30cm)",
            "finding_description": "Portahojas de acrílico estándar y cinta adhesiva transparente común colocados a menos de 10 cm del ensamble electrónico sensible (ESDS).",
            "containment_action": "Retiro inmediato de portahojas acrílicos y rollos de cinta común de las 6 estaciones de Final Assembly.",
            "root_cause_6m": "Material / Empaque ESD (Material)",
            "root_cause_detail": "Compra de papelería administrativa sin validación de Ingeniería ESD para uso dentro de EPA.",
            "corrective_action": "Sustitución por portahojas disipativos certificados (RS 10^7 Ohms) y cinta ESD con núcleo plástico disipativo.",
            "preventive_action": "Bloqueo en catálogo de almacén indirecto: solo números de parte aprobados por ESD pueden solicitarse para centros de costo EPA.",
            "verification_comments": "Verificado en piso con medidor de campo electrostático: lectura < 35V en todas las estaciones.",
            "evidence_before_url": "",
            "evidence_after_url": "",
            "storage_bucket": "evidencias_hallazgos",
            "is_lesson_learned": True,
        },
    ]

if "local_company_lessons" not in st.session_state:
    st.session_state.local_company_lessons = [
        {
            "lesson_code": "LL-GLOBAL-2026-001",
            "company_id": company_id,
            "company_name": company_name,
            "origin_site_id": site_id,
            "origin_site_name": site_name,
            "source_finding_code": "EASE-2026-0098",
            "esd_category": "Aislantes - EPA (General)",
            "process_area": "Final Assembly / Estaciones Manuales",
            "severity": "Major",
            "title": "Eliminación de portahojas acrílicos y cintas aislantes en estaciones con PCBA expuesta",
            "problem_description": "Se detectaron campos electrostáticos de +2,450V a menos de 10 cm de tarjetas electrónicas debido al ingreso de portahojas de acrílico convencional adquiridos como papelería general.",
            "root_cause_6m": "Material / Empaque ESD (Material)",
            "root_cause_analysis": "El catálogo de compras de insumos indirectos (MRO) permitía a supervisores pedir carpetas y cintas estándar sin filtro de aprobación ESD para áreas EPA.",
            "standard_solution": "1. Uso exclusivo de portahojas ESD disipativos permanentes (1x10^6 a <1x10^9 Ohms). 2. Candado en ERP/Almacén MRO para requerir sello ESD en centros de costo productivos.",
            "benefit_impact": "Reducción del 100% de hallazgos recurrentes por aislantes en LPA Layer 1 y eliminación de riesgo de carga por inducción en PCBA.",
            "evidence_before_url": "",
            "evidence_after_url": "",
            "published_by": "Carlos Mendoza (Auditor ESD)",
            "created_at": (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d %H:%M"),
            "yokoten_adoption": {
                site_name: {
                    "status": "Implementado en Planta",
                    "updated_by": "Carlos Mendoza",
                    "updated_at": datetime.now().strftime("%Y-%m-%d"),
                    "notes": "Aplicado en las 8 líneas de ensamble final."
                }
            }
        },
        {
            "lesson_code": "LL-GLOBAL-2026-002",
            "company_id": company_id,
            "company_name": company_name,
            "origin_site_id": "site-hermana-02",
            "origin_site_name": "Planta Norte - Juárez / SMT",
            "source_finding_code": "EASE-2026-0045",
            "esd_category": "Carrito",
            "process_area": "Logística Interna / Kitting SMT",
            "severity": "Critical",
            "title": "Aislamiento en ruedas conductivas de carritos PCB por residuos de cera y cinta en pasillos",
            "problem_description": "Durante auditoría TR53 semestral, el 35% de los carritos de transporte de magazines fallaron RTG (> 1.0x10^9 Ohms) pese a tener ruedas conductivas y cadena de arrastre.",
            "root_cause_6m": "Método / Proceso (Method)",
            "root_cause_analysis": "Los carritos transitaban por el área de almacén donde había restos de adhesivo de etiquetas y polvo acumulado que creaban una película aislante sobre la banda de rodamiento de las 4 llantas.",
            "standard_solution": "1. Instalar cepillos disipativos y tapete húmedo de limpieza de ruedas (Sticky/Clean Mat) a la entrada del EPA. 2. Limpieza semanal de llantas con limpiador ESD libre de silicona.",
            "benefit_impact": "Tasa de aprobación RTG en carritos subió del 65% al 99.2% en todas las auditorías posteriores.",
            "evidence_before_url": "",
            "evidence_after_url": "",
            "published_by": "Ing. Sofía Villarreal (Corp ESD Lead)",
            "created_at": (datetime.now() - timedelta(days=12)).strftime("%Y-%m-%d %H:%M"),
            "yokoten_adoption": {}
        }
    ]

# ==========================================
# 4. FUNCIONES AUXILIARES DE DATOS Y TIEMPOS (SLA)
# ==========================================
def obtener_lineas_planta():
    try:
        resp = supabase.table("catalogo_lineas").select("nombre_linea").eq("site_id", site_id).order("nombre_linea").execute()
        if resp and resp.data:
            return [x["nombre_linea"] for x in resp.data if x.get("nombre_linea")]
    except Exception:
        pass
    return ["SMT-01", "SMT-02", "ROUTER-01", "ICT-01", "CONFORMAL COATING", "FINAL ASSEMBLY", "CLEANROOM-01", "ALMACÉN EPA"]

def obtener_usuarios_planta():
    nombres = []
    try:
        resp = supabase.table("users").select("full_name, email, role").eq("site_id", site_id).execute()
        if resp and resp.data:
            for u in resp.data:
                nom = u.get("full_name") or u.get("email")
                if nom and nom not in nombres:
                    nombres.append(nom)
    except Exception:
        pass
    if not nombres:
        nombres = [
            user_name,
            "Ing. Roberto Sánchez (Mantenimiento SMT)",
            "Ing. Miguel Ángel Ruiz (Procesos)",
            "Sup. Diana Flores (Producción)",
            "Ing. Jorge Ramírez (Calidad ESD)",
        ]
    return nombres

def obtener_activos_planta():
    activos = ["N/A (General de Línea / Área)"]
    try:
        resp = supabase.table("assets").select("custom_id, category, location").eq("site_id", site_id).order("custom_id").execute()
        if resp and resp.data:
            for a in resp.data:
                cid = a.get("custom_id")
                cat = a.get("category", "")
                loc = a.get("location", "")
                if cid:
                    activos.append(f"{cid} ({cat} - {loc})")
    except Exception:
        pass
    return activos

def parse_dt_safe(val):
    if not val:
        return None
    try:
        return pd.to_datetime(val).to_pydatetime().replace(tzinfo=None)
    except Exception:
        return None

def enriquecer_hallazgos_con_sla(registros):
    """
    Calcula tiempos de respuesta (horas), tiempos de cierre (días/horas),
    días abiertos (Days Open) y evalúa automáticamente si un hallazgo está Past Due.
    """
    ahora = datetime.now()
    hoy = ahora.date()
    enriquecidos = []

    for r in registros:
        item = dict(r)
        status_raw = str(item.get("status", "Open"))
        is_closed = any(k in status_raw.lower() for k in ["closed", "completed", "cerrado", "fix now"])

        opened_dt = parse_dt_safe(item.get("opened_at"))
        first_resp_dt = parse_dt_safe(item.get("first_response_at"))
        closed_dt = parse_dt_safe(item.get("closed_at"))
        due_dt = parse_dt_safe(item.get("due_date"))
        due_date_obj = due_dt.date() if due_dt else None

        # Cálculo de Tiempo de Respuesta (Horas)
        resp_hours = None
        if opened_dt and first_resp_dt:
            diff_h = (first_resp_dt - opened_dt).total_seconds() / 3600.0
            resp_hours = round(max(0.0, diff_h), 1)
        item["calc_response_hours"] = resp_hours

        sla_resp_target = float(item.get("response_sla_hours") or 24)
        if resp_hours is not None:
            item["sla_response_ok"] = resp_hours <= sla_resp_target
        else:
            if opened_dt:
                elapsed_h = (ahora - opened_dt).total_seconds() / 3600.0
                item["sla_response_ok"] = False if elapsed_h > sla_resp_target else None
            else:
                item["sla_response_ok"] = None

        # Cálculo de Tiempo de Cierre (Días) y Días Abiertos (Days Open)
        close_days = None
        if opened_dt and closed_dt:
            diff_d = (closed_dt - opened_dt).total_seconds() / 86400.0
            close_days = round(max(0.0, diff_d), 1)
            days_open = int(round(max(0.0, diff_d)))
        elif opened_dt:
            days_open = max(0, (ahora - opened_dt).days)
        else:
            days_open = int(item.get("days_open") or 0)

        item["calc_close_days"] = close_days
        item["days_open"] = days_open

        # Evaluación automática de vencimiento (Past Due estilo EASE)
        is_past_due = False
        if not is_closed:
            if "past due" in status_raw.lower() or "vencido" in status_raw.lower():
                is_past_due = True
            elif due_date_obj and hoy > due_date_obj:
                is_past_due = True
                item["status_effective"] = "Past Due / Escalated"
            else:
                item["status_effective"] = status_raw
        else:
            item["status_effective"] = status_raw

        item["is_closed"] = is_closed
        item["is_past_due"] = is_past_due
        enriquecidos.append(item)

    return enriquecidos

def cargar_hallazgos_unificados():
    """Carga hallazgos desde Supabase ('esd_findings') y sincroniza con el almacén local de sesión."""
    db_rows = get_site_findings(site_id)
    if db_rows:
        codigos_db = {r.get("finding_code") for r in db_rows if r.get("finding_code")}
        locales_extra = [
            loc for loc in st.session_state.local_esd_findings
            if loc.get("finding_code") not in codigos_db and loc.get("site_id") == site_id
        ]
        combinados = db_rows + locales_extra
    else:
        combinados = [
            loc for loc in st.session_state.local_esd_findings
            if loc.get("site_id") in (site_id, None)
        ]
    return enriquecer_hallazgos_con_sla(combinados)

def cargar_lessons_learned_globales():
    """Carga las Lessons Learned de toda la compañía ('company_lessons_learned') + sesión local."""
    db_ll = get_company_lessons_learned(company_id)
    if db_ll:
        codigos_db = {r.get("lesson_code") for r in db_ll if r.get("lesson_code")}
        locales_extra = [
            loc for loc in st.session_state.local_company_lessons
            if loc.get("lesson_code") not in codigos_db
        ]
        return db_ll + locales_extra
    return list(st.session_state.local_company_lessons)

def render_evidence_preview(url_or_data: str, caption: str = "Evidencia"):
    """Muestra vista previa de imagen o enlace de descarga para PDF/documentos del bucket de Supabase."""
    if not url_or_data or str(url_or_data).strip() in ["", "None", "null", "N/D"]:
        st.caption(f"*{caption}: Sin archivo adjunto.*")
        return

    url_str = str(url_or_data).strip()
    is_img = (
        url_str.startswith("data:image/")
        or any(url_str.lower().split("?")[0].endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"])
    )
    if is_img:
        st.image(url_str, caption=caption, use_container_width=True)
    elif url_str.startswith("data:application/pdf"):
        st.markdown(f"📄 **{caption}:** Documento PDF almacenado en sesión.")
        st.markdown(f'<a href="{url_str}" download="evidencia.pdf">📥 Descargar PDF de Evidencia</a>', unsafe_allow_html=True)
    else:
        st.markdown(f"📎 **{caption}:** [🔗 Abrir / Descargar Archivo en Supabase Bucket]({url_str})")

# ==========================================
# 5. ENCABEZADO DEL MÓDULO
# ==========================================
st.markdown(f"### 🎯 {t('findings', 'title', 'Seguimiento de Hallazgos EASE, Acciones Correctivas y Lessons Learned')}")
st.caption(
    f"Gestión integral de mitigaciones estilo **EASE Audit**: Apertura con evidencia en Supabase Storage, "
    f"control de SLA (Respuesta y Cierre), CAPA/8D y **Lessons Learned Globales** — "
    f"Planta activa: **{site_name}** | Compañía: **{company_name}**"
)

hallazgos_lista = cargar_hallazgos_unificados()
lessons_lista = cargar_lessons_learned_globales()

tab_ease_dash, tab_open_finding, tab_capa_tracking, tab_lessons_global = st.tabs([
    "📊 Tablero EASE & Directorio",
    "🚨 Apertura de Hallazgo (+ Evidencia)",
    "🛠️ Mitigación, SLA y Acciones Correctivas",
    f"🌐 Lessons Learned Globales ({len(lessons_lista)})",
])

# ==============================================================================
# PESTAÑA 1: TABLERO DE CONTROL EASE & DIRECTORIO DE MITIGACIONES
# ==============================================================================
with tab_ease_dash:
    # --- KPIs EJECUTIVOS ESTILO EASE AUDIT ---
    total_f = len(hallazgos_lista)
    cerrados_f = [h for h in hallazgos_lista if h["is_closed"]]
    abiertos_f = [h for h in hallazgos_lista if not h["is_closed"]]
    vencidos_f = [h for h in abiertos_f if h["is_past_due"]]
    en_tiempo_f = [h for h in abiertos_f if not h["is_past_due"]]

    tiempos_resp = [h["calc_response_hours"] for h in hallazgos_lista if h.get("calc_response_hours") is not None]
    avg_resp_h = round(sum(tiempos_resp) / len(tiempos_resp), 1) if tiempos_resp else 0.0

    tiempos_cierre = [h["calc_close_days"] for h in cerrados_f if h.get("calc_close_days") is not None]
    avg_close_d = round(sum(tiempos_cierre) / len(tiempos_cierre), 1) if tiempos_cierre else 0.0

    tasa_cierre = round((len(cerrados_f) / total_f) * 100.0, 1) if total_f > 0 else 100.0

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("📋 Total Hallazgos", total_f)
    k2.metric("🟢 Cerrados / Verificados", len(cerrados_f), f"{tasa_cierre}% Cierre")
    k3.metric("🟡 En Proceso (On Time)", len(en_tiempo_f))
    k4.metric(
        "🔴 Vencidos (Past Due)",
        len(vencidos_f),
        delta="Atención Inmediata" if len(vencidos_f) > 0 else "0 Vencidos",
        delta_color="inverse" if len(vencidos_f) > 0 else "normal",
    )
    k5.metric("⏱️ Respuesta Promedio", f"{avg_resp_h} h", help="Tiempo promedio entre la apertura del hallazgo y la 1ra respuesta/contención.")
    k6.metric("🏁 Tiempo Promedio Cierre", f"{avg_close_d} días", help="Cycle Time promedio desde apertura hasta verificación de cierre.")

    st.divider()

    if hallazgos_lista:
        df_h = pd.DataFrame(hallazgos_lista)

        # --- GRÁFICOS DE ANÁLISIS EASE ---
        g_col1, g_col2, g_col3 = st.columns([1.1, 1.3, 1.1])

        with g_col1:
            df_est = df_h["status_effective"].value_counts().reset_index()
            df_est.columns = ["Estatus EASE", "Cantidad"]
            color_map_status = {
                "Closed / Completed": "#28a745",
                "Fix Now (Point of Cause)": "#20c997",
                "In Progress / Containment": "#ffc107",
                "Pending Verification": "#17a2b8",
                "Open": "#0d6efd",
                "Past Due / Escalated": "#dc3545",
                "Rejected / Reopened": "#6f42c1",
            }
            fig_donut = px.pie(
                df_est,
                values="Cantidad",
                names="Estatus EASE",
                title="Estado de Mitigaciones (EASE Workflow)",
                hole=0.48,
                color="Estatus EASE",
                color_discrete_map=color_map_status,
            )
            fig_donut.update_layout(margin=dict(t=35, b=10, l=10, r=10), height=300)
            st.plotly_chart(fig_donut, use_container_width=True)

        with g_col2:
            df_par = df_h["question_title"].fillna("Sin Categoría").value_counts().head(8).reset_index()
            df_par.columns = ["Requisito / Categoría ESD", "Hallazgos"]
            fig_pareto = px.bar(
                df_par,
                x="Hallazgos",
                y="Requisito / Categoría ESD",
                orientation="h",
                title="Pareto Top Categorías de Hallazgo",
                text_auto=True,
                color="Hallazgos",
                color_continuous_scale="Blues",
            )
            fig_pareto.update_layout(
                yaxis={"categoryorder": "total ascending"},
                margin=dict(t=35, b=10, l=10, r=10),
                coloraxis_showscale=False,
                height=300,
            )
            st.plotly_chart(fig_pareto, use_container_width=True)

        with g_col3:
            df_sev = df_h.groupby(["severity", "status_effective"]).size().reset_index(name="Cantidad")
            fig_sev = px.bar(
                df_sev,
                x="severity",
                y="Cantidad",
                color="status_effective",
                barmode="stack",
                title="Severidad vs. Estatus Actual",
                color_discrete_map=color_map_status,
                labels={"severity": "Severidad", "status_effective": "Estatus"},
            )
            fig_sev.update_layout(margin=dict(t=35, b=10, l=10, r=10), height=300)
            st.plotly_chart(fig_sev, use_container_width=True)

        # --- BARRA DE FILTROS MULTICRITERIO ESTILO EASE AUDIT ---
        st.markdown("#### 🔍 Consola de Seguimiento y Filtros EASE (Mitigation Tracking)")
        f1, f2, f3, f4, f5 = st.columns([1.2, 1, 1.1, 1.1, 1.4])

        opciones_est = ["Todos", "🔥 Solo Abiertos / Activos", "🔴 Solo Vencidos (Past Due)"] + sorted(df_h["status_effective"].dropna().unique().tolist())
        sel_est = f1.selectbox("Estatus EASE:", options=opciones_est)

        opciones_sev = ["Todas"] + [k for k in ["Critical", "Major", "Minor", "Observation"] if k in df_h["severity"].dropna().unique()]
        sel_sev = f2.selectbox("Severidad:", options=opciones_sev)

        opciones_loc = ["Todas"] + sorted(df_h["location"].dropna().unique().tolist())
        sel_loc = f3.selectbox("Línea / Ubicación:", options=opciones_loc)

        opciones_mit = ["Todos"] + sorted(df_h["mitigation_type"].dropna().unique().tolist())
        sel_mit = f4.selectbox("Tipo de Mitigación:", options=opciones_mit)

        busqueda_txt = f5.text_input("🔎 Buscar por Folio, Responsable o Descripción:", placeholder="Ej. EASE-2026, Ionizador...")

        df_filtrado = df_h.copy()
        if sel_est == "🔥 Solo Abiertos / Activos":
            df_filtrado = df_filtrado[~df_filtrado["is_closed"]]
        elif sel_est == "🔴 Solo Vencidos (Past Due)":
            df_filtrado = df_filtrado[df_filtrado["is_past_due"]]
        elif sel_est != "Todos":
            df_filtrado = df_filtrado[df_filtrado["status_effective"] == sel_est]

        if sel_sev != "Todas":
            df_filtrado = df_filtrado[df_filtrado["severity"] == sel_sev]
        if sel_loc != "Todas":
            df_filtrado = df_filtrado[df_filtrado["location"] == sel_loc]
        if sel_mit != "Todos":
            df_filtrado = df_filtrado[df_filtrado["mitigation_type"] == sel_mit]
        if busqueda_txt.strip():
            patron = busqueda_txt.strip().lower()
            mask_txt = (
                df_filtrado["finding_code"].astype(str).str.lower().str.contains(patron, na=False)
                | df_filtrado["finding_description"].astype(str).str.lower().str.contains(patron, na=False)
                | df_filtrado["responsible_party"].astype(str).str.lower().str.contains(patron, na=False)
                | df_filtrado["question_title"].astype(str).str.lower().str.contains(patron, na=False)
            )
            df_filtrado = df_filtrado[mask_txt]

        # Formatear tabla estilo EASE
        df_vista = pd.DataFrame({
            "Folio ID": df_filtrado["finding_code"],
            "Estatus EASE": df_filtrado["status_effective"].apply(
                lambda s: f"🔴 {s}" if "Past Due" in str(s) else (
                    f"🟢 {s}" if ("Closed" in str(s) or "Fix Now" in str(s)) else f"🟡 {s}"
                )
            ),
            "Severidad": df_filtrado["severity"],
            "Tipo Mitigación": df_filtrado["mitigation_type"],
            "Ubicación": df_filtrado["location"],
            "Requisito / Categoría": df_filtrado["question_title"],
            "Responsable": df_filtrado["responsible_party"],
            "Apertura": df_filtrado["opened_at"],
            "Fecha Compromiso": df_filtrado["due_date"],
            "Días Abierto": df_filtrado["days_open"],
            "T. Respuesta (h)": df_filtrado["calc_response_hours"].apply(lambda x: f"{x} h" if pd.notna(x) else "Pendiente"),
            "T. Cierre (d)": df_filtrado["calc_close_days"].apply(lambda x: f"{x} d" if pd.notna(x) else "-"),
            "Descripción del Hallazgo": df_filtrado["finding_description"],
        })

        st.dataframe(df_vista, use_container_width=True, hide_index=True)

        col_exp1, col_exp2 = st.columns([1, 2])
        with col_exp1:
            csv_export = df_filtrado.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Exportar Matriz EASE (.CSV)",
                data=csv_export,
                file_name=f"EASE_Findings_{site_name}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
    else:
        st.info("No hay hallazgos registrados en esta planta todavía. Usa la pestaña **🚨 Apertura de Hallazgo** para crear el primero.")

    # --- SINCRONIZADOR DE ARCHIVOS CSV EXPORTADOS DESDE EASE AUDIT ---
    with st.expander("📥 Importar / Sincronizar Reporte CSV directo desde EASE Audit"):
        st.caption("Compatible con exportaciones estándar de EASE (`ID`, `Status`, `Location`, `Question Title`, `Responsible Party`, `Finding Comment`, `Due Date`, `Days Open`).")
        csv_ease_file = st.file_uploader("Seleccionar archivo CSV de EASE Audit", type=["csv"], key="ease_csv_sync")
        if csv_ease_file is not None:
            if st.button("🔄 Procesar y Sincronizar Hallazgos EASE", type="primary"):
                try:
                    df_csv = pd.read_csv(csv_ease_file)
                    df_csv.columns = [str(c).strip() for c in df_csv.columns]
                    nuevos_importados = 0
                    for idx, row in df_csv.iterrows():
                        f_code = str(row.get("ID") or row.get("finding_code") or f"EASE-CSV-{idx+1}").strip()
                        nuevo_item = {
                            "finding_code": f_code,
                            "site_id": site_id,
                            "site_name": site_name,
                            "company_id": company_id,
                            "assessment_type": str(row.get("Assessment Description") or "EASE Audit Import"),
                            "question_title": str(row.get("Question Title") or row.get("Category") or "General ESD"),
                            "location": str(row.get("Location") or "PLANTA"),
                            "station_or_asset": str(row.get("Station") or "N/A"),
                            "severity": str(row.get("Severity") or "Major"),
                            "mitigation_type": str(row.get("Mitigation Type") or "Action Required (Short-Term)"),
                            "status": str(row.get("Status") or row.get("Estatus") or "Open"),
                            "opened_by": str(row.get("Auditor") or user_name),
                            "responsible_party": str(row.get("Responsible Party") or "Por Asignar"),
                            "escalation_owner": "Calidad ESD",
                            "opened_at": str(row.get("Created Date") or datetime.now().strftime("%Y-%m-%d %H:%M")),
                            "response_sla_hours": 24,
                            "first_response_at": None,
                            "due_date": str(row.get("Due Date") or (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")),
                            "closed_at": None,
                            "measured_value": "Importado desde EASE CSV",
                            "finding_description": str(row.get("Finding Comment") or row.get("Description") or "Hallazgo importado de EASE."),
                            "containment_action": "",
                            "root_cause_6m": "Sin Clasificar",
                            "root_cause_detail": "",
                            "corrective_action": str(row.get("Resolution") or ""),
                            "preventive_action": "",
                            "verification_comments": "",
                            "evidence_before_url": "",
                            "evidence_after_url": "",
                            "storage_bucket": "evidencias_hallazgos",
                            "is_lesson_learned": False,
                        }
                        try:
                            supabase.table("esd_findings").upsert(nuevo_item, on_conflict="finding_code").execute()
                        except Exception:
                            pass
                        st.session_state.local_esd_findings.insert(0, nuevo_item)
                        nuevos_importados += 1
                    st.success(f"✅ Se sincronizaron {nuevos_importados} hallazgos desde el archivo EASE CSV.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al importar el CSV de EASE: {e}")


# ==============================================================================
# PESTAÑA 2: APERTURA DE HALLAZGO CON EVIDENCIA EN SUPABASE BUCKET
# ==============================================================================
with tab_open_finding:
    st.markdown("#### 🚨 Apertura de Nuevo Hallazgo / No Conformidad ESD (EASE Format)")
    st.info(
        "Registra las desviaciones detectadas en piso, asigna responsable y tiempos compromiso (SLA), "
        "y sube la evidencia fotográfica o documental directamente al bucket de **Supabase Storage**."
    )

    # Selección previa de Severidad y Elemento ESD para mostrar SLA y límite normativo en tiempo real
    pre_c1, pre_c2, pre_c3 = st.columns([1.3, 1.3, 1.4])
    elementos_esd_lista = list(INFO_ELEMENTOS_ESD.keys()) + ["Entrenamiento / Certificación", "Señalización / 5S EPA", "Otro Requisito S20.20"]
    sel_elemento_apertura = pre_c1.selectbox("🔍 Categoría / Elemento Auditado (Question Title):", options=elementos_esd_lista)

    sel_severidad_apertura = pre_c2.selectbox(
        "⚡ Severidad del Hallazgo (EASE Priority):",
        options=list(EASE_SEVERITY_SLA.keys()),
        index=1,
        format_func=lambda k: EASE_SEVERITY_SLA[k]["label"],
    )

    sel_mitigacion_apertura = pre_c3.selectbox(
        "🛠️ Tipo de Mitigación EASE:",
        options=EASE_MITIGATION_TYPES,
        help="Fix Now: Corregido durante la auditoría | Action Required: Acción con fecha compromiso | CAPA / 8D: Análisis de Causa Raíz y Acción Sistémica.",
    )

    # Tarjeta informativa de referencia normativa y SLA automático
    info_norma = INFO_ELEMENTOS_ESD.get(sel_elemento_apertura, {
        "limite": "Cumplimiento ANSI/ESD S20.20",
        "metodo": "Inspección / Verificación en Piso",
        "frecuencia": "Periódica"
    })
    sla_cfg = EASE_SEVERITY_SLA[sel_severidad_apertura]
    fecha_compromiso_sugerida = (datetime.now() + timedelta(days=sla_cfg["close_days"])).date()

    st.markdown(
        f"""
        <div style="padding:10px 14px; border-radius:8px; background-color:rgba(13,110,253,0.08); border-left:4px solid {sla_cfg['color']}; margin-bottom:12px;">
            <b>📏 Referencia Normativa ({sel_elemento_apertura}):</b> Límite: <code>{info_norma['limite']}</code> | Método: <code>{info_norma['metodo']}</code>
            &nbsp;&nbsp;|&nbsp;&nbsp;
            <b>⏱️ SLA Sugerido ({sel_severidad_apertura}):</b> 1ra Respuesta ≤ <b>{sla_cfg['resp_hours']} h</b> / Cierre ≤ <b>{sla_cfg['close_days']} días</b> ({fecha_compromiso_sugerida})
        </div>
        """,
        unsafe_allow_html=True,
    )

    lineas_planta = obtener_lineas_planta()
    usuarios_planta = obtener_usuarios_planta()
    activos_planta = obtener_activos_planta()
    folio_sugerido = f"EASE-{datetime.now().strftime('%Y')}-{100 + len(hallazgos_lista) + 1:04d}"

    with st.form("form_apertura_hallazgo_ease", clear_on_submit=False):
        f_col1, f_col2, f_col3 = st.columns(3)
        folio_input = f_col1.text_input("🆔 Folio del Hallazgo (ID)", value=folio_sugerido)
        assessment_input = f_col2.selectbox("📋 Tipo de Auditoría (Assessment)", options=EASE_ASSESSMENT_TYPES)
        bucket_target = f_col3.selectbox(
            "☁️ Bucket de Supabase Storage",
            options=["evidencias_hallazgos", "evidencias_esd", "reportes_calificacion"],
            help="Nombre del bucket en Supabase Storage donde se alojarán los archivos de evidencia.",
        )

        loc_col1, loc_col2, loc_col3 = st.columns(3)
        linea_sel = loc_col1.selectbox("🏭 Línea / Ubicación (Location)", options=lineas_planta + ["Otra Ubicación (Especificar en estación)"])
        activo_sel = loc_col2.selectbox("🔩 Activo / Equipo Asociado (Opcional)", options=activos_planta)
        estacion_detalle = loc_col3.text_input("📍 Estación / Punto Específico", placeholder="Ej. Estación #3 / Mesa de Retoque")

        resp_col1, resp_col2, resp_col3, resp_col4 = st.columns([1.4, 1.2, 0.9, 1.0])
        responsable_sel = resp_col1.selectbox("👤 Responsable Asignado (Responsible Party)", options=usuarios_planta + ["Otro (Especificar en Escalación)"])
        escalacion_input = resp_col2.text_input("📣 Escalación / Supervisor", value="Supervisión Calidad / Ingeniería ESD")
        sla_horas_input = resp_col3.number_input("⏱️ Meta Respuesta (Horas)", min_value=1, max_value=720, value=int(sla_cfg["resp_hours"]))
        due_date_input = resp_col4.date_input("📅 Fecha Compromiso Cierre", value=fecha_compromiso_sugerida)

        med_col1, med_col2 = st.columns([1, 2])
        valor_medido_input = med_col1.text_input(
            "⚡ Lectura / Valor Medido vs. Norma",
            placeholder=f"Ej. Lectura fuera de {info_norma['limite']}",
        )
        contencion_inicial_input = med_col2.text_input(
            "🛡️ Acción de Contención Inmediata (Si se realizó en el momento)",
            placeholder="Ej. Se retiró el material aislante / Se reemplazó talonera...",
        )

        descripcion_input = st.text_area(
            "📝 Descripción Detallada del Hallazgo (Finding Comment / Non-Conformance)",
            height=100,
            placeholder="Describe qué se encontró, en qué proceso u operación, y cuál es el riesgo hacia el producto electrónico sensible (ESDS)...",
        )

        st.markdown("##### 📸 Evidencia de Apertura (Almacenamiento en Bucket de Supabase)")
        ev_col1, ev_col2 = st.columns(2)
        with ev_col1:
            archivo_evidencia_open = st.file_uploader(
                "📤 Subir Archivo de Evidencia (Foto JPG/PNG, PDF, Reporte)",
                type=["jpg", "jpeg", "png", "webp", "pdf", "xlsx", "docx"],
                key="upload_open_evidence",
            )
        with ev_col2:
            usar_camara_open = st.checkbox("📷 Habilitar cámara del dispositivo para tomar foto en vivo", value=False)
            foto_camara_open = st.camera_input("Capturar evidencia en piso") if usar_camara_open else None

        btn_abrir_hallazgo = st.form_submit_button("🚀 Registrar Hallazgo y Subir Evidencia a Supabase", type="primary", use_container_width=True)

        if btn_abrir_hallazgo:
            if not descripcion_input.strip():
                st.error("⚠️ La descripción del hallazgo es obligatoria.")
            else:
                with st.spinner("Subiendo evidencia al bucket de Supabase y registrando hallazgo..."):
                    ahora_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                    evidencia_file = foto_camara_open if foto_camara_open is not None else archivo_evidencia_open
                    url_evidencia_open = ""
                    bucket_usado = bucket_target

                    if evidencia_file is not None:
                        url_evidencia_open, b_used, err_up = upload_finding_evidence(
                            evidencia_file,
                            finding_id=folio_input.strip(),
                            stage="open",
                            bucket_name=bucket_target,
                        )
                        if b_used:
                            bucket_usado = b_used
                        if err_up and b_used == "local_session_cache":
                            st.warning(f"ℹ️ El bucket '{bucket_target}' aún no responde en Supabase ({err_up}). La evidencia quedó respaldada en sesión activa.")

                    # Determinar estatus inicial según tipo de mitigación EASE y contención
                    if sel_mitigacion_apertura == "Fix Now / Point of Cause":
                        estatus_inicial = "Fix Now (Point of Cause)"
                        first_resp_str = ahora_str
                        closed_str = ahora_str
                    elif contencion_inicial_input.strip():
                        estatus_inicial = "In Progress / Containment"
                        first_resp_str = ahora_str
                        closed_str = None
                    else:
                        estatus_inicial = "Open"
                        first_resp_str = None
                        closed_str = None

                    estacion_final = estacion_detalle.strip() if estacion_detalle.strip() else activo_sel

                    nuevo_hallazgo = {
                        "finding_code": folio_input.strip().upper(),
                        "site_id": site_id,
                        "site_name": site_name,
                        "company_id": company_id,
                        "assessment_type": assessment_input,
                        "question_title": sel_elemento_apertura,
                        "location": linea_sel.strip().upper(),
                        "station_or_asset": estacion_final,
                        "severity": sel_severidad_apertura,
                        "mitigation_type": sel_mitigacion_apertura,
                        "status": estatus_inicial,
                        "opened_by": user_name,
                        "responsible_party": responsable_sel,
                        "escalation_owner": escalacion_input.strip(),
                        "opened_at": ahora_str,
                        "response_sla_hours": int(sla_horas_input),
                        "first_response_at": first_resp_str,
                        "due_date": due_date_input.strftime("%Y-%m-%d"),
                        "closed_at": closed_str,
                        "measured_value": valor_medido_input.strip() or f"Ref: {info_norma['limite']}",
                        "finding_description": descripcion_input.strip(),
                        "containment_action": contencion_inicial_input.strip(),
                        "root_cause_6m": "Sin Clasificar",
                        "root_cause_detail": "",
                        "corrective_action": contencion_inicial_input.strip() if sel_mitigacion_apertura == "Fix Now / Point of Cause" else "",
                        "preventive_action": "",
                        "verification_comments": "Mitigado en punto de causa (Fix Now)." if sel_mitigacion_apertura == "Fix Now / Point of Cause" else "",
                        "evidence_before_url": url_evidencia_open,
                        "evidence_after_url": "",
                        "storage_bucket": bucket_usado,
                        "is_lesson_learned": False,
                    }

                    try:
                        supabase.table("esd_findings").insert(nuevo_hallazgo).execute()
                    except Exception:
                        pass

                    st.session_state.local_esd_findings.insert(0, nuevo_hallazgo)
                    st.success(
                        f"✅ Hallazgo **{nuevo_hallazgo['finding_code']}** abierto exitosamente con estatus **{estatus_inicial}** "
                        f"(Fecha compromiso: **{nuevo_hallazgo['due_date']}**)."
                    )
                    st.rerun()


# ==============================================================================
# PESTAÑA 3: MITIGACIÓN, TIEMPOS DE RESPUESTA/CIERRE Y ACCIONES CORRECTIVAS
# ==============================================================================
with tab_capa_tracking:
    st.markdown("#### 🛠️ Gestión de Mitigación, Tiempos de Respuesta/Cierre (SLA) y CAPA / 8D")

    if not hallazgos_lista:
        st.info("No hay hallazgos registrados para dar seguimiento.")
    else:
        # Ordenar priorizando vencidos y abiertos primero
        hallazgos_ordenados = sorted(
            hallazgos_lista,
            key=lambda x: (0 if x["is_past_due"] else (1 if not x["is_closed"] else 2), x.get("finding_code", "")),
        )

        opciones_selector = {
            h["finding_code"]: (
                f"{'🔴 [PAST DUE]' if h['is_past_due'] else ('🟢 [CERRADO]' if h['is_closed'] else '🟡 [ABIERTO]')} "
                f"{h['finding_code']} | {h['location']} - {h['question_title']} ({h['severity']}) → Resp: {h['responsible_party']}"
            )
            for h in hallazgos_ordenados
        }

        cod_seleccionado = st.selectbox(
            "🎯 Selecciona el Hallazgo para actualizar Acciones Correctivas, Tiempos o Evidencia de Cierre:",
            options=list(opciones_selector.keys()),
            format_func=lambda k: opciones_selector[k],
        )

        hallazgo_sel = next((h for h in hallazgos_ordenados if h["finding_code"] == cod_seleccionado), hallazgos_ordenados[0])

        # --- TARJETA DE CRONÓMETRO SLA Y TIEMPOS DE RESPUESTA / CIERRE ---
        with st.container(border=True):
            st.markdown(f"##### ⏱️ Cronómetro de SLA y Ciclo de Vida — **{hallazgo_sel['finding_code']}** ({hallazgo_sel['assessment_type']})")
            t1, t2, t3, t4, t5 = st.columns(5)

            t1.metric("📅 Fecha Apertura", hallazgo_sel.get("opened_at", "N/D"))

            resp_h_val = hallazgo_sel.get("calc_response_hours")
            meta_h_val = hallazgo_sel.get("response_sla_hours", 24)
            if resp_h_val is not None:
                cumple_sla_r = resp_h_val <= float(meta_h_val)
                t2.metric(
                    "⚡ Tiempo de Respuesta",
                    f"{resp_h_val} h",
                    delta=f"Meta ≤ {meta_h_val}h ({'En SLA' if cumple_sla_r else 'Fuera SLA'})",
                    delta_color="normal" if cumple_sla_r else "inverse",
                )
            else:
                t2.metric("⚡ Tiempo de Respuesta", "Sin Respuesta", delta=f"Meta ≤ {meta_h_val}h", delta_color="inverse")

            t3.metric(
                "📆 Fecha Compromiso",
                hallazgo_sel.get("due_date", "N/D"),
                delta="🔴 VENCIDO (Past Due)" if hallazgo_sel["is_past_due"] else ("🟢 Cerrado" if hallazgo_sel["is_closed"] else "En Tiempo"),
                delta_color="inverse" if hallazgo_sel["is_past_due"] else "normal",
            )

            t4.metric("⏳ Días Abierto (Days Open)", f"{hallazgo_sel.get('days_open', 0)} días")

            cierre_d_val = hallazgo_sel.get("calc_close_days")
            t5.metric(
                "🏁 Tiempo Total Cierre",
                f"{cierre_d_val} días" if cierre_d_val is not None else "En Proceso",
                delta=hallazgo_sel.get("closed_at") or "Abierto",
            )

            st.markdown(
                f"**📍 Ubicación:** `{hallazgo_sel.get('location')}` — `{hallazgo_sel.get('station_or_asset')}` &nbsp;|&nbsp; "
                f"**⚡ Lectura / Condición:** `{hallazgo_sel.get('measured_value', 'N/D')}` &nbsp;|&nbsp; "
                f"**👤 Responsable:** `{hallazgo_sel.get('responsible_party')}` &nbsp;|&nbsp; "
                f"**📣 Escalación:** `{hallazgo_sel.get('escalation_owner', 'N/D')}`"
            )
            st.info(f"**Descripción del Hallazgo:** {hallazgo_sel.get('finding_description', '')}")

        # --- COMPARADOR VISUAL DE EVIDENCIAS (ANTES VS DESPUÉS EN SUPABASE BUCKET) ---
        with st.expander("🖼️ Galería de Evidencias en Supabase Storage (Antes vs. Después)", expanded=True):
            ev_v1, ev_v2 = st.columns(2)
            with ev_v1:
                st.markdown("###### 📸 Evidencia de Apertura (Before / Condición Encontrada)")
                render_evidence_preview(hallazgo_sel.get("evidence_before_url"), "Evidencia de Apertura")
            with ev_v2:
                st.markdown("###### ✅ Evidencia de Cierre / Mitigación (After / Acción Implementada)")
                render_evidence_preview(hallazgo_sel.get("evidence_after_url"), "Evidencia de Cierre")

        # --- FORMULARIO DE ACCIONES CORRECTIVAS, CAUSA RAÍZ, TIEMPOS Y CIERRE ---
        with st.form(f"form_update_capa_{cod_seleccionado}"):
            st.markdown("##### 📝 Plan de Mitigación EASE, Causa Raíz (6M / 5 Porqués) y Cierre")

            u_col1, u_col2, u_col3 = st.columns(3)
            estatus_actual_val = hallazgo_sel.get("status", "Open")
            idx_est = EASE_STATUS_OPTIONS.index(estatus_actual_val) if estatus_actual_val in EASE_STATUS_OPTIONS else 0
            nuevo_estatus = u_col1.selectbox("🔄 Estatus de Seguimiento EASE:", options=EASE_STATUS_OPTIONS, index=idx_est)

            rc_actual = hallazgo_sel.get("root_cause_6m", "Sin Clasificar")
            idx_6m = ROOT_CAUSE_6M.index(rc_actual) if rc_actual in ROOT_CAUSE_6M else 0
            nueva_causa_6m = u_col2.selectbox("🧠 Categoría Causa Raíz (Ishikawa 6M):", options=ROOT_CAUSE_6M, index=idx_6m)

            nuevo_responsable = u_col3.text_input("👤 Responsable de Mitigación:", value=hallazgo_sel.get("responsible_party", ""))

            # Control explícito de Tiempos de Respuesta y Cierre
            tm_col1, tm_col2, tm_col3 = st.columns(3)
            tiene_resp_previa = bool(hallazgo_sel.get("first_response_at"))
            registrar_1ra_resp = tm_col1.checkbox(
                "⚡ Marcar / Actualizar Timestamp de 1ra Respuesta ahora",
                value=not tiene_resp_previa,
                help="Si el hallazgo aún no tenía primera respuesta registrada, calcula el tiempo de respuesta a partir de este momento.",
            )
            due_actual_dt = parse_dt_safe(hallazgo_sel.get("due_date"))
            nueva_due_date = tm_col2.date_input(
                "📅 Fecha Compromiso (Due Date):",
                value=due_actual_dt.date() if due_actual_dt else datetime.now().date(),
            )
            marcar_cierre_ahora = tm_col3.checkbox(
                "🏁 Registrar Timestamp de Cierre Oficial al guardar",
                value=("Closed" in nuevo_estatus or "Fix Now" in nuevo_estatus),
            )

            nueva_contencion = st.text_area(
                "1️⃣ Acción de Contención Inmediata (Containment / Point of Cause):",
                value=hallazgo_sel.get("containment_action", ""),
                height=68,
                placeholder="Acción inmediata para aislar el efecto y proteger las tarjetas ESDS...",
            )

            nuevo_5whys = st.text_area(
                "2️⃣ Análisis de Causa Raíz (5 Porqués / Root Cause Analysis):",
                value=hallazgo_sel.get("root_cause_detail", ""),
                height=80,
                placeholder="1. ¿Por qué ocurrió la falla? ... 2. ¿Por qué no se detectó? ... 3. ¿Por qué el sistema lo permitió? ...",
            )

            ca_col1, ca_col2 = st.columns(2)
            nueva_correctiva = ca_col1.text_area(
                "3️⃣ Acción Correctiva Definitiva (Corrective Action):",
                value=hallazgo_sel.get("corrective_action", ""),
                height=85,
                placeholder="Acción técnica que elimina la causa raíz detectada...",
            )
            nueva_preventiva = ca_col2.text_area(
                "4️⃣ Acción Preventiva / Sistémica (Preventive Action):",
                value=hallazgo_sel.get("preventive_action", ""),
                height=85,
                placeholder="Actualización de ayuda visual, frecuencia TR53, Poka-Yoke o entrenamiento...",
            )

            nuevos_comentarios_verif = st.text_input(
                "5️⃣ Verificación de Eficacia del Auditor (Lectura posterior, firma de conformidad):",
                value=hallazgo_sel.get("verification_comments", ""),
                placeholder="Ej. Verificado en piso con megger calibrado: lectura 4.2x10^6 Ohms (PASS).",
            )

            st.markdown("###### 📤 Adjuntar Evidencia de Cierre / Mitigación (After) o Actualizar Evidencia de Apertura")
            up_c1, up_c2 = st.columns(2)
            file_ev_after = up_c1.file_uploader(
                "✅ Subir Evidencia de Cierre / Acción Implementada (After)",
                type=["jpg", "jpeg", "png", "webp", "pdf", "xlsx", "docx"],
                key=f"ev_after_{cod_seleccionado}",
            )
            file_ev_before_replace = up_c2.file_uploader(
                "📸 Reemplazar / Agregar Evidencia de Apertura (Before - Opcional)",
                type=["jpg", "jpeg", "png", "webp", "pdf", "xlsx", "docx"],
                key=f"ev_before_upd_{cod_seleccionado}",
            )

            st.divider()
            promover_ll = st.checkbox(
                "🌐 Publicar / Actualizar este caso en el catálogo de **Lessons Learned Globales de la Compañía (Yokoten)**",
                value=bool(hallazgo_sel.get("is_lesson_learned", False)),
            )
            beneficio_ll_input = st.text_input(
                "💡 Impacto / Lección Clave para otras plantas de la Compañía (si se publica como Lesson Learned):",
                placeholder="Ej. Estandarizar protección en conectores de monitores continuos en todas las líneas SMT corporativas.",
            )

            btn_guardar_capa = st.form_submit_button("💾 Guardar Seguimiento, Tiempos y Evidencias", type="primary", use_container_width=True)

            if btn_guardar_capa:
                with st.spinner("Actualizando expediente de hallazgo y sincronizando con Supabase..."):
                    ahora_upd = datetime.now().strftime("%Y-%m-%d %H:%M")
                    bucket_pref = hallazgo_sel.get("storage_bucket") or "evidencias_hallazgos"

                    url_after_final = hallazgo_sel.get("evidence_after_url", "")
                    if file_ev_after is not None:
                        u_aft, _, _ = upload_finding_evidence(file_ev_after, cod_seleccionado, stage="close", bucket_name=bucket_pref)
                        if u_aft:
                            url_after_final = u_aft

                    url_before_final = hallazgo_sel.get("evidence_before_url", "")
                    if file_ev_before_replace is not None:
                        u_bef, _, _ = upload_finding_evidence(file_ev_before_replace, cod_seleccionado, stage="open", bucket_name=bucket_pref)
                        if u_bef:
                            url_before_final = u_bef

                    first_resp_final = hallazgo_sel.get("first_response_at")
                    if not first_resp_final and (registrar_1ra_resp or nueva_contencion.strip() or nuevo_estatus != "Open"):
                        first_resp_final = ahora_upd
                    elif registrar_1ra_resp and not tiene_resp_previa:
                        first_resp_final = ahora_upd

                    closed_at_final = hallazgo_sel.get("closed_at")
                    if marcar_cierre_ahora or ("Closed" in nuevo_estatus or "Fix Now" in nuevo_estatus):
                        if not closed_at_final:
                            closed_at_final = ahora_upd
                    elif "Open" in nuevo_estatus or "In Progress" in nuevo_estatus or "Reopened" in nuevo_estatus:
                        closed_at_final = None

                    datos_actualizados = {
                        "status": nuevo_estatus,
                        "responsible_party": nuevo_responsable.strip(),
                        "first_response_at": first_resp_final,
                        "due_date": nueva_due_date.strftime("%Y-%m-%d"),
                        "closed_at": closed_at_final,
                        "containment_action": nueva_contencion.strip(),
                        "root_cause_6m": nueva_causa_6m,
                        "root_cause_detail": nuevo_5whys.strip(),
                        "corrective_action": nueva_correctiva.strip(),
                        "preventive_action": nueva_preventiva.strip(),
                        "verification_comments": nuevos_comentarios_verif.strip(),
                        "evidence_before_url": url_before_final,
                        "evidence_after_url": url_after_final,
                        "is_lesson_learned": promover_ll,
                    }

                    try:
                        supabase.table("esd_findings").update(datos_actualizados).eq("finding_code", cod_seleccionado).execute()
                    except Exception:
                        pass

                    # Actualizar en sesión local
                    encontrado_local = False
                    for loc_item in st.session_state.local_esd_findings:
                        if loc_item.get("finding_code") == cod_seleccionado:
                            loc_item.update(datos_actualizados)
                            encontrado_local = True
                            break
                    if not encontrado_local:
                        copia_item = dict(hallazgo_sel)
                        copia_item.update(datos_actualizados)
                        st.session_state.local_esd_findings.insert(0, copia_item)

                    # Si se marcó como Lesson Learned Global, publicar/actualizar en el catálogo corporativo
                    if promover_ll:
                        ll_code = f"LL-GLOBAL-{cod_seleccionado}"
                        nueva_ll_corp = {
                            "lesson_code": ll_code,
                            "company_id": company_id,
                            "company_name": company_name,
                            "origin_site_id": site_id,
                            "origin_site_name": site_name,
                            "source_finding_code": cod_seleccionado,
                            "esd_category": hallazgo_sel.get("question_title", "General ESD"),
                            "process_area": hallazgo_sel.get("location", "Planta"),
                            "severity": hallazgo_sel.get("severity", "Major"),
                            "title": f"{hallazgo_sel.get('question_title')} en {hallazgo_sel.get('location')}: {nueva_correctiva[:90] or hallazgo_sel.get('finding_description', '')[:90]}",
                            "problem_description": hallazgo_sel.get("finding_description", ""),
                            "root_cause_6m": nueva_causa_6m,
                            "root_cause_analysis": nuevo_5whys.strip() or "Causa raíz documentada en expediente CAPA.",
                            "standard_solution": f"Correctiva: {nueva_correctiva.strip()} | Preventiva: {nueva_preventiva.strip()}",
                            "benefit_impact": beneficio_ll_input.strip() or "Prevención de recurrencia y blindaje normativo ANSI/ESD S20.20 en plantas hermanas.",
                            "evidence_before_url": url_before_final,
                            "evidence_after_url": url_after_final,
                            "published_by": user_name,
                            "created_at": ahora_upd,
                            "yokoten_adoption": {
                                site_name: {
                                    "status": "Implementado en Planta",
                                    "updated_by": user_name,
                                    "updated_at": datetime.now().strftime("%Y-%m-%d"),
                                    "notes": "Planta origen del hallazgo.",
                                }
                            },
                        }
                        try:
                            supabase.table("company_lessons_learned").upsert(nueva_ll_corp, on_conflict="lesson_code").execute()
                        except Exception:
                            pass

                        st.session_state.local_company_lessons = [
                            x for x in st.session_state.local_company_lessons if x.get("lesson_code") != ll_code
                        ]
                        st.session_state.local_company_lessons.insert(0, nueva_ll_corp)

                    st.success(f"✅ Seguimiento del hallazgo **{cod_seleccionado}** actualizado correctamente.")
                    st.rerun()


# ==============================================================================
# PESTAÑA 4: LESSONS LEARNED GLOBALES DE LA COMPAÑÍA (YOKOTEN MULTI-SITE)
# ==============================================================================
with tab_lessons_global:
    st.markdown(f"#### 🌐 Repositorio Global de Lessons Learned & Yokoten — **{company_name}**")
    st.caption(
        "Conocimiento compartido entre todas las plantas de la compañía. "
        "Evalúa las lecciones aprendidas de otros sitios y registra su réplica preventiva (*Read-Across / Yokoten*) en tu planta."
    )

    # --- KPIs GLOBALES DE LESSONS LEARNED ---
    total_ll = len(lessons_lista)
    plantas_origen = len({ll.get("origin_site_name", "Global") for ll in lessons_lista})
    adoptadas_mi_planta = sum(
        1 for ll in lessons_lista
        if isinstance(ll.get("yokoten_adoption"), dict)
        and ll["yokoten_adoption"].get(site_name, {}).get("status") == "Implementado en Planta"
    )
    pendientes_mi_planta = sum(
        1 for ll in lessons_lista
        if not isinstance(ll.get("yokoten_adoption"), dict)
        or site_name not in ll.get("yokoten_adoption", {})
    )

    ll_k1, ll_k2, ll_k3, ll_k4 = st.columns(4)
    ll_k1.metric("📚 Total Lessons Learned (Compañía)", total_ll)
    ll_k2.metric("🏭 Plantas Contribuyentes", plantas_origen)
    ll_k3.metric(f"✅ Adoptadas en {site_name}", adoptadas_mi_planta)
    ll_k4.metric(
        f"🔍 Pendientes de Evaluar en {site_name}",
        pendientes_mi_planta,
        delta="Requiere Read-Across" if pendientes_mi_planta > 0 else "100% Evaluado",
        delta_color="inverse" if pendientes_mi_planta > 0 else "normal",
    )

    # --- EXPANDER PARA PUBLICAR NUEVA LESSON LEARNED GLOBAL DIRECTAMENTE ---
    with st.expander("➕ **Publicar Nueva Lesson Learned Global para toda la Compañía**", expanded=False):
        with st.form("form_new_global_lesson", clear_on_submit=True):
            nl_c1, nl_c2, nl_c3 = st.columns(3)
            ll_titulo = nl_c1.text_input("📌 Título Ejecutivo de la Lección (One-Point Lesson)", placeholder="Ej. Blindaje de tierras en hornos de reflujo")
            ll_cat = nl_c2.selectbox("🔍 Categoría ESD", options=elementos_esd_lista)
            ll_proc = nl_c3.text_input("🏭 Área / Proceso Aplicable", placeholder="Ej. SMT / Logística / Cleanroom")

            nl_c4, nl_c5, nl_c6 = st.columns(3)
            ll_causa6m = nl_c4.selectbox("🧠 Categoría 6M", options=ROOT_CAUSE_6M)
            ll_sev = nl_c5.selectbox("⚡ Severidad Preventiva", options=["Critical", "Major", "Minor", "Observation"], index=1)
            ll_ref_fnd = nl_c6.text_input("🔗 Folio Hallazgo Origen (Opcional)", placeholder="Ej. EASE-2026-0105")

            ll_prob = st.text_area("1️⃣ ¿Qué ocurrió? (Descripción del Problema / Modo de Falla)", height=70)
            ll_rc = st.text_area("2️⃣ ¿Por qué ocurrió? (Causa Raíz Sistémica)", height=70)
            ll_sol = st.text_area("3️⃣ ¿Cómo se solucionó y estandarizó? (Poka-Yoke / Nuevo Estándar)", height=80)
            ll_imp = st.text_input("4️⃣ Beneficio e Impacto Medible (ROI / Reducción de Riesgo ESD)")

            ev_ll1, ev_ll2 = st.columns(2)
            file_ll_before = ev_ll1.file_uploader("📸 Evidencia Antes (Condición Incorrecta)", type=["jpg", "jpeg", "png", "webp", "pdf"], key="ll_up_bef")
            file_ll_after = ev_ll2.file_uploader("✅ Evidencia Después (Buena Práctica / Estándar)", type=["jpg", "jpeg", "png", "webp", "pdf"], key="ll_up_aft")

            if st.form_submit_button("🌐 Publicar Lesson Learned a Nivel Compañía", type="primary", use_container_width=True):
                if not ll_titulo.strip() or not ll_sol.strip():
                    st.error("⚠️ El título y la solución estándar son obligatorios.")
                else:
                    ll_new_code = f"LL-GLOBAL-{datetime.now().strftime('%Y')}-{len(lessons_lista) + 1:03d}"
                    u_ll_bef, _, _ = upload_finding_evidence(file_ll_before, ll_new_code, stage="ll_before") if file_ll_before else ("", None, None)
                    u_ll_aft, _, _ = upload_finding_evidence(file_ll_after, ll_new_code, stage="ll_after") if file_ll_after else ("", None, None)

                    nueva_leccion = {
                        "lesson_code": ll_new_code,
                        "company_id": company_id,
                        "company_name": company_name,
                        "origin_site_id": site_id,
                        "origin_site_name": site_name,
                        "source_finding_code": ll_ref_fnd.strip() or "N/A",
                        "esd_category": ll_cat,
                        "process_area": ll_proc.strip() or "General EPA",
                        "severity": ll_sev,
                        "title": ll_titulo.strip(),
                        "problem_description": ll_prob.strip(),
                        "root_cause_6m": ll_causa6m,
                        "root_cause_analysis": ll_rc.strip(),
                        "standard_solution": ll_sol.strip(),
                        "benefit_impact": ll_imp.strip(),
                        "evidence_before_url": u_ll_bef,
                        "evidence_after_url": u_ll_aft,
                        "published_by": user_name,
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "yokoten_adoption": {
                            site_name: {
                                "status": "Implementado en Planta",
                                "updated_by": user_name,
                                "updated_at": datetime.now().strftime("%Y-%m-%d"),
                                "notes": "Planta autora de la lección aprendida.",
                            }
                        },
                    }
                    try:
                        supabase.table("company_lessons_learned").insert(nueva_leccion).execute()
                    except Exception:
                        pass

                    st.session_state.local_company_lessons.insert(0, nueva_leccion)
                    st.success(f"✅ Lesson Learned **{ll_new_code}** publicada globalmente para todas las plantas de **{company_name}**.")
                    st.rerun()

    st.divider()

    # --- FILTROS DEL CATÁLOGO GLOBAL DE LESSONS LEARNED ---
    fl_1, fl_2, fl_3 = st.columns([1.2, 1.2, 1.6])
    sitios_ll = ["Todas las Plantas"] + sorted({ll.get("origin_site_name", "Global") for ll in lessons_lista})
    filtro_planta_ll = fl_1.selectbox("🏭 Filtrar por Planta Origen:", options=sitios_ll)

    cats_ll = ["Todas las Categorías"] + sorted({ll.get("esd_category", "General") for ll in lessons_lista})
    filtro_cat_ll = fl_2.selectbox("🔍 Filtrar por Categoría ESD:", options=cats_ll)

    filtro_txt_ll = fl_3.text_input("🔎 Buscar en Lessons Learned (Palabra clave, proceso, Poka-Yoke):")

    # --- LISTADO DE TARJETAS EJECUTIVAS (ONE-POINT LESSONS) ---
    for idx_ll, ll_item in enumerate(lessons_lista):
        if filtro_planta_ll != "Todas las Plantas" and ll_item.get("origin_site_name") != filtro_planta_ll:
            continue
        if filtro_cat_ll != "Todas las Categorías" and ll_item.get("esd_category") != filtro_cat_ll:
            continue
        if filtro_txt_ll.strip():
            q_ll = filtro_txt_ll.strip().lower()
            blob = f"{ll_item.get('title','')} {ll_item.get('problem_description','')} {ll_item.get('standard_solution','')} {ll_item.get('process_area','')}".lower()
            if q_ll not in blob:
                continue

        ll_code = ll_item.get("lesson_code", f"LL-{idx_ll}")
        adopciones = ll_item.get("yokoten_adoption") if isinstance(ll_item.get("yokoten_adoption"), dict) else {}
        mi_adopcion = adopciones.get(site_name, {})
        estatus_local = mi_adopcion.get("status", "Pendiente de Evaluar")

        badge_local = (
            "🟢 Implementado en esta Planta"
            if estatus_local == "Implementado en Planta"
            else ("➖ No Aplica en este Site" if estatus_local == "No Aplica en este Site" else "🟡 Pendiente de Réplica (Yokoten)")
        )

        with st.container(border=True):
            h_col1, h_col2 = st.columns([3, 1.2])
            with h_col1:
                st.markdown(f"##### 💡 {ll_code} — {ll_item.get('title', 'Sin Título')}")
                st.caption(
                    f"🏭 **Planta Origen:** `{ll_item.get('origin_site_name', 'Global')}` &nbsp;|&nbsp; "
                    f"🔧 **Área:** `{ll_item.get('process_area', 'EPA')}` &nbsp;|&nbsp; "
                    f"📏 **Categoría ESD:** `{ll_item.get('esd_category', 'General')}` &nbsp;|&nbsp; "
                    f"🔗 **Hallazgo Ref:** `{ll_item.get('source_finding_code', 'N/A')}` &nbsp;|&nbsp; "
                    f"📅 `{ll_item.get('created_at', '')}`"
                )
            with h_col2:
                st.markdown(f"**Estatus en {site_name}:**\n\n{badge_local}")

            b_col1, b_col2, b_col3 = st.columns(3)
            with b_col1:
                st.markdown("**🚨 1. Problema Detectado:**")
                st.write(ll_item.get("problem_description", "N/D"))
            with b_col2:
                st.markdown(f"**🧠 2. Causa Raíz ({ll_item.get('root_cause_6m', '6M')}):**")
                st.write(ll_item.get("root_cause_analysis", "N/D"))
            with b_col3:
                st.markdown("**🛡️ 3. Solución Estándar / Poka-Yoke:**")
                st.write(ll_item.get("standard_solution", "N/D"))
                if ll_item.get("benefit_impact"):
                    st.success(f"**Impacto:** {ll_item.get('benefit_impact')}")

            if ll_item.get("evidence_before_url") or ll_item.get("evidence_after_url"):
                with st.expander("📸 Ver Evidencia Fotográfica / Documental (Antes vs. Después)"):
                    ev_l1, ev_l2 = st.columns(2)
                    with ev_l1:
                        render_evidence_preview(ll_item.get("evidence_before_url"), "Antes (Condición de Riesgo)")
                    with ev_l2:
                        render_evidence_preview(ll_item.get("evidence_after_url"), "Después (Estándar Implementado)")

            # Control de Read-Across / Yokoten para la planta actual
            with st.expander(f"🔄 Actualizar Validación Yokoten / Read-Across en **{site_name}**"):
                with st.form(f"form_yokoten_{ll_code}_{idx_ll}"):
                    yk_c1, yk_c2 = st.columns([1.2, 2])
                    opciones_yk = ["Implementado en Planta", "En Evaluación / En Proceso", "No Aplica en este Site"]
                    idx_yk = opciones_yk.index(estatus_local) if estatus_local in opciones_yk else 1
                    nuevo_est_yk = yk_c1.selectbox("Estatus de Adopción Local:", options=opciones_yk, index=idx_yk)
                    notas_yk = yk_c2.text_input(
                        "Comentarios de Implementación Local / Líneas donde se replicó:",
                        value=mi_adopcion.get("notes", ""),
                        placeholder="Ej. Estandarizado en líneas SMT-01 y SMT-02 con ayuda visual...",
                    )
                    if st.form_submit_button("💾 Guardar Estatus de Réplica en mi Planta"):
                        adopciones[site_name] = {
                            "status": nuevo_est_yk,
                            "updated_by": user_name,
                            "updated_at": datetime.now().strftime("%Y-%m-%d"),
                            "notes": notas_yk.strip(),
                        }
                        ll_item["yokoten_adoption"] = adopciones
                        try:
                            supabase.table("company_lessons_learned").update(
                                {"yokoten_adoption": adopciones}
                            ).eq("lesson_code", ll_code).execute()
                        except Exception:
                            pass
                        st.success(f"✅ Validación Yokoten actualizada para **{site_name}**.")
                        st.rerun()


# ==============================================================================
# EXPANDER TÉCNICO: SCRIPT SQL PARA SUPABASE Y STORAGE BUCKET
# ==============================================================================
st.divider()
with st.expander("🛠️ Configuración de Base de Datos y Bucket en Supabase (SQL Script para Administradores)"):
    st.caption("Ejecuta este script en el **SQL Editor** de Supabase para aprovisionar el bucket `evidencias_hallazgos` y las tablas `esd_findings` y `company_lessons_learned`.")
    st.code(
        """-- 1. Crear Bucket Público en Supabase Storage para Evidencias de Hallazgos
INSERT INTO storage.buckets (id, name, public)
VALUES ('evidencias_hallazgos', 'evidencias_hallazgos', true)
ON CONFLICT (id) DO NOTHING;

-- 2. Tabla de Seguimiento de Hallazgos EASE (Multi-Tenant por site_id)
CREATE TABLE IF NOT EXISTS public.esd_findings (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    finding_code text UNIQUE NOT NULL,
    site_id uuid,
    site_name text,
    company_id uuid,
    assessment_type text,
    question_title text,
    location text,
    station_or_asset text,
    severity text DEFAULT 'Major',
    mitigation_type text DEFAULT 'Action Required (Short-Term)',
    status text DEFAULT 'Open',
    opened_by text,
    responsible_party text,
    escalation_owner text,
    opened_at timestamp with time zone DEFAULT now(),
    response_sla_hours integer DEFAULT 24,
    first_response_at timestamp with time zone,
    due_date date,
    closed_at timestamp with time zone,
    measured_value text,
    finding_description text,
    containment_action text,
    root_cause_6m text,
    root_cause_detail text,
    corrective_action text,
    preventive_action text,
    verification_comments text,
    evidence_before_url text,
    evidence_after_url text,
    storage_bucket text DEFAULT 'evidencias_hallazgos',
    is_lesson_learned boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now()
);

-- 3. Tabla de Lessons Learned Globales de la Compañía (Multi-Site por company_id)
CREATE TABLE IF NOT EXISTS public.company_lessons_learned (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    lesson_code text UNIQUE NOT NULL,
    company_id uuid,
    company_name text,
    origin_site_id uuid,
    origin_site_name text,
    source_finding_code text,
    esd_category text,
    process_area text,
    severity text DEFAULT 'Major',
    title text NOT NULL,
    problem_description text,
    root_cause_6m text,
    root_cause_analysis text,
    standard_solution text,
    benefit_impact text,
    evidence_before_url text,
    evidence_after_url text,
    published_by text,
    yokoten_adoption jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now()
);""",
        language="sql",
    )
