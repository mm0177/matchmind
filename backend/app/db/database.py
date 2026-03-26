from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create pgvector extension and all tables on startup."""
    async with engine.begin() as conn:
        await conn.execute(
            __import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector")
        )
        from app.auth.models import User  # noqa: F401
        from app.chat.models import ChatSession, ChatMessage, UserDayProgress  # noqa: F401
        from app.persona.models import PersonaSnapshot, PersonaFact, UserEntity  # noqa: F401
        from app.matching.models import MatchRun, Match  # noqa: F401
        from app.notifications.models import Notification  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
