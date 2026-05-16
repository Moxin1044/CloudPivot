from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.site_config import SiteConfig
from app.schemas.site_config import (
    SiteConfigItem, SiteConfigUpdate, SiteConfigResponse, RegistrationStatusResponse
)
from app.dependencies import get_current_active_admin
from app.models.user import User

router = APIRouter(prefix="/site-config", tags=["Site Config"])


async def _ensure_config(db: AsyncSession, key: str, default_value: str, description: str):
    result = await db.execute(select(SiteConfig).where(SiteConfig.key == key))
    config = result.scalar_one_or_none()
    if not config:
        config = SiteConfig(key=key, value=default_value, description=description)
        db.add(config)
        await db.flush()
        await db.refresh(config)
    return config


@router.get("/registration-status", response_model=RegistrationStatusResponse, summary="获取注册开放状态")
async def get_registration_status(db: AsyncSession = Depends(get_db)):
    config = await _ensure_config(
        db, "allow_register", "true",
        "Whether open registration is allowed"
    )
    return RegistrationStatusResponse(allow_register=config.value == "true")


@router.get("", response_model=list[SiteConfigResponse], summary="获取所有站点配置")
async def list_site_configs(
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SiteConfig))
    return result.scalars().all()


@router.put("/{key}", response_model=SiteConfigResponse, summary="更新站点配置")
async def update_site_config(
    key: str,
    data: SiteConfigUpdate,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SiteConfig).where(SiteConfig.key == key))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Config key not found")
    if data.value is not None:
        config.value = data.value
    if data.description is not None:
        config.description = data.description
    await db.flush()
    await db.refresh(config)
    return config


@router.post("/batch", response_model=list[SiteConfigResponse], summary="批量更新站点配置")
async def batch_update_site_configs(
    items: list[SiteConfigItem],
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    updated = []
    for item in items:
        result = await db.execute(select(SiteConfig).where(SiteConfig.key == item.key))
        config = result.scalar_one_or_none()
        if config:
            config.value = item.value
            if item.description is not None:
                config.description = item.description
        else:
            config = SiteConfig(
                key=item.key,
                value=item.value,
                description=item.description,
            )
            db.add(config)
        updated.append(config)
    await db.flush()
    for c in updated:
        await db.refresh(c)
    return updated
