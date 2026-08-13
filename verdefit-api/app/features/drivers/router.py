from datetime import UTC, datetime
from typing import Annotated

from core.db import get_session
from fastapi import APIRouter, Depends, HTTPException, Query, status
from features.delivery_zones.models import DeliveryZone
from sqlalchemy.exc import IntegrityError
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from .models import (
    Driver,
    DriverCreate,
    DriverRead,
    DriverUpdate,
    DriverZoneLink,
)

router = APIRouter(prefix="/drivers", tags=["Drivers"])


async def _get_assigned_zone_ids(session: AsyncSession, driver_id: int) -> list[int]:
    """Obtiene los identificadores de las zonas de delivery asociadas a un repartidor.

    Args:
        session (AsyncSession): Sesión asíncrona activa de la base de datos.
        driver_id (int): Identificador único del repartidor.

    Returns:
        list[int]: Lista con los IDs de las zonas asignadas al repartidor.
    """
    statement = select(DriverZoneLink.delivery_zone_id).where(
        DriverZoneLink.driver_id == driver_id,
        col(DriverZoneLink.delivery_zone_id).is_not(None),
    )
    result = await session.exec(statement)
    return [z_id for z_id in result.all() if z_id is not None]


async def _validate_zone_ids(session: AsyncSession, zone_ids: list[int]) -> None:
    """Verifica la existencia de una lista de zonas de delivery en la base de datos.

    Args:
        session (AsyncSession): Sesión asíncrona activa de la base de datos.
        zone_ids (list[int]): Lista de IDs de zonas de delivery a validar.

    Raises:
        HTTPException: Devuelve un código HTTP 404 si una o más zonas no existen.
    """
    if not zone_ids:
        return

    statement = select(DeliveryZone.id).where(
        col(DeliveryZone.id).in_(zone_ids)  # type: ignore
    )
    result = await session.exec(statement)
    found_ids = set(result.all())

    missing_ids = set(zone_ids) - found_ids
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Las siguientes zonas de delivery no existen: {sorted(missing_ids)}",
        )


