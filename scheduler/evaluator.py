DAYS = 5
SLOTS = 6


def count_free_slots(timetable):
    free_count = 0
    for cls_name, schedule in timetable.items():
        for day in schedule:
            for slot in day:
                if slot["subject"] == "FREE":
                    free_count += 1
    return free_count


def consecutive_subject_violations(timetable):
    violations = 0
    for cls_name, schedule in timetable.items():
        for day in schedule:
            for i in range(1, len(day)):
                if day[i]["subject"] == day[i - 1]["subject"]:
                    violations += 1
    return violations


def subject_spread_score(timetable):
    score = 0
    for cls_name, schedule in timetable.items():
        subject_days = {}
        for d, day in enumerate(schedule):
            for slot in day:
                sub = slot["subject"]
                if sub == "FREE":
                    continue
                if sub not in subject_days:
                    subject_days[sub] = set()
                subject_days[sub].add(d)
        for sub in subject_days:
            score += len(subject_days[sub])
    return score


def daily_balance_score(timetable):
    total_score = 0
    for cls_name, schedule in timetable.items():
        loads = [
            sum(1 for slot in day if slot["subject"] != "FREE")
            for day in schedule
        ]
        imbalance = max(loads) - min(loads)
        total_score += (10 - imbalance)
    return total_score


def teacher_load_score(timetable):
    teacher_slots = {}
    for cls_name, schedule in timetable.items():
        for day in schedule:
            for slot in day:
                teacher = slot["teacher"]
                if teacher is None:
                    continue
                teacher_slots[teacher] = teacher_slots.get(teacher, 0) + 1
    if not teacher_slots:
        return 0
    loads = list(teacher_slots.values())
    imbalance = max(loads) - min(loads)
    return max(0, 20 - imbalance)


def overall_timetable_score(timetable):
    free_penalty = count_free_slots(timetable) * 2
    consecutive_penalty = consecutive_subject_violations(timetable) * 3
    spread_bonus = subject_spread_score(timetable)
    balance_bonus = daily_balance_score(timetable)
    teacher_bonus = teacher_load_score(timetable)
    return 100 + spread_bonus + balance_bonus + teacher_bonus - free_penalty - consecutive_penalty


def evaluate_timetable(timetable):
    score = 0
    score -= count_free_slots(timetable) * 4
    score -= consecutive_subject_violations(timetable) * 6
    score += subject_spread_score(timetable)
    score += daily_balance_score(timetable)
    score += teacher_load_score(timetable)
    return score
