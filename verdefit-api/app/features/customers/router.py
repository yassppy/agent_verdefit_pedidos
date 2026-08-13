from datetime import UTC, datetime
from typing import Annotated

from core.db import get_session
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .models import Customer, CustomerCreate, CustomerRead, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post("/", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
async def create_customer(
    customer_in: CustomerCreate, session: Annotated[AsyncSession, Depends(get_session)]
):
    """Crea un nuevo cliente en el sistema.

    Args:
        customer_in (CustomerCreate): Datos de entrada para registrar el cliente.
        session (AsyncSession): Sesión asíncrona de la base de datos
        inyectada automáticamente por `get_session`.

    Returns:
        CustomerRead: Objeto del cliente creado con ID y fechas generadas.

    Raises:
        HTTPException: Devuelve un código HTTP 400 si el teléfono o el ID
        de Telegram ya se encuentran registrados.
    """

    customer = Customer.model_validate(
        customer_in
    )  # Aplica la validación al campo padre que es CustomerBase
    session.add(
        customer
    )  # Utiliza la inyección una vez obtenido el session y lo pone como pendiente

    try:
        await session.commit()  # Aquí si ya envia el insert en la base de datos
        await session.refresh(
            customer
        )  # Actualiza el objeto de python trayendo los datos recien generados
        return customer  # Devuelve el JSON
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El número de teléfeno o ID de telegram ya están registrados",
        )


@router.get("/", response_model=list[CustomerRead])
async def list_customers(
    session: Annotated[AsyncSession, Depends(get_session)],
    skip: int = Query(default=0, ge=0, description="Cantidad de registros a omitir"),
    limit: int = Query(
        default=100, ge=1, le=100, description="Límite máximo de registros a retornar"
    ),
):
    """Obtiene la lista de clientes registrados con paginación.

    Args:
        session (AsyncSession): Sesión asíncrona de la base de datos.
        skip (int): Cantidad de registros a omitir (por defecto 0).
        limit (int): Cantidad máxima de registros a retornar (por defecto 100).

    Returns:
        list[CustomerRead]: Lista de clientes encontrados.
    """
    statement = select(Customer).offset(skip).limit(limit)
    result = await session.exec(statement)
    return result.all()


@router.get("/{customer_id}", response_model=CustomerRead)
async def get_customer(
    customer_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Obtiene los detalles de un cliente específico por su ID.

    Args:
        customer_id (int): Identificador único del cliente.
        session (AsyncSession): Sesión asíncrona de la base de datos.

    Returns:
        CustomerRead: Información completa del cliente solicitado.

    Raises:
        HTTPException: Devuelve un código HTTP 404 si el cliente no existe.
    """
    customer = await session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado.",
        )
    return customer


@router.patch("/{customer_id}", response_model=CustomerRead)
async def update_customer(
    customer_id: int,
    customer_in: CustomerUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Actualiza parcialmente la información de un cliente existente.

    Args:
        customer_id (int): Identificador único del cliente a modificar.
        customer_in (CustomerUpdate): Datos parciales a actualizar.
        session (AsyncSession): Sesión asíncrona de la base de datos.

    Returns:
        CustomerRead: Información del cliente con los cambios aplicados.

    Raises:
        HTTPException: Devuelve HTTP 404 si el cliente no existe, o HTTP 400 si
            el nuevo teléfono o ID de Telegram ya pertenece a otro cliente.
    """
    customer = await session.get(Customer, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado.",
        )

    update_data = customer_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(customer, key, value)

    customer.updated_at = datetime.now(UTC).replace(tzinfo=None)

    session.add(customer)
    try:
        await session.commit()
        await session.refresh(customer)
        return customer
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El teléfono o ID de Telegram ya pertenece a otro cliente.",
        )
