from uuid import uuid4

import argon2
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Membership, Tenant, User

router = APIRouter()

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/register")
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    # Validate email uniqueness
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password with argon2
    hasher = argon2.PasswordHasher()
    password_hash = hasher.hash(request.password)

    # Create tenant with unique slug (localpart + UUID suffix)
    localpart = request.email.split("@")[0].lower().replace(".", "-")
    tenant_slug = f"{localpart}-{uuid4().hex[:6]}"
    tenant = Tenant(name=request.full_name + "'s Tenant", slug=tenant_slug)
    db.add(tenant)
    db.commit()
    db.refresh(tenant)

    # Create user
    user = User(email=request.email, password_hash=password_hash, full_name=request.full_name)
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create membership (user, tenant, role='owner')
    membership = Membership(user_id=user.id, tenant_id=tenant.id, role="owner")
    db.add(membership)
    db.commit()

    return {"message": "Registration successful"}