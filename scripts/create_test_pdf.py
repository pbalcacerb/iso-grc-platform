"""Genera un PDF de prueba para validación E2E."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def create_test_pdf(output_path: str) -> None:
    """Crea un PDF simple con texto de política de calidad."""
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    
    # Título
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 72, "Política de Calidad")
    
    # Contenido
    c.setFont("Helvetica", 12)
    text_lines = [
        "La dirección de la organización se compromete a:",
        "",
        "1. Establecer, implementar y mantener un Sistema de Gestión de Calidad",
        "   conforme a los requisitos de la norma ISO 9001:2015.",
        "",
        "2. Asegurar la satisfacción del cliente mediante la mejora continua",
        "   de nuestros procesos y servicios.",
        "",
        "3. Cumplir con los requisitos legales y reglamentarios aplicables.",
        "",
        "4. Promover la participación de todo el personal en la mejora",
        "   de la calidad.",
        "",
        "Esta política es comunicada y entendida por todo el personal.",
        "",
        "Firmado: Director General",
        "Fecha: 2026-01-15",
    ]
    
    y_position = height - 120
    for line in text_lines:
        c.drawString(72, y_position, line)
        y_position -= 20
        if y_position < 72:
            c.showPage()
            c.setFont("Helvetica", 12)
            y_position = height - 72
    
    c.save()
    print(f"✅ PDF creado en: {output_path}")


if __name__ == "__main__":
    output = "data/evidence/test_policy.pdf"
    Path("data/evidence").mkdir(exist_ok=True)
    create_test_pdf(output)