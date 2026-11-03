# Personalized Student Recommendation

A small Python tool that analyses a student's quiz performance (the current quiz, their latest
submission, and their quiz history) and produces a student persona, performance gaps, and
topic-level study recommendations, plus a per-topic accuracy chart.

It was built for a NEET-style biology quiz dataset served as JSON (the assignment's original
endpoints are listed below).

## What it does

- Loads three JSON inputs: the current quiz (questions + options), the latest submission
  (score, accuracy, `response_map` of question id to selected option id), and the historical
  submissions list. Inputs come from URLs or from a local folder (`--data-dir`).
- Checks each answer in the latest submission against the quiz's correct options.
- Aggregates history by topic and difficulty using **accuracy %** (so quizzes of different
  lengths are comparable). Missing difficulty levels are kept as `Unknown`.
- Classifies topics as strong (>= 80%), needs improvement (50-80%) or weak (< 50%), assigns a
  learning style from overall accuracy, and writes recommendations including the next topic to
  attempt.
- Writes everything to an output folder: `report.json`, `student_persona.json`,
  `performance_gaps.json`, `recommendations.json`, `historical_quiz_analysis.csv`,
  `current_quiz_questions.csv`, `response_scoring.csv` and `topic_accuracy.png`.

## Tech stack

Python 3.12, pandas, matplotlib, requests, pytest.

## Setup

```bash
git clone https://github.com/SAMARTHJAISWAL/Personalized-Student-Recommendation.git
cd Personalized-Student-Recommendation
python3.12 -m venv .venv && source .venv/bin/activate   # or: uv venv -p 3.12 .venv
pip install -r requirements-dev.txt                      # requirements.txt if you don't need tests
```

## Usage

Run offline on the bundled sample data:

```bash
python -m recommender --data-dir sample_data --out outputs
```

Run against the URLs (defaults, or override via environment variables, see `.env.example`):

```bash
python -m recommender --out outputs
# legacy entry point, same thing:
python scripts/main.py --out outputs
```

To analyse your own data, put `current_quiz.json`, `quiz_submission.json` and
`historical_quiz.json` in a folder (same shape as the files in `sample_data/`) and pass it with
`--data-dir`. Any missing file is skipped and the report says there is not enough data.

Run the tests:

```bash
python -m pytest -q
```

## Data notes

- Original endpoints: current quiz `https://www.jsonkeeper.com/b/LLQT`, submission
  `https://api.jsonserve.com/rJvd7g`, history `https://api.jsonserve.com/XgAgFJ`.
- As of November 2026 only the jsonkeeper URL still responds; `api.jsonserve.com` no longer
  resolves, so a live run only gets the current quiz and reports "not enough data" for the rest.
- `sample_data/` is **synthetic** (made-up topics and accuracies in the same schema) so the full
  pipeline can be run and tested offline. It is not real student data.

## Project structure

```
recommender/
  analysis.py   pure functions: accuracy parsing, history summary, persona, gaps, recommendations
  data.py       load inputs from URLs (env-overridable) or a local folder
  cli.py        argument parsing, writes CSV/JSON/PNG outputs
scripts/main.py backwards-compatible wrapper around recommender.cli
sample_data/    synthetic inputs for offline runs and tests
tests/          pytest suite (no network)
```

## Limitations

- Recommendations are rule-based thresholds, not a learned model.
- The scoring of individual responses needs the current quiz and the submission to refer to the
  same question ids.
- The real historical data is no longer reachable at its original URL.
