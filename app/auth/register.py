"""Registro (API JSON, usado por tests)."""
import uuid

import argon2
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Membership, Tenant, User

router = APIRouter()
hasher = argon2.PasswordHasher()


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


@router.post("/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)) -> dict:
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    slug = f"{request.email.split('@')[0]}-{uuid.uuid4().hex[:6]}"
    tenant = Tenant(name=f"{request.full_name}'s Tenant", slug=slug)
    db.add(tenant)
    db.flush()

    user = User(
        email=request.email,
        password_hash=hasher.hash(request.password),
        full_name=request.full_name,
    )
    db.add(user)
    db.flush()

    db.add(Membership(user_id=user.id, tenant_id=tenant.id, role="owner"))
    db.commit()
    return {
        "message": "Registration successful",
        "user_id": str(user.id),
        "tenant_id": str(tenant.id),
    }