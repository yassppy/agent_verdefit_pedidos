from datetime import UTC, datetime
from typing import Annotated

from core.db import get_session
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from .models import (
    DeliveryZone,
    DeliveryZoneCreate,
    DeliveryZoneRead,
    DeliveryZoneUpdate,
)

router = APIRouter(prefix="/delivery-zones", tags=["Delivery Zones"])


@router.post("/", response_model=DeliveryZoneRead, status_code=status.HTTP_201_CREATED)
async def create_delivery_zone(
    zone_in: DeliveryZoneCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Crea una nueva zona de delivery en el sistema.

    Args:
        zone_in (DeliveryZoneCreate): Datos de entrada para registrar la zona.
        session (AsyncSession): Sesión asíncrona de la base de datos
            inyectada automáticamente por `get_session`.

    Returns:
        DeliveryZoneRead: Objeto de la zona creada con ID y fechas generadas.

    Raises:
        HTTPException: Devuelve un código HTTP 400 si el código de zona
            ya se encuentra registrado.
    """
    zone = DeliveryZone.model_validate(zone_in)
    session.add(zone)

    try:
        await session.commit()
        await session.refresh(zone)
        return zone
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una zona de delivery registrada con ese código.",
        )


@router.get("/", response_model=list[DeliveryZoneRead])
async def list_delivery_zones(
    session: Annotated[AsyncSession, Depends(get_session)],
    skip: int = Query(default=0, ge=0, description="Registros a omitir"),
    limit: int = Query(default=100, ge=1, le=100, description="Límite de registros"),
    district: str | None = Query(
        default=None, description="Buscar zonas por distrito contenido"
    ),
    only_active: bool = Query(default=True, description="Mostrar solo zonas activas"),
):
    """Obtiene la lista de zonas de delivery registradas con soporte para filtros y paginación."""
    statement = select(DeliveryZone)

    if only_active:
        statement = statement.where(DeliveryZone.is_active == True)
    if district:
        # col() elimina el error del type checker
        statement = statement.where(col(DeliveryZone.districts).icontains(district))

    statement = statement.offset(skip).limit(limit)
    result = await session.exec(statement)
    return result.all()


@router.get("/{zone_id}", response_model=DeliveryZoneRead)
async def get_delivery_zone(
    zone_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Obtiene los detalles de una zona de delivery específica por su ID.

    Args:
        zone_id (int): Identificador único de la zona de delivery.
        session (AsyncSession): Sesión asíncrona de la base de datos.

    Returns:
        DeliveryZoneRead: Información completa de la zona solicitada.

    Raises:
        HTTPException: Devuelve un código HTTP 404 si la zona no existe.
    """
    zone = await session.get(DeliveryZone, zone_id)
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zona de delivery no encontrada.",
        )
    return zone


@router.patch("/{zone_id}", response_model=DeliveryZoneRead)
async def update_delivery_zone(
    zone_id: int,
    zone_in: DeliveryZoneUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Actualiza parcialmente la información de una zona de delivery existente.

    Args:
        zone_id (int): Identificador único de la zona a modificar.
        zone_in (DeliveryZoneUpdate): Datos parciales a actualizar.
        session (AsyncSession): Sesión asíncrona de la base de datos.

    Returns:
        DeliveryZoneRead: Información de la zona con los cambios aplicados.

    Raises:
        HTTPException: Devuelve HTTP 404 si la zona no existe, o HTTP 400 si
            el nuevo código ya pertenece a otra zona.
    """
    zone = await session.get(DeliveryZone, zone_id)
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zona de delivery no encontrada.",
        )

    update_data = zone_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(zone, key, value)

    zone.updated_at = datetime.now(UTC).replace(tzinfo=None)

    session.add(zone)
    try:
        await session.commit()
        await session.refresh(zone)
        return zone
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código de zona ingresado ya está en uso.",
        )
