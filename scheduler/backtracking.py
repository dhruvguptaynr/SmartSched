import copy
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scheduler.heuristics import rank_subjects
from scheduler.evaluator import overall_timetable_score
from utils.constraints import is_teacher_free, max_subject_per_day

DAYS = 5
SLOTS = 6


def is_complete(subject_count, classes, required_hours):
    for cls in classes:
        for sub in cls.subject_teacher_map:
            if subject_count[cls.name][sub] != required_hours[cls.name].get(sub, 0):
                return False
    return True


def find_mrv_slot(timetable, cls, subject_count, required_hours):
    best_slot = None
    min_domain = float("inf")

    for d in range(DAYS):
        for s in range(SLOTS):
            if timetable[cls.name][d][s] is not None:
                continue
            valid_subjects = 0
            for subject in cls.subject_teacher_map:
                if subject_count[cls.name][subject] >= required_hours[cls.name].get(subject, 0):
                    continue
                teacher = cls.subject_teacher_map[subject]["teacher"]
                if not is_teacher_free(timetable, teacher, d, s):
                    continue
                if not max_subject_per_day(timetable, cls.name, d, subject, required_hours):
                    continue
                valid_subjects += 1

            if 0 < valid_subjects < min_domain:
                min_domain = valid_subjects
                best_slot = (d, s)

    if best_slot is None:
        for d in range(DAYS):
            for s in range(SLOTS):
                if timetable[cls.name][d][s] is None:
                    return (d, s)
    return best_slot


def backtrack_single_class(timetable, cls, subject_count, required_hours):
    remaining_required = sum(
        required_hours[cls.name].get(sub, 0) - subject_count[cls.name][sub]
        for sub in cls.subject_teacher_map
    )
    if remaining_required <= 0:
        return True

    remaining_slots = sum(
        1 for d in range(DAYS) for s in range(SLOTS)
        if timetable[cls.name][d][s] is None
    )
    if remaining_required > remaining_slots:
        return False

    slot = find_mrv_slot(timetable, cls, subject_count, required_hours)
    if slot is None:
        return False

    d, s = slot
    subjects = list(cls.subject_teacher_map.keys())
    subjects = rank_subjects(subjects, timetable, cls, d, s, subject_count, required_hours)

    for subject in subjects:
        if subject_count[cls.name][subject] >= required_hours[cls.name].get(subject, 0):
            continue
        if not max_subject_per_day(timetable, cls.name, d, subject, required_hours):
            continue

        teacher = cls.subject_teacher_map[subject]["teacher"]
        room = cls.subject_teacher_map[subject]["room"]

        if not is_teacher_free(timetable, teacher, d, s):
            continue

        timetable[cls.name][d][s] = {"subject": subject, "teacher": teacher, "room": room}
        subject_count[cls.name][subject] += 1

        if backtrack_single_class(timetable, cls, subject_count, required_hours):
            return True

        timetable[cls.name][d][s] = None
        subject_count[cls.name][subject] -= 1

    return False


def generate_backtracking_timetable(classes, required_hours, max_attempts_per_class=200, num_generations=5):
    best_timetable = None
    best_subject_count = None
    best_score = float("-inf")
    generation_scores = []

    def class_demand(cls):
        return sum(required_hours[cls.name].get(sub, 0) for sub in cls.subject_teacher_map)

    classes = sorted(classes, key=class_demand, reverse=True)

    for generation in range(num_generations):
        timetable = {
            cls.name: [[None for _ in range(SLOTS)] for _ in range(DAYS)]
            for cls in classes
        }
        subject_count = {
            cls.name: {sub: 0 for sub in cls.subject_teacher_map}
            for cls in classes
        }
        generation_success = True

        for cls in classes:
            success = False
            for attempt in range(max_attempts_per_class):
                timetable[cls.name] = [[None for _ in range(SLOTS)] for _ in range(DAYS)]
                for sub in subject_count[cls.name]:
                    subject_count[cls.name][sub] = 0
                if backtrack_single_class(timetable, cls, subject_count, required_hours):
                    success = True
                    break
            if not success:
                generation_success = False
                break

        if not generation_success:
            generation_scores.append(0)
            continue

        if not is_complete(subject_count, classes, required_hours):
            generation_scores.append(0)
            continue

        for cls_name in timetable:
            current_cls = next(c for c in classes if c.name == cls_name)
            for d in range(DAYS):
                for s in range(SLOTS):
                    if timetable[cls_name][d][s] is None:
                        timetable[cls_name][d][s] = {
                            "subject": "FREE",
                            "teacher": None,
                            "room": current_cls.room
                        }

        score = overall_timetable_score(timetable)
        generation_scores.append(round(score, 2))

        if score > best_score:
            best_subject_count = copy.deepcopy(subject_count)
            best_score = score
            best_timetable = copy.deepcopy(timetable)

    if best_timetable is None:
        return None

    best_gen = generation_scores.index(max(generation_scores))
    return best_timetable, best_subject_count, generation_scores, best_gen
