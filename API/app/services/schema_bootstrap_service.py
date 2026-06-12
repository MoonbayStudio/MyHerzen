from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.models import AppSetting, SystemNotice, UserSession, Badge, UserBadge


def ensure_runtime_feature_tables(engine: Engine) -> None:
    AppSetting.__table__.create(bind=engine, checkfirst=True)
    SystemNotice.__table__.create(bind=engine, checkfirst=True)
    UserSession.__table__.create(bind=engine, checkfirst=True)
    Badge.__table__.create(bind=engine, checkfirst=True)
    UserBadge.__table__.create(bind=engine, checkfirst=True)

    # Migrations for UserSettings
    with engine.connect() as conn:
        # Add schedule_cache_weeks
        try:
            conn.execute(text("ALTER TABLE user_settings ADD COLUMN schedule_cache_weeks INTEGER NOT NULL DEFAULT 2"))
            conn.commit()
        except Exception:
            pass # Column already exists

        # Add live_activity_enabled
        try:
            conn.execute(text("ALTER TABLE user_settings ADD COLUMN live_activity_enabled BOOLEAN NOT NULL DEFAULT TRUE"))
            conn.commit()
        except Exception:
            pass # Column already exists

    with Session(engine) as db:
        seed_system_badges(db)


def seed_system_badges(db: Session) -> None:
    system_badges = [
        {
            "code": "first_tester",
            "title": "Первый тестер",
            "description": "Выдан участникам первого закрытого тестирования MyHerzen",
            "icon_name": "badge_first_tester",
            "rarity": "epic",
        },
        {
            "code": "active_tester",
            "title": "Активный тестер",
            "description": "За активное участие в поиске багов и улучшении приложения",
            "icon_name": "badge_active_tester",
            "rarity": "rare",
        },
    ]

    for badge_data in system_badges:
        existing = db.query(Badge).filter(Badge.code == badge_data["code"]).first()
        if not existing:
            badge = Badge(**badge_data)
            db.add(badge)
    db.commit()
