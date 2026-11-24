"""
roadsafety/backend/routers/auth.py
==================================
Authentication endpoints: login, citizen registration, profile, and user listing.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, CitizenProfile, Driver
from ..schemas import UserLogin, TokenResponse, UserCreate, UserResponse
from ..security import (
    verify_password, hash_password, create_access_token,
    get_current_user, require_roles, record_audit
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user with username and password, returning signed JWT."""
    user = db.query(User).filter(User.username == payload.username.strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    token = create_access_token({"sub": user.username, "role": user.role, "id": user.id})
    record_audit(db, user.username, user.role, "LOGIN_SUCCESS", "AUTH", f"User {user.username} logged in via API")

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "badge_number": user.badge_number,
            "hospital_id": user.hospital_id,
            "vehicle_id": user.vehicle_id,
        }
    }


@router.post("/register", response_model=TokenResponse)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    """Register a new user or citizen account."""
    existing = db.query(User).filter(User.username == payload.username.strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")

    new_user = User(
        username=payload.username.strip(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=payload.role or "CITIZEN",
        badge_number=payload.badge_number,
        phone=payload.phone,
        hospital_id=payload.hospital_id,
        vehicle_id=payload.vehicle_id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    if new_user.role == "CITIZEN":
        profile = CitizenProfile(
            user_id=new_user.id,
            full_name=new_user.full_name,
            phone=payload.phone or "N/A",
        )
        db.add(profile)
        db.commit()
    elif "DRIVER" in new_user.role:
        driver = Driver(
            user_id=new_user.id,
            full_name=new_user.full_name,
            badge_number=payload.badge_number or f"DRV-{new_user.id:03d}",
            phone=payload.phone or "N/A",
            assigned_vehicle_id=payload.vehicle_id,
        )
        db.add(driver)
        db.commit()

    token = create_access_token({"sub": new_user.username, "role": new_user.role, "id": new_user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "full_name": new_user.full_name,
            "role": new_user.role,
            "badge_number": new_user.badge_number,
            "hospital_id": new_user.hospital_id,
            "vehicle_id": new_user.vehicle_id,
        }
    }


@router.get("/me")
def get_current_user_profile(user: User = Depends(get_current_user)):
    """Return profile details of logged-in user."""
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "badge_number": user.badge_number,
        "phone": user.phone,
        "hospital_id": user.hospital_id,
        "vehicle_id": user.vehicle_id,
    }


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(["SUPER_ADMIN", "admin"]))
):
    """List all registered system users (admin only)."""
    users = db.query(User).order_by(User.id).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "role": u.role,
            "badge_number": u.badge_number,
            "hospital_id": u.hospital_id,
            "vehicle_id": u.vehicle_id,
            "is_active": u.is_active,
            "created_at": u.created_at,
        }
        for u in users
    ]
