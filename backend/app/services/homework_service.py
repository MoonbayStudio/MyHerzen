from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.db.models import Homework
from backend.app.services.schedule_service import (
    extract_lesson_type,
    extract_subject_name,
    extract_teacher_id,
    extract_teacher_name,
    get_schedule_entries_for_group,
    get_teacher_names,
)


def homework_to_response(homework: Homework) -> Dict[str, Any]:
    return {
        "id": homework.id,
        "group_id": homework.group_id,
        "lesson_date": homework.lesson_date,
        "lesson_time": homework.lesson_time,
        "subject": homework.subject,
        "teacher": homework.teacher,
        "room": homework.room,
        "text": homework.text,
        "created_by": homework.created_by_user_id,
        "created_at": homework.created_at,
        "updated_at": homework.updated_at,
    }


def build_homework_options(group_id: int) -> List[Dict[str, Any]]:
    raw_items = get_schedule_entries_for_group(group_id=group_id)

    teacher_ids: Set[int] = set()
    parsed_rows: List[Tuple[str, Optional[int], Optional[str], Optional[str]]] = []

    for lesson in raw_items:
        subject_name = extract_subject_name(lesson)
        if subject_name is None:
            continue

        teacher_id = extract_teacher_id(lesson)
        teacher_name = extract_teacher_name(lesson)
        lesson_type = extract_lesson_type(lesson)

        if teacher_id is not None and teacher_name is None:
            teacher_ids.add(teacher_id)

        parsed_rows.append((subject_name, teacher_id, teacher_name, lesson_type))

    teacher_name_map = get_teacher_names(teacher_ids) if teacher_ids else {}

    unique_options: Dict[Tuple[str, Optional[int], Optional[str], Optional[str]], Dict[str, Any]] = {}
    for subject_name, teacher_id, teacher_name, lesson_type in parsed_rows:
        resolved_teacher_name = teacher_name
        if resolved_teacher_name is None and teacher_id is not None:
            resolved_teacher_name = teacher_name_map.get(teacher_id)

        option_key = (
            subject_name,
            teacher_id,
            resolved_teacher_name,
            lesson_type,
        )
        if option_key in unique_options:
            continue

        unique_options[option_key] = {
            "subjectName": subject_name,
            "teacherId": teacher_id,
            "teacherName": resolved_teacher_name,
            "lessonType": lesson_type,
        }

    options = list(unique_options.values())
    options.sort(
        key=lambda option: (
            option.get("subjectName") or "",
            option.get("teacherName") or "",
            option.get("lessonType") or "",
        )
    )
    return options
