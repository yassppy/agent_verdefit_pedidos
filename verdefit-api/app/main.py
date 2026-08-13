from contextlib import asynccontextmanager

from core.config import settings
from core.db import init_db
from fastapi import FastAPI
from features.customers.models import Customer  # noqa: F401
from features.customers.router import router as customer_router
from features.delivery_zones.models import DeliveryZone  # noqa: F401
from features.delivery_zones.router import router as delivery_zone_router
from features.drivers.models import Driver  # noqa: F401
from features.drivers.router import router as driver_router
from features.health.router import router as health_router
from features.products.models import Product  # noqa: F401
from features.products.router import router as product_router
from scalar_fastapi import get_scalar_api_reference


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Maneja los eventos de inicio y cierre de la aplicación."""
    await init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API RESTful de Persistencia para VerdeFit Orders",
    lifespan=lifespan,  # Ejecutar init_db() al arrancar
)

app.include_router(health_router, prefix=settings.API_V1_STR)
app.include_router(customer_router, prefix=settings.API_V1_STR)
app.include_router(product_router, prefix=settings.API_V1_STR)
app.include_router(delivery_zone_router, prefix=settings.API_V1_STR)
app.include_router(driver_router, prefix=settings.API_V1_STR)


@app.get("/scalar", include_in_schema=False)
async def scalar_html():
    """Renderizar la documentación a Scalar"""
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title + " - Scalar Docs",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
