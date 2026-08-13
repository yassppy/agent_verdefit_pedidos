import os

import httpx
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")
PRODUCTS_URL = f"{API_BASE_URL}/products/"


async def get_menu(category: str | None = None) -> dict:
    """Obtiene la lista de productos disponibles en el menú de VerdeFit.

    Opcionalmente se puede filtrar por categoría (ej: 'almuerzos', 'bebidas', 'postres').
    """
    async with httpx.AsyncClient() as client:
        try:
            params = {}
            if category:
                params["category"] = category

            response = await client.get(PRODUCTS_URL, params=params)
            response.raise_for_status()

            products = response.json()
            return {"products": products, "count": len(products)}
        except httpx.HTTPError as err:
            return {"error": f"Error de comunicación al obtener el menú: {err}"}


async def search_product_by_name(query: str) -> dict:
    """Busca productos específicos por nombre o ingrediente."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(PRODUCTS_URL, params={"search": query})
            response.raise_for_status()
            return {"products": response.json()}
        except httpx.HTTPError as err:
            return {"error": f"Error al buscar producto: {err}"}
