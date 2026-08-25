"""Registro de usuario con tenant automático."""
import uuid

import argon2
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, Tenant, Membership

router = APIRouter()
hasher = argon2.PasswordHasher()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


@router.post("/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    # Validar email único
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Crear tenant con slug único
    local_part = request.email.split("@")[0]
    slug = f"{local_part}-{uuid.uuid4().hex[:6]}"

    tenant = Tenant(
        name=f"{request.full_name}'s Tenant",
        slug=slug,
        status="active",
    )
    db.add(tenant)
    db.flush()  # Obtiene el ID del tenant

    # Crear usuario
    user = User(
        email=request.email,
        password_hash=hasher.hash(request.password),
        full_name=request.full_name,
        status="active",
    )
    db.add(user)
    db.flush()

    # Crear membership
    membership = Membership(
        user_id=user.id,
        tenant_id=tenant.id,
        role="owner",
    )
    db.add(membership)
    db.commit()

    return {
        "message": "Registration successful",
        "user_id": str(user.id),
        "tenant_id": str(tenant.id),
    }