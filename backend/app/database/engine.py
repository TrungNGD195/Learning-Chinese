from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import get_settings

engine: AsyncEngine = create_async_engine(get_settings().effective_database_url)
