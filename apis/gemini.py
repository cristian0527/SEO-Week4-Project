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


def gemini_study_planner(prompt_or_calendar_summary: str, focus: str = "assignments and studying", tone: str = "supportive"):
    """
    Generate study plan using either:
    1. A custom prompt (new way)
    2. Calendar summary with default prompt (old way for backward compatibility)
    """
    
    # Check if it's a custom prompt (contains multiple lines or specific keywords)
    if ("Goal:" in prompt_or_calendar_summary or 
        "IMPORTANT:" in prompt_or_calendar_summary or 
        "## " in prompt_or_calendar_summary or
        len(prompt_or_calendar_summary.split('\n')) > 5):
        # It's a custom prompt, use it directly
        prompt = prompt_or_calendar_summary
    else:
        # It's just calendar summary, use the old default prompt
        prompt = f"""
        You are a helpful AI that curates personalized weekly time management plans, for studying,
        based on user's Google Calendar.

        Instructions:
        - Review the following calendar events
        - Identify open time blocks
        - Suggest an optimized (study) schedule
        - Make sure no conflicts occur with existing events
        - Maintain a {tone} tone

        Focus for this week: {focus}

        Calendar Events: {prompt_or_calendar_summary}

        Please return a bullet-point study plan that's not overwhelming (1-3 suggestions per day based on user's availability), labeled by day of the week
        """

    response = model.generate_content(
        prompt,
        generation_config={
            "temperature": 0.3,  # Lower temperature for more consistent formatting
            "top_p": 0.8
        }
    )

    return response.text.strip()



#def gemini_study_planner(calendar_summary: str, focus: str = "assignments and studying", tone: str = "supportive"):
    #prompt = f"""
    #You are a helpful AI that curates personalized weekly time mangagement plans, for studying,
    #based on user's Google Calendar.

    #Instructions:
    #- Review the following calendar events
    #- Identify open time blocks
    #- Suggest an optimized (study) schedule
    #- Make sure no conflicts occur with existing events
    #- Maintain a {tone} tone

    #Focus for this week: {focus}

    #Calendar Events: {calendar_summary}

    #Please return a bullet-point study plan that's not overwhelming (1-3 suggestions per day based on user's availablility), labeled by day of the week
    #"""

    #response = model.generate_content(
        #prompt,
        #generation_config={
            #"temperature": 0.7,
            #"top_p": 1
        #}
    #)

    #return response.text.strip()
