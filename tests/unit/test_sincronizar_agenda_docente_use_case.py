"""Unit tests for SincronizarAgendaDocenteUseCase."""

from datetime import date

from src.application.dtos.calendar_docencia_dto import SincronizarDocenciaDTO
from src.application.use_cases.consultar_agenda_docente import (
    ConsultarAgendaDocenteUseCase,
)
from src.application.use_cases.sincronizar_agenda_docente import (
    SincronizarAgendaDocenteUseCase,
)
from src.domain.horarios_docencia.entities import (
    DesignacionDocente,
    HorarioBloque,
)
from src.domain.horarios_docencia.ports import (
    DesignacionDocenteRepositoryPort,
)
from src.domain.horarios_docencia.value_objects import (
    DiaSemana,
    FranjaHoraria,
    MotivoCese,
    PeriodoVigencia,
    SituacionRevista,
    Turno,
)
from tests.unit.test_calendar_use_cases import FakeCalendarRepository


class FakeDesignacionRepository(DesignacionDocenteRepositoryPort):
    """In-memory mock for DesignacionDocenteRepositoryPort."""

    def __init__(self) -> None:
        self.designaciones: list[DesignacionDocente] = [
            DesignacionDocente(
                id_designacion="d-1",
                docente_cuit="20365283921",
                establecimiento="EEST N°1 San Martín",
                distrito="San Martín",
                cargo_asignatura="Electrónica Aplicada",
                revista=SituacionRevista.TITULAR,
                vigencia=PeriodoVigencia(
                    fecha_desde=date(2026, 3, 1), fecha_hasta=None
                ),
                ige="9991",
                modulos=4,
                es_cargo_base=False,
                horarios=(
                    HorarioBloque(
                        dia=DiaSemana.LUNES,
                        franja=FranjaHoraria("08:00", "10:00"),
                        turno=Turno.MANANA,
                    ),
                    HorarioBloque(
                        dia=DiaSemana.VIERNES,
                        franja=FranjaHoraria("10:00", "12:00"),
                        turno=Turno.MANANA,
                    ),
                ),
            )
        ]

    def guardar(self, designacion: DesignacionDocente) -> DesignacionDocente:
        self.designaciones.append(designacion)
        return designacion

    def obtener_por_id(self, id_designacion: str) -> DesignacionDocente | None:
        for d in self.designaciones:
            if d.id_designacion == id_designacion:
                return d
        return None

    def obtener_vigentes_en_fecha(
        self, docente_cuit: str, fecha: date
    ) -> tuple[DesignacionDocente, ...]:
        res = [
            d
            for d in self.designaciones
            if d.docente_cuit == docente_cuit and d.vigencia.esta_vigente_en(fecha)
        ]
        return tuple(res)

    def obtener_historial(self, docente_cuit: str) -> tuple[DesignacionDocente, ...]:
        res = [d for d in self.designaciones if d.docente_cuit == docente_cuit]
        return tuple(res)

    def cerrar_vigencia(
        self, id_designacion: str, fecha_hasta: date, motivo: MotivoCese
    ) -> DesignacionDocente | None:
        return None


def test_sincronizar_agenda_docente_use_case():
    doc_repo = FakeDesignacionRepository()
    cal_repo = FakeCalendarRepository()

    sync_uc = SincronizarAgendaDocenteUseCase(
        designacion_repo=doc_repo, calendar_repo=cal_repo
    )

    dto = SincronizarDocenciaDTO(
        cuit="20365283921",
        fecha_desde=date(2026, 9, 1),
        fecha_hasta=date(2026, 9, 7),
        limpiar_previos=True,
        incluir_eventos=True,
    )

    account = "openclaw@datamaq.com.ar"
    result = sync_uc.execute(dto=dto, account=account)

    # In 2026-09-01 (Tue) to 2026-09-07 (Mon):
    # 2026-09-04 (Friday) -> 1 class (10:00 - 12:00)
    # 2026-09-07 (Monday) -> 1 class (08:00 - 10:00)
    # Total = 2 events created
    assert result.cuit == "20365283921"
    assert result.total_eventos_creados == 2
    assert len(result.eventos) == 2

    # Query unified schedule
    consultar_uc = ConsultarAgendaDocenteUseCase(calendar_repo=cal_repo)
    agenda = consultar_uc.execute(
        account=account,
        fecha_desde=date(2026, 9, 1),
        fecha_hasta=date(2026, 9, 7),
        solo_docencia=True,
    )
    assert len(agenda) == 2
    assert all(e.categorias == "Docencia" for e in agenda)
