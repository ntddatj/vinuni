from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.modules.admin.infrastructure.settings_orm import (
    SystemSettingORM,
    get_setting,
    list_settings,
    upsert_setting,
)
from backend.src.modules.admin.presentation.schemas import (
    PublicSettingsSchema,
    SystemSettingSchema,
    UpdateSettingRequest,
)
from backend.src.modules.identity.domain.entities import User
from backend.src.modules.identity.infrastructure.auth_dependencies import get_current_user
from backend.src.modules.ingestion.infrastructure.orm_models import PaperORM
from backend.src.shared.infra.database import get_db_session as get_db

router = APIRouter(prefix="/admin", tags=["admin"])

# Các setting đã biết và phải là số nguyên dương. Chặn tạo key rác / giá trị sai.
_NUMERIC_SETTING_KEYS = {
    "MAX_PAPERS_PER_PROJECT",
    "BROAD_QUERY_THRESHOLD",
    "GC_RETENTION_DAYS",   # Story 4.1: số ngày giữ dữ liệu xóa mềm trước khi GC xóa cứng
    "MAX_SYNC_RETRIES",    # Story 4.1: số lần retry sync Postgres→Neo4j trước khi vào DLQ
}
ALLOWED_SETTING_KEYS = _NUMERIC_SETTING_KEYS


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Admin mới có quyền thực hiện thao tác này",
        )
    return current_user


@router.get("/settings", response_model=list[SystemSettingSchema])
async def get_settings(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[SystemSettingORM]:
    return await list_settings(db)


@router.get("/settings/public", response_model=PublicSettingsSchema)
async def get_public_settings(
    db: AsyncSession = Depends(get_db),
) -> PublicSettingsSchema:
    """Cấu hình công khai cho client thường (KHÔNG cần quyền admin).

    Expose MAX_PAPERS_PER_PROJECT để frontend hiển thị banner/disable theo đúng
    giới hạn admin đặt, thay vì hardcode 15.
    """
    raw = await get_setting(db, "MAX_PAPERS_PER_PROJECT", default="15")
    try:
        max_papers = int(raw)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        max_papers = 15
    return PublicSettingsSchema(max_papers_per_project=max_papers)


@router.put("/settings/{key}", response_model=SystemSettingSchema)
async def update_setting(
    key: str,
    body: UpdateSettingRequest,
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> SystemSettingORM:
    if key not in ALLOWED_SETTING_KEYS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cấu hình không tồn tại: {key}",
        )
    if key in _NUMERIC_SETTING_KEYS:
        try:
            parsed = int(body.value)
        except (ValueError, TypeError) as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Giá trị phải là số nguyên",
            ) from e
        if parsed < 1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Giá trị phải lớn hơn 0",
            )
    row = await upsert_setting(db, key, body.value)
    await db.commit()
    await db.refresh(row)
    return row


@router.post("/backfill-graph-extraction")
async def backfill_graph_extraction(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Re-enqueue graph_extract_task cho mọi paper đã indexed (idempotent via _job_id)."""
    from arq import create_pool
    from arq.connections import RedisSettings

    from backend.src.shared.infra.settings import get_settings as _get_settings

    result = await db.execute(
        select(PaperORM.id).where(
            PaperORM.status == "indexed", PaperORM.is_deleted.is_(False)
        )
    )
    paper_ids = result.scalars().all()

    settings = _get_settings()
    redis = await create_pool(RedisSettings.from_dsn(settings.arq_redis_url))
    enqueued = 0
    try:
        for paper_id in paper_ids:
            await redis.enqueue_job(
                "graph_extract_task",
                paper_id,
                _job_id=f"graph_extract:{paper_id}",
            )
            enqueued += 1
    finally:
        await redis.aclose()

    return {
        "enqueued": enqueued,
        "message": f"Đã đưa {enqueued} tài liệu vào hàng đợi trích xuất ontology",
    }
