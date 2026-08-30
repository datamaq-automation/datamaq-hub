"""DTOs para el Briefing Matutino Unificado de Agenda, Docencia y Tareas."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ClaseBriefingDTO(BaseModel):
    """Representa un bloque de clase que debe dictarse en el día."""

    model_config = ConfigDict(frozen=True)

    id_designacion: str = Field(description="ID de la designación docente")
    establecimiento: str = Field(description="Nombre o código de la escuela")
    distrito: str = Field(description="Distrito escolar (ej. Tigre, Escobar)")
    cargo_asignatura: str = Field(description="Materia o cargo docente")
    revista: str = Field(
        description="Situación de revista (TITULAR, PROVISIONAL, SUPLENTE)"
    )
    hora_inicio: str = Field(description="Hora de inicio en formato HH:MM")
    hora_fin: str = Field(description="Hora de finalización en formato HH:MM")
    turno: str = Field(description="Turno escolar (MANANA, TARDE, VESPERTINO, NOCHE)")
    modulos: int = Field(description="Cantidad de módulos del bloque")
    escuela_numero: str = Field(default="", description="Número de escuela")


class TareaBriefingDTO(BaseModel):
    """Representa una tarea pendiente relevante para el día."""

    model_config = ConfigDict(frozen=True)

    id_tarea: str = Field(description="Identificador único de la tarea")
    titulo: str = Field(description="Título descriptivo de la tarea")
    prioridad: str = Field(description="Prioridad (BAJA, MEDIA, ALTA, URGENTE)")
    categoria: str = Field(
        description="Categoría (DOCENCIA, RECIBOS, LEADS, CALENDARIO, GENERAL)"
    )
    fecha_limite: date | None = Field(
        default=None, description="Fecha límite de vencimiento si aplica"
    )
    es_urgente: bool = Field(
        default=False, description="True si es prioridad URGENTE o ALTA"
    )
    es_reclamo: bool = Field(
        default=False, description="True si es una tarea de reclamo de liquidación"
    )


class EventoBriefingDTO(BaseModel):
    """Representa un evento agendado en el calendario para el día."""

    model_config = ConfigDict(frozen=True)

    id_evento: str = Field(description="ID del evento")
    titulo: str = Field(description="Título o asunto del evento")
    inicio: datetime = Field(description="Fecha y hora de inicio")
    fin: datetime = Field(description="Fecha y hora de finalización")
    ubicacion: str = Field(default="", description="Ubicación física o enlace virtual")


class ResumenMetricasDTO(BaseModel):
    """Métricas cuantitativas de la jornada."""

    model_config = ConfigDict(frozen=True)

    total_horas_clase: float = Field(description="Total de horas/módulos a dictar hoy")
    cantidad_escuelas: int = Field(
        description="Cantidad de escuelas diferentes a visitar hoy"
    )
    total_tareas_pendientes: int = Field(
        description="Total de tareas pendientes del docente"
    )
    tareas_urgentes: int = Field(
        description="Total de tareas de prioridad ALTA o URGENTE"
    )
    total_reuniones: int = Field(
        description="Total de eventos y reuniones agendadas hoy"
    )
    mensajes_no_leidos: int = Field(default=0, description="Total de correos no leídos")


class TarjetaVencimientoBriefingDTO(BaseModel):
    """Representa una alerta de vencimiento de tarjeta para el briefing."""

    model_config = ConfigDict(frozen=True)

    banco: str = Field(description="Banco emisor (ej. BBVA, BAPRO)")
    tarjeta_tipo: str = Field(description="Tipo de tarjeta (ej. VISA, MASTERCARD)")
    tarjeta_categoria: str = Field(description="Categoría (ej. GOLD, CLASSIC)")
    fecha_vencimiento: date = Field(description="Fecha de vencimiento de la tarjeta")
    saldo_pesos: float = Field(description="Saldo en pesos")
    saldo_dolares: float = Field(description="Saldo en dólares")
    pago_minimo: float = Field(description="Pago mínimo requerido")


class BriefingDiarioResponseDTO(BaseModel):
    """Respuesta consolidada del Briefing Matutino para OpenClaw y la UI."""

    model_config = ConfigDict(frozen=True)

    fecha: date = Field(description="Fecha del briefing")
    dia_semana: str = Field(
        description="Día de la semana en español (LUNES, MARTES, etc.)"
    )
    docente_cuit: str = Field(description="CUIT normalizado del docente")
    metricas: ResumenMetricasDTO = Field(description="Métricas cuantitativas")
    clases_hoy: list[ClaseBriefingDTO] = Field(
        default_factory=list[ClaseBriefingDTO],
        description="Cronograma de clases ordenado cronológicamente",
    )
    tareas_hoy: list[TareaBriefingDTO] = Field(
        default_factory=list[TareaBriefingDTO],
        description="Tareas prioritarias pendientes",
    )
    eventos_hoy: list[EventoBriefingDTO] = Field(
        default_factory=list[EventoBriefingDTO],
        description="Reuniones y eventos agendados",
    )
    tarjetas_vencimiento: list[TarjetaVencimientoBriefingDTO] = Field(
        default_factory=list[TarjetaVencimientoBriefingDTO],
        description="Alertas de vencimientos de tarjetas de crédito próximas",
    )
    resumen_telegram: str = Field(
        description="Texto enriquecido en Markdown con formato y emojis optimizado para Telegram"
    )
