from typing import Annotated

from core.db import get_session
from fastapi import APIRouter, Depends, Query, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .models import Order, OrderCreate, OrderRead, OrderStatus, OrderUpdate
from .services import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_in: OrderCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await OrderService.create_order(session, order_in)


@router.get("/", response_model=list[OrderRead])
async def list_orders(
    session: Annotated[AsyncSession, Depends(get_session)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    status_filter: OrderStatus | None = None,
    customer_id: int | None = None,
    driver_id: int | None = None,
):
    statement = select(Order)
    if status_filter:
        statement = statement.where(Order.status == status_filter)
    if customer_id:
        statement = statement.where(Order.customer_id == customer_id)
    if driver_id:
        statement = statement.where(Order.driver_id == driver_id)

    statement = statement.offset(skip).limit(limit)
    orders = (await session.exec(statement)).all()

    return [
        OrderRead(
            **order.model_dump(),
            items=await OrderService.get_order_items(session, order.id),
        )
        for order in orders
        if order.id
    ]


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    order = await session.get(Order, order_id)
    if not order or not order.id:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Pedido no encontrado.")

    items = await OrderService.get_order_items(session, order.id)
    return OrderRead(**order.model_dump(), items=items)


@router.patch("/{order_id}", response_model=OrderRead)
async def update_order(
    order_id: int,
    order_in: OrderUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await OrderService.update_order(session, order_id, order_in)


@router.put("/{order_id}/items", response_model=OrderRead)
async def update_order_items(
    order_id: int,
    new_items: list[dict],
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Endpoint para reemplazar o editar la lista completa de ítems de una orden."""
    return await OrderService.update_order_items(session, order_id, new_items)


@router.delete("/{order_id}/cancel", response_model=OrderRead)
async def cancel_order(
    order_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    """Endpoint para cancelar un pedido (Soft Delete)."""
    return await OrderService.cancel_order(session, order_id)
