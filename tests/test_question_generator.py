import pytest
from models import Subject, PracticePaper, PaperQuestion
from services.question_generator import QuestionGenerator

def test_generate_paper_exact_marks(app, test_student, math_chapters):
    """Test that generated paper totals EXACTLY the requested marks."""
    with app.app_context():
        chapter_ids = list(math_chapters.values())
        math_sub = Subject.query.filter_by(name="Mathematics", class_level=10).first()
        
        # Test 20 Marks
        paper20 = QuestionGenerator.generate_paper(
            student_id=test_student.id,
            subject_id=math_sub.id,
            chapter_ids=chapter_ids,
            total_marks=20,
            duration_minutes=45,
            difficulty_preference="Mixed"
        )
        assert paper20.total_marks == 20
        actual_sum20 = sum(pq.marks_allocated for pq in paper20.paper_questions)
        assert actual_sum20 == 20
        
        # Test 30 Marks
        paper30 = QuestionGenerator.generate_paper(
            student_id=test_student.id,
            subject_id=math_sub.id,
            chapter_ids=chapter_ids,
            total_marks=30,
            duration_minutes=60,
            difficulty_preference="Mixed"
        )
        assert paper30.total_marks == 30
        actual_sum30 = sum(pq.marks_allocated for pq in paper30.paper_questions)
        assert actual_sum30 == 30

def test_no_duplicate_questions(app, test_student, math_chapters):
    """Test that all questions in a generated paper are distinct."""
    with app.app_context():
        chapter_ids = list(math_chapters.values())
        math_sub = Subject.query.filter_by(name="Mathematics", class_level=10).first()
        
        paper = QuestionGenerator.generate_paper(
            student_id=test_student.id,
            subject_id=math_sub.id,
            chapter_ids=chapter_ids,
            total_marks=30,
            duration_minutes=60,
            difficulty_preference="Mixed"
        )
        
        question_ids = [pq.question_id for pq in paper.paper_questions]
        assert len(question_ids) == len(set(question_ids))

def test_only_selected_chapters_included(app, test_student, math_chapters):
    """Test that questions are pulled ONLY from selected chapters."""
    with app.app_context():
        # Select only Trigonometry
        trig_id = math_chapters["Trigonometry"]
        math_sub = Subject.query.filter_by(name="Mathematics", class_level=10).first()
        
        paper = QuestionGenerator.generate_paper(
            student_id=test_student.id,
            subject_id=math_sub.id,
            chapter_ids=[trig_id],
            total_marks=15,
            duration_minutes=30,
            difficulty_preference="Easy"
        )
        
        for pq in paper.paper_questions:
            assert pq.question.chapter_id == trig_id

def test_invalid_marks_inventory_error(app, test_student, math_chapters):
    """Test that asking for more marks than available in question bank raises clear error."""
    with app.app_context():
        trig_id = math_chapters["Trigonometry"]
        math_sub = Subject.query.filter_by(name="Mathematics", class_level=10).first()
        
        with pytest.raises(ValueError) as exc_info:
            QuestionGenerator.generate_paper(
                student_id=test_student.id,
                subject_id=math_sub.id,
                chapter_ids=[trig_id],
                total_marks=500, # Way above available
                duration_minutes=180,
                difficulty_preference="Mixed"
            )
        assert "Insufficient question bank inventory" in str(exc_info.value)
