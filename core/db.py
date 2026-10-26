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

# --- FUNCIONES WRAPPER MULTI-TENANT ---

def get_site_assets(site_id: str = None):
    """Retorna todos los activos (Mobiliario, Maquinaria, etc.) del Site actual."""
    target_site = site_id or st.session_state.get("site_id")
    if not target_site:
        return []
        
    supabase = get_supabase_client()
    try:
        response = supabase.table("assets").select("*").eq("site_id", target_site).execute()
        return response.data or []
    except Exception as e:
        st.error(f"Error fetching assets: {e}")
        return []

def get_site_measurements(limit=1000):
    """Retorna el historial de mediciones del Site actual."""
    if not st.session_state.get("site_id"):
        return []
        
    supabase = get_supabase_client()
    try:
        response = supabase.table("measurements").select("*, assets(custom_id, category, classification)").eq("site_id", st.session_state.site_id).order("measured_at", desc=True).limit(limit).execute()
        return response.data
    except Exception as e:
        st.error(f"Error fetching measurements: {e}")
        return []

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
    import base64
    from datetime import datetime

    try:
        supabase = get_supabase_client()
    except Exception:
        supabase = None

    raw_name = getattr(file_obj, "name", f"{finding_id}.jpg")
    ext = raw_name.rsplit(".", 1)[-1].lower() if "." in raw_name else "jpg"
    clean_id = re.sub(r"[^A-Za-z0-9_-]", "_", str(finding_id).strip())
    site_prefix = re.sub(r"[^A-Za-z0-9_-]", "_", str(st.session_state.get("site_id") or "global"))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    content_type = getattr(file_obj, "type", None) or mimetypes.guess_type(raw_name)[0] or "application/octet-stream"
    file_bytes = None

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
                    file_options={"content-type": content_type, "upsert": "true"},
                )
                public_url = supabase.storage.from_(b_name).get_public_url(storage_path)
                return public_url, b_name, None
            except Exception as err:
                last_err = str(err)

    if file_bytes and len(file_bytes) <= 4 * 1024 * 1024:
        b64_data = base64.b64encode(file_bytes).decode("utf-8")
        data_uri = f"data:{content_type};base64,{b64_data}"
        return data_uri, "local_session_cache", last_err

    return "", None, last_err or "Error desconocido al subir evidencia a Supabase Storage."


def get_site_findings(site_id: str = None):
    """Obtiene los hallazgos del sitio desde 'esd_findings'."""
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


# ==========================================
# GESTIÓN PERSISTENTE DE LOGOTIPO POR EMPRESA
# ==========================================

def optimize_logo_image(file_bytes: bytes, mime_type: str = "image/png"):
    """
    Optimiza y redimensiona la imagen del logotipo preservando transparencia PNG
    para garantizar persistencia rápida en Supabase y renderizado fluido en el Sidebar.
    Retorna (optimized_bytes, final_mime, data_uri).
    """
    import io
    import base64

    final_bytes = file_bytes
    final_mime = mime_type or "image/png"

    try:
        from PIL import Image
        img = Image.open(io.BytesIO(file_bytes))
        if img.mode not in ("RGBA", "RGB"):
            img = img.convert("RGBA")
        img.thumbnail((560, 220))
        buf = io.BytesIO()
        if img.mode == "RGBA":
            img.save(buf, format="PNG", optimize=True)
            final_mime = "image/png"
        else:
            img.save(buf, format="JPEG", quality=88, optimize=True)
            final_mime = "image/jpeg"
        final_bytes = buf.getvalue()
    except Exception:
        pass

    b64_str = base64.b64encode(final_bytes).decode("utf-8")
    data_uri = f"data:{final_mime};base64,{b64_str}"
    return final_bytes, final_mime, data_uri


def save_company_logo(company_id: str, data_uri: str, file_bytes: bytes = None, mime_type: str = "image/png") -> bool:
    """
    Persiste el logotipo oficial de una empresa (company_id) en Supabase:
    1) Caché de sesión por empresa
    2) Tabla 'companies' (si cuenta con columna logo_url / logo_base64)
    3) Bucket Storage 'evidencias_esd'
    4) Tabla 'app_logs' (page='company_logo_config', level=str(company_id)) como almacén garantizado
    """
    if not company_id:
        company_id = "global"
    cid_str = str(company_id)

    if "company_logos_map" not in st.session_state:
        st.session_state["company_logos_map"] = {}
    st.session_state["company_logos_map"][cid_str] = data_uri

    try:
        supabase = get_supabase_client()
    except Exception:
        supabase = None

    if supabase is None:
        return True

    if cid_str != "global":
        for col_name in ["logo_url", "logo_base64", "logo"]:
            try:
                supabase.table("companies").update({col_name: data_uri}).eq("id", cid_str).execute()
                break
            except Exception:
                pass

    if file_bytes:
        try:
            ext = "png" if "png" in (mime_type or "").lower() else "jpg"
            path_logo = f"company_logos/company_{cid_str}.{ext}"
            supabase.storage.from_("evidencias_esd").upload(
                file=file_bytes,
                path=path_logo,
                file_options={"content-type": mime_type or "image/png", "upsert": "true"},
            )
        except Exception:
            pass

    try:
        supabase.table("app_logs").delete().eq("page", "company_logo_config").eq("level", cid_str).execute()
    except Exception:
        pass

    try:
        supabase.table("app_logs").insert({
            "page": "company_logo_config",
            "level": cid_str,
            "message": "ACTIVE_LOGO",
            "details": data_uri,
            "user_id": st.session_state.get("user_id"),
            "site_id": st.session_state.get("site_id"),
        }).execute()
    except Exception as e:
        print(f"Error saving company logo in app_logs: {e}")

    return True


