import logging
import os
from datetime import datetime

LOG_DIR = os.path.join(os.getcwd(), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "app.log")

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def log_login(email, success, reason=None):
    """Registra intentos de login (exitosos o fallidos)."""
    status = "SUCCESS" if success else f"FAILED ({reason})"
    logger.info(f"LOGIN ATTEMPT - Email: {email} - Status: {status}")


def log_data_access(user_id, action, resource, details=None):
    """Registra acceso a datos con fines de auditoría."""
    logger.info(
        f"DATA ACCESS - User: {user_id} - Action: {action} - Resource: {resource} - Details: {details}"
    )


def log_error(error_type, message, user_id=None, context=None):
    """Registra errores de aplicación."""
    logger.error(
        f"ERROR - Type: {error_type} - User: {user_id} - Message: {message} - Context: {context}"
    )
