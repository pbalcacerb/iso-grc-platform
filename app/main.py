# Main application file
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.audits import router as audits_router
from app.api.clients import router as clients_router
from app.auth.login import router as login_router
from app.auth.logout import router as logout_router
from app.auth.register import router as register_router
from app.middleware import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware)

# Add CORS middleware (optional, adjust as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (e.g., CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    # Redirect to /login by default
    return RedirectResponse(url="/login", status_code=302)

# Include routers
app.include_router(register_router, prefix="/auth")
app.include_router(login_router, prefix="/auth")
app.include_router(logout_router, prefix="/auth")
app.include_router(clients_router, prefix="/api")
app.include_router(audits_router, prefix="/api")