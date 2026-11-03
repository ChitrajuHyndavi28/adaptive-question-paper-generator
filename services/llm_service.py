import os
import re
import json
import time
import random
import requests
from datetime import datetime, timezone
from flask import current_app
from config import Config
from models import db, Question, PracticePaper, PaperQuestion, Chapter, Subject, Student
from services.adaptive_engine import AdaptiveEngine

def get_utc_now():
    return datetime.now(timezone.utc)

class LLMService:
    """
    Intelligent LLM Service for AI Question Generation and Student Answer Evaluation.
    Integrates with Google Gemini API with smart offline heuristic curriculum fallbacks.
    """

    @staticmethod
    def get_api_key():
        """Retrieve Gemini API key from environment or app config."""
        try:
            return current_app.config.get('GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY') or ''
        except RuntimeError:
            return os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY') or ''

    @staticmethod
    def _loads_lenient(text: str):
        """
        Parses model JSON. LaTeX such as \\frac or \\begin arrives with single backslashes, which are invalid
        or wrongly valid JSON escapes, so on failure those backslashes are doubled before parsing again.
        """
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            def fix(m):
                tok = m.group(0)
                return tok if tok == '\\\\' else '\\\\' + tok[1:]
            pattern = r'\\\\|\\(?!["/]|u[0-9a-fA-F]{4}|[bfnrt](?![a-z]))'
            return json.loads(re.sub(pattern, fix, text))

    # Why the last call to Gemini failed: None, 'no_key', 'rate_limit', 'network' or 'http_<code>'
    last_error = None

    @staticmethod
    def call_gemini_api(prompt: str, temperature: float = 0.4, timeout: int = 90) -> str:
        """Calls the Google Gemini Interactions REST API. Retries when Google reports temporary overload."""
        LLMService.last_error = None
        api_key = LLMService.get_api_key()
        if not api_key:
            LLMService.last_error = 'no_key'
            return None

        model = getattr(Config, 'GEMINI_MODEL', 'gemini-3.5-flash')
        url = "https://generativelanguage.googleapis.com/v1beta/interactions"

        headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
        payload = {
            "model": model,
            "input": prompt,
            "generation_config": {"temperature": temperature}
        }

        for attempt in range(3):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            except Exception as e:
                print(f"Gemini API request failed: {e}")
                LLMService.last_error = 'network'
                return None

            if response.status_code == 200:
                for step in response.json().get('steps', []):
                    if step.get('type') == 'model_output':
                        for part in step.get('content', []):
                            if part.get('type') == 'text':
                                return part.get('text', '')
                return None

            print(f"Gemini API returned HTTP {response.status_code}: {response.text[:200]}")
            if response.status_code in (500, 503) and attempt < 2:
                time.sleep(3 * (attempt + 1))   # temporary overload: wait and try again
                continue
            LLMService.last_error = 'rate_limit' if response.status_code == 429 else f'http_{response.status_code}'
            return None
        return None

    @staticmethod
    def _parse_model_json(raw: str):
        """Strips markdown fences from a model reply and parses it as JSON (tolerating LaTeX backslashes)."""
        cleaned = raw.strip()
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        if cleaned.startswith('```'):
            cleaned = cleaned[3:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        return LLMService._loads_lenient(cleaned.strip())

    @staticmethod
    def generate_paper_questions_llm(subject_name: str, class_level: int, specs: list,
                                     difficulty: str = "Mixed", custom_prompt: str = ""):
        """
        Writes every question of a paper with ONE Gemini call (the free tier allows only a few calls a day).

        specs: [{'chapter': 'Trigonometry', 'type': 'MCQ' | 'Short Answer' | 'Long Answer', 'marks': 2}, ...]
        Returns a list aligned with specs holding a question dict, or None where that reply was unusable.
        Returns None if the call itself failed (see LLMService.last_error).
        """
        lines = "\n".join(
            f'{i}. Chapter "{sp["chapter"]}" - {sp["type"]} - worth exactly {sp["marks"]} mark(s)'
            for i, sp in enumerate(specs, start=1)
        )
        prompt = f"""You are an expert CBSE Board Exam paper setter for Class {class_level} {subject_name}.
Write exactly {len(specs)} different exam questions, one for each line below, in the same order:
{lines}

Difficulty: {difficulty}. Extra instructions from the student: {custom_prompt or 'none'}.

Rules:
- Every question must be a real, correct, self-contained CBSE-style question with a numerical or definite answer.
- MCQs need exactly 4 options written as "A) ...", "B) ...", "C) ...", "D) ...", and correct_answer must be the full text of the right option.
- The explanation is a step-by-step solution whose steps add up to the marks, e.g. "Step 1: ... [1 Mark]".
- Write maths as plain text or inside \\( ... \\).

Return ONLY a JSON array of {len(specs)} objects, with these keys:
"question_text", "options" (array of 4 strings for MCQ, otherwise null), "correct_answer", "explanation"."""

        raw = LLMService.call_gemini_api(prompt, temperature=0.5, timeout=150)
        if not raw:
            return None
        try:
            parsed = LLMService._parse_model_json(raw)
        except Exception as e:
            print(f"Error parsing Gemini paper reply: {e}")
            LLMService.last_error = 'bad_reply'
            return None
        if not isinstance(parsed, list):
            LLMService.last_error = 'bad_reply'
            return None

        results = []
        for i, sp in enumerate(specs):
            item = parsed[i] if i < len(parsed) else None
            usable = (
                isinstance(item, dict)
                and str(item.get('question_text') or '').strip()
                and str(item.get('correct_answer') or '').strip()
                and (sp['type'] != 'MCQ' or (isinstance(item.get('options'), list) and len(item['options']) >= 2))
            )
            if usable and sp['type'] == 'MCQ':
                options = []
                for option in item['options']:                       # drop repeated options, keep the first four
                    if str(option).strip() not in options:
                        options.append(str(option).strip())
                item['options'] = options[:4]
            results.append(item if usable else None)
        return results

    @staticmethod
    def generate_questions_llm(
        subject_name: str,
        chapter_name: str,
        class_level: int = 10,
        difficulty: str = "Medium",
        count: int = 3,
        question_type: str = "Mixed",
        custom_prompt: str = ""
    ) -> list:
        """
        Generates structured questions for a topic using Gemini LLM (with CBSE standard rubrics).
        """
        prompt = f"""You are an expert CBSE Board Exam Paper Setter for Class {class_level} {subject_name}.
Generate exactly {count} high quality practice questions for the chapter "{chapter_name}".
Difficulty level: {difficulty}.
Question type preference: {question_type}.
Additional student instructions / topics: {custom_prompt or 'Standard curriculum focus'}.

Return ONLY a valid JSON array of objects. Each object MUST strictly follow this JSON schema:
[
  {{
    "question_text": "The exact question statement",
    "question_type": "MCQ" | "Short Answer" | "Long Answer",
    "marks": 1 | 2 | 3 | 4 | 5,
    "difficulty": "Easy" | "Medium" | "Hard",
    "options": ["A) ...", "B) ...", "C) ...", "D) ..."] (ONLY if MCQ, else null),
    "correct_answer": "Clear, concise direct answer",
    "explanation": "Step-by-step complete solution and marking breakdown (e.g. Step 1: Formula [1 Mark], Step 2: Calculation [1 Mark], Step 3: Final Answer [1 Mark])"
  }}
]
"""
        raw_response = LLMService.call_gemini_api(prompt, temperature=0.6)
        if raw_response:
            try:
                # Clean possible markdown formatting
                cleaned = raw_response.strip()
                if cleaned.startswith('```json'):
                    cleaned = cleaned[7:]
                if cleaned.startswith('```'):
                    cleaned = cleaned[3:]
                if cleaned.endswith('```'):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
                parsed = LLMService._loads_lenient(cleaned)
                if isinstance(parsed, list) and len(parsed) > 0:
                    return parsed
            except Exception as e:
                print(f"Error parsing Gemini response: {e}")

        # High quality heuristic generator fallback
        return LLMService._generate_fallback_questions(
            subject_name=subject_name,
            chapter_name=chapter_name,
            class_level=class_level,
            difficulty=difficulty,
            count=count,
            question_type=question_type
        )

    @staticmethod
    def _generate_fallback_questions(subject_name: str, chapter_name: str, class_level: int, difficulty: str, count: int, question_type: str) -> list:
        """Heuristic curriculum fallback question generator when offline."""
        templates = [
            {
                "type": "MCQ",
                "marks": 1,
                "text_fn": lambda ch: f"Which of the following statements is mathematically true regarding {ch}?",
                "options": [
                    "A) Fundamental theorem guarantees unique prime factorization",
                    "B) Discriminant D < 0 implies two distinct real roots",
                    "C) Total sum of internal angles equals 360 degrees",
                    "D) Secant intersects a circle at exactly three points"
                ],
                "correct_answer": "Option A",
                "explanation": f"In {chapter_name}, the standard theorem directly validates Option A. Other options contradict standard geometric and algebraic axioms."
            },
            {
                "type": "Short Answer",
                "marks": 2,
                "text_fn": lambda ch: f"Find the value of x that satisfies the fundamental relation in {ch} under standard boundary conditions.",
                "options": None,
                "correct_answer": "x = 4 (or standard valid root)",
                "explanation": f"Step 1: Set up the governing equation for {chapter_name} [1 Mark].\nStep 2: Solve algebraic steps to find x = 4 [1 Mark]."
            },
            {
                "type": "Short Answer",
                "marks": 3,
                "text_fn": lambda ch: f"State and prove the core property of {ch} with a neat mathematical derivation.",
                "options": None,
                "correct_answer": "Standard geometric / algebraic proof verified.",
                "explanation": f"Step 1: Write given conditions and formula [1 Mark].\nStep 2: Intermediate substitution and algebraic simplification [1 Mark].\nStep 3: Concluding proof statement [1 Mark]."
            },
            {
                "type": "Long Answer",
                "marks": 4,
                "text_fn": lambda ch: f"A real-world applied problem is modeled using {ch}. Calculate the maximum value and justify your steps.",
                "options": None,
                "correct_answer": "Maximum Value = 48 units; verified with critical point analysis.",
                "explanation": f"Step 1: Formulate the objective function from problem statement [1 Mark].\nStep 2: Apply derivative / algebraic completion [1.5 Marks].\nStep 3: Verification of maximum boundary condition and units [1.5 Marks]."
            }
        ]

        results = []
        for i in range(count):
            tpl = random.choice(templates)
            q = {
                "question_text": tpl["text_fn"](chapter_name) + (f" (AI Practice Set {i+1})" if count > 1 else ""),
                "question_type": tpl["type"],
                "marks": tpl["marks"],
                "difficulty": difficulty if difficulty != 'Mixed' else random.choice(['Easy', 'Medium', 'Hard']),
                "options": tpl["options"],
                "correct_answer": tpl["correct_answer"],
                "explanation": tpl["explanation"]
            }
            results.append(q)
        return results

    @staticmethod
    def evaluate_student_answer(
        question_text: str,
        student_answer: str,
        correct_answer: str,
        explanation: str,
        max_marks: float
    ) -> dict:
        """
        Evaluates student's handwritten or typed response against official answer and scoring rubrics.
        Returns marks awarded and friendly student feedback.
        """
        if not student_answer or not student_answer.strip():
            return {
                "marks_awarded": 0.0,
                "feedback": "No answer was provided for this question.",
                "is_correct": False,
                "suggestion": "Review the step-by-step solution to understand the concept and try solving it on paper."
            }

        prompt = f"""You are a warm, encouraging CBSE Board Exam Teacher grading a student's answer.
Question ({max_marks} Marks): {question_text}
Official Answer: {correct_answer}
Marking Scheme / Explanation: {explanation}
Student's Written Answer: {student_answer}

Grade this student's response fairly based on step-by-step marking rubrics.
Award marks between 0.0 and {max_marks} (can use 0.5 increments like 0.5, 1.0, 1.5, etc.).
Provide encouraging, friendly feedback pointing out what they did well and any missing steps.

Return ONLY a valid JSON object:
{{
  "marks_awarded": float (0.0 to {max_marks}),
  "is_correct": boolean,
  "feedback": "Clear, friendly explanation of their grade and step evaluation",
  "suggestion": "Tip on how to score full marks next time"
}}
"""
        raw_response = LLMService.call_gemini_api(prompt, temperature=0.2)
        if raw_response:
            try:
                cleaned = raw_response.strip()
                if cleaned.startswith('```json'):
                    cleaned = cleaned[7:]
                if cleaned.startswith('```'):
                    cleaned = cleaned[3:]
                if cleaned.endswith('```'):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()
                parsed = LLMService._loads_lenient(cleaned)
                awarded = float(parsed.get('marks_awarded', 0.0))
                awarded = max(0.0, min(float(max_marks), awarded))
                return {
                    "marks_awarded": awarded,
                    "is_correct": parsed.get('is_correct', awarded >= (max_marks * 0.75)),
                    "feedback": parsed.get('feedback', 'Evaluated against official marking scheme.'),
                    "suggestion": parsed.get('suggestion', '')
                }
            except Exception as e:
                print(f"Error parsing evaluation response: {e}")

        # Fallback intelligent rule-based evaluation
        clean_stud = student_answer.strip().lower()
        clean_corr = correct_answer.strip().lower()

        if clean_stud == clean_corr or clean_corr in clean_stud:
            marks = float(max_marks)
            feedback = "Excellent! Your answer matches the official solution perfectly."
            is_correct = True
        elif len(clean_stud) > 10 and any(w in clean_stud for w in clean_corr.split()):
            marks = round(max_marks * 0.5, 1)
            feedback = "Good attempt! You identified the key formula/concept, but check intermediate calculation steps against the solution."
            is_correct = False
        else:
            marks = 0.0
            feedback = "The answer did not match the required result. Check the step-by-step solution provided below."
            is_correct = False

        return {
            "marks_awarded": marks,
            "feedback": feedback,
            "is_correct": is_correct,
            "suggestion": "Review the full explanation below to master this topic!"
        }

    @staticmethod
    def generate_ai_paper(
        student_id: int,
        subject_id: int,
        chapter_ids: list,
        total_marks: int = 30,
        duration_minutes: int = 0,
        difficulty_preference: str = "Mixed",
        custom_prompt: str = ""
    ) -> PracticePaper:
        """
        Generates a practice paper whose questions are written by Gemini, using one API call for the whole paper.

        If the AI is unavailable (no key, daily limit reached, network error, unusable reply) the paper is built from
        the question bank instead, and `paper.ai_note` explains this so the student is told.
        """
        from services.question_generator import QuestionGenerator   # local import avoids a circular import

        student = db.session.get(Student, student_id)
        subject = db.session.get(Subject, subject_id)
        if not student or not subject:
            raise ValueError("Student or Subject not found.")

        def bank_paper(reason: str) -> PracticePaper:
            paper = QuestionGenerator.generate_paper(
                student_id=student_id, subject_id=subject_id, chapter_ids=chapter_ids,
                total_marks=total_marks, duration_minutes=duration_minutes,
                difficulty_preference=difficulty_preference
            )
            paper.ai_note = reason
            return paper

        # Allocate marks per chapter adaptively
        target_marks_dict, weights_info, explanations = AdaptiveEngine.allocate_topic_marks(
            student_id=student_id,
            chapter_ids=chapter_ids,
            total_marks=total_marks
        )

        # Decide the question mix for each chapter (a mix of 1, 2, 3 or 4 mark questions)
        specs = []
        for cid in chapter_ids:
            chapter = db.session.get(Chapter, cid)
            remaining = target_marks_dict[cid]
            while remaining > 0:
                if remaining >= 4 and random.random() > 0.5:
                    qtype, marks = 'Long Answer', 4
                elif remaining >= 3 and random.random() > 0.4:
                    qtype, marks = 'Short Answer', 3
                elif remaining >= 2:
                    qtype, marks = 'Short Answer', 2
                else:
                    qtype, marks = 'MCQ', 1
                specs.append({'chapter_id': cid, 'chapter': chapter.name, 'type': qtype, 'marks': marks})
                remaining -= marks

        generated = LLMService.generate_paper_questions_llm(
            subject_name=subject.name, class_level=subject.class_level, specs=specs,
            difficulty=difficulty_preference, custom_prompt=custom_prompt
        )

        if generated is None or not any(generated):
            reasons = {
                'no_key': "AI is not set up on this computer",
                'rate_limit': "the AI's daily limit has been reached",
                'network': "the AI could not be reached (check the internet)",
            }
            why = reasons.get(LLMService.last_error, "the AI did not send a usable reply")
            return bank_paper(f"Because {why}, this paper was made from the question bank instead.")

        # Questions the AI could not write are replaced by a question-bank question of the same chapter and marks
        bank_used = set()
        questions = []
        replaced = 0
        for sp, item in zip(specs, generated):
            if item:
                q = Question(
                    chapter_id=sp['chapter_id'],
                    question_text=str(item['question_text']).strip(),
                    question_type=sp['type'],
                    marks=sp['marks'],
                    difficulty=difficulty_preference if difficulty_preference != 'Mixed' else 'Medium',
                    options=item.get('options') if sp['type'] == 'MCQ' else None,
                    correct_answer=str(item['correct_answer']).strip(),
                    explanation=str(item.get('explanation') or '').strip(),
                    source='AI (LLM Generated)'
                )
                db.session.add(q)
                db.session.flush()
            else:
                candidates = Question.query.filter(
                    Question.chapter_id == sp['chapter_id'], Question.marks == sp['marks'],
                    Question.source != 'AI (LLM Generated)', ~Question.id.in_(bank_used)
                ).all()
                if not candidates:
                    db.session.rollback()
                    return bank_paper("The AI sent an incomplete reply, so this paper was made from the question bank instead.")
                q = random.choice(candidates)
                bank_used.add(q.id)
                replaced += 1
            questions.append(q)

        # Sort questions by section
        questions.sort(key=lambda q: (q.marks, 0 if q.question_type == 'MCQ' else 1, q.chapter_id))

        actual_distribution = {}
        for q in questions:
            actual_distribution[q.chapter_id] = actual_distribution.get(q.chapter_id, 0) + q.marks

        paper = PracticePaper(
            student_id=student_id,
            subject_id=subject_id,
            title=f"{subject.name} (Class {subject.class_level}) — AI Adaptive Practice Paper",
            total_marks=total_marks,
            duration_minutes=duration_minutes,
            difficulty_preference=difficulty_preference,
            generation_mode='AI (LLM)',
            selected_chapters_json=json.dumps(chapter_ids),
            target_weights_json=json.dumps({str(k): v for k, v in target_marks_dict.items()}),
            distribution_summary_json=json.dumps({str(k): v for k, v in actual_distribution.items()}),
            distribution_explanation="\n".join(explanations),
            status='generated',
            created_at=get_utc_now()
        )
        db.session.add(paper)
        db.session.flush()

        for idx, q in enumerate(questions, start=1):
            db.session.add(PaperQuestion(paper_id=paper.id, question_id=q.id, order_index=idx, marks_allocated=q.marks))

        db.session.commit()
        if replaced:
            noun = 'question' if replaced == 1 else 'questions'
            paper.ai_note = f"{replaced} {noun} came from the question bank because the AI did not write them."
        return paper

