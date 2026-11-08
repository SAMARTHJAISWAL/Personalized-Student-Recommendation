"""Pure analysis functions: no network, no file I/O.

All scores are expressed as accuracy percentages (0-100) so that thresholds
mean the same thing regardless of how many questions a quiz had.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping

import pandas as pd

STRONG_THRESHOLD = 80.0
WEAK_THRESHOLD = 50.0
UNKNOWN = "Unknown"


def parse_accuracy(value: Any) -> float:
    """Turn values like ``"90 %"``, ``"90%"``, ``90`` or ``None`` into a float."""
    if value is None:
        return float("nan")
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace("%", "").strip()
    return float(text) if text else float("nan")


def _clean_label(value: Any) -> str:
    if value is None:
        return UNKNOWN
    text = str(value).strip()
    return text if text else UNKNOWN


def submission_accuracy(submission: Mapping[str, Any]) -> float:
    """Accuracy of one submission, falling back to correct / (correct + incorrect)."""
    acc = parse_accuracy(submission.get("accuracy"))
    if acc == acc:  # not NaN
        return acc
    correct = float(submission.get("correct_answers") or 0)
    incorrect = float(submission.get("incorrect_answers") or 0)
    attempted = correct + incorrect
    return 100.0 * correct / attempted if attempted else float("nan")


def summarize_submission(submission: Mapping[str, Any]) -> dict[str, Any]:
    quiz = submission.get("quiz", {}) or {}
    return {
        "quiz_title": quiz.get("title"),
        "topic": _clean_label(quiz.get("topic")),
        "score": submission.get("score"),
        "correct_answers": submission.get("correct_answers"),
        "incorrect_answers": submission.get("incorrect_answers"),
        "accuracy": submission_accuracy(submission),
        "total_questions": quiz.get("questions_count"),
    }


def historical_summary(history: Iterable[Mapping[str, Any]]) -> pd.DataFrame:
    """Average accuracy per (topic, difficulty) across past submissions.

    Missing difficulty levels are labelled ``"Unknown"`` instead of being
    dropped (``groupby`` silently discards ``None`` keys).
    """
    rows = []
    for sub in history:
        quiz = sub.get("quiz", {}) or {}
        rows.append(
            {
                "topic": _clean_label(quiz.get("topic")),
                "difficulty": _clean_label(quiz.get("difficulty_level")),
                "accuracy": submission_accuracy(sub),
                "score": float(sub.get("score") or 0),
                "correct_answers": float(sub.get("correct_answers") or 0),
                "incorrect_answers": float(sub.get("incorrect_answers") or 0),
            }
        )
    columns = ["topic", "difficulty", "attempts", "avg_accuracy", "avg_score",
               "avg_correct", "avg_incorrect"]
    if not rows:
        return pd.DataFrame(columns=columns)
    df = pd.DataFrame(rows)
    out = (
        df.groupby(["topic", "difficulty"], dropna=False)
        .agg(
            attempts=("accuracy", "size"),
            avg_accuracy=("accuracy", "mean"),
            avg_score=("score", "mean"),
            avg_correct=("correct_answers", "mean"),
            avg_incorrect=("incorrect_answers", "mean"),
        )
        .reset_index()
    )
    return out[columns]


def topic_accuracy(summary: pd.DataFrame) -> pd.Series:
    """Attempt-weighted accuracy per topic (difficulty collapsed)."""
    if summary.empty:
        return pd.Series(dtype=float)
    weighted = summary["avg_accuracy"] * summary["attempts"]
    totals = weighted.groupby(summary["topic"]).sum() / summary.groupby("topic")["attempts"].sum()
    return totals.sort_values()


def score_responses(questions: Iterable[Mapping[str, Any]],
                    response_map: Mapping[Any, Any]) -> pd.DataFrame:
    """Mark each answered question correct/incorrect using the quiz's options."""
    by_id = {str(q["id"]): q for q in questions}
    rows = []
    for qid, option_id in response_map.items():
        q = by_id.get(str(qid))
        if q is None:
            continue
        correct_ids = {str(o["id"]) for o in q.get("options", []) if o.get("is_correct")}
        rows.append(
            {
                "question_id": int(qid) if str(qid).isdigit() else qid,
                "topic": _clean_label(q.get("topic")),
                "difficulty": _clean_label(q.get("difficulty_level")),
                "selected_option_id": option_id,
                "is_correct": str(option_id) in correct_ids,
            }
        )
    return pd.DataFrame(rows, columns=["question_id", "topic", "difficulty",
                                       "selected_option_id", "is_correct"])


def student_persona(topic_acc: pd.Series) -> dict[str, Any]:
    strengths = topic_acc[topic_acc >= STRONG_THRESHOLD].index.tolist()
    weaknesses = topic_acc[topic_acc < WEAK_THRESHOLD].index.tolist()
    mean = float(topic_acc.mean()) if len(topic_acc) else float("nan")
    if mean != mean:
        style = "Not enough data"
    elif mean >= 70:
        style = "Fast Learner"
    elif mean >= WEAK_THRESHOLD:
        style = "Steady Learner"
    else:
        style = "Needs Focused Attention"
    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "overall_accuracy": None if mean != mean else round(mean, 1),
        "learning_style": style,
    }


def performance_gaps(topic_acc: pd.Series) -> dict[str, list[str]]:
    return {
        "underperforming_topics": topic_acc[topic_acc < WEAK_THRESHOLD].index.tolist(),
        "improvement_topics": topic_acc[
            (topic_acc >= WEAK_THRESHOLD) & (topic_acc < STRONG_THRESHOLD)
        ].index.tolist(),
    }


def recommendations(topic_acc: pd.Series) -> list[str]:
    if topic_acc.empty:
        return ["Not enough quiz history for specific recommendations. "
                "Attempt a few quizzes across topics first."]
    gaps = performance_gaps(topic_acc)
    persona = student_persona(topic_acc)
    recs = []
    if gaps["underperforming_topics"]:
        recs.append("Revise fundamentals first: " + ", ".join(gaps["underperforming_topics"]) + ".")
    if gaps["improvement_topics"]:
        recs.append("Practise more questions in: " + ", ".join(gaps["improvement_topics"]) + ".")
    if persona["strengths"]:
        recs.append("Keep these sharp with occasional mixed tests: "
                    + ", ".join(persona["strengths"]) + ".")
    weakest = topic_acc.index[0]
    recs.append(f"Next quiz to attempt: {weakest} (lowest accuracy, "
                f"{topic_acc.iloc[0]:.1f}%).")
    return recs
