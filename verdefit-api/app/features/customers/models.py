from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from pydantic import computed_field
from sqlalchemy.sql.sqltypes import BigInteger
from sqlmodel import Field, SQLModel

PERU_TZ = ZoneInfo("America/Lima")


class CustomerBase(SQLModel):
    """Modelo base con atributos comunes para un cliente."""

    name: str = Field(
        index=True, max_length=100, description="Nombre completo del cliente"
    )
    phone: str = Field(
        unique=True, index=True, max_length=11, description="Número de teléfono único"
    )
    address: str = Field(
        max_length=255, description="Dirección exacta de entrega (OBLIGATORIA)"
    )
    district: str = Field(
        max_length=100, description="Distrito de entrega (OBLIGATORIO)"
    )
    reference: str | None = Field(
        default=None,
        max_length=255,
        description="Referencia de la dirección (OPCIONAL)",
    )
    telegram_chat_id: int | None = Field(
        default=None,
        sa_type=BigInteger,
        unique=True,
        index=True,
        description="Identificador único del chat de Telegram",
    )


class Customer(CustomerBase, table=True):
    """Tabla de la base de datos para almacenar la entidad Cliente."""

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )


class CustomerCreate(CustomerBase):
    """Esquema de validación para la creación de un nuevo cliente."""


class CustomerUpdate(SQLModel):
    """Esquema para la actualización parcial de un cliente existente."""

    name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=11)
    address: str | None = Field(default=None, max_length=255)
    district: str | None = Field(default=None, max_length=100)
    reference: str | None = Field(default=None, max_length=255)
    telegram_chat_id: int | None = None


class CustomerRead(CustomerBase):
    """Esquema de respuesta al consultar la información de un cliente."""

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
