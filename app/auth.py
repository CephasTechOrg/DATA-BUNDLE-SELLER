"""
Admin auth: credentials from .env, verified via HTTP Basic or Bearer token.
Tokens are issued by POST /admin/login so the frontend can use Bearer (works from file://).
"""
import os
import secrets
import time
from pathlib import Path

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials, HTTPBearer, HTTPAuthorizationCredentials

# Load .env from project root (parent of app/) so it works regardless of CWD
_env_path = Path(__file__).resolve().parent.parent / ".env"
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_env_path)
except ImportError:
    pass

def _get_env(key: str, default: str = "") -> str:
    val = os.getenv(key, default) or ""
    if isinstance(val, str):
        val = val.strip().strip('"').strip("'")
    return val

ADMIN_USERNAME = _get_env("ADMIN_USERNAME")
ADMIN_PASSWORD = _get_env("ADMIN_PASSWORD")

import logging
_log = logging.getLogger("uvicorn.error")
if _log:
    _log.info("Admin auth: .env path=%s, configured=%s", _env_path, bool(ADMIN_USERNAME and ADMIN_PASSWORD))

_security_basic = HTTPBasic()
_security_bearer = HTTPBearer(auto_error=False)

# In-memory tokens: token_string -> expiry timestamp. Use a real cache/DB in production if needed.
_admin_tokens = {}


def _check_credentials(username: str, password: str) -> bool:
    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        return False
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD


def create_admin_token() -> str:
    """Issue a short-lived token after successful login."""
    token = secrets.token_urlsafe(32)
    _admin_tokens[token] = time.time() + 3600
    return token


def _verify_token(token: str) -> bool:
    if not token:
        return False
    expiry = _admin_tokens.get(token)
    if expiry is None or time.time() > expiry:
        if token in _admin_tokens:
            del _admin_tokens[token]
        return False
    return True


def verify_admin(
    credentials: HTTPBasicCredentials = Depends(HTTPBasic(auto_error=False)),
    bearer: HTTPAuthorizationCredentials = Depends(_security_bearer),
) -> str:
    """Accept either Basic auth or Bearer token. Returns username on success."""
    if bearer and bearer.scheme.lower() == "bearer" and _verify_token(bearer.credentials):
        return ADMIN_USERNAME or "admin"
    if credentials and _check_credentials(credentials.username, credentials.password):
        return credentials.username
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid admin credentials",
        headers={"WWW-Authenticate": "Basic"},
    )
