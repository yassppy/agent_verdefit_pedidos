import os

import httpx
from dotenv import load_dotenv

load_dotenv()

# URL base centralizada
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
CUSTOMERS_URL = f"{API_BASE_URL}/customers"


async def get_customer_by_telegram_id(telegram_chat_id: str) -> dict:
    """Busca si un cliente ya existe en el sistema por su ID de Telegram."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{CUSTOMERS_URL}/telegram/{telegram_chat_id}")
            if response.status_code == 404:
                return {"exists": False, "message": "Cliente no registrado."}
            response.raise_for_status()
            data = response.json()
            data["exists"] = True
            return data
        except httpx.HTTPError as err:
            return {"error": f"Error de comunicación al verificar cliente: {err}"}


async def register_customer(
    telegram_chat_id: str,
    name: str,
    phone: str,
    address: str,
    district: str,
    reference: str | None = None,
) -> dict:
    """Registra un nuevo cliente en la base de datos."""
    payload = {
        "telegram_chat_id": int(telegram_chat_id),
        "name": name,
        "phone": phone,
        "address": address,
        "district": district,
        "reference": reference,
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(f"{CUSTOMERS_URL}/", json=payload)
            if response.status_code not in (200, 201):
                return {"error": f"No se pudo registrar al cliente: {response.text}"}
            return response.json()
        except httpx.HTTPError as err:
            return {"error": f"Error de comunicación al registrar cliente: {err}"}


async def update_customer(
    telegram_chat_id: str,
    name: str | None = None,
    phone: str | None = None,
    address: str | None = None,
    district: str | None = None,
    reference: str | None = None,
) -> dict:
    """Actualiza parcialmente la información de un cliente (Dirección, Distrito, Referencia, etc.).
    NOTA: Jamás actualiza el telegram_chat_id.
    """
    async with httpx.AsyncClient() as client:
        try:
            # 1. Obtener cliente para hallar su ID interno
            get_res = await client.get(f"{CUSTOMERS_URL}/telegram/{telegram_chat_id}")
            if get_res.status_code != 200:
                return {"error": "Cliente no encontrado para actualizar."}

            customer_data = get_res.json()
            customer_id = customer_data["id"]

            # 2. Filtrar únicamente los campos que no sean None
            update_payload = {}
            if name is not None:
                update_payload["name"] = name
            if phone is not None:
                update_payload["phone"] = phone
            if address is not None:
                update_payload["address"] = address
            if district is not None:
                update_payload["district"] = district
            if reference is not None:
                update_payload["reference"] = reference

            if not update_payload:
                return {"message": "No se enviaron campos válidos para actualizar."}

            # 3. Enviar actualización vía PATCH
            response = await client.patch(
                f"{CUSTOMERS_URL}/{customer_id}", json=update_payload
            )
            if response.status_code != 200:
                return {"error": f"Error al actualizar cliente: {response.text}"}

            return response.json()

        except httpx.HTTPError as err:
            return {"error": f"Error de comunicación al actualizar cliente: {err}"}
