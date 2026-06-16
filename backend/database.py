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
        # 迁移：为现有表添加新列（如果不存在）
        migrations = [
            "ALTER TABLE homework_records ADD COLUMN not_attempted_count INTEGER DEFAULT 0",
            "ALTER TABLE problem_records ADD COLUMN subject VARCHAR(20) DEFAULT ''",
            "ALTER TABLE problem_records ADD COLUMN student_answer TEXT DEFAULT ''",
            "ALTER TABLE problem_records ADD COLUMN correct_answer TEXT DEFAULT ''",
            "ALTER TABLE problem_records ADD COLUMN parent_correction VARCHAR(20) DEFAULT ''",
        ]
        for m in migrations:
            try:
                await conn.exec_driver_sql(m)
            except Exception:
                pass  # 列已存在则忽略
