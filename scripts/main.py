import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
from fpdf import FPDF

# Constants
CURRENT_QUIZ_URL = "https://www.jsonkeeper.com/b/LLQT"
QUIZ_SUBMISSION_URL = "https://api.jsonserve.com/rJvd7g"
HISTORICAL_QUIZ_URL = "https://api.jsonserve.com/XgAgFJ"
OUTPUT_DIR = "enhanced_outputs"

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_data():
    """Fetches data from endpoints and returns as JSON."""
    try:
        current_quiz = requests.get(CURRENT_QUIZ_URL).json()
        quiz_submission = requests.get(QUIZ_SUBMISSION_URL).json()
        historical_quiz = requests.get(HISTORICAL_QUIZ_URL).json()
        print("Data fetched successfully!")
        return current_quiz, quiz_submission, historical_quiz
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None, None, None

def analyze_current_quiz_data(current_data):
    """Analyzes current quiz data and saves questions to a CSV file."""
    try:
        if 'quiz' in current_data and 'questions' in current_data['quiz']:
            questions = current_data['quiz']['questions']
            df = pd.DataFrame(questions)
            df.to_csv(f"{OUTPUT_DIR}/current_quiz_questions.csv", index=False)
            print("Current quiz analysis saved.")
            return df
        else:
            print("No valid quiz data available.")
            return pd.DataFrame()
    except Exception as e:
        print(f"Error processing current quiz data: {e}")
        return pd.DataFrame()

def analyze_quiz_submission(submission_data):
    """Analyzes the quiz submission data and saves response map to a CSV file."""
    try:
        quiz_details = {
            "Quiz Title": submission_data['quiz']['title'],
            "Topic": submission_data['quiz']['topic'],
            "Score": submission_data['score'],
            "Correct Answers": submission_data['correct_answers'],
            "Incorrect Answers": submission_data['incorrect_answers'],
            "Accuracy (%)": float(submission_data['accuracy'].replace("%", "")),
            "Total Questions": submission_data['quiz']['questions_count']
        }
        print("\nQuiz Submission Details:")
        for key, value in quiz_details.items():
            print(f"{key}: {value}")
        response_map = submission_data.get('response_map', {})
        if response_map:
            pd.DataFrame(list(response_map.items()), columns=["Question ID", "Selected Option ID"]).to_csv(
                f"{OUTPUT_DIR}/response_map.csv", index=False)
            print("Response map saved.")
        else:
            print("No response map found in the submission data.")
    except Exception as e:
        print(f"Error analyzing quiz submission: {e}")

def analyze_historical_data(historical_data):
    """Analyzes historical quiz data and saves the analysis to a CSV file."""
    try:
        topics, scores, correct, incorrect, difficulties = [], [], [], [], []
        for quiz in historical_data:
            topic = quiz['quiz']['topic']
            difficulty = quiz['quiz'].get('difficulty_level', 'Unknown')
            topics.append(topic)
            difficulties.append(difficulty)
            scores.append(quiz['score'])
            correct.append(quiz['correct_answers'])
            incorrect.append(quiz['incorrect_answers'])
        df = pd.DataFrame({
            'topic': topics,
            'difficulty': difficulties,
            'average_score': scores,
            'total_correct': correct,
            'total_incorrect': incorrect
        }).groupby(['topic', 'difficulty']).mean()
        df.to_csv(f"{OUTPUT_DIR}/historical_quiz_analysis.csv")
        print("Historical quiz analysis saved.")
        return df
    except Exception as e:
        print(f"Error analyzing historical data: {e}")
        return pd.DataFrame()

