def is_teacher_free(timetable, teacher, day, slot):
    if not teacher:
        return True
    for cls in timetable:
        entry = timetable[cls][day][slot]
        if entry is not None and entry["teacher"] == teacher:
            return False
    return True


def is_room_free(timetable, room, day, slot):
    for cls in timetable:
        entry = timetable[cls][day][slot]
        if entry is not None and entry["room"] == room:
            return False
    return True


def max_subject_per_day(timetable, cls_name, d, subject, required_hours):
    """
    Mirrors the original constraints.py exactly:
      weekly_hours <= 5  →  max 1 per day
      weekly_hours >  5  →  max 2 per day
    """
    weekly_hours = required_hours[cls_name].get(subject, 0)

    limit = 1 if weekly_hours <= 5 else 2

    count_today = sum(
        1
        for x in timetable[cls_name][d]
        if x is not None and x["subject"] == subject
    )

    return count_today < limit
