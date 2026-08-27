"""Generación y búsqueda de embeddings vía proveedor conmutable (WP0)."""
import uuid
from typing import List, Tuple

from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.ai.providers import get_provider
from app.models import EvidenceTextChunk
from app.utils.chunker import chunk_text


def generate_embedding(text: str) -> List[float]:
    """Genera un embedding usando el proveedor activo."""
    return get_provider().embed(text)


def create_chunks_and_embeddings(
    evidence_file_id: uuid.UUID,
    extraction_id: uuid.UUID,  # ← NUEVO PARÁMETRO OBLIGATORIO
    text: str,
    tenant_id: uuid.UUID,
    db: Session,
    chunk_size: int = 500,
) -> List[EvidenceTextChunk]:
    """Divide el texto en chunks y guarda cada chunk con su vector."""
    chunks_text = chunk_text(text, chunk_size=chunk_size)
    if not chunks_text:
        return []

    provider = get_provider()
    chunks: List[EvidenceTextChunk] = []

    for seq, body in enumerate(chunks_text):
        chunk = EvidenceTextChunk(
            tenant_id=tenant_id,
            extraction_id=extraction_id,  # ← USAR EL PARÁMETRO
            evidence_file_id=evidence_file_id,
            seq=seq,
            text=body,
        )
        db.add(chunk)
        db.flush()

        embedding = provider.embed(body)
        vector_str = "[" + ",".join(str(x) for x in embedding) + "]"
        db.execute(
            sql_text(
                "INSERT INTO evidence_vectors "
                "(id, chunk_id, tenant_id, model, dim, embedding) "
                "VALUES (:id, :chunk_id, :tenant_id, :model, :dim, :emb::vector)"
            ),
            {
                "id": uuid.uuid4(),
                "chunk_id": chunk.id,
                "tenant_id": tenant_id,
                "model": provider.embedding_model,
                "dim": len(embedding),
                "emb": vector_str,
            },
        )
        chunks.append(chunk)

    db.commit()
    return chunks


def search_similar_chunks(
    query_text: str,
    audit_id: uuid.UUID,
    db: Session,
    top_k: int = 5,
    threshold: float = 0.6,
) -> List[Tuple[EvidenceTextChunk, float]]:
    """Busca chunks relevantes por similitud coseno dentro de la auditoría."""
    provider = get_provider()
    query_vec = provider.embed(query_text)
    query_str = "[" + ",".join(str(x) for x in query_vec) + "]"
    max_distance = 1.0 - threshold

    rows = db.execute(
        sql_text(
            """
            SELECT c.id,
                   1 - (v.embedding <=> :q::vector) AS similarity
            FROM evidence_text_chunks c
            JOIN evidence_vectors v ON v.chunk_id = c.id
            JOIN evidence_files ef ON ef.id = c.evidence_file_id
            WHERE ef.audit_id = :audit_id
              AND (v.embedding <=> :q::vector) <= :max_distance
            ORDER BY similarity DESC
            LIMIT :top_k
            """
        ),
        {
            "q": query_str,
            "audit_id": audit_id,
            "max_distance": max_distance,
            "top_k": top_k,
        },
    ).fetchall()

    result: List[Tuple[EvidenceTextChunk, float]] = []
    for row in rows:
        chunk = (
            db.query(EvidenceTextChunk)
            .filter(EvidenceTextChunk.id == row.id)
            .first()
        )
        if chunk:
            result.append((chunk, float(row.similarity)))
    return result