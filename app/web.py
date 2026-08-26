"""Rutas web server-rendered (Jinja2) para la demo."""
import hashlib
import re
import uuid
from pathlib import Path

import argon2
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    AIAnalysis, Audit, ChecklistItem, Clause, Client,
    EvidenceFile, Membership, QuestionPack, Standard, Tenant, User,
)
from app.security import parse_session, require_role
from app.worker.assess import assess_compliance

router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")
hasher = argon2.PasswordHasher()


def _parse_session(request: Request) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    cookie = request.cookies.get("session") or ""
    m_t = re.search(r"tenant=([0-9a-f\-]{36})", cookie)
    m_u = re.search(r"user=([0-9a-f\-]{36})", cookie)
    tenant = uuid.UUID(m_t.group(1)) if m_t else None
    user = uuid.UUID(m_u.group(1)) if m_u else None
    return tenant, user


@router.get("/", response_class=RedirectResponse)
def root() -> RedirectResponse:
    return RedirectResponse(url="/login")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "login.html")


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "register.html")


@router.post("/web/register")
def web_register(
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if db.query(User).filter(User.email == email).first():
        return RedirectResponse(url="/login?error=email_exists", status_code=303)

    slug = f"{email.split('@')[0]}-{uuid.uuid4().hex[:6]}"
    tenant = Tenant(name=f"{full_name}'s Tenant", slug=slug)
    db.add(tenant)
    db.flush()

    user = User(email=email, password_hash=hasher.hash(password), full_name=full_name)
    db.add(user)
    db.flush()

    db.add(Membership(user_id=user.id, tenant_id=tenant.id, role="owner"))
    db.commit()
    return RedirectResponse(url="/login?msg=registered", status_code=303)


@router.post("/web/login")
def web_login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return RedirectResponse(url="/login?error=invalid", status_code=303)
    try:
        hasher.verify(user.password_hash, password)
    except argon2.exceptions.VerifyMismatchError:
        return RedirectResponse(url="/login?error=invalid", status_code=303)

    membership = db.query(Membership).filter(Membership.user_id == user.id).first()
    if not membership:
        return RedirectResponse(url="/login?error=no_tenant", status_code=303)

    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key="session",
        value=f"tenant={membership.tenant_id};user={user.id}",
        httponly=True, samesite="lax", max_age=86400,
    )
    return response


@router.get("/web/logout")
def web_logout() -> RedirectResponse:
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session")
    return response


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    tenant_id, _ = _parse_session(request)
    if not tenant_id:
        return RedirectResponse(url="/login", status_code=303)

    audits = db.query(Audit).filter(Audit.tenant_id == tenant_id).all()
    audit_data = []
    for a in audits:
        client = db.query(Client).filter(Client.id == a.client_id).first()
        audit_data.append({
            "id": str(a.id), "name": a.name, "status": a.status,
            "client_name": client.name if client else "Desconocido",
        })

    role = None
    if tenant_id:
        m = db.query(Membership).filter(
            Membership.tenant_id == tenant_id,
        ).first()
        role = m.role if m else None
    return templates.TemplateResponse(
        request, "dashboard.html", {"audits": audit_data, "role": role}
    )


@router.get("/clients/new", response_class=HTMLResponse)
def new_client(
    request: Request,
    membership: Membership = Depends(require_role("owner", "auditor")),
) -> HTMLResponse:
    return templates.TemplateResponse(request, "create_client.html")


