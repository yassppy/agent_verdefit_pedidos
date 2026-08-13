from datetime import UTC, datetime
from enum import Enum
from typing import Optional
from zoneinfo import ZoneInfo

from pydantic import computed_field
from sqlmodel import Field, Relationship, SQLModel

PERU_TZ = ZoneInfo("America/Lima")


class OrderStatus(str, Enum):
    """Estados del ciclo de vida de un pedido."""

    PENDING = "Pendiente"
    CONFIRMED = "Confirmado"
    IN_PREPARATION = "En preparación"
    ON_THE_WAY = "En camino"
    DELIVERED = "Entregado"
    CANCELLED = "Cancelado"
    ACCIDENT = "Accidente"


class DeliveryType(str, Enum):
    """Modalidad de entrega del pedido."""

    DELIVERY = "Delivery"
    PICKUP = "Recojo en local"
    CUSTOMER_DELIVERY = "Delivery propio del cliente"


# ----------------------------------------------------------------------
# DETALLE DEL PEDIDO (Order Detail)
# ----------------------------------------------------------------------
class OrderDetailBase(SQLModel):
    """Atributos base para el detalle de un pedido."""

    product_id: int = Field(foreign_key="product.id", description="ID del producto")
    quantity: int = Field(gt=0, description="Cantidad comprada")
    item_notes: str | None = Field(
        default=None,
        max_length=255,
        description="Notas específicas del ítem (ej. Sin cebolla)",
    )


class OrderDetail(OrderDetailBase, table=True):
    """Tabla en base de datos para los ítems de un pedido."""

    __tablename__ = "order_details"  # type: ignore[assignment]
    id: int | None = Field(default=None, primary_key=True)

    order_id: int | None = Field(default=None, foreign_key="orders.id")
    unit_price: float = Field(ge=0)
    subtotal_line: float = Field(
        ge=0, description="Subtotal de la línea (cantidad * precio_unitario)"
    )
    order: Optional["Order"] = Relationship(back_populates="items")


class OrderDetailCreate(OrderDetailBase):
    """Esquema de entrada para agregar un producto al pedido."""


class OrderDetailRead(OrderDetailBase):
    """Esquema de respuesta para el detalle de un pedido."""

    id: int
    order_id: int
    unit_price: float
    subtotal_line: float


# ----------------------------------------------------------------------
# CABECERA DEL PEDIDO (Order)
# ----------------------------------------------------------------------
class OrderBase(SQLModel):
    """Atributos base de la cabecera del pedido."""

    customer_id: int = Field(foreign_key="customer.id", description="ID del cliente")
    driver_id: int | None = Field(
        default=None,
        foreign_key="driver.id",
        description="ID del repartidor asignado (opcional)",
    )
    accident_driver_id: int | None = Field(
        default=None,
        foreign_key="driver.id",
        description="ID del repartidor accidentado previamente para reasignación",
    )
    delivery_zone_id: int | None = Field(
        default=None,
        foreign_key="deliveryzone.id",
        description="ID de la zona de delivery (si aplica)",
    )

    delivery_type: DeliveryType = Field(
        default=DeliveryType.DELIVERY, description="Modalidad de entrega"
    )
    status: OrderStatus = Field(
        default=OrderStatus.PENDING, description="Estado del pedido"
    )

    delivery_fee: float = Field(
        default=0.0, ge=0, description="Costo del servicio de delivery"
    )
    discount: float = Field(
        default=0.0, ge=0, description="Descuento aplicado al pedido"
    )
    payment_method: str = Field(
        max_length=50,
        description="Método de pago (Yape, Plin, Tarjeta, Efectivo, etc.)",
    )
    is_paid: bool = Field(default=False, description="Indica si el pedido está pagado")

    customer_notes: str | None = Field(
        default=None, max_length=255, description="Notas enviadas por el cliente"
    )
    internal_notes: str | None = Field(
        default=None, max_length=255, description="Notas internas del equipo/agente"
    )


class Order(OrderBase, table=True):
    """Tabla en base de datos para la entidad Pedido."""

    __tablename__ = "orders"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    subtotal: float = Field(
        default=0.0, ge=0, description="Suma de los subtotales de ítems"
    )
    total: float = Field(
        default=0.0,
        ge=0,
        description="Monto final (subtotal + delivery_fee - discount)",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )

    items: list[OrderDetail] = Relationship(
        back_populates="order", sa_relationship_kwargs={"lazy": "selectin"}
    )


class OrderCreate(OrderBase):
    """Esquema de entrada para crear un nuevo pedido con sus detalles."""

    items: list[OrderDetailCreate] = Field(
        min_length=1, description="Lista de productos del pedido"
    )


class OrderUpdate(SQLModel):
    """Esquema para actualización parcial de un pedido."""

    driver_id: int | None = None
    accident_driver_id: int | None = None
    delivery_zone_id: int | None = None
    delivery_type: DeliveryType | None = None
    status: OrderStatus | None = None
    delivery_fee: float | None = Field(default=None, ge=0)
    discount: float | None = Field(default=None, ge=0)
    payment_method: str | None = Field(default=None, max_length=50)
    is_paid: bool | None = None
    customer_notes: str | None = Field(default=None, max_length=255)
    internal_notes: str | None = Field(default=None, max_length=255)


class OrderRead(OrderBase):
    """Esquema de respuesta detallada para un pedido."""

    id: int
    subtotal: float
    total: float
    created_at: datetime
    updated_at: datetime
    items: list[OrderDetailRead] = Field(default_factory=list)

    @computed_field
    @property
    def created_at_peru(self) -> str:
        """Formatea la fecha UTC a hora local de Perú."""
        dt = (
            self.created_at
            if self.created_at.tzinfo
            else self.created_at.replace(tzinfo=UTC)
        )
        return dt.astimezone(PERU_TZ).strftime("%Y-%m-%d %H:%M:%S")

    @computed_field
    @property
    def updated_at_peru(self) -> str:
        """Formatea la fecha de actualización a hora local de Perú."""
        dt = (
            self.updated_at
            if self.updated_at.tzinfo
            else self.updated_at.replace(tzinfo=UTC)
        )
        return dt.astimezone(PERU_TZ).strftime("%Y-%m-%d %H:%M:%S")
