import json

import pytest

from models import Student, Subject, PracticePaper
from services.llm_service import LLMService


@pytest.fixture
def setup(app):
    student = Student.query.filter_by(name="Aarav Sharma").first()
    subject = Subject.query.filter_by(name="Mathematics", class_level=10).first()
    return student.id, subject.id, [c.id for c in subject.chapters]


def _fake_gemini(monkeypatch, reply_for_specs):
    """Replaces the network call; reply_for_specs(prompt) returns the raw text Gemini would send."""
    monkeypatch.setattr(LLMService, 'get_api_key', staticmethod(lambda: 'test-key'))
    monkeypatch.setattr(LLMService, 'call_gemini_api',
                        staticmethod(lambda prompt, temperature=0.4, timeout=90: reply_for_specs(prompt)))


def _good_reply(prompt):
    n = int(prompt.split('Write exactly ')[1].split(' ')[0])
    items = []
    for i in range(n):
        line = [l for l in prompt.splitlines() if l.startswith(f'{i + 1}. Chapter')][0]
        item = {"question_text": f"Real AI question {i + 1} with \\(\\frac{{1}}{{2}}\\)", "correct_answer": "42",
                "explanation": "Step 1: work [1 Mark]", "options": None}
        if ' MCQ ' in line:
            item["options"] = ["A) 1", "B) 2", "C) 3", "D) 4"]
        items.append(item)
    return json.dumps(items).replace('\\\\', '\\')    # raw LaTeX backslashes, as Gemini sends them


def test_ai_paper_uses_one_call_and_exact_marks(app, setup, monkeypatch):
    student_id, subject_id, chapters = setup
    calls = []
    _fake_gemini(monkeypatch, lambda prompt: calls.append(prompt) or _good_reply(prompt))

    paper = LLMService.generate_ai_paper(student_id, subject_id, chapters, total_marks=30)

    assert len(calls) == 1                                           # one request for the whole paper
    assert paper.generation_mode == 'AI (LLM)'
    assert sum(pq.marks_allocated for pq in paper.paper_questions) == 30
    assert all(pq.question.source == 'AI (LLM Generated)' for pq in paper.paper_questions)
    assert all(pq.question.question_text.startswith('Real AI question') for pq in paper.paper_questions)
    assert not getattr(paper, 'ai_note', None)


def test_ai_paper_falls_back_to_bank_when_rate_limited(app, setup, monkeypatch):
    student_id, subject_id, chapters = setup
    monkeypatch.setattr(LLMService, 'get_api_key', staticmethod(lambda: 'test-key'))

    def limited(prompt, temperature=0.4, timeout=90):
        LLMService.last_error = 'rate_limit'
        return None
    monkeypatch.setattr(LLMService, 'call_gemini_api', staticmethod(limited))

    paper = LLMService.generate_ai_paper(student_id, subject_id, chapters, total_marks=30)

    assert sum(pq.marks_allocated for pq in paper.paper_questions) == 30
    assert all(pq.question.source == 'Curriculum Bank' for pq in paper.paper_questions)
    assert "daily limit" in paper.ai_note


def test_unusable_reply_items_are_replaced_from_the_bank(app, setup, monkeypatch):
    student_id, subject_id, chapters = setup

    def half_broken(prompt):
        items = json.loads(_good_reply(prompt).replace('\\', '\\\\'))
        items[0] = {"question_text": ""}                             # unusable
        return json.dumps(items)
    _fake_gemini(monkeypatch, half_broken)

    paper = LLMService.generate_ai_paper(student_id, subject_id, chapters, total_marks=30)

    sources = [pq.question.source for pq in paper.paper_questions]
    assert sum(pq.marks_allocated for pq in paper.paper_questions) == 30
    assert 'AI (LLM Generated)' in sources and 'Curriculum Bank' in sources
    assert "question bank" in paper.ai_note


def test_mcq_options_are_deduplicated_to_four(app, setup, monkeypatch):
    student_id, subject_id, chapters = setup

    def with_extra_option(prompt):
        items = json.loads(_good_reply(prompt).replace('\\', '\\\\'))
        for item in items:
            if item['options']:
                item['options'] = item['options'] + [item['options'][1]]     # model repeats the answer as a 5th option
        return json.dumps(items)
    _fake_gemini(monkeypatch, with_extra_option)
    # With random() = 0 only 2-mark questions are planned, so an odd total always leaves at least one 1-mark MCQ
    monkeypatch.setattr('services.llm_service.random.random', lambda: 0.0)

    paper = LLMService.generate_ai_paper(student_id, subject_id, chapters, total_marks=31)

    mcqs = [pq.question for pq in paper.paper_questions if pq.question.question_type == 'MCQ']
    assert mcqs and all(len(q.options) == 4 and len(set(q.options)) == 4 for q in mcqs)
