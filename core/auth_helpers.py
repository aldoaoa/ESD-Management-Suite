from core.db import get_supabase_client
from core.logging import log_error


def validate_user_site_access(user_id, site_id):
    """
    Valida que el usuario tiene permiso para acceder a un sitio específico.
    Previene escalación de privilegios.
    """
    supabase = get_supabase_client()
    try:
        response = supabase.table("users").select("site_id").eq("id", user_id).execute()
        if response.data and response.data[0].get("site_id") == site_id:
            return True
        log_error(
            "UNAUTHORIZED_ACCESS",
            f"User {user_id} attempted to access site {site_id}",
            user_id=user_id
        )
        return False
    except Exception as e:
        log_error("VALIDATION_ERROR", str(e), user_id=user_id)
        return False
