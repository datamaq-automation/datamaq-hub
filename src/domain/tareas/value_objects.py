"""Value Objects para el subdominio de tareas (To-Do List)."""

from enum import Enum


class PrioridadTarea(str, Enum):
    BAJA = "BAJA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    URGENTE = "URGENTE"


class EstadoTarea(str, Enum):
    PENDIENTE = "PENDIENTE"
    EN_PROGRESO = "EN_PROGRESO"
    COMPLETADA = "COMPLETADA"
    CANCELADA = "CANCELADA"


class CategoriaTarea(str, Enum):
    DOCENCIA = "DOCENCIA"
    RECIBOS = "RECIBOS"
    LEADS = "LEADS"
    CALENDARIO = "CALENDARIO"
    GENERAL = "GENERAL"
