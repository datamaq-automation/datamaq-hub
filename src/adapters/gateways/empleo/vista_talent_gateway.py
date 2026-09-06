"""Gateway for querying Vista Energy career and talent opportunities."""

from typing import Any

import httpx

from src.domain.empleo.entities import OfertaLaboral
from src.domain.empleo.ports import PortalEmpleoPort
from src.domain.empleo.value_objects import (
    FuenteOferta,
    ModalidadTrabajo,
)

DEFAULT_VISTA_CAREERS_URL = "https://vistaenergy.com/api/careers"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


class VistaTalentGateway(PortalEmpleoPort):
    """Implementación del puerto PortalEmpleoPort para el portal de talento de Vista Energy."""

    def __init__(
        self,
        base_url: str = DEFAULT_VISTA_CAREERS_URL,
        http_client: Any | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._base_url = base_url
        self._http_client = http_client
        self._timeout_seconds = timeout_seconds

    def obtener_fuente(self) -> FuenteOferta:
        """Identificador de la fuente."""
        return FuenteOferta.VISTA

    def buscar_ofertas(
        self,
        palabras_clave: tuple[str, ...],
        ubicacion: str | None = None,
    ) -> list[OfertaLaboral]:
        """Consulta ofertas en el portal de Vista Energy y las normaliza al dominio."""
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        }

        query_str = " ".join(palabras_clave)
        params: dict[str, str] = {}
        if query_str:
            params["q"] = query_str
        if ubicacion:
            params["location"] = ubicacion

        try:
            if self._http_client is not None:
                response = self._http_client.get(
                    self._base_url,
                    params=params,
                    headers=headers,
                    timeout=self._timeout_seconds,
                )
            else:
                with httpx.Client(timeout=self._timeout_seconds) as client:
                    response = client.get(
                        self._base_url,
                        params=params,
                        headers=headers,
                    )

            if response.status_code != 200:
                return []

            data = response.json()
            return self._parsear_resultados(data)

        except (httpx.HTTPError, ValueError, KeyError, OSError):
            # Resiliencia: ante fallas de conexión o formato retorna lista vacía
            return []

    def _parsear_resultados(self, data: dict[str, Any]) -> list[OfertaLaboral]:
        """Extrae y normaliza las entidades OfertaLaboral a partir del payload JSON."""
        resultados: list[OfertaLaboral] = []

        items: list[Any] = []
        if isinstance(data, dict):
            if "jobs" in data and isinstance(data["jobs"], list):
                items = list(data["jobs"])
            elif "results" in data and isinstance(data["results"], list):
                items = list(data["results"])
            elif "d" in data and isinstance(data["d"], dict) and "results" in data["d"]:
                items = list(data["d"]["results"])
        elif isinstance(data, list):
            items = list(data)

        for item in items:
            if not isinstance(item, dict):
                continue

            req_id = str(item.get("id") or item.get("jobReqId") or "")
            titulo = str(item.get("title") or item.get("jobTitle") or "")
            if not titulo:
                continue

            ubicacion = str(
                item.get("location") or item.get("city") or "Neuquén, Argentina"
            )
            descripcion = str(
                item.get("description") or item.get("jobDescription") or ""
            )
            url = str(item.get("url") or item.get("applyUrl") or "")
            fecha = str(item.get("date") or item.get("postingDate") or "")

            modalidad = ModalidadTrabajo.INDEFINIDO
            desc_lower = (titulo + " " + descripcion).lower()
            if (
                "rotativ" in desc_lower
                or "rotacional" in desc_lower
                or "campamento" in desc_lower
                or "yacimiento" in desc_lower
            ):
                modalidad = ModalidadTrabajo.ROTACIONAL_YACIMIENTO
            elif "remoto" in desc_lower or "remote" in desc_lower:
                modalidad = ModalidadTrabajo.REMOTO
            elif "hibrid" in desc_lower or "híbrid" in desc_lower:
                modalidad = ModalidadTrabajo.HIBRIDO
            elif "presencial" in desc_lower:
                modalidad = ModalidadTrabajo.PRESENCIAL

            clean_id = req_id if req_id.startswith("vista-") else f"vista-{req_id}"
            oferta = OfertaLaboral(
                id_oferta=clean_id if req_id else f"vista-{hash(titulo)}",
                titulo=titulo,
                empresa="Vista Energy",
                ubicacion=ubicacion,
                descripcion=descripcion,
                url_postulacion=url,
                fecha_publicacion=fecha,
                fuente=FuenteOferta.VISTA,
                modalidad=modalidad,
            )
            resultados.append(oferta)

        return resultados
