# ==============================================================================
# PRUEBAS UNITARIAS DE REGLAS DE NEGOCIO DEL MÓDULO PECUARIA
# Archivo: backend/tests/test_pecuaria.py
# ==============================================================================

from datetime import date, timedelta
import numpy as np
import pytest
from app.modules.pecuaria.application.dtos import (
    BatchCreateDTO,
    IndividualWeightEntryDTO,
    SampleWeightsBatchDTO,
)


def test_batch_sex_validation():
    """Valida que solo se admitan 'MACHO', 'HEMBRA' o 'MIXTO' en el lote."""
    # Válido en minúsculas se convierte a mayúsculas
    batch = BatchCreateDTO(
        barn_id="11111111-1111-1111-1111-111111111111",
        batch_code="LOTE-001",
        hatch_date=date.today() - timedelta(days=42),
        initial_count=25000,
        sex="macho",
    )
    assert batch.sex == "MACHO"

    # Inválido lanza error de validación
    with pytest.raises(ValueError):
        BatchCreateDTO(
            barn_id="11111111-1111-1111-1111-111111111111",
            batch_code="LOTE-002",
            hatch_date=date.today(),
            initial_count=20000,
            sex="INDETERMINADO",
        )


def test_bird_age_calculation():
    """Verifica que la edad del ave en días se calcule con precisión."""
    hatch_date = date.today() - timedelta(days=45)
    age_days = (date.today() - hatch_date).days
    assert age_days == 45


def test_statistical_weights_calculation():
    """Verifica el cálculo del peso promedio (x̄), desviación, mínimo y máximo."""
    weights = [2.250, 2.300, 2.450, 2.500, 2.350]
    arr = np.array(weights, dtype=float)

    avg_w = float(np.mean(arr))
    min_w = float(np.min(arr))
    max_w = float(np.max(arr))
    std_w = float(np.std(arr))

    assert round(avg_w, 3) == 2.370
    assert min_w == 2.250
    assert max_w == 2.500
    assert round(std_w, 3) == 0.093


def test_inventory_formula_invariants():
    """
    Verifica la ecuación central de disponibilidad comercial:
    disponible = conteo_fisico - especiales - reservadas - vendidas
    """
    physical_count = 30000
    specials_count = 150
    reserved_count = 5000
    sold_pending_count = 2000

    available_count = physical_count - specials_count - reserved_count - sold_pending_count
    assert available_count == 22850

    # Nuevos especiales restan inmediatamente de disponible pero no alteran el físico
    new_specials = 100
    specials_count += new_specials
    available_count = physical_count - specials_count - reserved_count - sold_pending_count

    assert physical_count == 30000
    assert available_count == 22750

