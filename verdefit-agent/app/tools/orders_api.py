import os

import httpx
from dotenv import load_dotenv

load_dotenv()

# URLs base centralizadas
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
ORDERS_URL = f"{API_BASE_URL}/orders"
CUSTOMERS_URL = f"{API_BASE_URL}/customers"
DELIVERY_ZONES_URL = f"{API_BASE_URL}/delivery-zones"
DRIVERS_URL = f"{API_BASE_URL}/drivers"


async def create_order(
    telegram_chat_id: str,
    items: list[dict],
    delivery_type: str = "Delivery",
    payment_method: str = "YAPE",
    customer_notes: str | None = None,
) -> dict:
    """Crea un pedido consultando automáticamente la zona de delivery, tarifa y asignación de motorizado.

    Args:
        telegram_chat_id (str): Chat ID del cliente en Telegram.
        items (list[dict]): Lista de productos, ej: [{"product_id": 1, "quantity": 2, "item_notes": "Sin sal"}]
        delivery_type (str): "Delivery" o "PickUp". Por defecto "Delivery".
        payment_method (str): Método de pago (YAPE, PLIN, Efectivo, Tarjeta).
        customer_notes (str | None): Notas u observaciones adicionales para el pedido.
    """
    async with httpx.AsyncClient() as client:
        try:
            # 1. Obtener cliente por ID de Telegram
            cust_res = await client.get(f"{CUSTOMERS_URL}/telegram/{telegram_chat_id}")
            if cust_res.status_code == 404:
                return {
                    "error": "El cliente no está registrado. Regístrate antes de pedir."
                }
            cust_res.raise_for_status()
            customer_data = cust_res.json()

            customer_id = customer_data.get("id")
            district = customer_data.get("district")

            # Valores por defecto para PickUp o fallbacks
            delivery_zone_id = None
            delivery_fee = 0.0
            driver_id = None

            # 2. Si es Delivery, buscar zona, tarifa y driver disponible
            if delivery_type.lower() == "delivery":
                if not district:
                    return {
                        "error": "El cliente no tiene un distrito registrado para delivery."
                    }

                # a. Obtener Zona de Delivery según el distrito
                zone_res = await client.get(
                    f"{DELIVERY_ZONES_URL}/",
                    params={"district": district, "only_active": True},
                )
                if zone_res.status_code == 200:
                    zones = zone_res.json()
                    if zones:
                        zone = zones[0]  # Tomamos la primera zona coincidente
                        delivery_zone_id = zone.get("id")
                        delivery_fee = float(zone.get("price") or 0.0)

                if not delivery_zone_id:
                    return {
                        "error": f"Lamentablemente no contamos con cobertura de delivery para el distrito '{district}'."
                    }

                # b. Buscar un Driver disponible asignado a esa zona
                drivers_res = await client.get(
                    f"{DRIVERS_URL}/",
                    params={"only_available": True, "only_active": True},
                )
                if drivers_res.status_code == 200:
                    available_drivers = drivers_res.json()
                    for drv in available_drivers:
                        # Verifica si la zona requerida está en las zonas del driver
                        if delivery_zone_id in drv.get("assigned_zone_ids", []):
                            driver_id = drv.get("id")
                            break  # Asigna el primer repartidor libre encontrado

            # 3. Formatear la lista de ítems requerida
            formatted_items = []
            for item in items:
                raw_product_id = item.get("product_id")
                if raw_product_id is None:
                    return {
                        "error": "Uno de los productos no tiene un 'product_id' válido."
                    }

                formatted_items.append(
                    {
                        "product_id": int(raw_product_id),
                        "quantity": int(item.get("quantity") or 1),
                        "item_notes": str(item.get("item_notes") or ""),
                    }
                )

            # 4. Construir Payload final del Pedido
            payload = {
                "customer_id": customer_id,
                "delivery_zone_id": delivery_zone_id,
                "driver_id": driver_id,
                "delivery_type": "Delivery"
                if delivery_type.lower() == "delivery"
                else "PickUp",
                "payment_method": payment_method.upper(),
                "is_paid": False,
                "delivery_fee": delivery_fee,
                "customer_notes": customer_notes or "",
                "internal_notes": "Pedido registrado desde Telegram Bot",
                "items": formatted_items,
            }

            # 5. Enviar POST a la API de Ordenes
            response = await client.post(f"{ORDERS_URL}/", json=payload)
            if response.status_code not in (200, 201):
                return {"error": f"No se pudo registrar la orden: {response.text}"}

            return response.json()

        except httpx.HTTPError as err:
            return {"error": f"Error de comunicación con la API de órdenes: {err}"}


async def get_order_status(order_id: int) -> dict:
    """Consulta el estado actual de un pedido por su ID."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{ORDERS_URL}/{order_id}")
            if response.status_code == 404:
                return {"error": "El pedido especificado no existe."}
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as err:
            return {"error": f"Error al consultar el pedido: {err}"}
