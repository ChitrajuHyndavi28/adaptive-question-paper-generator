import json

from models import db, Student, Subject, Chapter, Question, PracticePaper, PaperQuestion
from services.performance_analyzer import PerformanceAnalyzer


def _new_student():
    student = Student(name="Fresh Student", email="fresh@example.edu", class_level=10)
    db.session.add(student)
    db.session.flush()
    return student


def _paper_with(student, subject, questions, status='generated'):
    paper = PracticePaper(
        student_id=student.id, subject_id=subject.id, title="Test paper",
        total_marks=sum(q.marks for q in questions), selected_chapters_json=json.dumps([]), status=status
    )
    db.session.add(paper)
    db.session.flush()
    for i, q in enumerate(questions, start=1):
        db.session.add(PaperQuestion(paper_id=paper.id, question_id=q.id, order_index=i, marks_allocated=q.marks))
    db.session.commit()
    return paper


def _setup(app):
    subject = Subject.query.filter_by(name="Mathematics", class_level=10).first()
    trig = Chapter.query.filter_by(subject_id=subject.id, name="Trigonometry").first()
    questions = Question.query.filter_by(chapter_id=trig.id, marks=1).limit(3).all()
    return subject, questions


def test_solved_question_is_flagged_in_next_paper(app):
    subject, (q1, q2, q3) = _setup(app)
    student = _new_student()

    first = _paper_with(student, subject, [q1, q2])
    PerformanceAnalyzer.submit_and_evaluate_paper(
        first.id, {pq.id: (1 if pq.question_id == q1.id else 0) for pq in first.paper_questions}
    )

    second = _paper_with(student, subject, [q1, q3])
    previous = PerformanceAnalyzer.get_previous_attempts(second)

    assert set(previous) == {q1.id}                  # only the question solved before
    assert previous[q1.id]['paper_id'] == first.id
    assert previous[q1.id]['obtained'] == 1
    assert previous[q1.id]['available'] == 1


def test_unsubmitted_or_own_paper_does_not_count(app):
    subject, (q1, q2, _) = _setup(app)
    student = _new_student()

    unsolved = _paper_with(student, subject, [q1])                 # generated but never attempted
    candidate = _paper_with(student, subject, [q1, q2])
    assert PerformanceAnalyzer.get_previous_attempts(candidate) == {}
    assert PerformanceAnalyzer.get_previous_attempts(unsolved) == {}


def test_other_students_attempts_are_ignored(app):
    subject, (q1, q2, _) = _setup(app)
    student, other = _new_student(), _new_student()

    theirs = _paper_with(other, subject, [q1])
    PerformanceAnalyzer.submit_and_evaluate_paper(theirs.id, {pq.id: 1 for pq in theirs.paper_questions})

    mine = _paper_with(student, subject, [q1, q2])
    assert PerformanceAnalyzer.get_previous_attempts(mine) == {}


def test_paper_page_shows_previously_solved_tag(app, client):
    subject, (q1, q2, q3) = _setup(app)
    student = _new_student()

    first = _paper_with(student, subject, [q1])
    PerformanceAnalyzer.submit_and_evaluate_paper(first.id, {pq.id: 1 for pq in first.paper_questions})
    repeat = _paper_with(student, subject, [q1, q2])
    fresh = _paper_with(student, subject, [q2, q3])

    client.post('/login', data={'student_id': str(student.id)}, follow_redirects=True)

    page = client.get(f'/paper/{repeat.id}').data
    assert b"Previously solved on" in page
    assert b"1 of 2 questions already solved before" in page

    page = client.get(f'/paper/{fresh.id}').data
    assert b"Previously solved on" not in page
    assert b"questions are new to you" in page

    pdf = client.get(f'/paper/{repeat.id}/pdf')
    assert pdf.status_code == 200 and pdf.data.startswith(b'%PDF-')
