from datetime import datetime
from typing import Iterable, List, Optional

from sqlalchemy.orm import Session

from backend.app.db.models import AppSetting


def get_setting(db: Session, key: str) -> Optional[AppSetting]:
    return db.query(AppSetting).filter(AppSetting.key == key).first()


def list_settings_by_keys(db: Session, keys: Iterable[str]) -> List[AppSetting]:
    keys_list = list(keys)
    if not keys_list:
        return []
    return db.query(AppSetting).filter(AppSetting.key.in_(keys_list)).all()


def list_public_settings(db: Session, keys: Iterable[str]) -> List[AppSetting]:
    keys_list = list(keys)
    if not keys_list:
        return []
    return db.query(AppSetting).filter(
        AppSetting.key.in_(keys_list),
        AppSetting.is_public == True,
    ).all()


def upsert_setting(
    db: Session,
    key: str,
    value: str,
    value_type: str,
    description: Optional[str],
    is_public: bool,
    updated_by: Optional[int],
    now: datetime,
) -> AppSetting:
    setting = get_setting(db=db, key=key)
    if setting is None:
        setting = AppSetting(
            key=key,
            value=value,
            value_type=value_type,
            description=description,
            is_public=is_public,
            updated_at=now,
            updated_by=updated_by,
        )
        db.add(setting)
        return setting

    setting.value = value
    setting.value_type = value_type
    setting.description = description
    setting.is_public = is_public
    setting.updated_at = now
    setting.updated_by = updated_by
    return setting
