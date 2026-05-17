# Timetable Optimiser — Vercel Deployment

## Project Structure

```
├── api/
│   └── optimise.py        ← Python serverless API route
├── public/
│   └── index.html         ← Frontend (auto-served at /)
├── scheduler/
│   ├── backtracking.py    ← Backtracking + MRV scheduler
│   ├── evaluator.py       ← Scoring functions
│   └── heuristics.py      ← Subject ranking
├── utils/
│   └── constraints.py     ← Teacher / room constraints
├── models/
│   └── class_section.py   ← ClassObj model
├── requirements.txt        ← Python dependencies
└── vercel.json             ← Vercel routing config
```

## How it works

- **Frontend** (`public/index.html`) is served as a static file at `/`
- **Backend** (`api/optimise.py`) runs as a Python serverless function at `/api/optimise`
- Clicking **Re-run optimiser** calls `POST /api/optimise`, which runs the real backtracking scheduler and returns a fresh timetable + metrics as JSON

## Deploy to Vercel

### Option 1 — Vercel CLI (recommended)
```bash
npm i -g vercel
vercel login
vercel --prod
```

### Option 2 — GitHub + Vercel Dashboard
1. Push this folder to a GitHub repo
2. Go to https://vercel.com/new
3. Import the repo
4. Vercel auto-detects `vercel.json` — click **Deploy**

## API

### POST /api/optimise
Runs 5 generations of backtracking and returns the best timetable.

**Response:**
```json
{
  "timetable": {
    "4A": [["CN","ADS","S&UL","MOS","ADS","S&UL"], ...5 days],
    "4B": [...],
    "4C": [...],
    "4D": [...]
  },
  "generation_scores": [112.0, 118.5, 124.2, 115.8, 120.1],
  "best_gen": 2,
  "metrics": {
    "eval_score": 87.4,
    "free_slots": 4,
    "violations": 2,
    "spread_score": 38,
    "balance_score": 36,
    "teacher_score": 18,
    "overall_score": 124.2
  }
}
```

## Notes
- The `timetable_model.pkl` ML model is NOT used on Vercel (300MB limit). The evaluator score alone is used.
- Vercel Python functions have a **10s timeout** on Hobby plan; the optimiser runs 5 generations with 150 attempts each, which fits comfortably.
- On Pro plan you get 60s — you can increase `num_generations` to 10+ in `api/optimise.py`.
