from collections.abc import AsyncGenerator

from core.config import settings
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

# Procesar peticiones asíncronas mientras que esperas la respuesta, puedes ir procesando otras solicitudes
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Habilita o desabilita la setencia SQL que se está procesando
    pool_pre_ping=True,  # Previene desconexiones inactivas típicas de Neon
)

# Fábrica de sesiones asíncronas moderna de SQLAlchemy para entornos asíncronos
async_session_maker = async_sessionmaker(
    bind=engine,  # vinculamos la base de datos
    class_=AsyncSession,  # especifica la clase que se va a utilizar
    expire_on_commit=False,  # Evita que los objetos queden expirados
)


async def init_db() -> None:
    """Crea las tablas en Neon al iniciar la aplicación."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Inyector de dependencia para obtener la sesión de base de datos en endpoints."""
    async with async_session_maker() as session:
        yield session
