"""Controller for employment search, analysis, and application tracking."""

from src.application.dtos.empleo_dtos import (
    ActualizarEstadoOportunidadDTO,
    BuscarOfertasQueryDTO,
    InteraccionDTO,
    OportunidadDTO,
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
    ) -> None:
        self._buscar_ofertas_uc = buscar_ofertas_uc
        self._registrar_oportunidad_uc = registrar_oportunidad_uc
        self._listar_oportunidades_uc = listar_oportunidades_uc
        self._actualizar_estado_uc = actualizar_estado_uc
        self._registrar_interaccion_uc = registrar_interaccion_uc
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
