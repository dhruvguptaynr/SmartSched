import sys
import os
import json

# Add project root to path so imports work in Vercel's serverless env
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

# ─────────────────────────────────────────────
# STATIC CONFIG  (mirrors main.py)
# ─────────────────────────────────────────────
BASE_REQUIRED = {
    "CN": 5,
    "ADS": 10,
    "S&UL": 8,
    "PBL-I": 2,
    "MOS": 3,
    "Explore": 1,
    "FREE": 1,
}

CLASS_NAMES = ["4A", "4B", "4C", "4D"]

# Teacher & room map parsed from timetable.json
SUBJECT_TEACHER_MAP = {
    "CN":      {"teacher": "Dhananjay", "room": "BB LH-1"},
    "ADS":     {"teacher": "Taniya",    "room": "BB LH-1"},
    "S&UL":    {"teacher": "Mudrik",    "room": "BB LH-1"},
    "PBL-I":   {"teacher": "Mudrik",    "room": "BB LH-1"},
    "MOS":     {"teacher": "Rajwinder", "room": "MB LH-401"},
    "Explore": {"teacher": "Trainer",   "room": "BB LH-1"},
}


def build_classes():
    classes = []
    for name in CLASS_NAMES:
        cls = ClassObj(name, dict(SUBJECT_TEACHER_MAP), "BB LH-1")
        classes.append(cls)
    return classes


def timetable_to_simple(tt):
    """Convert {cls: [[{subject,teacher,room}]]} → {cls: [[subject_str]]}"""
    simple = {}
    for cls_name, schedule in tt.items():
        simple[cls_name] = [[slot["subject"] for slot in day] for day in schedule]
    return simple


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        self._respond({"status": "Timetable Optimiser API is running"})

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length else b"{}"
            payload = json.loads(body) if body else {}
        except Exception:
            payload = {}

        try:
            classes = build_classes()
            required_hours = {name: BASE_REQUIRED.copy() for name in CLASS_NAMES}

            result = generate_backtracking_timetable(
                classes,
                required_hours,
                max_attempts_per_class=150,
                num_generations=5,
            )

            if result is None:
                self._respond({"error": "Optimiser failed to find a valid timetable"}, 500)
                return

            tt, subject_count, generation_scores, best_gen = result

            eval_score  = evaluate_timetable(tt)
            free_slots  = count_free_slots(tt)
            violations  = consecutive_subject_violations(tt)
            spread      = subject_spread_score(tt)
            balance     = daily_balance_score(tt)
            t_load      = teacher_load_score(tt)
            overall     = overall_timetable_score(tt)

            response = {
                "timetable":          timetable_to_simple(tt),
                "generation_scores":  generation_scores,
                "best_gen":           best_gen,
                "metrics": {
                    "eval_score":    round(eval_score, 2),
                    "free_slots":    free_slots,
                    "violations":    violations,
                    "spread_score":  spread,
                    "balance_score": balance,
                    "teacher_score": t_load,
                    "overall_score": round(overall, 2),
                },
            }

            self._respond(response)

        except Exception as e:
            self._respond({"error": str(e)}, 500)

    # ── helpers ──────────────────────────────
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _respond(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type",   "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # suppress default access logs
