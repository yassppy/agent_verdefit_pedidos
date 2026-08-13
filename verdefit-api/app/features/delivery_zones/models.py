from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from pydantic import computed_field
from sqlmodel import Field, SQLModel

PERU_TZ = ZoneInfo("America/Lima")


class DeliveryZoneBase(SQLModel):
    """Modelo base con atributos comunes para una zona de delivery."""

    code: str = Field(
        index=True,
        unique=True,
        max_length=20,
        description="Código único de la zona (ej. Z01)",
    )
    name: str = Field(
        index=True,
        max_length=100,
        description="Nombre de la zona (ej. Zona A - Premium)",
    )
    districts: str = Field(
        max_length=255, description="Distritos incluidos separados por comas"
    )
    estimated_time_min: int = Field(
        ge=0, description="Tiempo estimado de entrega en minutos"
    )
    delivery_fee: float = Field(ge=0, description="Costo de envío en Soles (PEN)")
    start_time: str = Field(
        max_length=10, description="Horario de inicio de atención (ej. 11:00)"
    )
    end_time: str = Field(
        max_length=10, description="Horario de fin de atención (ej. 20:30)"
    )
    is_active: bool = Field(
        default=True, description="Indica si la zona está activa para envíos"
    )
    notes: str | None = Field(
        default=None, max_length=255, description="Notas o condiciones del delivery"
    )


class DeliveryZone(DeliveryZoneBase, table=True):
    """Tabla de la base de datos para la entidad Zona de Delivery."""

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )


class DeliveryZoneCreate(DeliveryZoneBase):
    """Esquema de validación para registrar una nueva zona de delivery."""


class DeliveryZoneUpdate(SQLModel):
    """Esquema para actualización parcial de una zona de delivery."""

    code: str | None = Field(default=None, max_length=20)
    name: str | None = Field(default=None, max_length=100)
    districts: str | None = Field(default=None, max_length=255)
    estimated_time_min: int | None = Field(default=None, ge=0)
    delivery_fee: float | None = Field(default=None, ge=0)
    start_time: str | None = Field(default=None, max_length=10)
    end_time: str | None = Field(default=None, max_length=10)
    is_active: bool | None = None
    notes: str | None = Field(default=None, max_length=255)


class DeliveryZoneRead(DeliveryZoneBase):
    """Esquema de respuesta al consultar la información de una zona de delivery."""

    id: int
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def created_at_peru(self) -> str:
        """Formatea la fecha UTC almacenada a la hora local de Perú."""
        dt = (
            self.created_at
            if self.created_at.tzinfo
            else self.created_at.replace(tzinfo=UTC)
        )
        return dt.astimezone(PERU_TZ).strftime("%Y-%m-%d %H:%M:%S")

    @computed_field
    @property
    def updated_at_peru(self) -> str:
        """Formatea la fecha de actualización a la hora local de Perú."""
        dt = (
            self.updated_at
            if self.updated_at.tzinfo
            else self.updated_at.replace(tzinfo=UTC)
        )
        return dt.astimezone(PERU_TZ).strftime("%Y-%m-%d %H:%M:%S")
