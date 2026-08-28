"""Data Transfer Objects for lead ingestion and responses."""

from pydantic import BaseModel, Field


class IngestLeadDTO(BaseModel):
    """Payload received when a lead is captured on web forms or ads."""

    nombre: str = Field(
        ..., min_length=2, description="Nombre y apellido del prospecto"
    )
    email: str = Field(default="", description="Correo electrónico de contacto")
    telefono: str = Field(default="", description="Teléfono o WhatsApp de contacto")
    empresa: str = Field(default="", description="Nombre de la empresa u organización")
    mensaje: str = Field(default="", description="Consulta técnica o mensaje")
    fuente: str = Field(
        default="web",
        description="Canal de origen (ej. landing_energia, web, ads)",
    )
    utm_campaign: str = Field(default="", description="Campaña UTM de procedencia")
    cuenta: str = Field(
        default="", description="Cuenta o buzón de destino para el contacto"
    )


class IngestLeadResponseDTO(BaseModel):
    """Response returned after processing and persisting lead."""

    success: bool = True
    id_contacto: str = Field(..., description="ID del contacto generado en Roundcube")
    id_evento_seguimiento: str = Field(
        default="", description="ID del evento de agenda generado en Roundcube"
    )
    mensaje: str = Field(
        default="Lead registrado y agendado con éxito",
        description="Mensaje descriptivo",
    )