@router.post("/web/clients")
def create_client_web(
    request: Request,
    name: str = Form(...),
    sector: str = Form(""),
    country: str = Form(""),
    confidentiality_level: str = Form("internal"),
    membership: Membership = Depends(require_role("owner", "auditor")),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    client = Client(
        tenant_id=membership.tenant_id,
        name=name,
        sector=sector,
        country=country,
        confidentiality_level=confidentiality_level,
        status="active",
    )
    db.add(client)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/audits/new", response_class=HTMLResponse)
def new_audit(
    request: Request,
    membership: Membership = Depends(require_role("owner", "auditor")),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    clients = db.query(Client).filter(Client.tenant_id == membership.tenant_id).all()
    standards = db.query(Standard).filter(Standard.status == "active").all()
    return templates.TemplateResponse(
        request, "create_audit.html", {"clients": clients, "standards": standards}
    )


@router.post("/web/audits")
def create_audit_web(
    request: Request,
    name: str = Form(...),
    client_id: str = Form(...),
    standard_id: str = Form(...),
    status: str = Form("planned"),
    membership: Membership = Depends(require_role("owner", "auditor")),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    audit = Audit(
        tenant_id=membership.tenant_id,
        client_id=uuid.UUID(client_id),
        standard_id=uuid.UUID(standard_id),
        name=name,
        status=status,
    )
    db.add(audit)
    db.flush()
    
    question_packs = db.query(QuestionPack).join(Clause).filter(
        Clause.standard_id == uuid.UUID(standard_id)
    ).all()
    
    for qp in question_packs:
        checklist_item = ChecklistItem(
            tenant_id=membership.tenant_id,
            audit_id=audit.id,
            clause_id=qp.clause_id,
            question_pack_id=qp.id,
            status="pending",
            response="",
            notes="",
        )
        db.add(checklist_item)
    
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/audit/{audit_id}", response_class=HTMLResponse)
def audit_detail(
    request: Request, audit_id: str, db: Session = Depends(get_db),
) -> HTMLResponse:
    tenant_id, _ = _parse_session(request)
    if not tenant_id:
        return RedirectResponse(url="/login", status_code=303)

    audit = db.query(Audit).filter(
        Audit.id == uuid.UUID(audit_id), Audit.tenant_id == tenant_id,
    ).first()
    if not audit:
        return RedirectResponse(url="/dashboard", status_code=303)

    rows = (
        db.query(ChecklistItem, Clause.number, QuestionPack.question)
        .join(Clause, ChecklistItem.clause_id == Clause.id)
        .join(QuestionPack, ChecklistItem.question_pack_id == QuestionPack.id)
        .filter(ChecklistItem.audit_id == audit.id)
        .all()
    )
    checklist = [
        {"clause_number": r[1], "question": r[2], "status": r[0].status,
         "response": r[0].response}
        for r in rows
    ]
    analysis = db.query(AIAnalysis).filter(AIAnalysis.audit_id == audit.id).first()

    return templates.TemplateResponse(
        request, "audit_detail.html",
        {"audit": audit, "checklist": checklist, "analysis": analysis},
    )


@router.post("/audit/{audit_id}/analyze")
def analyze(
    request: Request,
    audit_id: str,
    file: UploadFile = File(...),
    membership: Membership = Depends(require_role("owner", "auditor")),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    tenant_id = membership.tenant_id
    user_id = membership.user_id

    content = file.file.read()
    sha = hashlib.sha256(content).hexdigest()
    ev_dir = Path("data/evidence")
    ev_dir.mkdir(parents=True, exist_ok=True)
    (ev_dir / sha).write_bytes(content)

    evidence = EvidenceFile(
        tenant_id=tenant_id, audit_id=uuid.UUID(audit_id),
        original_filename=file.filename or "unknown",
        mime_type=file.content_type or "application/octet-stream",
        file_size=len(content), sha256=sha,
        storage_path=str(ev_dir / sha), uploaded_by=user_id,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    assess_compliance(evidence.id, uuid.UUID(audit_id), db, tenant_id=tenant_id)
    return RedirectResponse(url=f"/audit/{audit_id}", status_code=303)


@router.get("/users", response_class=HTMLResponse)
def manage_users(
    request: Request,
    membership: Membership = Depends(require_role("owner")),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    rows = (
        db.query(User, Membership)
        .join(Membership, Membership.user_id == User.id)
        .filter(Membership.tenant_id == membership.tenant_id)
        .all()
    )
    users = [{"email": u.email, "full_name": u.full_name, "role": m.role} for u, m in rows]
    return templates.TemplateResponse(request, "manage_users.html", {"users": users})


@router.post("/users/invite")
def invite_user(
    email: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    membership: Membership = Depends(require_role("owner")),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    if role not in ("auditor", "reviewer", "viewer"):
        return RedirectResponse(url="/users", status_code=303)
    if db.query(User).filter(User.email == email).first():
        return RedirectResponse(url="/users", status_code=303)
    user = User(email=email, password_hash=hasher.hash(password), full_name=full_name)
    db.add(user)
    db.flush()
    db.add(Membership(user_id=user.id, tenant_id=membership.tenant_id, role=role))
    db.commit()
    return RedirectResponse(url="/users", status_code=303)