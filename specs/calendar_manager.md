# Especificación Técnica: Calendar Manager (Calendario y Eventos Corporativos)

## 1. Identificación y Propósito
- **ID:** `SPEC-CAL-001`
- **Módulo:** `calendar`
- **Capa DDD:** `domain/calendar`, `application/`, `adapters/`, `infrastructure/`
- **Consumidores:** Asistente AI (OpenClaw), API REST Datamaq Hub, Webmail Roundcube.
- **Objetivo:** Proveer una API de calendario corporativo para consultar eventos, listar citas próximas, comprobar disponibilidad horaria y agendar/modificar/cancelar reuniones en la base de datos de Roundcube.

---

## 2. Invariantes de Dominio
1. **Intervalo Temporal Válido:** Todo evento debe poseer una fecha/hora de inicio (`start`) anterior o igual a la de fin (`end`).
2. **Identificador Global Único (UID):** Todo evento posee un UUID iCalendar estándar para interoperabilidad RFC 5545.
3. **Respeto de Disponibilidad:** El cálculo de disponibilidad evalúa eventos activos (excluyendo cancelados) para determinar bloques libres y ocupados.
4. **Multiusuario Particionado:** Todo calendario y evento pertenece a un `calendar_id` asociado al `user_id` de la cuenta corporativa.

---

## 3. Modelo de Dominio (`src/domain/calendar/`)

### Entidades y Value Objects
- `CalendarEvent`: Entidad `@dataclass(frozen=True)` representando una cita o evento (`id_evento`, `uid`, `titulo`, `descripcion`, `inicio`, `fin`, `ubicacion`, `todo_el_dia`, `estado`, `asistentes`, `url`, `categorias`).
- `Calendar`: Entidad `@dataclass(frozen=True)` representando el calendario contenedor (`id_calendario`, `nombre`, `color`).
- `TimeSlot`: Entidad `@dataclass(frozen=True)` representando un bloque horario (`inicio`, `fin`, `disponible`).
- `EventId`: Value Object identificador del evento.
- `EventDateTimeInterval`: Value Object que valida coherencia entre `start` y `end`.
- `EventStatus`: Enum de estado (`CONFIRMED`, `TENTATIVE`, `CANCELLED`).

### Puerto (`ports.py`)
```python
from datetime import datetime
from typing import Protocol
from src.domain.calendar.entities import Calendar, CalendarEvent


class CalendarRepositoryPort(Protocol):
    def get_or_create_default_calendar(self, account: str) -> Calendar: ...

    def list_events(
        self,
        account: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 50,
    ) -> list[CalendarEvent]: ...

    def get_event_by_id(self, event_id: str, account: str) -> CalendarEvent | None: ...

    def create_event(self, event: CalendarEvent, account: str) -> CalendarEvent: ...

    def update_event(self, event: CalendarEvent, account: str) -> CalendarEvent: ...

    def delete_event(self, event_id: str, account: str) -> bool: ...
```

---

## 4. Casos de Uso (`src/application/`)
1. `ListCalendarEventsUseCase`: Listado de eventos en un rango de fechas.
2. `GetUpcomingEventsUseCase`: Obtención rápida de eventos de los próximos $N$ días.
3. `GetEventDetailUseCase`: Detalle completo de un evento por ID.
4. `CreateCalendarEventUseCase`: Creación y persistencia de un nuevo evento.
5. `UpdateCalendarEventUseCase`: Modificación de horario, título, descripción o ubicación de un evento.
6. `DeleteCalendarEventUseCase`: Eliminación física o cancelación de un evento.
7. `CheckAvailabilityUseCase`: Cálculo de franjas horarias libres y ocupadas para una fecha dada.
8. `SincronizarAgendaDocenteUseCase`: Proyección e inserción de clases de designaciones docentes vigentes como eventos de calendario categorizados como `"Docencia"`.
9. `ConsultarAgendaDocenteUseCase`: Consulta unificada de agenda escolar y citas corporativas.

---

## 5. Integración con Horarios de Docencia (`DocenciaEventProjectorService`)
- Mapea las designaciones vigentes (`DesignacionDocente`) y sus bloques semanales (`HorarioBloque`) a instancias de `CalendarEvent` en un rango temporal `[fecha_desde, fecha_hasta]`.
- Mapeo de días:
  - `LUNES` -> 0, `MARTES` -> 1, `MIERCOLES` -> 2, `JUEVES` -> 3, `VIERNES` -> 4, `SABADO` -> 5.
- Categoría asignada: `"Docencia"`.
- Permite limpieza previa (`limpiar_previos=True`) para evitar solapamientos al actualizar horarios de cursada.

---

## 6. Endpoints HTTP
- `GET /api/v1/calendario/eventos`: Listar eventos por rango de fechas (`?fecha_desde=&fecha_hasta=&account=&limit=`).
- `GET /api/v1/calendario/proximos`: Próximos eventos (`?dias=7&limit=10&account=`).
- `GET /api/v1/calendario/disponibilidad`: Franjas horarias libres (`?fecha=&duracion_minutos=30&account=`).
- `GET /api/v1/calendario/eventos/{event_id}`: Detalle de evento (`?account=`).
- `POST /api/v1/calendario/eventos`: Crear evento (`CreateEventDTO`).
- `PUT /api/v1/calendario/eventos/{event_id}`: Actualizar evento (`UpdateEventDTO`).
- `DELETE /api/v1/calendario/eventos/{event_id}`: Eliminar evento (`?account=`).
- `POST /api/v1/calendario/docencia/sincronizar`: Sincronizar clases docentes en el calendario (`SincronizarDocenciaDTO`).
- `GET /api/v1/calendario/docencia/agenda`: Agenda unificada docente (`?cuit=&fecha_desde=&fecha_hasta=`).
