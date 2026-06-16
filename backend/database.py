import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

DB_PATH = os.path.join(os.path.dirname(__file__), "homework.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    from models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # 迁移：补充后续新增的字段（SQLite ALTER TABLE 安全操作）
        try:
            await conn.execute(text("ALTER TABLE problem_records ADD COLUMN student_answer TEXT"))
        except Exception:
            pass  # 字段已存在
        try:
            await conn.execute(text("ALTER TABLE problem_records ADD COLUMN correct_answer TEXT"))
        except Exception:
            pass
        try:
            await conn.execute(text("ALTER TABLE problem_records ADD COLUMN parent_correction TEXT"))
        except Exception:
            pass
