import os
import pandas as pd
import joblib

# Always resolve relative to this file so it works in any working directory
_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "timetable_model.pkl"
)

model = joblib.load(_MODEL_PATH)


def predict_timetable_quality(df):
    if "score" in df.columns:
        X = df.drop(columns=["score"])
    else:
        X = df
    predictions = model.predict(X)
    return predictions.mean()
