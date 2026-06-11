from datetime import datetime


def resolve_persona_theme(now: datetime) -> str:
    month = now.month
    day = now.day

    if (month == 12 and day >= 20) or (month == 1 and day <= 10):
        return "christmas"
    if (month == 10 and day >= 25) or (month == 11 and day <= 2):
        return "halloween"
    if (month == 8 and day >= 25) or (month == 9 and day <= 10):
        return "back_to_school"
    if month == 1 and 15 <= day <= 31:
        return "exams"
    if (month == 5 and day >= 20) or (month == 6 and day <= 15):
        return "finals"
    return "default"
