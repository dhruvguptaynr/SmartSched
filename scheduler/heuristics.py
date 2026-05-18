import random

SLOTS = 6


def teacher_current_load(timetable, teacher):
    load = 0
    for cls_name, schedule in timetable.items():
        for day in schedule:
            for slot in day:
                if slot is not None and slot["teacher"] == teacher:
                    load += 1
    return load


def rank_subjects(subjects, timetable, cls, d, s, subject_count, required_hours):
    def score(sub):
        remaining = required_hours[cls.name].get(sub, 0) - subject_count[cls.name][sub]
        sc = remaining * 10

        count_today = sum(
            1 for x in timetable[cls.name][d]
            if x is not None and x["subject"] == sub
        )
        required = required_hours[cls.name].get(sub, 0)

        if required > 5:
            sc -= count_today * 1
        elif required > 2:
            sc -= count_today * 2
        else:
            sc -= count_today * 4

        if s > 0:
            prev = timetable[cls.name][d][s - 1]
            if prev is not None and prev["subject"] == sub:
                if required > 2:
                    sc += 25
                else:
                    sc -= 8

        for prev_s in range(max(0, s - 3), s):
            prev = timetable[cls.name][d][prev_s]
            if prev is not None and prev["subject"] == sub:
                required = required_hours[cls.name].get(sub, 0)
                if required > 5:
                    if s - prev_s > 1:
                        sc -= 18
                else:
                    sc -= 5

        teacher = cls.subject_teacher_map[sub]["teacher"]
        load = teacher_current_load(timetable, teacher)
        sc -= load * 0.5

        weekly_hours = required_hours[cls.name].get(sub, 0)
        limit = 1 if weekly_hours <= 2 else 2
        if limit == 2:
            sc += (SLOTS - s)
        else:
            sc += s * 0.5

        return sc

    subjects.sort(key=score, reverse=True)
    top_k = subjects[:3]
    random.shuffle(top_k)
    subjects = top_k + subjects[3:]
    return subjects
