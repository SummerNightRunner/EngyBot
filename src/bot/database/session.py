from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.config import get_settings
from bot.database.base import Base
from bot.services.content import seed_word_sets


settings = get_settings()
engine = create_async_engine(settings.database_url, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def migrate_schema() -> None:
    async with engine.begin() as connection:
        def collect_missing(sync_connection) -> dict[str, set[str]]:
            inspector = inspect(sync_connection)
            required = {
                "words": {"level"},
                "daily_practices": set(),
            }
            missing: dict[str, set[str]] = {}
            for table_name, required_columns in required.items():
                if not inspector.has_table(table_name):
                    missing[table_name] = required_columns
                    continue
                existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
                missing[table_name] = required_columns - existing_columns
            return missing

        missing = await connection.run_sync(collect_missing)

        if "level" in missing.get("words", set()):
            await connection.exec_driver_sql("ALTER TABLE words ADD COLUMN level VARCHAR(32) DEFAULT 'A1'")


async def init_db() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    await migrate_schema()

    async with SessionLocal() as session:
        await seed_word_sets(session)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
