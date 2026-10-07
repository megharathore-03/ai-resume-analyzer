import os, json, sqlite3, re
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'resume_analyzer.db'
UPLOAD_DIR = BASE_DIR / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024

# Initialize the database when Flask/Gunicorn starts the app.
init_db_called = False


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.execute('''CREATE TABLE IF NOT EXISTS analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        filename TEXT,
        target_role TEXT,
        score INTEGER,
        result_json TEXT NOT NULL
    )''')
    conn.commit(); conn.close()


def extract_pdf(path):
    # First try pypdf.
    from pypdf import PdfReader
    try:
        text = '\n'.join((p.extract_text() or '') for p in PdfReader(str(path)).pages).strip()
        if text:
            return text
    except Exception:
        pass

    # Fallback to PyMuPDF for PDFs where pypdf cannot extract the text cleanly.
    try:
        import fitz
        doc = fitz.open(str(path))
        text = '\n'.join(page.get_text('text') or '' for page in doc).strip()
        doc.close()
        return text
    except Exception as e:
        raise ValueError(f'Could not read this PDF: {e}')


def extract_docx(path):
    from docx import Document
    return '\n'.join(p.text for p in Document(path).paragraphs)


def extract_text(file):
    name = file.filename.lower()
    from werkzeug.utils import secure_filename
    safe_name = secure_filename(file.filename)
    if not safe_name:
        raise ValueError('Invalid file name.')
    path = UPLOAD_DIR / safe_name
    file.save(path)
    try:
        if name.endswith('.pdf'):
            text = extract_pdf(path)
        elif name.endswith('.docx'):
            text = extract_docx(path)
        elif name.endswith('.txt'):
            text = path.read_text(encoding='utf-8', errors='ignore')
        else:
            raise ValueError('Only PDF, DOCX or TXT files are supported.')
    finally:
        try: path.unlink()
        except OSError: pass
    return text


def demo_analysis(resume, jd):
    text = (resume + ' ' + jd).lower()
    skills = ['python','java','javascript','html','css','react','flask','django','sql','mysql','git','github','aws','docker','machine learning','data structures']
    found = [s for s in skills if s in text]
    missing = [s for s in skills if s not in text][:6]
    score = min(95, 45 + len(found) * 4 + (10 if jd else 0))
    return {
        'score': score,
        'summary': 'Your resume has a workable technical foundation. Improve measurable achievements, role-specific keywords and project impact.',
        'strengths': [f'Contains {len(found)} relevant technical skills.' if found else 'Shows a technical profile suitable for entry-level roles.', 'Projects and education can be positioned clearly for ATS screening.', 'Target-role matching can be improved with specific keywords.'],
        'weaknesses': ['Add measurable results to project/experience bullets.', 'Use stronger role-specific keywords from the job description.', 'Keep formatting consistent and concise.'],
        'recommendedJobs': ['Software Developer', 'Python Developer', 'Web Developer'],
        'missingSkills': missing or ['REST APIs','Testing','Git/GitHub'],
        'roadmap': ['Strengthen SQL and Git/GitHub', 'Build one complete full-stack project', 'Practice REST APIs and deployment', 'Prepare role-specific DSA and interview questions']
    }


def call_gemini(resume, jd, target_role):
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        return demo_analysis(resume, jd), True
    import requests
    model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
    prompt = f'''You are an ATS expert and career coach. Analyze this resume for the target role: {target_role or 'General Software Engineering'}.\n\nJob Description:\n{jd or 'Not provided'}\n\nResume:\n{resume}\n\nReturn ONLY valid JSON with keys: score (integer 0-100), summary (string), strengths (array of 3-5 strings), weaknesses (array of 3-5 strings), recommendedJobs (array of 3-5 strings), missingSkills (array of 4-8 strings), roadmap (array of 4-6 strings). Do not use markdown.'''
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}'
    r = requests.post(url, json={'contents':[{'parts':[{'text':prompt}]}], 'generationConfig':{'temperature':0.2}}, timeout=60)
    r.raise_for_status()
    raw = r.json()['candidates'][0]['content']['parts'][0]['text']
    raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw.strip(), flags=re.I|re.S)
    return json.loads(raw), False


@app.route('/')
def index():
    return render_template('index.html')


@app.post('/api/analyze')
def analyze():
    resume = request.form.get('resume_text','').strip()
    jd = request.form.get('job_description','').strip()
    role = request.form.get('target_role','').strip()
    filename = ''
    upload = request.files.get('resume_file')
    if upload and upload.filename:
        filename = upload.filename
        try:
            resume = extract_text(upload).strip()
        except ValueError as e:
            return jsonify(error=str(e)), 400
    if not resume:
        return jsonify(error='Please paste your resume or upload a PDF/DOCX/TXT file.'), 400
    if len(resume) < 80:
        return jsonify(error='Please provide more resume content for a meaningful analysis.'), 400
    try:
        result, demo = call_gemini(resume, jd, role)
        conn = db()
        conn.execute('INSERT INTO analyses(created_at,filename,target_role,score,result_json) VALUES(?,?,?,?,?)',
                     (datetime.now().isoformat(timespec='seconds'), filename, role, int(result.get('score',0)), json.dumps(result)))
        conn.commit(); conn.close()
        return jsonify(result=result, demo_mode=demo)
    except Exception as e:
        return jsonify(error=f'AI analysis failed: {e}'), 502


@app.get('/api/history')
def history():
    conn = db(); rows = conn.execute('SELECT id,created_at,filename,target_role,score FROM analyses ORDER BY id DESC LIMIT 20').fetchall(); conn.close()
    return jsonify(items=[dict(r) for r in rows])


@app.get('/api/history/<int:item_id>')
def history_item(item_id):
    conn = db(); row = conn.execute('SELECT * FROM analyses WHERE id=?',(item_id,)).fetchone(); conn.close()
    if not row: return jsonify(error='Analysis not found'),404
    return jsonify(id=row['id'], created_at=row['created_at'], result=json.loads(row['result_json']))


@app.get('/health')
def health(): return jsonify(status='ok')


# Run once at import time so it also works with Gunicorn/Render.
init_db()

if __name__ == '__main__':
    app.run(debug=True)
