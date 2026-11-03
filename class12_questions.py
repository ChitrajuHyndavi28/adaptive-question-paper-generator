import json
from models import db, Subject, Chapter, Question

INTEGRALS = [
    {
        "text": "The value of ∫ x² dx is:",
        "type": "MCQ", "marks": 1, "diff": "Easy",
        "opts": ["A) x³ + C", "B) x³/3 + C", "C) 2x + C", "D) x²/2 + C"],
        "ans": "B) x³/3 + C",
        "sol": "Using the power rule ∫ xⁿ dx = xⁿ⁺¹/(n+1) + C with n = 2 gives x³/3 + C."
    },
    {
        "text": "∫ sec² x dx is equal to:",
        "type": "MCQ", "marks": 1, "diff": "Easy",
        "opts": ["A) sec x tan x + C", "B) tan x + C", "C) cot x + C", "D) sec x + C"],
        "ans": "B) tan x + C",
        "sol": "d(tan x)/dx = sec² x, so ∫ sec² x dx = tan x + C."
    },
    {
        "text": "The value of ∫₀^π sin x dx is:",
        "type": "MCQ", "marks": 1, "diff": "Medium",
        "opts": ["A) 0", "B) 1", "C) 2", "D) π"],
        "ans": "C) 2",
        "sol": "[-cos x] from 0 to π = -cos π + cos 0 = 1 + 1 = 2."
    },
    {
        "text": "Evaluate: ∫ (3x² + 2x + 1) dx.",
        "type": "Short Answer", "marks": 2, "diff": "Easy",
        "opts": None, "ans": "x³ + x² + x + C",
        "sol": "Step 1: Integrate term by term: ∫3x² dx = x³, ∫2x dx = x², ∫1 dx = x (1 Mark).\nStep 2: Add the constant of integration: x³ + x² + x + C (1 Mark)."
    },
    {
        "text": "Evaluate: ∫ sin² x dx.",
        "type": "Short Answer", "marks": 2, "diff": "Medium",
        "opts": None, "ans": "x/2 - (sin 2x)/4 + C",
        "sol": "Step 1: Use sin² x = (1 - cos 2x)/2 (1 Mark).\nStep 2: ∫(1 - cos 2x)/2 dx = x/2 - (sin 2x)/4 + C (1 Mark)."
    },
    {
        "text": "Evaluate: ∫ x eˣ dx.",
        "type": "Short Answer", "marks": 3, "diff": "Medium",
        "opts": None, "ans": "x eˣ - eˣ + C = eˣ(x - 1) + C",
        "sol": "Step 1: Integrate by parts with u = x, dv = eˣ dx, so du = dx, v = eˣ (1 Mark).\nStep 2: ∫ x eˣ dx = x eˣ - ∫ eˣ dx (1 Mark).\nStep 3: = x eˣ - eˣ + C (1 Mark)."
    },
    {
        "text": "Evaluate: ∫₀¹ x/(1 + x²) dx.",
        "type": "Short Answer", "marks": 3, "diff": "Medium",
        "opts": None, "ans": "(1/2) ln 2",
        "sol": "Step 1: Put t = 1 + x², dt = 2x dx. Limits change from x = 0, 1 to t = 1, 2 (1 Mark).\nStep 2: Integral = (1/2)∫₁² dt/t = (1/2)[ln t]₁² (1 Mark).\nStep 3: = (1/2)(ln 2 - ln 1) = (1/2) ln 2 (1 Mark)."
    },
    {
        "text": "Find the area bounded by the curve y = x², the x-axis and the lines x = 1 and x = 3.",
        "type": "Long Answer", "marks": 4, "diff": "Hard",
        "opts": None, "ans": "26/3 square units",
        "sol": "Step 1: y = x² is non-negative, so Area = ∫₁³ x² dx (1 Mark).\nStep 2: = [x³/3] from 1 to 3 (1 Mark).\nStep 3: = 27/3 - 1/3 (1 Mark).\nStep 4: = 26/3 square units (1 Mark)."
    },
    {
        "text": "Evaluate: ∫₀^(π/2) sin x/(sin x + cos x) dx.",
        "type": "Long Answer", "marks": 5, "diff": "Hard",
        "opts": None, "ans": "π/4",
        "sol": "Step 1: Let I = ∫₀^(π/2) sin x/(sin x + cos x) dx (1 Mark).\nStep 2: Using ∫₀^a f(x) dx = ∫₀^a f(a - x) dx, I = ∫₀^(π/2) cos x/(cos x + sin x) dx (2 Marks).\nStep 3: Adding both, 2I = ∫₀^(π/2) 1 dx = π/2 (1 Mark).\nStep 4: I = π/4 (1 Mark)."
    },
]

