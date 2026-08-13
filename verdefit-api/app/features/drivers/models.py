from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from pydantic import computed_field
from sqlmodel import Field, SQLModel

PERU_TZ = ZoneInfo("America/Lima")


# Tabla de relación entre Repartidor y Zona de Delivery (Muchos a Muchos)
class DriverZoneLink(SQLModel, table=True):
    """Tabla de relación entre repartidores y zonas de delivery."""

    driver_id: int | None = Field(
        default=None, foreign_key="driver.id", primary_key=True
    )
    delivery_zone_id: int | None = Field(
        default=None, foreign_key="deliveryzone.id", primary_key=True
    )


class DriverBase(SQLModel):
    """Modelo base con atributos comunes para un repartidor."""

    full_name: str = Field(
        index=True, max_length=100, description="Nombre completo del repartidor"
    )
    phone: str = Field(
        unique=True,
        index=True,
        max_length=15,
        description="Teléfono principal de contacto",
    )
    vehicle_type: str | None = Field(
        default="Moto",
        max_length=50,
        description="Tipo de vehículo (Moto, Bicicleta, Auto)",
    )
    license_plate: str | None = Field(
        default=None, max_length=20, description="Placa del vehículo si aplica"
    )

    # Contacto para imprevistos / accidentes
    emergency_contact_name: str | None = Field(
        default=None, max_length=100, description="Nombre del contacto de emergencia"
    )
    emergency_contact_phone: str | None = Field(
        default=None, max_length=15, description="Teléfono del contacto de emergencia"
    )

    # Estados operativos
    is_available: bool = Field(
        default=True, description="Indica si está disponible para recibir pedidos"
    )
    is_active: bool = Field(
        default=True, description="Indica si está activo en el sistema"
    )
    notes: str | None = Field(
        default=None, max_length=255, description="Observaciones sobre el repartidor"
    )


class Driver(DriverBase, table=True):
    """Tabla de la base de datos para la entidad Repartidor."""

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )


class DriverCreate(DriverBase):
    """Esquema de validación para crear un nuevo repartidor."""

    zone_ids: list[int] = Field(
        default_factory=list, description="Lista de IDs de zonas de delivery asignadas"
    )


class DriverUpdate(SQLModel):
    """Esquema para actualización parcial de un repartidor."""

    full_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=15)
    vehicle_type: str | None = Field(default=None, max_length=50)
    license_plate: str | None = Field(default=None, max_length=20)
    emergency_contact_name: str | None = Field(default=None, max_length=100)
    emergency_contact_phone: str | None = Field(default=None, max_length=15)
    is_available: bool | None = None
    is_active: bool | None = None
    notes: str | None = Field(default=None, max_length=255)
    zone_ids: list[int] | None = None


class DriverRead(DriverBase):
    """Esquema de respuesta al consultar la información de un repartidor."""

    id: int
    created_at: datetime
    updated_at: datetime
    assigned_zone_ids: list[int] = Field(default_factory=list)

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
