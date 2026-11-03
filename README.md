# Adaptive Question Paper Generator for Students

An intelligent, full-stack, rule-based web application engineered for Class 10 and Class 12 board examination preparation. The system dynamically adapts question distributions to target students' individual weak topics while preserving critical revision questions from strong topics.

Built entirely using local Python, Flask, SQLite, and ReportLab without any paid or external LLM dependencies.

---

## 🌟 Key Features

1. **Deterministic Rule-Based Adaptive Algorithm**:
   - Classifies topics into **Weak (< 40%)**, **Average (40%–74%)**, and **Strong (≥ 75%)** based on real attempt history.
   - Dynamically calculates topic weights: **1.8x** for Weak (remediation), **1.2x** for Average (reinforcement), **0.7x** for Strong (retention revision), and **1.0x** for Unattempted topics.
   - Employs the **Largest Remainder Method (Hare-Niemeyer)** to ensure integer mark allocations strictly equal the requested total paper marks.
   - Smooths progress across multiple attempts using rolling exponential averaging (`Mastery = 0.6 × Latest + 0.4 × Prior`).

2. **Intelligent Paper Generation Engine**:
   - Solves knapsack/backtracking subset sums to select questions matching exact total marks.
   - Enforces curriculum topic constraints, difficulty preferences (Easy, Medium, Hard, Mixed), and recency anti-repetition.
   - Formats papers with standard board exam sections: Section A (1M MCQs), Section B (2M SA), Section C (3M SA), and Section D (4/5M LA).

3. **Attempt & Self-Assessment Workflow**:
   - Enables students to enter their question-wise marks obtained with real-time validation and calculation.
   - Records responses and updates historical topic mastery.

4. **Performance Analytics & Solution Review**:
   - Provides instant post-submission topic-wise breakdowns, solution schemes, and detailed explanations of how the attempt will adjust the next paper's topic distribution.

5. **Printable Board Exam PDF Export**:
   - Uses ReportLab with a multi-pass `NumberedCanvas` to produce formatted, downloadable question papers.

6. **Curriculum Question Bank**:
   - Pre-seeded with authentic CBSE board questions across Trigonometry, Statistics, Probability, and Science.
   - Full filtering and modal interface to create and manage questions.

7. **Student Profile Isolation**:
   - Multi-student support allowing seamless profile switching to verify independent performance tracking.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.13, Flask 3.1, Flask-SQLAlchemy, SQLite
- **PDF Engine**: ReportLab 4.5
- **Frontend**: HTML5, CSS3, Bootstrap 5.3, Bootstrap Icons, Vanilla JavaScript, Chart.js
- **Templating**: Jinja2
- **Testing**: pytest

---

## 📁 Project Architecture

```
Flask/Python/
├── app.py                     # Flask application factory and route handlers
├── config.py                  # Configurable thresholds, weights, and database paths
├── models.py                  # SQLAlchemy models (Student, Subject, Chapter, Question, etc.)
├── seed_data.py               # Comprehensive curriculum question bank seeder
├── requirements.txt           # Python dependency specifications
├── README.md                  # Project documentation and user guide
├── .gitignore                 # Version control ignore rules
├── services/
│   ├── __init__.py
│   ├── adaptive_engine.py     # Deterministic topic weighting and mark allocation
│   ├── question_generator.py  # Knapsack subset sum selection and paper assembly
│   ├── performance_analyzer.py# Score evaluation, topic mastery, and analytics
│   └── pdf_generator.py       # ReportLab PDF creation with two-pass pagination
├── templates/
│   ├── base.html              # Core navigation layout and design system
│   ├── dashboard.html         # Visual analytics, topic mastery charts, and action CTA
│   ├── generate_paper.html    # Interactive generation form with live adaptive preview
│   ├── question_paper.html    # Saved question paper view
│   ├── attempt_paper.html     # Question-wise mark entry and validator
│   ├── results.html           # Performance breakdown, strategy review, and answers
│   ├── history.html           # Attempt history with filters
│   ├── question_bank.html     # Curriculum question repository
│   └── settings.html          # Student profile switcher and algorithm parameters
├── static/
│   ├── css/
│   │   └── style.css          # Custom academic UI styles
│   └── js/
│       ├── dashboard.js       # Chart.js visualization logic
│       └── paper.js           # Live preview and marks validation
└── tests/
    ├── __init__.py
    ├── conftest.py            # Isolated in-memory SQLite pytest fixtures
    ├── test_question_generator.py
    ├── test_performance_analyzer.py
    ├── test_adaptive_engine.py
    ├── test_pdf_generator.py
    └── test_routes.py
```

---

## 🚀 Setup & Execution Instructions (Windows)

### 1. Create and Activate Virtual Environment (Optional / Recommended)
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 2. Install Required Dependencies
```powershell
python -m pip install -r requirements.txt
```

### 3. Run the Automated Test Suite
```powershell
pytest -v
```

### 4. Initialize Database & Launch the Web Application
```powershell
python app.py
```

### 5. Access the Web Application
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🧠 How the Adaptive Algorithm Works (Concrete Example)

Suppose a student attempts a **30-mark** paper on **Class 10 Mathematics** across 3 chapters:
1. **Initial Paper (No History)**:
   - All topics have multiplier `1.0x` (Equal baseline).
   - Allocation: Trigonometry (10M), Statistics (10M), Probability (10M). Total = 30M.

2. **Student Performance on Attempt 1**:
   - **Trigonometry**: 2/10 (20.0%) $\rightarrow$ Classified as **Weak**
   - **Statistics**: 6/10 (60.0%) $\rightarrow$ Classified as **Average**
   - **Probability**: 10/10 (100.0%) $\rightarrow$ Classified as **Strong**

3. **Adaptive Recalculation for Paper 2 (30 Marks)**:
   - Multipliers: Trigonometry (`1.8x`), Statistics (`1.2x`), Probability (`0.7x`).
   - Total Weight Sum = $1.8 + 1.2 + 0.7 = 3.7$.
   - **Trigonometry Target**: $(1.8 / 3.7) \times 30 \approx 14.6 \rightarrow$ **15 Marks** (50.0% share, +16.7% boost).
   - **Statistics Target**: $(1.2 / 3.7) \times 30 \approx 9.7 \rightarrow$ **9 Marks** (30.0% share).
   - **Probability Target**: $(0.7 / 3.7) \times 30 \approx 5.7 \rightarrow$ **6 Marks** (20.0% share, revision preserved).
   - **Total**: $15 + 9 + 6 = \mathbf{30\text{ Marks strictly}}$.

4. **Outcome**: The student receives 50% of their practice in their weak topic (Trigonometry) to build competence, while still revising the strong topic (Probability) to prevent knowledge decay.