def delete_company_logo(company_id: str) -> bool:
    """Elimina el logotipo personalizado de la empresa indicada."""
    if not company_id:
        company_id = "global"
    cid_str = str(company_id)

    if "company_logos_map" not in st.session_state:
        st.session_state["company_logos_map"] = {}
    st.session_state["company_logos_map"][cid_str] = None

    try:
        supabase = get_supabase_client()
    except Exception:
        supabase = None

    if supabase is not None:
        if cid_str != "global":
            for col_name in ["logo_url", "logo_base64", "logo"]:
                try:
                    supabase.table("companies").update({col_name: None}).eq("id", cid_str).execute()
                    break
                except Exception:
                    pass

        try:
            supabase.table("app_logs").delete().eq("page", "company_logo_config").eq("level", cid_str).execute()
        except Exception:
            pass

        try:
            supabase.table("app_logs").insert({
                "page": "company_logo_config",
                "level": cid_str,
                "message": "DELETED_LOGO",
                "details": "",
                "user_id": st.session_state.get("user_id"),
                "site_id": st.session_state.get("site_id"),
            }).execute()
        except Exception:
            pass

    return True


def get_company_logo(company_id: str = None, force_refresh: bool = False):
    """Recupera el logotipo de la empresa activa desde caché de sesión o Supabase."""
    target_cid = str(company_id or st.session_state.get("company_id") or "global")

    if "company_logos_map" not in st.session_state:
        st.session_state["company_logos_map"] = {}

    if not force_refresh and target_cid in st.session_state["company_logos_map"]:
        return st.session_state["company_logos_map"][target_cid]

    try:
        supabase = get_supabase_client()
    except Exception:
        return st.session_state["company_logos_map"].get(target_cid)

    logo_found = None

    try:
        resp_log = (
            supabase.table("app_logs")
            .select("message, details")
            .eq("page", "company_logo_config")
            .eq("level", target_cid)
            .order("id", desc=True)
            .limit(1)
            .execute()
        )
        if resp_log and resp_log.data:
            rec = resp_log.data[0]
            if rec.get("message") == "DELETED_LOGO":
                st.session_state["company_logos_map"][target_cid] = None
                return None
            if rec.get("message") == "ACTIVE_LOGO" and rec.get("details"):
                logo_found = rec["details"]
    except Exception:
        pass

    if not logo_found and target_cid != "global":
        try:
            resp_c = supabase.table("companies").select("*").eq("id", target_cid).limit(1).execute()
            if resp_c and resp_c.data:
                c_row = resp_c.data[0]
                for col_name in ["logo_url", "logo_base64", "logo"]:
                    if c_row.get(col_name):
                        logo_found = c_row[col_name]
                        break
        except Exception:
            pass

    st.session_state["company_logos_map"][target_cid] = logo_found
    return logo_found


def resolve_site_company(site_id: str):
    """Dado un site_id, retorna (company_id, company_name) buscando en available_sites o tabla sites."""
    if not site_id:
        return st.session_state.get("company_id"), st.session_state.get("company_name", "Global")

    for s in st.session_state.get("available_sites", []):
        if s.get("id") == site_id and s.get("company_id"):
            return s.get("company_id"), s.get("company_name") or st.session_state.get("company_name", "Global")

    try:
        supabase = get_supabase_client()
        try:
            r_s = supabase.table("sites").select("company_id, companies(name)").eq("id", site_id).limit(1).execute()
            if r_s and r_s.data:
                row = r_s.data[0]
                cid = row.get("company_id")
                cname = row["companies"]["name"] if isinstance(row.get("companies"), dict) else None
                if cid:
                    return cid, cname or st.session_state.get("company_name", "Global")
        except Exception:
            r_s = supabase.table("sites").select("company_id").eq("id", site_id).limit(1).execute()
            if r_s and r_s.data and r_s.data[0].get("company_id"):
                cid = r_s.data[0]["company_id"]
                cname = st.session_state.get("company_name", "Global")
                try:
                    r_c = supabase.table("companies").select("name").eq("id", cid).limit(1).execute()
                    if r_c and r_c.data:
                        cname = r_c.data[0].get("name", cname)
                except Exception:
                    pass
                return cid, cname
    except Exception:
        pass

    return st.session_state.get("company_id"), st.session_state.get("company_name", "Global")


def sync_company_logo_in_session(force: bool = False):
    """
    Sincroniza el logotipo de la empresa activa en st.session_state.company_logo
    y st.session_state.site_logo según la empresa a la que pertenece el usuario o planta actual.
    """
    if st.session_state.get("modo_lectura", True):
        return

    current_cid = st.session_state.get("company_id")
    current_sid = st.session_state.get("site_id")

    if current_sid and (not current_cid or st.session_state.get("_last_synced_site_id") != current_sid):
        resolved_cid, resolved_cname = resolve_site_company(current_sid)
        if resolved_cid:
            current_cid = resolved_cid
            st.session_state["company_id"] = resolved_cid
            if resolved_cname:
                st.session_state["company_name"] = resolved_cname
        st.session_state["_last_synced_site_id"] = current_sid

    cid_key = str(current_cid or "global")
    if force or st.session_state.get("_logo_loaded_for_company") != cid_key:
        logo_uri = get_company_logo(cid_key, force_refresh=force)
        st.session_state["company_logo"] = logo_uri
        st.session_state["site_logo"] = logo_uri
        st.session_state["_logo_loaded_for_company"] = cid_key
