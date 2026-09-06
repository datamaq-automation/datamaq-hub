"""Port interfaces for empleo bounded context."""

from typing import Protocol

from src.domain.empleo.entities import (
    InteraccionPostulacion,
    OfertaLaboral,
    OportunidadLaboral,
)
from src.domain.empleo.value_objects import EstadoOportunidad, FuenteOferta


class PortalEmpleoPort(Protocol):
    """Puerto para consultar un portal de empleo externo."""

    def obtener_fuente(self) -> FuenteOferta:
        """Devuelve el identificador de la fuente del portal."""
        ...

    def buscar_ofertas(
        self,
        palabras_clave: tuple[str, ...],
        ubicacion: str | None = None,
    ) -> list[OfertaLaboral]:
        """Consulta ofertas vigentes en el portal externo."""
        ...


class OfertasCachePort(Protocol):
    """Puerto para almacenamiento en caché de ofertas laborales."""

    def obtener_ofertas(self, cache_key: str) -> list[OfertaLaboral] | None:
        """Recupera ofertas cacheadas si no han expirado."""
        ...

    def guardar_ofertas(
        self,
        cache_key: str,
        ofertas: list[OfertaLaboral],
        ttl_segundos: int = 3600,
    ) -> None:
        """Almacena ofertas en caché con un tiempo de vida dado."""
        ...


class OportunidadesRepositoryPort(Protocol):
    """Puerto para persistencia relacional de oportunidades laborales e interacciones."""

    def guardar(self, oportunidad: OportunidadLaboral) -> OportunidadLaboral:
        """Guarda o actualiza una oportunidad laboral."""
        ...

    def obtener_por_id(self, id_oportunidad: int) -> OportunidadLaboral | None:
        """Obtiene una oportunidad laboral por su identificador primario."""
        ...

    def listar(
        self,
        estado: EstadoOportunidad | None = None,
        empresa: str | None = None,
    ) -> list[OportunidadLaboral]:
        """Lista oportunidades aplicando filtros opcionales de estado y empresa."""
        ...

    def actualizar_estado(
        self,
        id_oportunidad: int,
        nuevo_estado: EstadoOportunidad,
        notas: str | None = None,
    ) -> OportunidadLaboral:
        """Actualiza el estado y notas de una oportunidad."""
        ...

    def eliminar(self, id_oportunidad: int) -> bool:
        """Elimina una oportunidad de la base de datos."""
        ...

    def registrar_interaccion(
        self,
        interaccion: InteraccionPostulacion,
    ) -> InteraccionPostulacion:
        """Registra una interacción o contacto de seguimiento."""
        ...

    def listar_interacciones(
        self,
        oportunidad_id: int,
    ) -> list[InteraccionPostulacion]:
        """Lista las interacciones asociadas a una oportunidad."""
        ...
