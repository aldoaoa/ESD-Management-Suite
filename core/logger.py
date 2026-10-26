# core/logger.py
"""
Módulo de registro de eventos y errores del sistema.
Envuelve log_app_event de core/db.py con tolerancia a fallos.
"""
from core.db import log_app_event


def log_event(level_or_page: str, page_or_msg: str, message: str = None, details: str = None):
    """Registra un evento informativo o de advertencia en app_logs."""
    try:
        if message is None:
            log_app_event(page=str(level_or_page), level="INFO", message=str(page_or_msg), details=details)
        else:
            log_app_event(page=str(page_or_msg), level=str(level_or_page), message=str(message), details=details)
    except Exception as e:
        print(f"[log_event] {e}")


def log_error(page: str, message: str, error: Exception = None):
    """Registra un error de ejecución en app_logs."""
    try:
        err_details = str(error) if error is not None else None
        log_app_event(page=str(page), level="ERROR", message=str(message), details=err_details)
    except Exception as e:
        print(f"[log_error] {e}")
