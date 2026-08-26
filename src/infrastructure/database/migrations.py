"""Inicialización del schema de caché en MySQL mediante SQLAlchemy (CREATE TABLE IF NOT EXISTS)."""

from src.infrastructure.database.engine import Base, get_engine


def init_db() -> None:
    """Crea las tablas necesarias si no existen.

    Operación idempotente y segura: no destruye datos existentes.
    No hace nada si DATABASE_URL no está configurado (degradación elegante).
    """
    engine = get_engine()
    if engine is not None:
        Base.metadata.create_all(engine)
