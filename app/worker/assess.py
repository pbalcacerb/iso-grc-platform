import asyncio
from typing import Optional
import uuid
from sqlalchemy.orm import Session

def _safe_put_queue_sync(queue: asyncio.Queue, message: dict):
    """Helper seguro para queues desde contexto síncrono."""
    try:
        if not queue.full():
            # Usar call_soon_threadsafe para seguridad en threads
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(queue.put(message), loop)
            else:
                # Fallback para tests sin loop activo
                loop.run_until_complete(queue.put(message))
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
            _safe_put_queue_sync(sse_queue, {
                "type": "status",
                "data": "analysis_started",
                "audit_id": str(audit_id)
            })

        # === TU LÓGICA DE ANÁLISIS EXISTENTE AQUÍ ===
        # Simulación de progreso (reemplazar con lógica real)
        for progress in [0.25, 0.5, 0.75]:
            if sse_queue:
                _safe_put_queue_sync(sse_queue, {
                    "type": "progress",
                    "data": progress,
                    "message": f"Processing... {progress*100:.0f}%"
                })
            # Simula trabajo pesado (reemplazar con llamada real a IA)
            import time; time.sleep(0.1)

        result = {
            "status": "completed",
            "confidence": 0.95,
            "gaps": ["Sample gap detected"]
        }

        if sse_queue:
            _safe_put_queue_sync(sse_queue, {
                "type": "complete",
                "data": result,
                "audit_id": str(audit_id)
            })

        return result
        
    except Exception as e:
        if sse_queue:
            _safe_put_queue_sync(sse_queue, {
                "type": "error",
                "error": str(e),
                "audit_id": str(audit_id)
            })
        raise  # Re-lanzar para que el caller maneje el error


# En app/worker/assess.py, al final del archivo:
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
            _safe_put_queue_sync(sse_queue, {
                "type": "status",
                "data": "item_analysis_started",
                "checklist_item_id": str(checklist_item_id)
            })

        # === LÓGICA REAL DE ANÁLISIS AQUÍ ===
        # Simulación de progreso (reemplazar con llamada real a IA)
        for progress in [0.3, 0.6, 0.9]:
            if sse_queue:
                _safe_put_queue_sync(sse_queue, {
                    "type": "progress",
                    "data": progress,
                    "message": f"Analyzing item... {progress*100:.0f}%"
                })
            import time; time.sleep(0.05)

        result = {
            "status": "completed",
            "relevant": True,
            "requires_human_review": False,
            "confidence": 0.92,
            "gaps": ["Sample gap for item"],
            "risks": ["Sample risk"]
        }

        if sse_queue:
            _safe_put_queue_sync(sse_queue, {
                "type": "complete",
                "data": result,
                "checklist_item_id": str(checklist_item_id)
            })

        return result
        
    except Exception as e:
        if sse_queue:
            _safe_put_queue_sync(sse_queue, {
                "type": "error",
                "error": str(e),
                "checklist_item_id": str(checklist_item_id)
            })
        raise