from datetime import UTC, datetime

from fastapi import HTTPException, status
from features.delivery_zones.models import DeliveryZone
from features.products.models import Product
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .models import (
    Order,
    OrderCreate,
    OrderDetail,
    OrderDetailRead,
    OrderRead,
    OrderStatus,
    OrderUpdate,
)


class OrderService:
    @staticmethod
    async def get_order_items(
        session: AsyncSession, order_id: int
    ) -> list[OrderDetailRead]:
        """Obtiene los ítems formateados de una orden."""
        statement = select(OrderDetail).where(OrderDetail.order_id == order_id)
        result = await session.exec(statement)
        items = result.all()

        return [
            OrderDetailRead(**item.model_dump())
            for item in items
            if item.id is not None and item.order_id is not None
        ]

    @classmethod
    async def create_order(
        cls, session: AsyncSession, order_in: OrderCreate
    ) -> OrderRead:
        """Crea una orden con ítems y auto-calcula delivery según la zona."""
        order_data = order_in.model_dump(exclude={"items"})
        db_order = Order(**order_data)

        # 1. Si la orden trae zona de delivery y no enviaron tarifa manual, buscar la tarifa
        if db_order.delivery_zone_id and db_order.delivery_fee == 0.0:
            zone = await session.get(DeliveryZone, db_order.delivery_zone_id)
            if zone:
                db_order.delivery_fee = round(zone.delivery_fee, 2)

        calculated_subtotal = 0.0
        db_items: list[OrderDetail] = []

        # 2. Procesar productos
        for item in order_in.items:
            product = await session.get(Product, item.product_id)
            if not product or not product.is_active:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"El producto ID {item.product_id} no existe o no está activo.",
                )

            unit_price = round(product.price, 2)
            subtotal_line = round(unit_price * item.quantity, 2)
            calculated_subtotal += subtotal_line

            db_items.append(
                OrderDetail(
                    product_id=item.product_id,
                    quantity=item.quantity,
                    item_notes=item.item_notes,
                    unit_price=unit_price,
                    subtotal_line=subtotal_line,
                )
            )

        db_order.subtotal = round(calculated_subtotal, 2)
        db_order.total = round(
            max(0.0, db_order.subtotal + db_order.delivery_fee - db_order.discount), 2
        )
        db_order.items = db_items

        session.add(db_order)
        await session.commit()
        await session.refresh(db_order)

        if db_order.id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error interno al generar el ID del pedido.",
            )

        items_read = await cls.get_order_items(session, db_order.id)
        return OrderRead(**db_order.model_dump(), items=items_read)

    @classmethod
    async def update_order(
        cls, session: AsyncSession, order_id: int, order_in: OrderUpdate
    ) -> OrderRead:
        """Actualiza cabecera de orden, recalcula tarifa por cambio de zona y totales."""
        order = await session.get(Order, order_id)
        if not order or order.id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado."
            )

        update_data = order_in.model_dump(exclude_unset=True)

        # Lógica para accidentes
        if order_in.status == OrderStatus.ACCIDENT and order.driver_id is not None:
            update_data["accident_driver_id"] = order.driver_id
            update_data["driver_id"] = None

        # Si cambió de zona de delivery y NO forzaron un delivery_fee manual
        if "delivery_zone_id" in update_data and "delivery_fee" not in update_data:
            new_zone_id = update_data["delivery_zone_id"]
            if new_zone_id:
                zone = await session.get(DeliveryZone, new_zone_id)
                if zone:
                    update_data["delivery_fee"] = round(zone.delivery_fee, 2)
            else:
                update_data["delivery_fee"] = 0.0

        for key, value in update_data.items():
            setattr(order, key, value)

        # Recalcular total de la orden con redondeo a 2 decimales
        order.subtotal = round(order.subtotal, 2)
        order.delivery_fee = round(order.delivery_fee, 2)
        order.discount = round(order.discount, 2)
        order.total = round(
            max(0.0, order.subtotal + order.delivery_fee - order.discount), 2
        )
        order.updated_at = datetime.now(UTC).replace(tzinfo=None)

        session.add(order)
        await session.commit()
        await session.refresh(order)

        if order.id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al procesar el ID del pedido.",
            )

        items_read = await cls.get_order_items(session, order.id)
        return OrderRead(**order.model_dump(), items=items_read)

    @classmethod
    async def update_order_items(
        cls, session: AsyncSession, order_id: int, new_items: list
    ) -> OrderRead:
        """Permite modificar, agregar o quitar ítems de un pedido y reajustar subtotales."""
        order = await session.get(Order, order_id)
        if not order or order.id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Pedido no encontrado."
            )

        # 1. Eliminar ítems antiguos
        statement = select(OrderDetail).where(OrderDetail.order_id == order_id)
        result = await session.exec(statement)
        for old_item in result.all():
            await session.delete(old_item)

        await session.flush()

        if hasattr(order, "items") and order.items is not None:
            order.items.clear()

        # 2. Crear nuevos ítems y recalcular redondeando
        calculated_subtotal = 0.0
        for item in new_items:
            p_id = (
                item.product_id if hasattr(item, "product_id") else item["product_id"]
            )
            qty = item.quantity if hasattr(item, "quantity") else item["quantity"]
            notes = (
                item.item_notes
                if hasattr(item, "item_notes")
                else item.get("item_notes")
            )

            product = await session.get(Product, p_id)
            if not product or not product.is_active or product.id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Producto ID {p_id} inválido o inexistente.",
                )

            unit_price = round(product.price, 2)
            subtotal_line = round(unit_price * qty, 2)
            calculated_subtotal += subtotal_line

            new_detail = OrderDetail(
                order_id=order_id,
                product_id=product.id,
                quantity=qty,
                item_notes=notes,
                unit_price=unit_price,
                subtotal_line=subtotal_line,
            )
            session.add(new_detail)

        # 3. Guardar subtotales y totales redondeados
        order.subtotal = round(calculated_subtotal, 2)
        order.total = round(
            max(0.0, order.subtotal + order.delivery_fee - order.discount), 2
        )
        order.updated_at = datetime.now(UTC).replace(tzinfo=None)

        session.add(order)
        await session.commit()
        await session.refresh(order)

        if order.id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al procesar el ID del pedido.",
            )

        items_read = await cls.get_order_items(session, order.id)
        return OrderRead(**order.model_dump(), items=items_read)

    @classmethod
    async def cancel_order(cls, session: AsyncSession, order_id: int) -> OrderRead:
        """Cancela la orden (Soft Delete) cambiando su estado."""
        return await cls.update_order(
            session, order_id, OrderUpdate(status=OrderStatus.CANCELLED)
        )
