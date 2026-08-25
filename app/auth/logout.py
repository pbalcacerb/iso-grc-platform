from fastapi import APIRouter, Response

router = APIRouter()

@router.get("/logout")
def logout(response: Response):
    # Clear the session cookie
    response.delete_cookie(key="session")
    return {"message": "Logout successful"}