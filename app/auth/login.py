"""Login endpoint."""
import uuid
import argon2
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, Membership

router = APIRouter()
hasher = argon2.PasswordHasher()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/login")
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)) -> dict:
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    try:
        hasher.verify(user.password_hash, request.password)
    except argon2.exceptions.VerifyMismatchError:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    membership = db.query(Membership).filter(Membership.user_id == user.id).first()
    if not membership:
        raise HTTPException(status_code=401, detail="User has no tenant")

    tenant_id = str(membership.tenant_id)
    user_id = str(user.id)

    # Formato exacto que espera el middleware
    session_value = f"tenant={tenant_id};user={user_id}"
    response.set_cookie(
        key="session",
        value=session_value,
        httponly=True,
        samesite="lax",
        max_age=86400,
    )

    return {"message": "Login successful", "user_id": user_id, "tenant_id": tenant_id}