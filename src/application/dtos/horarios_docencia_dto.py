"""DTOs (Data Transfer Objects) con validación Pydantic v2 para horarios de docencia y persistencia temporal."""

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class HorarioBloqueDTO(BaseModel):
    """DTO para un bloque horario individual."""

    model_config = ConfigDict(extra="forbid")

    dia: str = Field(description="Día de la semana: LUNES, MARTES, MIERCOLES, JUEVES, VIERNES, SABADO")
    hora_inicio: str = Field(description="Hora de inicio en formato HH:MM (ej. 07:30)")
    hora_fin: str = Field(description="Hora de fin en formato HH:MM (ej. 09:30)")
    turno: str = Field(default="MANANA", description="Turno escolar: MANANA, TARDE, VESPERTINO, NOCHE, INTERNO")


class CargoDocenteDTO(BaseModel):
    """DTO para un cargo o espacio curricular docente (auditoría ad-hoc)."""

    model_config = ConfigDict(extra="forbid")

    id_cargo: str = Field(description="Identificador del cargo o secuencia (ej. 'CARGO-01')")
    establecimiento: str = Field(description="Nombre de la escuela o institución (ej. 'EEST N° 1 Pilar')")
    distrito: str = Field(default="", description="Distrito escolar (ej. 'Pilar', 'Tigre')")
    cargo_asignatura: str = Field(description="Nombre de la materia o cargo (ej. 'Electrotecnia 4to')")
    revista: str = Field(default="TITULAR", description="Situación de revista: TITULAR, PROVISIONAL, SUPLENTE")
    ige: str = Field(default="", description="Identificador de Gestión Educativa (DGCyE PBA)")
    modulos: int = Field(default=0, ge=0, description="Cantidad de módulos o horas cátedra semanales")
    es_cargo_base: bool = Field(default=False, description="True si es cargo de base de jornada simple o completa")
    horarios: list[HorarioBloqueDTO] = Field(
        default_factory=list[HorarioBloqueDTO],
        description="Lista de franjas horarias semanales en las que se dicta este cargo",
    )


class DeclaracionHorariaInputDTO(BaseModel):
    """DTO de entrada para auditar una declaración jurada horaria ad-hoc."""

    model_config = ConfigDict(extra="forbid")

    docente_nombre: str = Field(description="Nombre y apellido del docente")
    cuit: str = Field(default="", description="CUIT del docente (opcional)")
    dni: str = Field(default="", description="DNI del docente (opcional)")
    margen_traslado_minutos: int = Field(
        default=20,
        ge=0,
        le=120,
        description="Minutos mínimos de viaje requeridos entre escuelas distintas en el mismo día",
    )
    cargos: list[CargoDocenteDTO] = Field(
        default_factory=list[CargoDocenteDTO],
        description="Listado de cargos o asignaturas a auditar",
    )


class RegistrarDesignacionInputDTO(BaseModel):
    """DTO de entrada para registrar y persistir una designación o suplencia con vigencia temporal."""

    model_config = ConfigDict(extra="forbid")

    docente_cuit: str = Field(description="CUIT del docente titular/suplente (ej. '20-36528392-4')")
    ige: str = Field(default="", description="Identificador de Gestión Educativa oficial (DGCyE PBA)")
    establecimiento: str = Field(description="Nombre del establecimiento educativo (ej. 'EEST N° 1 Pilar')")
    distrito: str = Field(default="", description="Distrito escolar (ej. 'Pilar', 'Tigre')")
    cargo_asignatura: str = Field(description="Asignatura o cargo (ej. 'Electrotecnia 4to')")
    revista: str = Field(default="TITULAR", description="Situación de revista: TITULAR, PROVISIONAL, SUPLENTE")
    modulos: int = Field(default=0, ge=0, description="Cantidad de módulos o horas cátedra semanales")
    es_cargo_base: bool = Field(default=False, description="True si es cargo de base")
    fecha_desde: str = Field(description="Fecha de inicio/toma de posesión en formato YYYY-MM-DD")
    fecha_hasta: str | None = Field(
        default=None,
        description="Fecha de fin conocida en formato YYYY-MM-DD (opcional para suplencias cerradas)",
    )
    horarios: list[HorarioBloqueDTO] = Field(
        default_factory=list[HorarioBloqueDTO],
        description="Horarios semanales de la designación",
    )


class CesarDesignacionInputDTO(BaseModel):
    """DTO de entrada para finalizar la vigencia de una designación o suplencia."""

    model_config = ConfigDict(extra="forbid")

    fecha_hasta: str = Field(description="Fecha efectiva del cese en formato YYYY-MM-DD")
    motivo_cese: str = Field(
        default="FIN_SUPLENCIA",
        description="Motivo del cese: FIN_SUPLENCIA, RENUNCIA, DESPLAZAMIENTO, CIERRE_CURSO, OTRO",
    )


class DesignacionDocenteDTO(BaseModel):
    """DTO de salida que representa una designación persistida en el tiempo."""

    model_config = ConfigDict(extra="forbid")

    id_designacion: str
    docente_cuit: str
    ige: str
    establecimiento: str
    distrito: str
    cargo_asignatura: str
    revista: str
    modulos: int
    es_cargo_base: bool
    fecha_desde: str
    fecha_hasta: str | None
    motivo_cese: str | None
    horarios: list[HorarioBloqueDTO] = Field(default_factory=list[HorarioBloqueDTO])
    creado_en: str


class ConflictoDTO(BaseModel):
    """DTO para un conflicto o incompatibilidad horaria detectada."""

    tipo: str = Field(description="Tipo de conflicto: SUPERPOSICION_HORARIA, TRASLADO_INSUFICIENTE, etc.")
    severidad: str = Field(description="Severidad: CRITICO (incompatible) o ADVERTENCIA")
    dia: str | None = Field(default=None, description="Día donde ocurre el conflicto")
    cargos_involucrados: list[str] = Field(default_factory=list[str], description="IDs de cargos afectados")
    descripcion: str = Field(description="Explicación detallada del conflicto")
    minutos_solapamiento_o_traslado: int = Field(
        default=0, description="Minutos de superposición o minutos disponibles para el viaje"
    )


class ItemGrillaDiaDTO(BaseModel):
    """DTO para un elemento de la grilla horaria semanal."""

    id_cargo: str
    establecimiento: str
    distrito: str
    cargo_asignatura: str
    revista: str
    hora_inicio: str
    hora_fin: str
    turno: str
    modulos: int
    ige: str = ""


class ResultadoCompatibilidadDTO(BaseModel):
    """DTO de respuesta formal con el veredicto de compatibilidad horaria."""

    es_compatible: bool = Field(description="True si no existen superposiciones horarias críticas")
    total_cargos: int = Field(description="Cantidad total de cargos declarados")
    total_cargos_base: int = Field(description="Cantidad total de cargos de base")
    total_modulos: int = Field(description="Suma total de módulos semanales declarados")
    total_minutos_semanales: int = Field(description="Total de minutos semanales frente a alumnos")
    cantidad_conflictos: int = Field(description="Cantidad total de conflictos y advertencias")
    conflictos: list[ConflictoDTO] = Field(
        default_factory=list[ConflictoDTO],
        description="Listado de superposiciones y advertencias detectadas",
    )
    grilla_semanal: dict[str, list[ItemGrillaDiaDTO]] = Field(
        default_factory=dict[str, list[ItemGrillaDiaDTO]],
        description="Grilla horaria organizada por día de la semana",
    )
