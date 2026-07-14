# core/logger.py
import streamlit as st
import traceback
from core.db import get_supabase_client

def log_event(level: str, page: str, message: str, details: str = None):
    """
    Registra un evento general en la tabla app_logs de Supabase.
    Evita interrumpir el flujo del usuario si falla la conexión.
    """
    try:
        supabase = get_supabase_client()
        user_id = st.session_state.get("user_id")
        site_id = st.session_state.get("site_id")
        
        log_data = {
            "level": level,
            "page": page,
            "message": message,
            "details": details,
            "user_id": user_id,
            "site_id": site_id
        }
        
        supabase.table("app_logs").insert(log_data).execute()
    except Exception as e:
        # Fallback local en consola
        print(f"[Supabase Logger Error] Failed to write log: {e}")

def log_error(page: str, message: str, exception: Exception = None):
    """
    Función de conveniencia para registrar errores con el traceback completo.
    """
    details = None
    if exception:
        details = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
    log_event("ERROR", page, message, details)