MATRICES = [
    {
        "text": "If A is a matrix of order 2 × 3 and B is a matrix of order 3 × 4, then the order of AB is:",
        "type": "MCQ", "marks": 1, "diff": "Easy",
        "opts": ["A) 3 × 3", "B) 2 × 4", "C) 4 × 2", "D) AB is not defined"],
        "ans": "B) 2 × 4",
        "sol": "Columns of A (3) equal rows of B (3), so AB is defined with order (rows of A) × (columns of B) = 2 × 4."
    },
    {
        "text": "The value of the determinant |2 3; 1 4| is:",
        "type": "MCQ", "marks": 1, "diff": "Easy",
        "opts": ["A) 11", "B) 5", "C) -5", "D) 8"],
        "ans": "B) 5",
        "sol": "|a b; c d| = ad - bc = (2)(4) - (3)(1) = 8 - 3 = 5."
    },
    {
        "text": "If A is a square matrix of order 3 with |A| = 4, then |2A| is equal to:",
        "type": "MCQ", "marks": 1, "diff": "Medium",
        "opts": ["A) 8", "B) 16", "C) 32", "D) 64"],
        "ans": "C) 32",
        "sol": "For a square matrix of order n, |kA| = kⁿ|A|. So |2A| = 2³ × 4 = 32."
    },
    {
        "text": "Find the values of x if the determinant |x 2; 3 x| = 10.",
        "type": "Short Answer", "marks": 2, "diff": "Easy",
        "opts": None, "ans": "x = 4 or x = -4",
        "sol": "Step 1: Expand the determinant: x·x - 2·3 = x² - 6 (1 Mark).\nStep 2: x² - 6 = 10 ⇒ x² = 16 ⇒ x = ±4 (1 Mark)."
    },
    {
        "text": "If A = [1 2; 3 4], find A².",
        "type": "Short Answer", "marks": 2, "diff": "Easy",
        "opts": None, "ans": "A² = [7 10; 15 22]",
        "sol": "Step 1: A² = A × A, row-by-column multiplication (1 Mark).\nStep 2: Row 1: [1·1+2·3, 1·2+2·4] = [7, 10]. Row 2: [3·1+4·3, 3·2+4·4] = [15, 22] (1 Mark)."
    },
    {
        "text": "Find the inverse of the matrix A = [2 1; 5 3].",
        "type": "Short Answer", "marks": 3, "diff": "Medium",
        "opts": None, "ans": "A⁻¹ = [3 -1; -5 2]",
        "sol": "Step 1: |A| = 2·3 - 1·5 = 1, which is non-zero so A⁻¹ exists (1 Mark).\nStep 2: adj A = [3 -1; -5 2] (1 Mark).\nStep 3: A⁻¹ = (1/|A|) adj A = [3 -1; -5 2] (1 Mark)."
    },
    {
        "text": "Express the matrix A = [3 5; 1 -1] as the sum of a symmetric and a skew-symmetric matrix.",
        "type": "Short Answer", "marks": 3, "diff": "Medium",
        "opts": None, "ans": "A = [3 3; 3 -1] + [0 2; -2 0]",
        "sol": "Step 1: A' = [3 1; 5 -1]. Symmetric part P = (A + A')/2 = [3 3; 3 -1] (1 Mark).\nStep 2: Skew-symmetric part Q = (A - A')/2 = [0 2; -2 0] (1 Mark).\nStep 3: P + Q = [3 5; 1 -1] = A (1 Mark)."
    },
    {
        "text": "Solve the system x + y = 3 and 2x - y = 0 using the matrix inverse method.",
        "type": "Long Answer", "marks": 4, "diff": "Hard",
        "opts": None, "ans": "x = 1, y = 2",
        "sol": "Step 1: Write AX = B with A = [1 1; 2 -1], X = [x; y], B = [3; 0] (1 Mark).\nStep 2: |A| = -1 - 2 = -3 ≠ 0, so A⁻¹ exists (1 Mark).\nStep 3: A⁻¹ = (1/-3)[-1 -1; -2 1] = [1/3 1/3; 2/3 -1/3] (1 Mark).\nStep 4: X = A⁻¹B = [1; 2], so x = 1, y = 2 (1 Mark)."
    },
    {
        "text": "Solve using Cramer's rule: x + y + z = 6, x - y + z = 2, 2x + y - z = 1.",
        "type": "Long Answer", "marks": 5, "diff": "Hard",
        "opts": None, "ans": "x = 1, y = 2, z = 3",
        "sol": "Step 1: Δ = |1 1 1; 1 -1 1; 2 1 -1| = 6 (1 Mark).\nStep 2: Δx = |6 1 1; 2 -1 1; 1 1 -1| = 6 (1 Mark).\nStep 3: Δy = |1 6 1; 1 2 1; 2 1 -1| = 12 (1 Mark).\nStep 4: Δz = |1 1 6; 1 -1 2; 2 1 1| = 18 (1 Mark).\nStep 5: x = Δx/Δ = 1, y = Δy/Δ = 2, z = Δz/Δ = 3 (1 Mark)."
    },
]


def add_class12_questions():
    """Adds the Class 12 Mathematics questions to any chapter that has none. Safe to call repeatedly."""
    subject = Subject.query.filter_by(class_level=12, name="Mathematics").first()
    if not subject:
        return 0

    sources = {"Integrals and Calculus": INTEGRALS, "Matrices and Determinants": MATRICES}
    added = 0
    for chapter in Chapter.query.filter_by(subject_id=subject.id).all():
        data = sources.get(chapter.name)
        if not data or Question.query.filter_by(chapter_id=chapter.id).first():
            continue
        for q in data:
            db.session.add(Question(
                chapter_id=chapter.id,
                question_text=q["text"],
                question_type=q["type"],
                marks=q["marks"],
                difficulty=q["diff"],
                options_json=json.dumps(q["opts"]) if q["opts"] else None,
                correct_answer=q["ans"],
                explanation=q["sol"]
            ))
            added += 1
    db.session.commit()
    return added
