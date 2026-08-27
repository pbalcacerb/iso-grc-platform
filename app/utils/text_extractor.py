"""Utilidad para extraer texto de archivos (TXT/PDF)."""
from pathlib import Path

from pypdf import PdfReader


def extract_text_from_file(file_path: str) -> str:
    """
    Extrae texto de un archivo (TXT o PDF).
    
    Args:
        file_path: Ruta al archivo
        
    Returns:
        Texto extraído
    """
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
    
    suffix = path.suffix.lower()
    
    if suffix == '.txt':
        return path.read_text(encoding='utf-8')
    
    elif suffix == '.pdf':
        reader = PdfReader(str(path))  # Convertir Path a str
        parts = []
        for page in reader.pages:
            try:
                extracted = page.extract_text() or ""
            except Exception:
                extracted = ""
            if extracted.strip():
                parts.append(extracted)
        return "\n".join(parts).strip()
    
    else:
        try:
            return path.read_text(encoding='utf-8')
        except Exception:
            return ""