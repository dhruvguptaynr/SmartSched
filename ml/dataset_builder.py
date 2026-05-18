import pandas as pd

from ml.feature_extractor import extract_features


# -----------------------------------
# BUILD TRAINING DATASET
# -----------------------------------


def build_dataset(
    timetable,
    classes,
    subject_count,
    required_hours,
    evaluator_score
):

    rows = []

    for cls in classes:

        for d in range(5):

            for s in range(6):

                slot = timetable[cls.name][d][s]

                if slot is None:
                    continue

                subject = slot["subject"]

                if subject == "FREE":
                    continue

                features = extract_features(
                    timetable,
                    cls,
                    subject,
                    d,
                    s,
                    subject_count,
                    required_hours
                )

                # target label
                features["score"] = evaluator_score

                rows.append(features)

    return pd.DataFrame(rows)