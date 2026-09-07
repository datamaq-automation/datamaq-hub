"""Controller for employment search, analysis, and application tracking."""

from pathlib import Path

from src.application.dtos.empleo_dtos import (
    ActualizarEstadoOportunidadDTO,
    BuscarOfertasQueryDTO,
    InteraccionDTO,
    OportunidadDTO,
    PerfilCandidatoDetalladoDTO,
    RegistrarInteraccionDTO,
    RegistrarOportunidadDTO,
    ResultadoBusquedaDTO,
)
from src.application.use_cases.empleo.buscar_ofertas_vaca_muerta_use_case import (
    BuscarOfertasVacaMuertaUseCase,
)
from src.application.use_cases.empleo.gestionar_oportunidades_use_cases import (
    ActualizarEstadoOportunidadUseCase,
    ListarInteraccionesUseCase,
    ListarOportunidadesUseCase,
    RegistrarInteraccionUseCase,
    RegistrarOportunidadUseCase,
)
from src.application.use_cases.empleo.parsear_perfil_linkedin_use_case import (
    ParsearPerfilLinkedInUseCase,
)


class EmpleoController:
    """Agnostic controller orchestrating job searches and application tracking in Vaca Muerta."""

    def __init__(
        self,
        buscar_ofertas_uc: BuscarOfertasVacaMuertaUseCase,
        registrar_oportunidad_uc: RegistrarOportunidadUseCase | None = None,
        listar_oportunidades_uc: ListarOportunidadesUseCase | None = None,
        actualizar_estado_uc: ActualizarEstadoOportunidadUseCase | None = None,
        registrar_interaccion_uc: RegistrarInteraccionUseCase | None = None,
        listar_interacciones_uc: ListarInteraccionesUseCase | None = None,
        parsear_perfil_linkedin_uc: ParsearPerfilLinkedInUseCase | None = None,
    ) -> None:
        self._buscar_ofertas_uc = buscar_ofertas_uc
        self._registrar_oportunidad_uc = registrar_oportunidad_uc
        self._listar_oportunidades_uc = listar_oportunidades_uc
        self._actualizar_estado_uc = actualizar_estado_uc
        self._registrar_interaccion_uc = registrar_interaccion_uc
        self._listar_interacciones_uc = listar_interacciones_uc
        self._parsear_perfil_linkedin_uc = parsear_perfil_linkedin_uc
        self._listar_interacciones_uc = listar_interacciones_uc

    def buscar_ofertas_vaca_muerta(
        self,
        query: BuscarOfertasQueryDTO,
    ) -> ResultadoBusquedaDTO:
        """Invoca el caso de uso para buscar y clasificar ofertas en Vaca Muerta."""
        return self._buscar_ofertas_uc.execute(query)

    def registrar_oportunidad(
        self,
        dto: RegistrarOportunidadDTO,
    ) -> OportunidadDTO:
        """Registra una nueva oportunidad o postulación laboral."""
        if not self._registrar_oportunidad_uc:
            raise ValueError("RegistrarOportunidadUseCase no está configurado")
        return self._registrar_oportunidad_uc.execute(dto)

    def listar_oportunidades(
        self,
        estado: str | None = None,
        empresa: str | None = None,
    ) -> list[OportunidadDTO]:
        """Lista las oportunidades registradas aplicando filtros opcionales."""
        if not self._listar_oportunidades_uc:
            raise ValueError("ListarOportunidadesUseCase no está configurado")
        return self._listar_oportunidades_uc.execute(estado=estado, empresa=empresa)

    def actualizar_estado_oportunidad(
        self,
        dto: ActualizarEstadoOportunidadDTO,
    ) -> OportunidadDTO:
        """Actualiza el estado y notas de una oportunidad."""
        if not self._actualizar_estado_uc:
            raise ValueError("ActualizarEstadoOportunidadUseCase no está configurado")
        return self._actualizar_estado_uc.execute(dto)

    def registrar_interaccion(
        self,
        dto: RegistrarInteraccionDTO,
    ) -> InteraccionDTO:
        """Registra un nuevo contacto o avance en el seguimiento de una postulación."""
        if not self._registrar_interaccion_uc:
            raise ValueError("RegistrarInteraccionUseCase no está configurado")
        return self._registrar_interaccion_uc.execute(dto)

    def listar_interacciones(
        self,
        oportunidad_id: int,
    ) -> list[InteraccionDTO]:
        """Lista las interacciones asociadas a una oportunidad específica."""
        if not self._listar_interacciones_uc:
            raise ValueError("ListarInteraccionesUseCase no está configurado")
        return self._listar_interacciones_uc.execute(oportunidad_id=oportunidad_id)

    def parsear_perfil_linkedin_pdf(
        self,
        contenido_pdf: bytes,
        guardar_como_yaml: bool = False,
        nombre_yaml: str = "agustin_bustos_parsed",
    ) -> PerfilCandidatoDetalladoDTO:
        """Parsea un PDF de perfil de LinkedIn recibido como bytes en memoria."""
        if not self._parsear_perfil_linkedin_uc:
            raise ValueError("ParsearPerfilLinkedInUseCase no está configurado")
        return self._parsear_perfil_linkedin_uc.execute_from_bytes(
            contenido_pdf=contenido_pdf,
            guardar_como_yaml=guardar_como_yaml,
            nombre_yaml=nombre_yaml,
        )

    def parsear_perfil_linkedin_local(
        self,
        ruta_pdf: str | Path,
        guardar_como_yaml: bool = False,
        nombre_yaml: str = "agustin_bustos_parsed",
    ) -> PerfilCandidatoDetalladoDTO:
        """Parsea un archivo PDF de perfil de LinkedIn ubicado en el disco local."""
        if not self._parsear_perfil_linkedin_uc:
            raise ValueError("ParsearPerfilLinkedInUseCase no está configurado")
        path_obj = Path(ruta_pdf) if isinstance(ruta_pdf, str) else ruta_pdf
        return self._parsear_perfil_linkedin_uc.execute_from_path(
            ruta_pdf=path_obj,
            guardar_como_yaml=guardar_como_yaml,
            nombre_yaml=nombre_yaml,
        )
