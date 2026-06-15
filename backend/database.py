import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

DB_PATH = os.path.join(os.path.dirname(__file__), "homework.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    from models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
