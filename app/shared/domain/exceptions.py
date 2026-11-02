# ==============================================================================
# EXCEPCIONES DE DOMINIO DEL NEGOCIO
# Archivo: backend/app/shared/domain/exceptions.py
# ==============================================================================

class DomainException(Exception):
    """Clase base para todas las excepciones del dominio."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class InsufficientStockException(DomainException):
    """Se dispara cuando se intenta reservar una cantidad mayor al saldo disponible."""
    pass


class BarnLockedException(DomainException):
    """Se dispara cuando se intenta operar comercialmente sobre un galpón bloqueado."""
    pass


class SimulatedDataNotAllowedException(DomainException):
    """Se dispara cuando se intenta respaldar una operación real sobre una muestra simulada."""
    pass


class IncompleteSampleException(DomainException):
    """Se dispara cuando el total de pesos no coincide con la muestra declarada."""
    pass


class RevalidationFailedException(DomainException):
    """Se dispara cuando el saldo cambió mientras Gerencia evaluaba un caso de aprobación."""
    pass


class SaldoNegativoException(DomainException):
    """Se dispara si una operación produciría un saldo físico o disponible negativo."""
    pass

