"""Gateway for querying Pan American Energy (PAE) career and talent opportunities."""

from typing import Any

import httpx

from src.domain.empleo.entities import OfertaLaboral
from src.domain.empleo.ports import PortalEmpleoPort
from src.domain.empleo.value_objects import (
    FuenteOferta,
    ModalidadTrabajo,
)

DEFAULT_PAE_CAREERS_URL = "https://jobs.pan-energy.com/career"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


class PaeTalentGateway(PortalEmpleoPort):
    """Implementación del puerto PortalEmpleoPort para el portal de talento de Pan American Energy (PAE)."""

    def __init__(
        self,
        base_url: str = DEFAULT_PAE_CAREERS_URL,
        http_client: Any | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._base_url = base_url
        self._http_client = http_client
        self._timeout_seconds = timeout_seconds

    def obtener_fuente(self) -> FuenteOferta:
        """Identificador de la fuente."""
        return FuenteOferta.PAE

    def buscar_ofertas(
        self,
        palabras_clave: tuple[str, ...],
        ubicacion: str | None = None,
    ) -> list[OfertaLaboral]:
        """Consulta ofertas en el portal de PAE y las normaliza al dominio."""
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        }

        query_str = " ".join(palabras_clave)
        params: dict[str, str] = {
            "company": "PAE",
            "career_ns": "job_listing_summary",
            "nav_bar": "job_search",
        }
        if query_str:
            params["keyword"] = query_str
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
            # Resiliencia: ante caídas de conexión retorna lista vacía
            return []

    def _parsear_resultados(self, data: dict[str, Any]) -> list[OfertaLaboral]:
        """Extrae y normaliza las entidades OfertaLaboral a partir del payload JSON."""
        resultados: list[OfertaLaboral] = []

        items: list[Any] = []
        if isinstance(data, dict):
            d_dict = data.get("d")
            if isinstance(d_dict, dict) and isinstance(d_dict.get("results"), list):
                items = list(d_dict["results"])
            elif isinstance(data.get("results"), list):
                items = list(data["results"])
            elif isinstance(data.get("jobs"), list):
                items = list(data["jobs"])
        elif isinstance(data, list):
            items = list(data)

        for item in items:
            if not isinstance(item, dict):
                continue

            req_id = str(item.get("jobReqId") or item.get("id") or "")
            titulo = str(item.get("jobTitle") or item.get("title") or "")
            if not titulo:
                continue

            ubicacion = str(
                item.get("location") or item.get("city") or "Neuquén, Argentina"
            )
            descripcion = str(
                item.get("jobDescription") or item.get("description") or ""
            )
            url = str(item.get("applyUrl") or item.get("url") or "")
            fecha = str(item.get("postingDate") or item.get("date") or "")

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

            clean_id = req_id if req_id.startswith("pae-") else f"pae-{req_id}"
            oferta = OfertaLaboral(
                id_oferta=clean_id if req_id else f"pae-{hash(titulo)}",
                titulo=titulo,
                empresa="Pan American Energy (PAE)",
                ubicacion=ubicacion,
                descripcion=descripcion,
                url_postulacion=url,
                fecha_publicacion=fecha,
                fuente=FuenteOferta.PAE,
                modalidad=modalidad,
            )
            resultados.append(oferta)

        return resultados
