import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from http.server import BaseHTTPRequestHandler

from models.class_section import ClassObj
from scheduler.backtracking import generate_backtracking_timetable
from scheduler.evaluator import (
    count_free_slots,
    consecutive_subject_violations,
    subject_spread_score,
    daily_balance_score,
    teacher_load_score,
    evaluate_timetable,
    overall_timetable_score,
)
from ml.dataset_builder import build_dataset
from ml.predictor import predict_timetable_quality

# ─────────────────────────────────────────────
# REQUIRED HOURS  (same for all classes)
# ─────────────────────────────────────────────
BASE_REQUIRED = {
    "CN":      5,
    "ADS":     10,
    "S&UL":    8,
    "PBL-I":   2,
    "MOS":     3,
    "Explore": 1,
    "FREE":    1,
}

_JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "processed_data", "timetable.json"
)

_TRAINING_CSV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "training_data.csv"
)


def _load_class_maps():
    """
    Mirrors split_by_class() + build_class_map() from the original pipeline.
    Reads timetable.json so no PDF dependency at runtime.
    Each class has its OWN teacher/room per subject as extracted from the PDF.
    """
    class_names = ["4A", "4B", "4C", "4D"]

    with open(_JSON_PATH) as f:
        structured = json.load(f)

    # split_by_class: new class when "Mo" follows "Fr"
    classes_raw = []
    current = []
    prev_day = None
    for entry in structured:
        if entry["day"] == "Mo" and prev_day == "Fr":
            classes_raw.append(current)
            current = []
        current.append(entry)
        prev_day = entry["day"]
    if current:
        classes_raw.append(current)

    # build_class_map: first occurrence of each subject per class wins
    class_objects = []
    for name, data in zip(class_names, classes_raw):
        subject_teacher_map = {}
        class_room = None
        for entry in data:
            sub = entry["subject"]
            if sub not in subject_teacher_map:
                subject_teacher_map[sub] = {
                    "teacher": entry["teacher"],
                    "room":    entry.get("room", "UNKNOWN"),
                }
            if class_room is None:
                class_room = entry.get("room", "UNKNOWN")
        cls = ClassObj(name, subject_teacher_map, class_room)
        class_objects.append(cls)

    return class_objects


def timetable_to_simple(tt):
    return {
        cls_name: [[slot["subject"] for slot in day] for day in schedule]
        for cls_name, schedule in tt.items()
    }


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        self._respond({"status": "Timetable Optimiser API is running"})

    def do_POST(self):
        try:
            classes = _load_class_maps()
        except Exception as e:
            self._respond({"error": f"Failed to load class data: {e}"}, 500)
            return

        required_hours = {cls.name: BASE_REQUIRED.copy() for cls in classes}

        try:
            # ── Run 5 generations, pick best by combined score ──────────────
            best_tt            = None
            best_subject_count = None
            best_combined      = float("-inf")
            generation_scores  = []

            for generation in range(5):
                result = generate_backtracking_timetable(
                    classes,
                    required_hours,
                    max_attempts_per_class=150,
                    num_generations=1,   # one generation at a time so we can run ML per gen
                )

                if result is None:
                    generation_scores.append(0)
                    continue

                tt, subject_count, _, _ = result

                # ── Evaluator score ─────────────────────────────────────────
                eval_score = evaluate_timetable(tt)

                # ── ML quality prediction (mirrors main.py exactly) ─────────
                try:
                    df = build_dataset(
                        tt,
                        classes,
                        subject_count,
                        required_hours,
                        eval_score
                    )
                    ml_score = float(predict_timetable_quality(df))
                except Exception:
                    ml_score = eval_score  # graceful fallback

                # ── Save training data (append) ─────────────────────────────
                try:
                    import os as _os
                    file_exists = _os.path.exists(_TRAINING_CSV)
                    df_save = build_dataset(tt, classes, subject_count, required_hours, eval_score)
                    df_save.to_csv(_TRAINING_CSV, mode="a", header=not file_exists, index=False)
                except Exception:
                    pass  # non-critical

                # ── Combined score (same weights as main.py) ────────────────
                combined = 0.7 * eval_score + 0.3 * ml_score
                generation_scores.append(round(combined, 2))

                if combined > best_combined:
                    best_combined      = combined
                    best_tt            = tt
                    best_subject_count = subject_count
                    best_eval_score    = eval_score
                    best_ml_score      = ml_score

            if best_tt is None:
                self._respond({"error": "Optimiser failed to generate any valid timetable"}, 500)
                return

            best_gen = generation_scores.index(max(generation_scores))

            # ── Build per-class teacher map for frontend ────────────────────
            class_teacher_maps = {
                cls.name: {
                    sub: cls.subject_teacher_map[sub]
                    for sub in cls.subject_teacher_map
                }
                for cls in classes
            }

            response = {
                "timetable":          timetable_to_simple(best_tt),
                "generation_scores":  generation_scores,
                "best_gen":           best_gen,
                "class_teacher_maps": class_teacher_maps,
                "metrics": {
                    "eval_score":    round(best_eval_score, 2),
                    "ml_score":      round(best_ml_score, 2),
                    "combined_score":round(best_combined, 2),
                    "free_slots":    count_free_slots(best_tt),
                    "violations":    consecutive_subject_violations(best_tt),
                    "spread_score":  subject_spread_score(best_tt),
                    "balance_score": daily_balance_score(best_tt),
                    "teacher_score": teacher_load_score(best_tt),
                    "overall_score": round(overall_timetable_score(best_tt), 2),
                },
            }
            self._respond(response)

        except Exception as e:
            self._respond({"error": str(e)}, 500)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _respond(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type",   "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass
