import argon2
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import User

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/login")
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)):
    # Verify user exists
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Verify password hash
    hasher = argon2.PasswordHasher()
    try:
        hasher.verify(user.password_hash, request.password)
    except argon2.exceptions.VerifyMismatchError:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Create session cookie with tenant_id and user_id
    response.set_cookie(
        key="session",
        value=f"tenant_id={user.memberships[0].tenant_id};user_id={user.id}",
        httponly=True,
        secure=True,
        samesite="lax"
    )

    return {"message": "Login successful"}