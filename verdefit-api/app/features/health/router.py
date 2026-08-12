from typing import Annotated

from core.db import get_session
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

router = APIRouter()


@router.get("/health")
async def health_check(
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Verifica la salud de la API y la conectividad con la base de datos.
    Args:
        session (AsyncSession): Sesión asíncrona de la base de datos
        inyectada automáticamente por la dependencia `get_session`.

    Returns:
        dict: Estado actual de la aplicación y confirmación de conexión.

    Raises:
        HTTPException: Devuelve un código HTTP 503 (Service Unavailable)
        si ocurre un error de red o de base de datos.
    """
    try:
        await session.exec(select(1))
        return {"status": "ok", "database": "connected"}
    except (SQLAlchemyError, OSError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La base de datos no está disponible temporalmente.",
        )
