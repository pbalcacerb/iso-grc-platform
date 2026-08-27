"""Utilidad para dividir texto en chunks."""
import re
from typing import List


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Divide texto en chunks con solapamiento.
    
    Args:
        text: Texto completo
        chunk_size: Tamaño máximo de cada chunk (en caracteres)
        overlap: Solapamiento entre chunks (en caracteres)
        
    Returns:
        Lista de chunks
    """
    if not text or not text.strip():
        return []
    
    # Dividir por párrafos
    paragraphs = re.split(r'\n\s*\n', text)
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # Si agregar este párrafo excede el tamaño, guardar chunk actual
        if len(current_chunk) + len(para) > chunk_size and current_chunk:
            chunks.append(current_chunk.strip())
            # Mantener overlap del chunk anterior
            if overlap > 0:
                current_chunk = current_chunk[-overlap:] + "\n\n" + para
            else:
                current_chunk = para
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
    
    # Agregar último chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks