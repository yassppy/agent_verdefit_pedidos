from datetime import UTC, datetime
from typing import Annotated

from core.db import get_session
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .models import Product, ProductCreate, ProductRead, ProductUpdate

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("/", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    product_in: ProductCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Crea un nuevo producto en el catálogo de VerdeFit.

    Args:
        product_in (ProductCreate): Datos de entrada para registrar el producto.
        session (AsyncSession): Sesión asíncrona de la base de datos
            inyectada automáticamente por `get_session`.

    Returns:
        ProductRead: Objeto del producto creado con ID y fechas generadas.

    Raises:
        HTTPException: Devuelve un código HTTP 400 si el código de producto
            ya se encuentra registrado.
    """
    product = Product.model_validate(product_in)
    session.add(product)

    try:
        await session.commit()
        await session.refresh(product)
        return product
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un producto registrado con ese código.",
        )


@router.get("/", response_model=list[ProductRead])
async def list_products(
    session: Annotated[AsyncSession, Depends(get_session)],
    skip: int = Query(default=0, ge=0, description="Registros a omitir"),
    limit: int = Query(default=100, ge=1, le=100, description="Límite de registros"),
    category: str | None = Query(default=None, description="Filtrar por categoría"),
    only_active: bool = Query(
        default=True, description="Mostrar solo productos activos"
    ),
):
    """Obtiene la lista de productos registrados con soporte para filtros y paginación.

    Args:
        session (AsyncSession): Sesión asíncrona de la base de datos.
        skip (int): Cantidad de registros a omitir (por defecto 0).
        limit (int): Cantidad máxima de registros a retornar (por defecto 100).
        category (str | None): Categoría opcional por la cual filtrar los productos.
        only_active (bool): Si es True, filtra únicamente los productos activos (por defecto True).

    Returns:
        list[ProductRead]: Lista de productos encontrados.
    """
    statement = select(Product)

    if only_active:
        statement = statement.where(Product.is_active == True)
    if category:
        statement = statement.where(Product.category == category)

    statement = statement.offset(skip).limit(limit)
    result = await session.exec(statement)
    return result.all()


@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Obtiene los detalles de un producto específico por su ID.

    Args:
        product_id (int): Identificador único del producto.
        session (AsyncSession): Sesión asíncrona de la base de datos.

    Returns:
        ProductRead: Información completa del producto solicitado.

    Raises:
        HTTPException: Devuelve un código HTTP 404 si el producto no existe.
    """
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )
    return product


@router.patch("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: int,
    product_in: ProductUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Actualiza parcialmente la información de un producto existente.

    Args:
        product_id (int): Identificador único del producto a modificar.
        product_in (ProductUpdate): Datos parciales a actualizar.
        session (AsyncSession): Sesión asíncrona de la base de datos.

    Returns:
        ProductRead: Información del producto con los cambios aplicados.

    Raises:
        HTTPException: Devuelve HTTP 404 si el producto no existe, o HTTP 400 si
            el nuevo código ya pertenece a otro producto.
    """
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado.",
        )

    update_data = product_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)

    product.updated_at = datetime.now(UTC).replace(tzinfo=None)

    session.add(product)
    try:
        await session.commit()
        await session.refresh(product)
        return product
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código de producto ingresado ya está en uso.",
        )
