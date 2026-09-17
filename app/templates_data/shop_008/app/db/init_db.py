from loguru import logger
from app.db.session import engine
from app.db.base_class import Base


async def init_db() -> None:
    """Initialize database, create all tables (noop if already exist via migrations)."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialization completed")
    except Exception as e:
        logger.warning(f"init_db: {e}")
