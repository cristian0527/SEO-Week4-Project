 # 📘 Kairos: Academic Planner with Google Calendar & AI Integration

**Kairos** is an intelligent productivity app that combines Google Calendar integration with AI-powered scheduling to help students and professionals plan their critical moments effectively.

---

## ✨ Features

- **📅 Google Calendar Integration**  
  Two-way sync with your class schedules, assignments, and study sessions.

- *🤖 AI Goal Scheduler** - Gemini AI creates personalized study plans based on your deadlines

- **✅ Task Management** - Tasks automatically sync to Google Calendar

- **🤖 AI-Powered Study Assistant (Gemini API)**  
  Smart study planning, assignment difficulty assessment, and AI-generated note summaries.

- - **🔄 Smart Scheduling** - Handles future dates and multi-day planning

---

# 🚀 Quick Setup

Follow these steps to get Kairos up and running:

1.  **Clone & Install**

    ```bash
    git clone <repository-url>
    cd kairos
    pip install -r requirements.txt
    ```

2.  **Environment Variables**

    Create a `.env` file in the root directory:

    ```env
    GENAI_API_KEY=your_gemini_api_key_here
    GOOGLE_CLIENT_ID=client_id_from_google
    GOOGLE_CLIENT_SECRET=client_secret_from_google
    ```

3.  **Google Calendar API Setup**

    * **Get API Credentials:**
        * Go to [Google Cloud Console](https://console.cloud.google.com/)
        * Create a new project or select an existing one
        * Enable the Google Calendar API
        * Go to `Credentials` → `Create Credentials` → `OAuth 2.0 Client ID`
        * Download the credentials and save as `google_calendar_credentials.json` in the root directory

    * **Configure OAuth:**
        * In Google Cloud Console → `OAuth consent screen`
        * Add test users' emails who will use the app
        * In `Credentials` → `Edit your OAuth client`
        * Add redirect URI: `http://localhost:3000/oauth2callback` (replace with your domain)

4.  **Update Redirect URI**

    In `main.py` line 50, update the redirect URI:

    ```python
    REDIRECT_URI = 'http://your-domain:3000/oauth2callback'  # Replace with your URL
    ```

5.  **Run the App**

    ```bash
    python main.py
    ```
    Visit `http://your-domain:3000`

---

# 🎯 Usage

-- Register/Login - Create an account or sign in
-- Connect Google Calendar - Authorize calendar access, if not connected
-- Add Tasks - Create tasks with due dates (auto-syncs to calendar)
-- Use AI Scheduler - Set goals and let Gemini create study plans
-- Navigate Calendar - View tasks and events across any month

--

## ⚙️ Tech Stack

- **Backend**: Flask, SQLAlchemy  
- **Database**: SQLite  
- **Frontend**: HTML, CSS, Bootstrap  
- **APIs**: Google Calendar API, Gemini API
- **Authentication**: OAuth 2.0, Flask-Bcrypt

---
