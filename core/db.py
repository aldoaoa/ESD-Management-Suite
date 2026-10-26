# core/db.py
import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client() -> Client:
    """Inicializa y retorna la conexión a Supabase usando los secrets de Streamlit."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def log_app_event(page: str, level: str, message: str, details: str = None):
    """Registra eventos del sistema en la tabla app_logs."""
    try:
        supabase = get_supabase_client()
        user_id = st.session_state.get("user_id")
        site_id = st.session_state.get("site_id")
        
        supabase.table("app_logs").insert({
            "page": page,
            "level": level,
            "message": message,
            "details": details,
            "user_id": user_id,
            "site_id": site_id
        }).execute()
    except Exception as e:
        print(f"Error logging to app_logs: {e}")

# --- WRAPPERS MULTI-TENANT POR SITE_ID ---

def get_site_assets(site_id: str = None):
    """Retorna los activos de la planta desde la tabla assets."""
    target_site = site_id or st.session_state.get("site_id")
    if not target_site:
        return []
    supabase = get_supabase_client()
    resp = supabase.table("assets").select("*").eq("site_id", target_site).execute()
    return resp.data or []

def get_grounding_logs(site_id: str = None):
    """Retorna bitácora de tierras físicas."""
    target_site = site_id or st.session_state.get("site_id")
    if not target_site:
        return []
    supabase = get_supabase_client()
    resp = supabase.table("grounding_logs").select("*").eq("site_id", target_site).order("measured_at", desc=True).execute()
    return resp.data or []

def get_floor_validation_logs(site_id: str = None):
    """Retorna bitácora de pisos ESD."""
    target_site = site_id or st.session_state.get("site_id")
    if not target_site:
        return []
    supabase = get_supabase_client()
    resp = supabase.table("floor_validation_logs").select("*").eq("site_id", target_site).order("measured_at", desc=True).execute()
    return resp.data or []

def get_event_meter_logs(site_id: str = None):
    """Retorna mediciones de Event Meter."""
    target_site = site_id or st.session_state.get("site_id")
    if not target_site:
        return []
    supabase = get_supabase_client()
    resp = supabase.table("event_meter_logs").select("*").eq("site_id", target_site).order("measured_at", desc=True).execute()
    return resp.data or []

def get_entrance_checkers_logs(site_id: str = None):
    """Retorna bitácora de checadores de calzado/pulsera."""
    target_site = site_id or st.session_state.get("site_id")
    if not target_site:
        return []
    supabase = get_supabase_client()
    resp = supabase.table("entrance_checkers_logs").select("*").eq("site_id", target_site).order("measured_at", desc=True).execute()
    return resp.data or []

def get_empleados_batas(site_id: str = None):
    """Retorna empleados y control de batas/entrenamiento."""
    target_site = site_id or st.session_state.get("site_id")
    if not target_site:
        return []
    supabase = get_supabase_client()
    resp = supabase.table("empleados_batas").select("*").eq("site_id", target_site).execute()
    return resp.data or []


def upload_finding_evidence(file_obj, finding_id: str, stage: str = "open", bucket_name: str = "evidencias_hallazgos"):
    """
    Sube archivos de evidencia (imágenes, PDF, documentos) a un bucket de Supabase Storage
    y retorna (public_url, bucket_usado, error_msg).
    Intenta primero el bucket solicitado ('evidencias_hallazgos') y aplica fallback a 'evidencias_esd'.
    """
    if file_obj is None:
        return "", None, "No se proporcionó ningún archivo."

    import io
    import re
    import mimetypes
    from datetime import datetime

    try:
        supabase = get_supabase_client()
    except Exception as e:
        supabase = None

    raw_name = getattr(file_obj, "name", f"{finding_id}.jpg")
    ext = raw_name.rsplit(".", 1)[-1].lower() if "." in raw_name else "jpg"
    clean_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(finding_id).strip())
    site_prefix = re.sub(r"[^A-Za-z0-9_-]", "_", str(st.session_state.get("site_id") or "global"))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    content_type = getattr(file_obj, "type", None) or mimetypes.guess_type(raw_name)[0] or "application/octet-stream"
    file_bytes = None

    # Optimización de imágenes para carga rápida en piso
    if ext in ["jpg", "jpeg", "png", "webp"]:
        try:
            from PIL import Image
            file_obj.seek(0)
            img = Image.open(file_obj)
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            img.thumbnail((1280, 1280))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=82)
            file_bytes = buf.getvalue()
            ext = "jpg"
            content_type = "image/jpeg"
        except Exception:
            file_obj.seek(0)
            file_bytes = file_obj.read()
    else:
        file_obj.seek(0)
        file_bytes = file_obj.read()

    storage_path = f"{site_prefix}/{clean_id}_{stage}_{timestamp}.{ext}"

    buckets_to_try = [bucket_name]
    for fallback_b in ["evidencias_esd", "reportes_calificacion"]:
        if fallback_b not in buckets_to_try:
            buckets_to_try.append(fallback_b)

    last_err = None
    if supabase is not None:
        for b_name in buckets_to_try:
            try:
                supabase.storage.from_(b_name).upload(
                    file=file_bytes,
                    path=storage_path,
                    file_options={"content-type": content_type, "upsert": "true"}
                )
                public_url = supabase.storage.from_(b_name).get_public_url(storage_path)
                return public_url, b_name, None
            except Exception as err:
                last_err = str(err)

    # Respaldo en memoria (Data URI para imágenes/PDF pequeños) si el bucket aún no está creado en Supabase
    import base64
    if file_bytes and len(file_bytes) <= 4 * 1024 * 1024:
        b64_data = base64.b64encode(file_bytes).decode("utf-8")
        data_uri = f"data:{content_type};base64,{b64_data}"
        return data_uri, "local_session_cache", last_err

    return "", None, last_err or "Error desconocido al subir evidencia a Supabase Storage."


def get_site_findings(site_id: str = None):
    """Obtiene los hallazgos del sitio desde 'esd_findings' o 'hallazgos_4q'."""
    target_site = site_id or st.session_state.get("site_id")
    supabase = get_supabase_client()
    try:
        q = supabase.table("esd_findings").select("*")
        if target_site:
            q = q.eq("site_id", target_site)
        resp = q.order("opened_at", desc=True).execute()
        if resp and resp.data:
            return resp.data
    except Exception:
        pass
    return []


def get_company_lessons_learned(company_id: str = None):
    """Obtiene las lecciones aprendidas globales de la compañía desde 'company_lessons_learned'."""
    target_company = company_id or st.session_state.get("company_id")
    supabase = get_supabase_client()
    try:
        q = supabase.table("company_lessons_learned").select("*")
        if target_company:
            q = q.eq("company_id", target_company)
        resp = q.order("created_at", desc=True).execute()
        if resp and resp.data:
            return resp.data
    except Exception:
        pass
    return []

