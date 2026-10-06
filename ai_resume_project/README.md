# CareerLens AI — AI Resume Analyzer & Career Recommendation System

A B.Tech CSE final-year full-stack project built with **HTML/CSS/JavaScript + Python Flask + SQLite + Gemini API**.

## Features
- Resume upload: PDF, DOCX, TXT
- Resume text analysis
- Target-role / job-description matching
- ATS score
- Strengths and improvement areas
- Recommended job roles
- Missing skills / keywords
- AI learning roadmap
- Analysis history stored in SQLite
- Secure API-key architecture: Gemini key stays on the server in `.env`
- Demo mode works without an API key

## Run in VS Code

1. Install Python 3.10+.
2. Open this folder in VS Code.
3. Create a terminal and run:

```bash
python -m venv .venv
```

Windows PowerShell:
```powershell
.\.venv\Scripts\Activate.ps1
```

Windows CMD:
```cmd
.venv\Scripts\activate
```

4. Install packages:
```bash
pip install -r requirements.txt
```

5. Copy `.env.example` to `.env` and add your Gemini API key:
```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
```

6. Start:
```bash
python app.py
```

7. Open the local address shown by Flask, normally `http://127.0.0.1:5000`.

## Important
Do not put the Gemini API key in HTML or JavaScript. Never commit `.env` to GitHub.

## Suggested final-year extensions
- User authentication with hashed passwords
- MySQL/PostgreSQL instead of SQLite
- Separate user dashboard
- PDF report export
- Resume version comparison
- Job-board API integration
- AI interview question generator
- Admin dashboard
- Skill-learning recommendations
- Deployment with a production WSGI server

## Project structure
```
ai_resume_project/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── resume_analyzer.db       # created automatically
├── uploads/                 # temporary uploaded files
├── templates/
│   └── index.html
└── static/
    ├── style.css
    └── app.js
```