def define_student_persona(historical_df):
    """Defines the student persona based on historical quiz performance."""
    try:
        strengths = historical_df[historical_df['average_score'] > 80].index.tolist()
        weaknesses = historical_df[historical_df['average_score'] < 50].index.tolist()
        learning_style = (
            "Fast Learner" if historical_df['average_score'].mean() > 70
            else "Steady Learner" if historical_df['average_score'].mean() > 50
            else "Needs Focused Attention"
        )
        persona = {
            "Strengths": strengths or ["No notable strengths identified."],
            "Weaknesses": weaknesses or ["No significant weaknesses identified."],
            "Learning Style": learning_style
        }
        with open(f"{OUTPUT_DIR}/student_persona.json", "w") as f:
            json.dump(persona, f, indent=2)
        print("Student persona saved.")
    except Exception as e:
        print(f"Error defining student persona: {e}")

def analyze_performance_gaps(historical_df):
    """Analyzes performance gaps based on historical data."""
    try:
        improvement_topics = historical_df[(historical_df['average_score'] >= 50) & (historical_df['average_score'] < 80)].index.tolist()
        underperforming_topics = historical_df[historical_df['average_score'] < 50].index.tolist()
        gaps = {
            "Improvement Topics": improvement_topics or ["No improvement topics identified."],
            "Underperforming Topics": underperforming_topics or ["No underperforming topics identified."]
        }
        with open(f"{OUTPUT_DIR}/performance_gaps.json", "w") as f:
            json.dump(gaps, f, indent=2)
        print("Performance gaps saved.")
    except Exception as e:
        print(f"Error analyzing performance gaps: {e}")

def generate_recommendations(historical_df):
    """Generates recommendations based on historical quiz data."""
    try:
        recommendations = []
        if not historical_df.empty:
            weak_topics = historical_df[historical_df['average_score'] < 60].index.tolist()
            strong_topics = historical_df[historical_df['average_score'] > 70].index.tolist()
            improvement_topics = historical_df[(historical_df['average_score'] >= 60) & (historical_df['average_score'] <= 70)].index.tolist()
            if weak_topics:
                recommendations.append(f"Focus on these weak topics: {', '.join(weak_topics)}.")
            if strong_topics:
                recommendations.append(f"You excel in these topics: {', '.join(strong_topics)}.")
            if improvement_topics:
                recommendations.append(f"Consider improving these topics: {', '.join(improvement_topics)}.")
        if not recommendations:
            recommendations.append("Data insufficient for specific recommendations. Focus on reviewing all topics evenly.")
        print("\nRecommendations:")
        for rec in recommendations:
            print(f"- {rec}")
        recommendations_output = {"Recommendations": recommendations}
        with open(f"{OUTPUT_DIR}/recommendations.json", "w") as f:
            json.dump(recommendations_output, f, indent=2)
        print(f"Recommendations saved to {OUTPUT_DIR}/recommendations.json.")
    except Exception as e:
        print(f"Error generating recommendations: {e}")

def generate_visualizations(historical_df):
    """Generates visualizations of historical quiz data."""
    try:
        if not historical_df.empty:
            plt.figure(figsize=(12, 7))
            sns.heatmap(historical_df['average_score'].unstack(), annot=True, cmap="coolwarm", fmt=".1f")
            plt.title("Heatmap of Average Scores by Topic and Difficulty")
            plt.ylabel("Topics")
            plt.xlabel("Difficulty Levels")
            plt.tight_layout()
            plt.savefig(f"{OUTPUT_DIR}/heatmap_topic_performance.png")
            print("Visualization saved.")
    except Exception as e:
        print(f"Error generating visualizations: {e}")

if __name__ == "__main__":
    current_quiz, quiz_submission, historical_quiz = fetch_data()
    if current_quiz and quiz_submission and historical_quiz:
        historical_df = analyze_historical_data(historical_quiz)
        current_df = analyze_current_quiz_data(current_quiz)
        analyze_quiz_submission(quiz_submission)
        analyze_performance_gaps(historical_df)
        define_student_persona(historical_df)
        generate_recommendations(historical_df)
        generate_visualizations(historical_df)
    else:
        print("Failed to fetch data.")
