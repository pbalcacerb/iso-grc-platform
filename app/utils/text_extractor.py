"""Utilidad para extraer texto de archivos."""
import io
from pathlib import Path

from PyPDF2 import PdfReader


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
    
    # Leer según extensión
    suffix = path.suffix.lower()
    
    if suffix == '.txt':
        return path.read_text(encoding='utf-8')
    
    elif suffix == '.pdf':
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    
    else:
        # Para otros tipos, intentar leer como texto
        try:
            return path.read_text(encoding='utf-8')
        except:
            return ""