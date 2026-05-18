from utils.constraints import max_subject_per_day

def extract_features(
    timetable,
    cls,
    subject,
    d,
    s,
    subject_count,
    required_hours
):

    features = {}

    # -------------------------
    # Remaining hours
    # -------------------------

    remaining = (
        required_hours[cls.name].get(subject, 0)
        - subject_count[cls.name][subject]
    )

    features["remaining_hours"] = remaining

    # -------------------------
    # Count today
    # -------------------------

    count_today = sum(
        1
        for x in timetable[cls.name][d]
        if x is not None and x["subject"] == subject
    )

    features["count_today"] = count_today

    # -------------------------
    # Previous same subject
    # -------------------------

    prev_same = 0

    if s > 0:

        prev = timetable[cls.name][d][s - 1]

        if prev is not None and prev["subject"] == subject:
            prev_same = 1

    features["prev_same"] = prev_same

    # -------------------------
    # Slot position
    # -------------------------

    features["slot"] = s

    # -------------------------
    # Day index
    # -------------------------

    features["day"] = d

    # -------------------------
    # Subject daily limit
    # -------------------------

    valid_limit = max_subject_per_day(
        timetable,
        cls.name,
        d,
        subject,
        required_hours
    )

    features["within_daily_limit"] = int(valid_limit)

    return features