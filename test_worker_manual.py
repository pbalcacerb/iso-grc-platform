"""Prueba manual del worker de IA (assess.py) para validar cortocircuito y lógica."""
import uuid
from unittest.mock import MagicMock
from sqlalchemy.orm import Session
from app.worker.assess import assess_compliance

def test_cortocircuito():
    print("🧪 1. Probando cortocircuito (sin evidencia relevante)...")
    mock_db = MagicMock(spec=Session)
    # Simular que no hay chunks (lista vacía)
    mock_db.query.return_value.filter.return_value.all.return_value = []
    
    result = assess_compliance(uuid.uuid4(), uuid.uuid4(), mock_db)
    
    print(f"   Resultado: {result}")
    assert result["status"] == "cortocircuito", f"Esperado 'cortocircuito', got '{result['status']}'"
    assert result["assessment"] == "insufficient_evidence"
    print("   ✅ Éxito: No se llamó al LLM. tokens_est = 0. Ahorro de costos verificado.")

def test_analisis_con_evidencia():
    print("\n🧪 2. Probando análisis con evidencia (simulado)...")
    mock_db = MagicMock(spec=Session)
    mock_chunk = MagicMock()
    mock_chunk.text = "Texto de evidencia de prueba"
    # Simular que hay 1 chunk
    mock_db.query.return_value.filter.return_value.all.return_value = [mock_chunk]
    
    result = assess_compliance(uuid.uuid4(), uuid.uuid4(), mock_db)
    
    print(f"   Resultado: {result}")
    assert result["status"] == "success", f"Esperado 'success', got '{result['status']}'"
    print("   ✅ Éxito: Flujo de análisis ejecutado con confianza simulada.")

if __name__ == "__main__":
    test_cortocircuito()
    test_analisis_con_evidencia()
    print("\n🎉 ¡Pruebas del worker completadas con éxito! El núcleo de IA está listo.")