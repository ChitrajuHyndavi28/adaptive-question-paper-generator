import pytest
from models import Subject, PracticePaper, TopicPerformance
from services.question_generator import QuestionGenerator
from services.performance_analyzer import PerformanceAnalyzer

def test_performance_evaluation_and_mastery(app, test_student, math_chapters):
    """Test submission evaluation, percentage calculation, and topic mastery classification."""
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
        
        # Prepare marks obtained: Score 100% on Trigonometry, 0% on Statistics, 50% on Probability
        marks_dict = {}
        for pq in paper.paper_questions:
            cid = pq.question.chapter_id
            if cid == math_chapters["Trigonometry"]:
                marks_dict[pq.id] = float(pq.marks_allocated) # 100%
            elif cid == math_chapters["Statistics"]:
                marks_dict[pq.id] = 0.0 # 0%
            else:
                marks_dict[pq.id] = float(pq.marks_allocated) * 0.5 # 50%

        results = PerformanceAnalyzer.submit_and_evaluate_paper(
            paper_id=paper.id,
            marks_dict=marks_dict
        )
        
        assert results['paper_id'] == paper.id
        assert paper.status == 'submitted'
        assert paper.total_score == sum(marks_dict.values())
        
        # Check topic performances updated
        trig_perf = TopicPerformance.query.filter_by(student_id=test_student.id, chapter_id=math_chapters["Trigonometry"]).first()
        stat_perf = TopicPerformance.query.filter_by(student_id=test_student.id, chapter_id=math_chapters["Statistics"]).first()
        prob_perf = TopicPerformance.query.filter_by(student_id=test_student.id, chapter_id=math_chapters["Probability"]).first()
        
        assert trig_perf.status_classification == 'Strong'
        assert trig_perf.mastery_score == 100.0
        assert trig_perf.number_of_attempts == 1
        
        assert stat_perf.status_classification == 'Weak'
        assert stat_perf.mastery_score == 0.0
        assert stat_perf.number_of_attempts == 1
        
        assert prob_perf.status_classification == 'Average'
        assert prob_perf.mastery_score == 50.0

def test_rolling_mastery_smoothing(app, test_student, math_chapters):
    """Test that multiple attempts smooth mastery using alpha=0.6."""
    with app.app_context():
        trig_id = math_chapters["Trigonometry"]
        math_sub = Subject.query.filter_by(name="Mathematics", class_level=10).first()
        
        # Attempt 1: 0% in Trigonometry
        paper1 = QuestionGenerator.generate_paper(
            student_id=test_student.id, subject_id=math_sub.id,
            chapter_ids=[trig_id], total_marks=10, duration_minutes=20, difficulty_preference="Mixed"
        )
        marks1 = {pq.id: 0.0 for pq in paper1.paper_questions}
        PerformanceAnalyzer.submit_and_evaluate_paper(paper1.id, marks1)
        
        perf1 = TopicPerformance.query.filter_by(student_id=test_student.id, chapter_id=trig_id).first()
        assert perf1.mastery_score == 0.0
        assert perf1.number_of_attempts == 1
        
        # Attempt 2: 100% in Trigonometry
        paper2 = QuestionGenerator.generate_paper(
            student_id=test_student.id, subject_id=math_sub.id,
            chapter_ids=[trig_id], total_marks=10, duration_minutes=20, difficulty_preference="Mixed"
        )
        marks2 = {pq.id: float(pq.marks_allocated) for pq in paper2.paper_questions}
        PerformanceAnalyzer.submit_and_evaluate_paper(paper2.id, marks2)
        
        perf2 = TopicPerformance.query.filter_by(student_id=test_student.id, chapter_id=trig_id).first()
        # New mastery = 0.6 * 100 + 0.4 * 0 = 60.0
        assert perf2.mastery_score == 60.0
        assert perf2.status_classification == 'Average'
        assert perf2.number_of_attempts == 2

def test_invalid_mark_out_of_bounds(app, test_student, math_chapters):
    """Test that entering marks greater than allocated marks throws a ValueError."""
    with app.app_context():
        trig_id = math_chapters["Trigonometry"]
        math_sub = Subject.query.filter_by(name="Mathematics", class_level=10).first()
        
        paper = QuestionGenerator.generate_paper(
            student_id=test_student.id, subject_id=math_sub.id,
            chapter_ids=[trig_id], total_marks=10, duration_minutes=20, difficulty_preference="Mixed"
        )
        
        # Enter 99 marks for a 1-mark question
        pq = paper.paper_questions[0]
        invalid_marks = {p.id: 0.0 for p in paper.paper_questions}
        invalid_marks[pq.id] = pq.marks_allocated + 5.0
        
        with pytest.raises(ValueError) as exc_info:
            PerformanceAnalyzer.submit_and_evaluate_paper(paper.id, invalid_marks)
        assert "must be between 0 and" in str(exc_info.value)
