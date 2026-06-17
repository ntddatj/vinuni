from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from backend.src.shared.infra.settings import get_settings

_pool: AsyncConnectionPool | None = None
_checkpointer: AsyncPostgresSaver | None = None

_SQLALCHEMY_SCHEME_PREFIXES = (
    "postgresql+asyncpg://",
    "postgresql+psycopg://",
    "postgresql+psycopg2://",
    "postgres://",
)


def _to_psycopg_conn_str(database_url: str) -> str:
    for prefix in _SQLALCHEMY_SCHEME_PREFIXES:
        if database_url.startswith(prefix):
            return "postgresql://" + database_url[len(prefix):]
    return database_url


async def setup_postgres_checkpointer() -> AsyncPostgresSaver:
    global _checkpointer, _pool
    settings = get_settings()
    conn_str = _to_psycopg_conn_str(settings.database_url)
    # autocommit=True là BẮT BUỘC: AsyncPostgresSaver.setup() chạy
    # `CREATE INDEX CONCURRENTLY`, lệnh này không thể nằm trong transaction block.
    # prepare_threshold=0 tránh lỗi prepared statement khi dùng connection pool.
    _pool = AsyncConnectionPool(
        conninfo=conn_str,
        min_size=2,
        max_size=10,
        open=False,
        kwargs={"autocommit": True, "prepare_threshold": 0},
    )
    await _pool.open()
    _checkpointer = AsyncPostgresSaver(_pool)
    await _checkpointer.setup()
    return _checkpointer


async def close_postgres_checkpointer() -> None:
    global _pool, _checkpointer
    if _pool is not None:
        await _pool.close()
        _pool = None
    _checkpointer = None


async def get_postgres_checkpointer() -> AsyncPostgresSaver:
    if _checkpointer is None:
        raise RuntimeError("PostgresSaver chưa được khởi tạo. Gọi setup_postgres_checkpointer() trong lifespan.")
    return _checkpointer
