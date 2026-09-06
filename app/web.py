"""Rutas web server-rendered (Jinja2) para la demo ISO GRC Platform."""
import asyncio
import hashlib
import json
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

import argon2
from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from jinja2 import pass_context
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func
from sqlalchemy.orm import Session

# Imports internos
from app.db import get_db
from app.models import (
    AIAnalysis, Audit, AuditLog, ChecklistItem, Clause, Client,
    EvidenceFile, Membership, PasswordResetToken, QuestionPack, 
    Standard, Tenant, User,
)
from app.permissions import require_perm, role_can
from app.security import parse_session, require_role
from app.worker.assess import assess_compliance, assess_item

# Inicialización del Router y Templates
router = APIRouter(tags=["web"])
templates = Jinja2Templates(directory="app/templates")
hasher = argon2.PasswordHasher()

# Rate Limiter específico para rutas web
limiter = Limiter(key_func=get_remote_address)


def _parse_session(request: Request) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    """Extrae tenant_id y user_id desde la cookie de sesión."""
    cookie = request.cookies.get("session") or ""
    m_t = re.search(r"tenant=([0-9a-f\-]{36})", cookie)
    m_u = re.search(r"user=([0-9a-f\-]{36})", cookie)
    tenant = uuid.UUID(m_t.group(1)) if m_t else None
    user = uuid.UUID(m_u.group(1)) if m_u else None
    return tenant, user


def get_user_role(request: Request) -> str | None:
    """Helper para extraer el rol del usuario desde la cookie de sesión."""
    tenant_id, user_id = _parse_session(request)
    if not user_id:
        return None
    db = next(get_db())
    membership = db.query(Membership).filter(
        Membership.user_id == user_id,
        Membership.tenant_id == tenant_id,
    ).first()
    return membership.role if membership else None


def jinja_role_can(first_arg, permission: str) -> bool:
    """Función Jinja2 flexible: acepta Request o rol-string como primer arg."""
    if isinstance(first_arg, str):
        role = first_arg
    elif hasattr(first_arg, 'cookies'):
        role = get_user_role(first_arg)
    else:
        role = None
    
    return role_can(role, permission) if role else False


# Registra los helpers como funciones disponibles en TODOS los templates
templates.env.globals.update({
    "get_user_role": get_user_role,
    "role_can": jinja_role_can,
})


# ===== RUTAS DE AUTENTICACIÓN BÁSICA =====

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
@limiter.limit("5/minute")
def web_register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Registro de nuevo usuario con rate limiting (5/min)."""
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
@limiter.limit("10/minute")
def web_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Login con rate limiting (10/min) para prevenir brute force."""
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


# ===== DASHBOARD Y NAVEGACIÓN PRINCIPAL =====

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    tenant_id, user_id = _parse_session(request)
    if not tenant_id:
        return RedirectResponse(url="/login", status_code=303)

    membership = None
    role = None
    if user_id:
        membership = db.query(Membership).filter(
            Membership.tenant_id == tenant_id,
            Membership.user_id == user_id,
        ).first()
        role = membership.role if membership else None

    if role_can(role, "view_portal") and not role_can(role, "view_internal"):
        return RedirectResponse(url="/portal", status_code=303)

    audits = db.query(Audit).filter(Audit.tenant_id == tenant_id).all()
    audit_data = []
    for a in audits:
        client = db.query(Client).filter(Client.id == a.client_id).first()
        audit_data.append({
            "id": str(a.id), "name": a.name, "status": a.status,
            "client_name": client.name if client else "Desconocido",
        })

    return templates.TemplateResponse(
        request, "dashboard.html", {"audits": audit_data, "role": role}
    )


# ===== GESTIÓN DE CLIENTES =====

@router.get("/clients/new", response_class=HTMLResponse)
def new_client(
    request: Request,
    membership: Membership = Depends(require_perm("create_audit")),
) -> HTMLResponse:
    return templates.TemplateResponse(request, "create_client.html")


