import json
import math
from pathlib import Path

import pandas as pd
import pytest

from recommender import analysis
from recommender.cli import run

SAMPLE = Path(__file__).resolve().parent.parent / "sample_data"


@pytest.mark.parametrize("raw,expected", [("90 %", 90.0), ("66.67%", 66.67), (75, 75.0), (" 12 ", 12.0)])
def test_parse_accuracy(raw, expected):
    assert analysis.parse_accuracy(raw) == pytest.approx(expected)


def test_parse_accuracy_missing_is_nan():
    assert math.isnan(analysis.parse_accuracy(None))
    assert math.isnan(analysis.parse_accuracy(""))


def test_submission_accuracy_falls_back_to_counts():
    assert analysis.submission_accuracy({"correct_answers": 3, "incorrect_answers": 1}) == 75.0


def _sub(topic, acc, difficulty=None):
    return {"quiz": {"topic": topic, "difficulty_level": difficulty}, "score": 0,
            "correct_answers": 0, "incorrect_answers": 0, "accuracy": f"{acc} %"}


def test_historical_summary_keeps_missing_difficulty():
    # Regression: groupby used to drop rows whose difficulty_level was None,
    # which produced an empty analysis for the real assignment data.
    df = analysis.historical_summary([_sub("A", 40), _sub("A", 60), _sub("B", 90, "easy")])
    assert len(df) == 2
    row = df[df.topic == "A"].iloc[0]
    assert row.difficulty == "Unknown"
    assert row.attempts == 2
    assert row.avg_accuracy == pytest.approx(50.0)


def test_historical_summary_empty():
    assert analysis.historical_summary([]).empty


def test_topic_accuracy_is_attempt_weighted():
    df = analysis.historical_summary([_sub("A", 40, "easy"), _sub("A", 40, "easy"), _sub("A", 100, "hard")])
    assert analysis.topic_accuracy(df)["A"] == pytest.approx(60.0)


def test_persona_gaps_and_recommendations():
    acc = pd.Series({"Weak": 30.0, "Mid": 65.0, "Strong": 90.0}).sort_values()
    persona = analysis.student_persona(acc)
    assert persona["strengths"] == ["Strong"]
    assert persona["weaknesses"] == ["Weak"]
    assert persona["learning_style"] == "Steady Learner"
    gaps = analysis.performance_gaps(acc)
    assert gaps == {"underperforming_topics": ["Weak"], "improvement_topics": ["Mid"]}
    recs = analysis.recommendations(acc)
    assert any("Weak" in r for r in recs)
    assert recs[-1].startswith("Next quiz to attempt: Weak")


def test_recommendations_without_data():
    assert "Not enough" in analysis.recommendations(pd.Series(dtype=float))[0]


def test_score_responses():
    questions = [{"id": 1, "topic": "t", "options": [{"id": 10, "is_correct": True}, {"id": 11, "is_correct": False}]},
                 {"id": 2, "topic": "t", "options": [{"id": 20, "is_correct": True}]}]
    scored = analysis.score_responses(questions, {"1": 10, "2": 99, "3": 5})
    assert scored["is_correct"].tolist() == [True, False]


def test_cli_run_on_sample_data(tmp_path):
    report = run(SAMPLE, tmp_path)
    assert report["persona"]["weaknesses"] == ["Human Physiology"]
    assert report["latest_submission"]["responses_correct"] == 2
    for name in ["report.json", "recommendations.json", "student_persona.json",
                 "performance_gaps.json", "historical_quiz_analysis.csv", "topic_accuracy.png"]:
        assert (tmp_path / name).exists(), name
    assert json.loads((tmp_path / "recommendations.json").read_text())["recommendations"]
