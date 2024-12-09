from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://postgres:GZVqKSkgeJifyNidfPDKJhAHyVowCDql@junction.proxy.rlwy.net:57879/railway"

# Асинхронный движок SQLAlchemy
engine = create_async_engine(DATABASE_URL, echo=True)

# Создаем сессию
async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)


async def init_db():
    from models import Base

    async with engine.begin() as conn:
        # Создаем таблицы
        await conn.run_sync(Base.metadata.create_all)
