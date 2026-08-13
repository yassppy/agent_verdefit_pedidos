from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from pydantic import computed_field
from sqlmodel import Field, SQLModel

PERU_TZ = ZoneInfo("America/Lima")


class ProductBase(SQLModel):
    """Modelo base con atributos comunes para un producto."""

    code: str = Field(
        index=True, unique=True, max_length=20, description="Identificador único"
    )
    name: str = Field(index=True, max_length=150, description="Nombre del producto")
    category: str = Field(
        index=True, max_length=50, description="Categoría (ej. Platos Criollos)"
    )
    description: str | None = Field(
        default=None, max_length=500, description="Descripción del producto"
    )
    price: float = Field(gt=0, description="Precio en Soles (PEN)")

    # Información nutricional opcional
    kcal: int | None = Field(default=None, ge=0, description="Calorías (kcal)")
    protein_g: float | None = Field(
        default=None, ge=0, description="Proteínas en gramos"
    )
    carbs_g: float | None = Field(
        default=None, ge=0, description="Carbohidratos en gramos"
    )
    fat_g: float | None = Field(default=None, ge=0, description="Grasas en gramos")

    # Inventario y estado
    stock: int = Field(default=0, ge=0, description="Stock disponible")
    image_url: str | None = Field(
        default=None, max_length=500, description="URL de la imagen"
    )
    is_available: bool = Field(
        default=True, description="Indica si hay disponibilidad para venta"
    )
    is_active: bool = Field(
        default=True, description="Soft delete / Desactivar producto"
    )


class Product(ProductBase, table=True):
    """Tabla de la base de datos para la entidad Producto."""

    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )


class ProductCreate(ProductBase):
    """Esquema de validación para crear un nuevo producto."""


class ProductUpdate(SQLModel):
    """Esquema para actualización parcial de un producto."""

    code: str | None = Field(default=None, max_length=20)
    name: str | None = Field(default=None, max_length=150)
    category: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=500)
    price: float | None = Field(default=None, gt=0)

    kcal: int | None = Field(default=None, ge=0)
    protein_g: float | None = Field(default=None, ge=0)
    carbs_g: float | None = Field(default=None, ge=0)
    fat_g: float | None = Field(default=None, ge=0)

    stock: int | None = Field(default=None, ge=0)
    image_url: str | None = Field(default=None, max_length=500)
    is_available: bool | None = None
    is_active: bool | None = None


class ProductRead(ProductBase):
    """Esquema de respuesta al consultar información de un producto."""

    id: int
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def created_at_peru(self) -> str:
        dt = (
            self.created_at
            if self.created_at.tzinfo
            else self.created_at.replace(tzinfo=UTC)
        )
        return dt.astimezone(PERU_TZ).strftime("%Y-%m-%d %H:%M:%S")

    @computed_field
    @property
    def updated_at_peru(self) -> str:
        dt = (
            self.updated_at
            if self.updated_at.tzinfo
            else self.updated_at.replace(tzinfo=UTC)
        )
        return dt.astimezone(PERU_TZ).strftime("%Y-%m-%d %H:%M:%S")