@router.post("/", response_model=DriverRead, status_code=status.HTTP_201_CREATED)
async def create_driver(
    driver_in: DriverCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Crea un nuevo repartidor en el sistema y le asigna zonas de delivery iniciales.

    Args:
        driver_in (DriverCreate): Datos de entrada del repartidor y lista de zonas.
        session (AsyncSession): Sesión asíncrona de la base de datos inyectada.

    Returns:
        DriverRead: Objeto del repartidor creado con ID, fechas y zonas asignadas.

    Raises:
        HTTPException: Devuelve HTTP 404 si alguna zona no existe, HTTP 400 si
            el teléfono ya pertenece a otro repartidor, o HTTP 500 en fallo de ID.
    """
    if driver_in.zone_ids:
        await _validate_zone_ids(session, driver_in.zone_ids)

    driver_data = driver_in.model_dump(exclude={"zone_ids"})
    driver = Driver.model_validate(driver_data)
    session.add(driver)

    try:
        await session.commit()
        await session.refresh(driver)

        if driver.id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al generar el ID del repartidor.",
            )

        if driver_in.zone_ids:
            for zone_id in driver_in.zone_ids:
                session.add(
                    DriverZoneLink(driver_id=driver.id, delivery_zone_id=zone_id)
                )
            await session.commit()

        zone_ids = await _get_assigned_zone_ids(session, driver.id)
        return DriverRead(**driver.model_dump(), assigned_zone_ids=zone_ids)

    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El número de teléfono ya se encuentra registrado para otro repartidor.",
        )


@router.get("/", response_model=list[DriverRead])
async def list_drivers(
    session: Annotated[AsyncSession, Depends(get_session)],
    skip: int = Query(default=0, ge=0, description="Registros a omitir"),
    limit: int = Query(default=100, ge=1, le=100, description="Límite de registros"),
    only_available: bool = Query(
        default=False, description="Mostrar solo repartidores disponibles para asignar"
    ),
    only_active: bool = Query(
        default=True, description="Mostrar solo repartidores activos"
    ),
):
    """Obtiene la lista de repartidores registrados con soporte para filtros y paginación.

    Args:
        session (AsyncSession): Sesión asíncrona de la base de datos.
        skip (int): Cantidad de registros a omitir (por defecto 0).
        limit (int): Cantidad máxima de registros a retornar (por defecto 100).
        only_available (bool): Filtra solo repartidores disponibles para despacho.
        only_active (bool): Filtra solo repartidores activos en el sistema.

    Returns:
        list[DriverRead]: Lista de repartidores encontrados con sus zonas asociadas.
    """
    statement = select(Driver)

    if only_active:
        statement = statement.where(Driver.is_active == True)
    if only_available:
        statement = statement.where(Driver.is_available == True)

    statement = statement.offset(skip).limit(limit)
    result = await session.exec(statement)
    drivers = result.all()

    response: list[DriverRead] = []
    for driver in drivers:
        if driver.id is not None:
            zone_ids = await _get_assigned_zone_ids(session, driver.id)
            response.append(
                DriverRead(**driver.model_dump(), assigned_zone_ids=zone_ids)
            )

    return response


@router.get("/{driver_id}", response_model=DriverRead)
async def get_driver(
    driver_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Obtiene los detalles de un repartidor específico por su ID.

    Args:
        driver_id (int): Identificador único del repartidor.
        session (AsyncSession): Sesión asíncrona de la base de datos.

    Returns:
        DriverRead: Información completa del repartidor solicitado con sus zonas.

    Raises:
        HTTPException: Devuelve un código HTTP 404 si el repartidor no existe.
    """
    driver = await session.get(Driver, driver_id)
    if not driver or driver.id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repartidor no encontrado.",
        )

    zone_ids = await _get_assigned_zone_ids(session, driver.id)
    return DriverRead(**driver.model_dump(), assigned_zone_ids=zone_ids)


@router.patch("/{driver_id}", response_model=DriverRead)
async def update_driver(
    driver_id: int,
    driver_in: DriverUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Actualiza parcialmente la información de un repartidor existente y sus zonas.

    Args:
        driver_id (int): Identificador único del repartidor a modificar.
        driver_in (DriverUpdate): Datos parciales a actualizar y/o nueva lista de zonas.
        session (AsyncSession): Sesión asíncrona de la base de datos.

    Returns:
        DriverRead: Información actualizada del repartidor con sus cambios aplicados.

    Raises:
        HTTPException: Devuelve HTTP 404 si el repartidor o alguna zona no existe,
            o HTTP 400 si el teléfono actualizado ya pertenece a otro repartidor.
    """
    driver = await session.get(Driver, driver_id)
    if not driver or driver.id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repartidor no encontrado.",
        )

    if driver_in.zone_ids is not None:
        await _validate_zone_ids(session, driver_in.zone_ids)

    update_data = driver_in.model_dump(exclude_unset=True, exclude={"zone_ids"})
    for key, value in update_data.items():
        setattr(driver, key, value)

    driver.updated_at = datetime.now(UTC).replace(tzinfo=None)
    session.add(driver)

    try:
        if driver_in.zone_ids is not None:
            existing_links = await session.exec(
                select(DriverZoneLink).where(DriverZoneLink.driver_id == driver_id)
            )
            for link in existing_links.all():
                await session.delete(link)

            for zone_id in driver_in.zone_ids:
                session.add(
                    DriverZoneLink(driver_id=driver_id, delivery_zone_id=zone_id)
                )

        await session.commit()
        await session.refresh(driver)

        zone_ids = await _get_assigned_zone_ids(session, driver.id)
        return DriverRead(**driver.model_dump(), assigned_zone_ids=zone_ids)

    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El número de teléfono ingresado ya pertenece a otro repartidor.",
        )
