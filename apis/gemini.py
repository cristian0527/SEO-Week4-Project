import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load Gemini API key from .env
load_dotenv()
my_api_key = os.getenv('GENAI_API_KEY')

if not my_api_key:
    raise ValueError("GENAI_API_KEY not found in .env")

genai.configure(api_key=my_api_key)
model = genai.GenerativeModel("gemini-2.5-flash")

def gemini_study_planner(calendar_summary: str, focus: str = "assignments and studying", tone: str = "supportive"):
    prompt = f"""
    You are a helpful AI that curates personalized weekly time mangagement plans, for studying,
    based on user's Google Calendar.

    Instructions:
    - Review the following calendar events
    - Identify open time blocks
    - Suggest an optimized (study) schedule
    - Make sure no conflicts occur with existing events
    - Maintain a {tone} tone

    Focus for this week: {focus}

    Calendar Events: {calendar_summary}

    Please return a bullet-point study plan that's not overwhelming (1-3 suggestions per day based on user's availablility), labeled by day of the week
    """

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.7,
            "top_p": 1
        }
    )

    return response.text.strip()
