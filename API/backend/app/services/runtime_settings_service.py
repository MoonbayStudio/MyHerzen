import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Literal, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app.core.config import PERSONA_THEME
from backend.app.db.session import SessionLocal
from backend.app.repositories import runtime_settings_repository


SettingValueType = Literal["string", "int", "bool", "json"]


@dataclass(frozen=True)
class RuntimeSettingDefinition:
    key: str
    value_type: SettingValueType
    default_value: Any
    description: str
    is_public: bool


RUNTIME_SETTING_DEFINITIONS: Dict[str, RuntimeSettingDefinition] = {
    "AI_ENABLED": RuntimeSettingDefinition(
        key="AI_ENABLED",
        value_type="bool",
        default_value=True,
        description="Enable or disable AI assistant responses.",
        is_public=True,
    ),
    "AI_DAILY_LIMIT": RuntimeSettingDefinition(
        key="AI_DAILY_LIMIT",
        value_type="int",
        default_value=0,
        description="Optional global cap for daily AI messages per user. 0 means no override.",
        is_public=True,
    ),
    "PERSONA_THEME": RuntimeSettingDefinition(
        key="PERSONA_THEME",
        value_type="string",
        default_value=PERSONA_THEME,
        description="Active persona theme (default/auto/seasonal).",
        is_public=True,
    ),
    "MAINTENANCE_MODE": RuntimeSettingDefinition(
        key="MAINTENANCE_MODE",
        value_type="bool",
        default_value=False,
        description="Show maintenance state in clients.",
        is_public=True,
    ),
    "SCHEDULE_CACHE_TTL_SECONDS": RuntimeSettingDefinition(
        key="SCHEDULE_CACHE_TTL_SECONDS",
        value_type="int",
        default_value=1800,
        description="Assistant schedule context cache TTL in seconds.",
        is_public=False,
    ),
}


_RUNTIME_SETTINGS_CACHE_TTL = timedelta(seconds=15)
_runtime_settings_cached_at: Optional[datetime] = None
_runtime_settings_cache: Dict[str, Any] = {}


def _normalize_key(key: str) -> str:
    normalized = (key or "").strip().upper()
    if not normalized:
        raise HTTPException(status_code=400, detail="Setting key is required")
    return normalized


def _validate_key(key: str) -> RuntimeSettingDefinition:
    normalized_key = _normalize_key(key)
    setting_definition = RUNTIME_SETTING_DEFINITIONS.get(normalized_key)
    if setting_definition is None:
        raise HTTPException(status_code=400, detail="Setting key is not allowed")
    return setting_definition


def _deserialize_value(raw_value: str, value_type: SettingValueType) -> Any:
    if value_type == "string":
        return raw_value

    if value_type == "int":
        return int(raw_value)

    if value_type == "bool":
        normalized = raw_value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
        raise ValueError("Invalid bool value")

    if value_type == "json":
        return json.loads(raw_value)

    raise ValueError("Unsupported value type")


def _serialize_value(value: Any, value_type: SettingValueType) -> str:
    if value_type == "string":
        return str(value)

    if value_type == "int":
        return str(int(value))

    if value_type == "bool":
        return "true" if bool(value) else "false"

    if value_type == "json":
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    raise ValueError("Unsupported value type")


def _coerce_value(value: Any, value_type: SettingValueType) -> Any:
    if value_type == "string":
        if not isinstance(value, str):
            raise HTTPException(status_code=400, detail="Setting value must be a string")
        return value

    if value_type == "int":
        if isinstance(value, bool):
            raise HTTPException(status_code=400, detail="Setting value must be an integer")
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value.strip())
            except ValueError as error:
                raise HTTPException(status_code=400, detail="Setting value must be an integer") from error
        raise HTTPException(status_code=400, detail="Setting value must be an integer")

    if value_type == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes"}:
                return True
            if normalized in {"false", "0", "no"}:
                return False
        raise HTTPException(status_code=400, detail="Setting value must be a boolean")

    if value_type == "json":
        try:
            json.dumps(value)
        except (TypeError, ValueError) as error:
            raise HTTPException(status_code=400, detail="Setting value must be valid JSON") from error
        return value

    raise HTTPException(status_code=400, detail="Unsupported setting type")


def _build_effective_settings_map(db: Session) -> Dict[str, Any]:
    db_rows = runtime_settings_repository.list_settings_by_keys(
        db=db,
        keys=RUNTIME_SETTING_DEFINITIONS.keys(),
    )
    rows_by_key = {row.key: row for row in db_rows}

    settings_map: Dict[str, Any] = {}
    for key, definition in RUNTIME_SETTING_DEFINITIONS.items():
        row = rows_by_key.get(key)
        if row is None:
            settings_map[key] = definition.default_value
            continue

        try:
            settings_map[key] = _deserialize_value(
                raw_value=row.value,
                value_type=definition.value_type,
            )
        except (TypeError, ValueError, json.JSONDecodeError):
            settings_map[key] = definition.default_value

    return settings_map


