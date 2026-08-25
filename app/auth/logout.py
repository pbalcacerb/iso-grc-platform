"""Logout endpoint."""
from fastapi import APIRouter, Response

router = APIRouter()


@router.get("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(key="session")
    return {"message": "Logged out successfully"}