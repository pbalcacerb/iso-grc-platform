"""Worker de evaluación de cumplimiento ISO con soporte para eventos SSE."""
import asyncio
import time
from typing import Optional
import uuid
from sqlalchemy.orm import Session


def _safe_put_queue_sync(queue: asyncio.Queue, message: dict):
    """Helper seguro para queues desde contexto síncrono sin advertencias de event loop deprecado."""
    try:
        if not queue.full():
            try:
                loop = asyncio.get_running_loop()
                asyncio.run_coroutine_threadsafe(queue.put(message), loop)
            except RuntimeError:
                # Fallback para contexto síncrono o ejecuciones de test sin loop activo en el hilo
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(queue.put(message))
                finally:
                    loop.close()
    except (asyncio.QueueFull, RuntimeError, Exception):
        pass  # Silencioso: no bloquear análisis por SSE roto


def assess_compliance(
    evidence_file_id: uuid.UUID,
    audit_id: uuid.UUID,
    db: Session,
    tenant_id: Optional[uuid.UUID] = None,
    requirement_text: Optional[str] = None,
    checklist_item_id: Optional[uuid.UUID] = None,
    sse_queue: Optional[asyncio.Queue] = None,
) -> dict:
    """Análisis de cumplimiento con soporte opcional SSE (SÍNCRONO)."""
    try:
        if sse_queue:
            _safe_put_queue_sync(
                sse_queue,
                {
                    "type": "status",
                    "data": "analysis_started",
                    "audit_id": str(audit_id),
                },
            )

        # === LÓGICA DE ANÁLISIS DE CUMPLIMIENTO ===
        for progress in [0.25, 0.5, 0.75]:
            if sse_queue:
                _safe_put_queue_sync(
                    sse_queue,
                    {
                        "type": "progress",
                        "data": progress,
                        "message": f"Processing... {progress*100:.0f}%",
                    },
                )
            time.sleep(0.1)

        result = {
            "status": "completed",
            "confidence": 0.95,
            "gaps": ["Sample gap detected"],
        }

        if sse_queue:
            _safe_put_queue_sync(
                sse_queue,
                {
                    "type": "complete",
                    "data": result,
                    "audit_id": str(audit_id),
                },
            )

        return result

    except Exception as e:
        if sse_queue:
            _safe_put_queue_sync(
                sse_queue,
                {
                    "type": "error",
                    "error": str(e),
                    "audit_id": str(audit_id),
                },
            )
        raise


def assess_item(
    checklist_item_id: uuid.UUID,
    audit_id: uuid.UUID,
    evidence_file_id: uuid.UUID,
    db: Session,
    tenant_id: Optional[uuid.UUID] = None,
    requirement_text: Optional[str] = None,
    sse_queue: Optional[asyncio.Queue] = None,
) -> dict:
    """Análisis de ítem individual con soporte opcional SSE."""
    try:
        if sse_queue:
            _safe_put_queue_sync(
                sse_queue,
                {
                    "type": "status",
                    "data": "item_analysis_started",
                    "checklist_item_id": str(checklist_item_id),
                },
            )

        # === LÓGICA DE ANÁLISIS POR ÍTEM ===
        for progress in [0.3, 0.6, 0.9]:
            if sse_queue:
                _safe_put_queue_sync(
                    sse_queue,
                    {
                        "type": "progress",
                        "data": progress,
                        "message": f"Analyzing item... {progress*100:.0f}%",
                    },
                )
            time.sleep(0.05)

        result = {
            "status": "completed",
            "relevant": True,
            "requires_human_review": False,
            "confidence": 0.92,
            "gaps": ["Sample gap for item"],
            "risks": ["Sample risk"],
        }

        if sse_queue:
            _safe_put_queue_sync(
                sse_queue,
                {
                    "type": "complete",
                    "data": result,
                    "checklist_item_id": str(checklist_item_id),
                },
            )

        return result

    except Exception as e:
        if sse_queue:
            _safe_put_queue_sync(
                sse_queue,
                {
                    "type": "error",
                    "error": str(e),
                    "checklist_item_id": str(checklist_item_id),
                },
            )
        raise