def invalidate_runtime_settings_cache() -> None:
    global _runtime_settings_cached_at, _runtime_settings_cache
    _runtime_settings_cached_at = None
    _runtime_settings_cache = {}


def get_cached_runtime_setting_value(key: str) -> Any:
    definition = _validate_key(key)

    global _runtime_settings_cached_at, _runtime_settings_cache

    now = datetime.now(timezone.utc)
    if (
        _runtime_settings_cached_at is not None
        and now - _runtime_settings_cached_at <= _RUNTIME_SETTINGS_CACHE_TTL
        and definition.key in _runtime_settings_cache
    ):
        return _runtime_settings_cache[definition.key]

    db = SessionLocal()
    try:
        settings_map = _build_effective_settings_map(db)
        _runtime_settings_cache = settings_map
        _runtime_settings_cached_at = now
        return settings_map.get(definition.key, definition.default_value)
    except Exception:
        return definition.default_value
    finally:
        db.close()


def list_admin_settings(db: Session) -> list[dict[str, Any]]:
    db_rows = runtime_settings_repository.list_settings_by_keys(
        db=db,
        keys=RUNTIME_SETTING_DEFINITIONS.keys(),
    )
    rows_by_key = {row.key: row for row in db_rows}

    payload: list[dict[str, Any]] = []
    for key, definition in RUNTIME_SETTING_DEFINITIONS.items():
        row = rows_by_key.get(key)

        if row is None:
            payload.append(
                {
                    "key": key,
                    "value": definition.default_value,
                    "valueType": definition.value_type,
                    "description": definition.description,
                    "isPublic": definition.is_public,
                    "updatedAt": None,
                    "updatedBy": None,
                }
            )
            continue

        try:
            value = _deserialize_value(row.value, definition.value_type)
        except (TypeError, ValueError, json.JSONDecodeError):
            value = definition.default_value

        payload.append(
            {
                "key": key,
                "value": value,
                "valueType": definition.value_type,
                "description": row.description
                if row.description is not None
                else definition.description,
                "isPublic": bool(row.is_public),
                "updatedAt": row.updated_at,
                "updatedBy": row.updated_by,
            }
        )

    return payload


def update_setting(
    db: Session,
    key: str,
    value: Any,
    updated_by: Optional[int],
    description: Optional[str] = None,
    is_public: Optional[bool] = None,
) -> dict[str, Any]:
    definition = _validate_key(key)
    normalized_value = _coerce_value(value=value, value_type=definition.value_type)

    existing_setting = runtime_settings_repository.get_setting(db=db, key=definition.key)

    final_description = description
    if final_description is None:
        if existing_setting is None:
            final_description = definition.description
        else:
            final_description = existing_setting.description

    final_is_public = is_public
    if final_is_public is None:
        if existing_setting is None:
            final_is_public = definition.is_public
        else:
            final_is_public = bool(existing_setting.is_public)

    now = datetime.now(timezone.utc)
    runtime_settings_repository.upsert_setting(
        db=db,
        key=definition.key,
        value=_serialize_value(normalized_value, definition.value_type),
        value_type=definition.value_type,
        description=final_description,
        is_public=bool(final_is_public),
        updated_by=updated_by,
        now=now,
    )

    db.commit()

    refreshed = runtime_settings_repository.get_setting(db=db, key=definition.key)
    if refreshed is None:
        raise HTTPException(status_code=500, detail="Failed to update setting")

    invalidate_runtime_settings_cache()

    return {
        "key": refreshed.key,
        "value": normalized_value,
        "valueType": definition.value_type,
        "description": refreshed.description,
        "isPublic": bool(refreshed.is_public),
        "updatedAt": refreshed.updated_at,
        "updatedBy": refreshed.updated_by,
    }


def get_public_config(db: Session) -> dict[str, Any]:
    db_rows = runtime_settings_repository.list_settings_by_keys(
        db=db,
        keys=RUNTIME_SETTING_DEFINITIONS.keys(),
    )
    rows_by_key = {row.key: row for row in db_rows}

    config: Dict[str, Any] = {}
    for key, definition in RUNTIME_SETTING_DEFINITIONS.items():
        row = rows_by_key.get(key)

        is_public = definition.is_public if row is None else bool(row.is_public)
        if not is_public:
            continue

        if row is None:
            config[key] = definition.default_value
            continue

        try:
            config[key] = _deserialize_value(row.value, definition.value_type)
        except (TypeError, ValueError, json.JSONDecodeError):
            config[key] = definition.default_value

    return config


def get_runtime_setting_value(db: Session, key: str) -> Any:
    definition = _validate_key(key)

    row = runtime_settings_repository.get_setting(db=db, key=definition.key)
    if row is None:
        return definition.default_value

    try:
        return _deserialize_value(row.value, definition.value_type)
    except (TypeError, ValueError, json.JSONDecodeError):
        return definition.default_value


def get_runtime_persona_theme() -> str:
    value = get_cached_runtime_setting_value("PERSONA_THEME")
    if not isinstance(value, str):
        return PERSONA_THEME
    return value