@router.post("/web/clients")
def create_client_web(
    request: Request,
    name: str = Form(...),
    sector: str = Form(""),
    country: str = Form(""),
    confidentiality_level: str = Form("internal"),
    membership: Membership = Depends(require_perm("create_audit")),
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


# ===== GESTIÓN DE AUDITORÍAS =====

@router.get("/audits/new", response_class=HTMLResponse)
def new_audit(
    request: Request,
    membership: Membership = Depends(require_perm("create_audit")),
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
    membership: Membership = Depends(require_perm("create_audit")),
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
    request: Request, audit_id: str, db: Session = Depends(get_db)
) -> HTMLResponse:
    tenant_id, user_id = _parse_session(request)
    if not tenant_id:
        return RedirectResponse(url="/login", status_code=303)

    try:
        audit_uuid = uuid.UUID(audit_id)
    except ValueError:
        return RedirectResponse(url="/dashboard", status_code=303)

    audit = db.query(Audit).filter(
        Audit.id == audit_uuid, Audit.tenant_id == tenant_id,
    ).first()
    if not audit:
        return RedirectResponse(url="/dashboard", status_code=303)

    membership = db.query(Membership).filter(
        Membership.tenant_id == tenant_id,
        Membership.user_id == user_id,
    ).first()
    role = membership.role if membership else None

    if role_can(role, "view_portal") and not role_can(role, "view_internal"):
        if membership and membership.client_id and audit.client_id != membership.client_id:
            return RedirectResponse(url="/portal", status_code=303)

    can_upload = role_can(role, "upload_evidence")
    can_approve = role_can(role, "approve_item")
    can_reopen = role_can(role, "reopen_item")

    rows = (
        db.query(ChecklistItem, Clause.number, QuestionPack.question)
        .join(Clause, ChecklistItem.clause_id == Clause.id)
        .join(QuestionPack, ChecklistItem.question_pack_id == QuestionPack.id)
        .filter(ChecklistItem.audit_id == audit.id)
        .order_by(Clause.number)
        .all()
    )
    checklist = [
        {"id": str(r[0].id), "clause_number": r[1], "question": r[2],
         "status": r[0].status, "response": r[0].response}
        for r in rows
    ]

    analysis = (
        db.query(AIAnalysis)
        .filter(AIAnalysis.audit_id == audit.id)
        .order_by(AIAnalysis.created_at.desc())
        .first()
    )

    rows_a = (
        db.query(AIAnalysis, EvidenceFile.checklist_item_id)
        .join(EvidenceFile, EvidenceFile.id == AIAnalysis.evidence_file_id)
        .filter(AIAnalysis.audit_id == audit.id)
        .order_by(AIAnalysis.created_at.desc())
        .all()
    )
    analyses_by_item = {}
    for a, item_uuid in rows_a:
        key = str(item_uuid)
        if key not in analyses_by_item:
            analyses_by_item[key] = a

    # Detectar si hay evidencia pendiente de análisis para activar SSE
    has_pending_evidence = any(
        item["status"] == "pending" for item in checklist
    ) if checklist else False

    return templates.TemplateResponse(
        request, "audit_detail.html",
        {
            "audit": audit,
            "checklist": checklist,
            "analysis": analysis,
            "can_upload": can_upload,
            "can_approve": can_approve,
            "can_reopen": can_reopen,
            "analyses_by_item": analyses_by_item,
            "has_pending_evidence": has_pending_evidence,
        },
    )


# ===== COLA DE REVISIÓN HUMANA =====

@router.get("/review-queue", response_class=HTMLResponse)
def review_queue(
    request: Request,
    membership: Membership = Depends(require_perm("view_internal")),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Cola de ítems pendientes de revisión humana para roles internos."""
    latest_by_date = (
        db.query(
            EvidenceFile.checklist_item_id.label("item_id"),
            func.max(AIAnalysis.created_at).label("max_date"),
        )
        .join(EvidenceFile, EvidenceFile.id == AIAnalysis.evidence_file_id)
        .group_by(EvidenceFile.checklist_item_id)
        .subquery()
    )

    rows = (
        db.query(ChecklistItem, Audit, Client, Clause, QuestionPack, AIAnalysis)
        .join(Audit, Audit.id == ChecklistItem.audit_id)
        .join(Client, Client.id == Audit.client_id)
        .join(Clause, Clause.id == ChecklistItem.clause_id)
        .join(QuestionPack, QuestionPack.id == ChecklistItem.question_pack_id)
        .join(EvidenceFile, EvidenceFile.checklist_item_id == ChecklistItem.id)
        .join(AIAnalysis, AIAnalysis.evidence_file_id == EvidenceFile.id)
        .join(
            latest_by_date,
            (latest_by_date.c.item_id == ChecklistItem.id)
            & (AIAnalysis.created_at == latest_by_date.c.max_date),
        )
        .filter(
            ChecklistItem.tenant_id == membership.tenant_id,
            ChecklistItem.status.in_(["pending_review", "completed"]),
        )
        .order_by(Audit.name, Clause.number)
        .all()
    )

    items = []
    for checklist_item, audit, client, clause, question_pack, analysis in rows:
        items.append({
            "item_id": str(checklist_item.id),
            "audit_id": str(audit.id),
            "audit_name": audit.name,
            "client_name": client.name,
            "clause_number": clause.number,
            "clause_title": clause.title,
            "question": question_pack.question,
            "status": checklist_item.status,
            "assessment": analysis.compliance_assessment if analysis else "unknown",
            "confidence": analysis.confidence if analysis else 0.0,
            "gaps": analysis.gaps if analysis else [],
            "provider": analysis.provider if analysis else "none",
        })

    pending_count = sum(1 for i in items if i["status"] == "pending_review")

    return templates.TemplateResponse(
        request, "review_queue.html",
        {
            "items": items,
            "pending_count": pending_count,
        },
    )


# ===== SUBIDA Y ANÁLISIS DE EVIDENCIA =====

@router.post("/audit/{audit_id}/item/{item_id}/evidence")
@limiter.limit("20/minute")
def upload_item_evidence(
    request: Request,
    audit_id: str,
    item_id: str,
    file: List[UploadFile] = File(...),
    membership: Membership = Depends(require_perm("upload_evidence")),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Sube 1..5 evidencias al ítem y ejecuta un análisis consolidado (20/min)."""
    item = db.query(ChecklistItem).filter(
        ChecklistItem.id == uuid.UUID(item_id),
        ChecklistItem.tenant_id == membership.tenant_id,
    ).first()
    if not item:
        return RedirectResponse(url=f"/audit/{audit_id}", status_code=303)

    last_evidence = None
    for upload in file[:5]:
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in (".pdf", ".txt"):
            continue
        content = upload.file.read()
        if not content or len(content) > 10 * 1024 * 1024:
            continue

        sha = hashlib.sha256(content).hexdigest()
        ev_dir = Path("data/evidence")
        ev_dir.mkdir(parents=True, exist_ok=True)
        file_path = ev_dir / f"{sha}{suffix}"
        file_path.write_bytes(content)

        evidence = EvidenceFile(
            tenant_id=membership.tenant_id,
            audit_id=uuid.UUID(audit_id),
            checklist_item_id=uuid.UUID(item_id),
            original_filename=upload.filename or "unknown",
            mime_type=upload.content_type or "application/octet-stream",
            file_size=len(content),
            sha256=sha,
            storage_path=str(file_path),
            uploaded_by=membership.user_id,
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        if last_evidence is None:
            last_evidence = evidence
            
    if last_evidence is None:
        return RedirectResponse(url=f"/audit/{audit_id}", status_code=303)

    clause = db.query(Clause).filter(Clause.id == item.clause_id).first()
    pack = db.query(QuestionPack).filter(QuestionPack.id == item.question_pack_id).first()
    requirement_text = None
    if clause and pack:
        requirement_text = f"Cláusula {clause.number} ({clause.title}): {pack.question}"

    result = assess_item(
        checklist_item_id=uuid.UUID(item_id),
        audit_id=uuid.UUID(audit_id),
        evidence_file_id=last_evidence.id,
        db=db,
        tenant_id=membership.tenant_id,
        requirement_text=requirement_text,
    )

    if result.get("status") == "success":
        if not result.get("relevant", True):
            item.status = "pending"
        elif result.get("requires_human_review"):
            item.status = "pending_review"
        else:
            item.status = "completed"
    elif result.get("status") == "simulated":
        item.status = "pending_review"
    else:
        item.status = "pending"
    db.commit()

    return RedirectResponse(url=f"/audit/{audit_id}", status_code=303)


@router.post("/audit/{audit_id}/analyze")
@limiter.limit("20/minute")
def analyze(
    request: Request,
    audit_id: str,
    file: UploadFile = File(...),
    membership: Membership = Depends(require_perm("upload_evidence")),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """Análisis de evidencia con rate limiting (20/min) para proteger costos de IA."""
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


# ===== PORTAL DEL CLIENTE =====

_PORTAL_VISIBLE_STATUSES = ("completed", "pending")


@router.get("/portal", response_class=HTMLResponse)
def portal(
    request: Request,
    membership: Membership = Depends(require_perm("view_portal")),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Portal del cliente: solo auditorías de SU client_id."""
    role = membership.role
    show_findings = role_can(role, "propose_capa")

    query = db.query(Audit).filter(Audit.tenant_id == membership.tenant_id)
    if membership.client_id:
        query = query.filter(Audit.client_id == membership.client_id)
    audits = query.all()

    portal_audits = []
    for audit in audits:
        # REGLA DE ORO: excluir `pending_review` del portal
        items = (
            db.query(ChecklistItem)
            .filter(
                ChecklistItem.audit_id == audit.id,
                ChecklistItem.status.in_(_PORTAL_VISIBLE_STATUSES),
            )
            .order_by(ChecklistItem.id)
            .all()
        )
        total = len(items)
        completed = sum(1 for i in items if i.status == "completed")
        progress = (completed / total * 100) if total else 0

        item_views = []
        for it in items:
            analysis = (
                db.query(AIAnalysis)
                .join(EvidenceFile, EvidenceFile.id == AIAnalysis.evidence_file_id)
                .filter(EvidenceFile.checklist_item_id == it.id)
                .order_by(AIAnalysis.created_at.desc())
                .first()
            )
            include_details = show_findings and it.status == "completed"
            item_views.append({
                "id": str(it.id),
                "clause_number": _clause_number(db, it),
                "status": it.status,
                "assessment": analysis.compliance_assessment if analysis else None,
                "confidence": analysis.confidence if analysis else 0.0,
                "gaps": (analysis.gaps if analysis and include_details else []) or [],
                "risks": (analysis.risks if analysis and include_details else []) or [],
            })

        portal_audits.append({
            "id": str(audit.id),
            "name": audit.name,
            "status": audit.status,
            "progress": progress,
            "completed": completed,
            "total": total,
            "checklist_items": item_views,
        })

    return templates.TemplateResponse(
        request, "portal.html",
        {"audits": portal_audits, "role": role, "show_findings": show_findings},
    )


def _clause_number(db: Session, item) -> str:
    """Helper: obtener número de cláusula de un ítem."""
    clause = db.query(Clause).filter(Clause.id == item.clause_id).first()
    return clause.number if clause else ""


# ===== GESTIÓN DE USUARIOS =====

@router.get("/users", response_class=HTMLResponse)
def manage_users(
    request: Request,
    membership: Membership = Depends(require_perm("manage_users")),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    rows = (
        db.query(User, Membership)
        .join(Membership, Membership.user_id == User.id)
        .filter(Membership.tenant_id == membership.tenant_id)
        .all()
    )
    users = [{"id": str(u.id), "email": u.email, "full_name": u.full_name, "role": m.role} for u, m in rows]
    return templates.TemplateResponse(
        request, "manage_users.html", {"users": users}
    )


@router.post("/users/invite")
def invite_user(
    email: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    membership: Membership = Depends(require_perm("manage_users")),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    valid_roles = (
        "lead_auditor", "auditor", "coordinator", "observer",
        "client_responsible", "client_process_owner", "client_sponsor",
    )
    if role not in valid_roles:
        return RedirectResponse(url="/users", status_code=303)
    if db.query(User).filter(User.email == email).first():
        return RedirectResponse(url="/users", status_code=303)
    user = User(email=email, password_hash=hasher.hash(password), full_name=full_name)
    db.add(user)
    db.flush()
    db.add(Membership(user_id=user.id, tenant_id=membership.tenant_id, role=role))
    db.commit()
    return RedirectResponse(url="/users", status_code=303)


# ===== ACCIONES SOBRE ÍTEMS DE CHECKLIST =====

@router.post("/audit/{audit_id}/item/{item_id}/reopen")
def reopen_item(
    audit_id: str,
    item_id: str,
    membership: Membership = Depends(require_perm("reopen_item")),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    item = db.query(ChecklistItem).filter(
        ChecklistItem.id == uuid.UUID(item_id),
        ChecklistItem.tenant_id == membership.tenant_id,
    ).first()
    if not item:
        return RedirectResponse(url=f"/audit/{audit_id}", status_code=303)
    item.status = "pending"
    db.commit()
    return RedirectResponse(url=f"/audit/{audit_id}", status_code=303)


@router.post("/audit/{audit_id}/item/{item_id}/approve")
def approve_item(
    audit_id: str,
    item_id: str,
    membership: Membership = Depends(require_perm("approve_item")),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    item = db.query(ChecklistItem).filter(
        ChecklistItem.id == uuid.UUID(item_id),
        ChecklistItem.tenant_id == membership.tenant_id,
    ).first()
    if not item:
        return RedirectResponse(url=f"/audit/{audit_id}", status_code=303)
    item.status = "completed"
    db.commit()
    return RedirectResponse(url=f"/audit/{audit_id}", status_code=303)


# ===== STREAMING SSE PARA ANÁLISIS EN TIEMPO REAL =====

@router.get("/audit/{audit_id}/stream")
async def stream_audit_updates(
    request: Request,
    audit_id: str,
    membership: Membership = Depends(require_perm("view_internal")),
    db: Session = Depends(get_db),
):
    """Stream SSE para análisis en tiempo real (usa evidencia más reciente)."""
    latest_evidence = (
        db.query(EvidenceFile)
        .filter(EvidenceFile.audit_id == uuid.UUID(audit_id))
        .order_by(EvidenceFile.created_at.desc())
        .first()
    )
    
    if not latest_evidence:
        async def error_generator():
            yield f"data: {json.dumps({'type': 'error', 'message': 'No evidence found'})}\n\n"
        return StreamingResponse(error_generator(), media_type="text/event-stream")

    async def event_generator():
        queue = asyncio.Queue(maxsize=10)
        
        loop = asyncio.get_event_loop()
        analysis_task = loop.run_in_executor(
            None,
            assess_compliance,
            latest_evidence.id,
            uuid.UUID(audit_id),
            db,
            membership.tenant_id,
            None,
            None,
            queue
        )

        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") in ("complete", "error"):
                    break
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'type': 'timeout', 'message': 'Analysis timed out'})}\n\n"
        finally:
            if not analysis_task.done():
                analysis_task.cancel()
            while not queue.empty():
                try: 
                    queue.get_nowait()
                except Exception:
                    pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )


# ===== RECUPERACIÓN DE CONTRASEÑA =====

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _find_valid_token(db: Session, raw_token: str):
    """Token existente, sin usar y no expirado (no lo consume)."""
    th = hashlib.sha256(raw_token.encode()).hexdigest()
    tok = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == th
    ).first()
    if tok is None or tok.used_at is not None or tok.expires_at < _utcnow():
        return None
    return tok


@router.post("/users/{user_id}/reset-link")
@limiter.limit("10/minute")
def generate_reset_link(
    request: Request,
    user_id: str,
    membership: Membership = Depends(require_perm("manage_users")),
    db: Session = Depends(get_db),
):
    """Owner genera enlace de un solo uso (60 min) y lo entrega por canal confiable."""
    try:
        target_id = uuid.UUID(user_id)
    except ValueError:
        return RedirectResponse(url="/users", status_code=303)
    target = db.query(User).filter(User.id == target_id).first()
    if not target:
        return RedirectResponse(url="/users", status_code=303)

    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == target.id,
        PasswordResetToken.used_at.is_(None),
    ).update({"used_at": _utcnow()})

    raw = secrets.token_urlsafe(32)
    db.add(PasswordResetToken(
        user_id=target.id,
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        created_by=membership.user_id,
        expires_at=_utcnow() + timedelta(minutes=60),
    ))
    db.add(AuditLog(
        tenant_id=membership.tenant_id,
        actor_user_id=membership.user_id,
        action="password_reset_link_generated",
        entity_type="user",
        entity_id=target.id,
    ))
    db.commit()

    full_link = str(request.base_url).rstrip("/") + f"/reset-password?token={raw}"
    return templates.TemplateResponse(
        request, "reset_link.html", {"email": target.email, "link": full_link},
    )


@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(
    request: Request, token: str = "", db: Session = Depends(get_db),
) -> HTMLResponse:
    valid = token != "" and _find_valid_token(db, token) is not None
    return templates.TemplateResponse(
        request, "reset_password.html",
        {"token": token, "valid": valid, "error": request.query_params.get("error")},
    )


@router.post("/web/reset-password")
@limiter.limit("10/minute")
def web_reset_password(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    tok = _find_valid_token(db, token)
    if tok is None:
        return RedirectResponse(url="/reset-password?error=invalid", status_code=303)
    if len(password) < 8:
        return RedirectResponse(
            url=f"/reset-password?token={token}&error=weak", status_code=303
        )
    user = db.query(User).filter(User.id == tok.user_id).first()
    if not user or user.status != "active":
        return RedirectResponse(url="/reset-password?error=invalid", status_code=303)

    user.password_hash = hasher.hash(password)
    tok.used_at = _utcnow()
    m = db.query(Membership).filter(Membership.user_id == user.id).first()
    if m:
        db.add(AuditLog(
            tenant_id=m.tenant_id,
            actor_user_id=user.id,
            action="password_reset_completed",
            entity_type="user",
            entity_id=user.id,
        ))
    db.commit()
    return RedirectResponse(url="/login?msg=password_reset", status_code=303)


# ===== INCREMENTO 5: ENDPOINT DE AUDIT LOGS (API JSON + UI) =====

# ===== INCREMENTO 5: AUDIT LOGS UI & API =====

@router.get("/audit-logs", response_class=HTMLResponse)
def audit_logs_page(
    request: Request,
    membership: Membership = Depends(require_perm("manage_users")),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    """Página de visualización de logs de auditoría."""
    tenant_id, user_id = _parse_session(request)
    
    # Obtener lista de usuarios para el filtro dropdown
    users = db.query(User).join(Membership).filter(
        Membership.tenant_id == membership.tenant_id
    ).all()
    
    return templates.TemplateResponse(
        request, "audit_logs.html", 
        {
            "users": users, 
            "role": membership.role,
            "tenant_id": str(membership.tenant_id)
        }
    )


@router.get("/api/audit-logs")
async def get_audit_logs(
    request: Request,
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    actor_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),      # ← str, no datetime
    end_date: Optional[str] = Query(None),         # ← str, no datetime
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
):
    """Consulta logs de auditoría con filtros usando sesión por cookie."""
    tenant_id, user_id = _parse_session(request)
    
    if not tenant_id or not user_id:
        return []

    query = db.query(AuditLog).filter(AuditLog.tenant_id == tenant_id)
    
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        try:
            query = query.filter(AuditLog.entity_id == uuid.UUID(entity_id))
        except ValueError:
            pass
    if actor_id:
        try:
            query = query.filter(AuditLog.actor_user_id == uuid.UUID(actor_id))
        except ValueError:
            pass
    
    # Parsear fechas manualmente desde string YYYY-MM-DD
    if start_date:
        try:
            from datetime import date
            sd = date.fromisoformat(start_date)
            query = query.filter(AuditLog.created_at >= sd)
        except ValueError:
            pass
    
    if end_date:
        try:
            from datetime import date, timedelta
            ed = date.fromisoformat(end_date) + timedelta(days=1)
            query = query.filter(AuditLog.created_at < ed)
        except ValueError:
            pass
    
    # RBAC
    membership = db.query(Membership).filter(
        Membership.user_id == user_id,
        Membership.tenant_id == tenant_id,
    ).first()
    
    is_admin = membership and membership.role in ("owner", "admin", "lead_auditor")
    if not is_admin:
        query = query.filter(AuditLog.actor_user_id == user_id)
    
    logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": str(log.id),
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": str(log.entity_id) if log.entity_id else None,
            "actor_user_id": str(log.actor_user_id) if log.actor_user_id else None,
            "before": log.before,
            "after": log.after,
            "created_at": log.created_at.isoformat()
        }
        for log in logs
    ]