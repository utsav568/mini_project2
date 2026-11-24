"""
roadsafety/backend/security.py
==============================
Authentication, JWT token lifecycle, salted password hashing,
and Role-Based Access Control (RBAC) dependencies for FastAPI.
"""

import os
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, AuditLog

SECRET_KEY = os.getenv("ROADSOS_SECRET_KEY", "roadsos-emergency-cad-ecosystem-secret-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
PASSWORD_SALT = "roadso_salt_2026_delhi_cad"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    """Create a secure SHA-256 HMAC hash."""
    return hmac.new(PASSWORD_SALT.encode(), password.encode(), hashlib.sha256).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against constant-time comparison, supporting legacy hashes."""
    # Check legacy seed format
    legacy_hash = hashlib.sha256(f"roadso_{plain_password}_salt2026".encode()).hexdigest()
    if hmac.compare_digest(hashed_password, legacy_hash):
        return True
    current_hash = hash_password(plain_password)
    return hmac.compare_digest(hashed_password, current_hash)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed JWT token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None


def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Retrieve user if token provided, else None."""
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None
    username = payload["sub"]
    return db.query(User).filter(User.username == username, User.is_active == True).first()


def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional)
) -> User:
    """Require valid authenticated user."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_roles(allowed_roles: List[str]):
    """Enforce role-based access control dependency."""
    def role_checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles and user.role != "SUPER_ADMIN" and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires role in {allowed_roles}",
            )
        return user
    return role_checker


def record_audit(
    db: Session,
    username: str,
    role: str,
    action: str,
    target: str,
    details: str = "",
    ip_address: str = "127.0.0.1",
) -> None:
    """Log an immutable audit action."""
    try:
        log = AuditLog(
            username=username,
            role=role,
            action=action,
            target_entity=target,
            details=details,
            ip_address=ip_address,
        )
        db.add(log)
        db.commit()
    except Exception as exc:
        db.rollback()
