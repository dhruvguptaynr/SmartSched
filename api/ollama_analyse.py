"""
Rule-based timetable analyser — zero external dependencies.
Mirrors the logic of evaluator.py but produces human-readable text.
POST /api/ollama_analyse
Body: { timetable, metrics, class_teacher_maps }
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from http.server import BaseHTTPRequestHandler

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


# ── helpers ────────────────────────────────────────────────────────────────

def find_consecutive(timetable):
    issues = []
    for cls, schedule in timetable.items():
        for d, day in enumerate(schedule):
            for s in range(1, len(day)):
                if day[s] == day[s-1] and day[s] != "FREE":
                    issues.append(
                        f"Class {cls} · {DAYS[d]}: '{day[s]}' runs back-to-back "
                        f"in periods {s} and {s+1}"
                    )
    return issues


def find_daily_imbalance(timetable):
    issues = []
    for cls, schedule in timetable.items():
        loads = [sum(1 for s in day if s != "FREE") for day in schedule]
        hi, lo = max(loads), min(loads)
        if hi - lo >= 3:
            heavy = DAYS[loads.index(hi)]
            light = DAYS[loads.index(lo)]
            issues.append(
                f"Class {cls}: heavy load on {heavy} ({hi} subjects) "
                f"vs light on {light} ({lo} subjects) — gap of {hi-lo}"
            )
    return issues


def find_teacher_conflicts(timetable, class_teacher_maps):
    """Find slots where the same teacher is assigned to two classes at once."""
    issues = []
    for d in range(5):
        for s in range(6):
            teacher_cls = {}
            for cls, schedule in timetable.items():
                subj = schedule[d][s]
                tmap = class_teacher_maps.get(cls, {})
                teacher = tmap.get(subj, {}).get("teacher")
                if teacher:
                    teacher_cls.setdefault(teacher, []).append(cls)
            for teacher, clses in teacher_cls.items():
                if len(clses) > 1:
                    issues.append(
                        f"{teacher} is double-booked on {DAYS[d]} period {s+1}: "
                        f"classes {', '.join(clses)}"
                    )
    return issues


def find_subject_spread(timetable):
    """Flag subjects that are clustered on too few days."""
    issues = []
    for cls, schedule in timetable.items():
        subj_days = {}
        for d, day in enumerate(schedule):
            for s in day:
                if s != "FREE":
                    subj_days.setdefault(s, set()).add(d)
        for subj, days in subj_days.items():
            count = sum(1 for d in schedule for s in d if s == subj)
            if count >= 4 and len(days) <= 2:
                issues.append(
                    f"Class {cls}: '{subj}' ({count} periods) only appears on "
                    f"{len(days)} day(s) — spread it across more days"
                )
    return issues


def subject_counts(timetable):
    totals = {}
    for cls, schedule in timetable.items():
        for day in schedule:
            for s in day:
                totals[s] = totals.get(s, 0) + 1
    return totals


def overall_verdict(metrics):
    violations = metrics.get("violations", 0)
    free_slots  = metrics.get("free_slots",  0)
    eval_score  = metrics.get("eval_score",  0)
    if violations == 0 and free_slots <= 4 and eval_score >= 80:
        return "Excellent", "No conflicts, balanced load, all constraints met."
    if violations <= 2 and eval_score >= 60:
        return "Good", "Minor issues only — a few adjustments would make it optimal."
    if violations <= 5:
        return "Needs Work", "Several consecutive-subject violations reduce teaching effectiveness."
    return "Poor", "High number of violations — consider re-running the optimiser."


def build_analysis(timetable, metrics, class_teacher_maps):
    consecutive  = find_consecutive(timetable)
    imbalance    = find_daily_imbalance(timetable)
    conflicts    = find_teacher_conflicts(timetable, class_teacher_maps)
    spread       = find_subject_spread(timetable)
    verdict, reason = overall_verdict(metrics)

    lines = []

    # ── Overall verdict ────────────────────────────────────────────────────
    verdict_icons = {"Excellent": "✅", "Good": "✓", "Needs Work": "⚠", "Poor": "✗"}
    lines.append(f"Overall Quality: {verdict_icons.get(verdict,'·')} {verdict}")
    lines.append(f"Reason: {reason}")
    lines.append("")

    # ── Metrics summary ────────────────────────────────────────────────────
    lines.append("── Metrics ──────────────────────────────")
    lines.append(f"  Evaluator score : {metrics.get('eval_score', '—')}")
    lines.append(f"  Free slots      : {metrics.get('free_slots', '—')}")
    lines.append(f"  Violations      : {metrics.get('violations', '—')} consecutive-subject")
    lines.append(f"  Spread score    : {metrics.get('spread_score', '—')}")
    lines.append(f"  Balance score   : {metrics.get('balance_score', '—')}")
    lines.append("")

    # ── Teacher conflicts (critical) ───────────────────────────────────────
    lines.append("── Teacher Conflicts ────────────────────")
    if conflicts:
        for i, c in enumerate(conflicts, 1):
            lines.append(f"  {i}. {c}")
    else:
        lines.append("  ✓ No teacher double-bookings detected.")
    lines.append("")

    # ── Consecutive violations ─────────────────────────────────────────────
    lines.append("── Consecutive Subject Violations ───────")
    if consecutive:
        for i, c in enumerate(consecutive[:6], 1):   # cap at 6 to stay readable
            lines.append(f"  {i}. {c}")
        if len(consecutive) > 6:
            lines.append(f"  … and {len(consecutive)-6} more.")
        lines.append("")
        lines.append("  Fix: Swap the second occurrence with any different subject")
        lines.append("  in the same day that still meets its weekly quota.")
    else:
        lines.append("  ✓ No consecutive same-subject slots detected.")
    lines.append("")

    # ── Daily load imbalance ───────────────────────────────────────────────
    lines.append("── Daily Load Imbalance ─────────────────")
    if imbalance:
        for i, c in enumerate(imbalance, 1):
            lines.append(f"  {i}. {c}")
        lines.append("")
        lines.append("  Fix: Move 1–2 subjects from the heavy day to the light day,")
        lines.append("  checking teacher availability before swapping.")
    else:
        lines.append("  ✓ Load is well-balanced across all days.")
    lines.append("")

    # ── Subject spread ─────────────────────────────────────────────────────
    lines.append("── Subject Spread ───────────────────────")
    if spread:
        for i, c in enumerate(spread, 1):
            lines.append(f"  {i}. {c}")
    else:
        lines.append("  ✓ All subjects are spread adequately across the week.")
    lines.append("")

    # ── Top 3 action items ─────────────────────────────────────────────────
    all_issues = conflicts + consecutive + imbalance + spread
    lines.append("── Top 3 Action Items ───────────────────")
    if all_issues:
        for i, item in enumerate(all_issues[:3], 1):
            lines.append(f"  {i}. {item}")
    else:
        lines.append("  No significant issues found — timetable is optimal.")

    return "\n".join(lines)


# ── Vercel handler ──────────────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        try:
            length  = int(self.headers.get("Content-Length", 0))
            body    = self.rfile.read(length) if length else b"{}"
            payload = json.loads(body)
        except Exception:
            self._respond({"error": "Invalid JSON body"}, 400)
            return

        timetable          = payload.get("timetable", {})
        metrics            = payload.get("metrics", {})
        class_teacher_maps = payload.get("class_teacher_maps", {})

        if not timetable:
            self._respond({"error": "No timetable provided"}, 400)
            return

        analysis = build_analysis(timetable, metrics, class_teacher_maps)
        self._respond({"analysis": analysis, "model": "rule-based analyser"})

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
