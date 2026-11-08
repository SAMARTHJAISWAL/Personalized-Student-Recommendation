"""Command-line entry point: ``python -m recommender [--data-dir DIR] [--out DIR]``."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: write PNGs, never open a window
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from . import analysis  # noqa: E402
from .data import load_all  # noqa: E402


def _write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def _plot_topic_accuracy(topic_acc: pd.Series, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, max(3, 0.5 * len(topic_acc) + 1)))
    topic_acc.plot.barh(ax=ax, color="#4C72B0")
    ax.axvline(analysis.WEAK_THRESHOLD, color="#C44E52", ls="--", lw=1, label="weak (<50%)")
    ax.axvline(analysis.STRONG_THRESHOLD, color="#55A868", ls="--", lw=1, label="strong (>=80%)")
    ax.set_xlim(0, 100)
    ax.set_xlabel("Average accuracy (%)")
    ax.set_ylabel("")
    ax.set_title("Accuracy by topic (quiz history)")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def run(data_dir: Path | None, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    data = load_all(data_dir)
    report: dict = {}

    current, submission, history = data["current_quiz"], data["submission"], data["history"]

    if current and "quiz" in current:
        questions = current["quiz"].get("questions", [])
        pd.DataFrame(questions).drop(columns=["options"], errors="ignore").to_csv(
            out_dir / "current_quiz_questions.csv", index=False)
        report["current_quiz"] = {"title": current["quiz"].get("title"),
                                  "questions": len(questions)}
    else:
        questions = []

    if submission:
        report["latest_submission"] = analysis.summarize_submission(submission)
        response_map = submission.get("response_map") or {}
        if response_map and questions:
            scored = analysis.score_responses(questions, response_map)
            scored.to_csv(out_dir / "response_scoring.csv", index=False)
            report["latest_submission"]["responses_checked"] = int(len(scored))
            report["latest_submission"]["responses_correct"] = int(scored["is_correct"].sum())

    summary = analysis.historical_summary(history or [])
    summary.to_csv(out_dir / "historical_quiz_analysis.csv", index=False)
    topic_acc = analysis.topic_accuracy(summary)

    report["persona"] = analysis.student_persona(topic_acc)
    report["performance_gaps"] = analysis.performance_gaps(topic_acc)
    report["recommendations"] = analysis.recommendations(topic_acc)

    _write_json(out_dir / "student_persona.json", report["persona"])
    _write_json(out_dir / "performance_gaps.json", report["performance_gaps"])
    _write_json(out_dir / "recommendations.json", {"recommendations": report["recommendations"]})
    _write_json(out_dir / "report.json", report)
    if not topic_acc.empty:
        _plot_topic_accuracy(topic_acc, out_dir / "topic_accuracy.png")
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Quiz performance analysis and recommendations")
    parser.add_argument("--data-dir", type=Path, default=None,
                        help="Read current_quiz.json / quiz_submission.json / historical_quiz.json "
                             "from this folder instead of the URLs")
    parser.add_argument("--out", type=Path, default=Path("outputs"), help="Output folder")
    args = parser.parse_args(argv)

    report = run(args.data_dir, args.out)
    sub = report.get("latest_submission")
    if sub:
        print(f"\nLatest quiz: {sub['quiz_title']} | accuracy {sub['accuracy']}%")
    p = report["persona"]
    overall = "n/a" if p["overall_accuracy"] is None else f"{p['overall_accuracy']}%"
    print(f"Learning style: {p['learning_style']} (overall {overall})")
    print("Strengths:", ", ".join(p["strengths"]) or "-")
    print("Weaknesses:", ", ".join(p["weaknesses"]) or "-")
    print("\nRecommendations:")
    for rec in report["recommendations"]:
        print(" -", rec)
    print(f"\nOutputs written to {args.out}/")


if __name__ == "__main__":
    main()
