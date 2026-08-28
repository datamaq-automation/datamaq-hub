"""Excepciones de dominio para el módulo de calculadora de factor de potencia cos fi."""


class CalculadoraCosFiException(Exception):
    """Excepción base para errores de la calculadora de cos fi."""


class ValorCosFiInvalidoException(CalculadoraCosFiException):
    """Lanzada cuando el valor de cos fi no está en el rango (0.0, 1.0]."""


class PotenciaInvalidaException(CalculadoraCosFiException):
    """Lanzada cuando el valor de potencia activa es menor o igual a cero."""


class FacturaInvalidaException(CalculadoraCosFiException):
    """Lanzada cuando el importe de factura base es negativo."""
