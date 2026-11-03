import pytest
from models import Subject, TopicPerformance
from services.adaptive_engine import AdaptiveEngine
from services.performance_analyzer import PerformanceAnalyzer
from services.question_generator import QuestionGenerator

def test_initial_balanced_distribution(app, test_student, math_chapters):
    """Test that with no previous attempts, chapters receive a balanced distribution."""
    with app.app_context():
        chapter_ids = list(math_chapters.values())
        total_marks = 30
        
        allocated_marks, weights_info, explanations = AdaptiveEngine.allocate_topic_marks(
            student_id=test_student.id,
            chapter_ids=chapter_ids,
            total_marks=total_marks
        )
        
        assert sum(allocated_marks.values()) == total_marks
        # 3 chapters with 30 marks should each get 10 marks
        for cid in chapter_ids:
            assert allocated_marks[cid] == 10
            assert weights_info[cid]['status'] == 'Unattempted'
            assert weights_info[cid]['multiplier'] == 1.0

def test_adaptive_weak_topic_boost(app, test_student, math_chapters):
    """
    Test adaptive behavior:
    1. Score 0% in Trigonometry (Weak)
    2. Score 100% in Probability (Strong)
    3. Score 50% in Statistics (Average)
    4. Verify that the next paper allocates more marks to Trigonometry and fewer to Probability.
    """
    with app.app_context():
        trig_id = math_chapters["Trigonometry"]
        stat_id = math_chapters["Statistics"]
        prob_id = math_chapters["Probability"]
        chapter_ids = [trig_id, stat_id, prob_id]
        math_sub = Subject.query.filter_by(name="Mathematics", class_level=10).first()
        
        # Paper 1: Attempt
        paper1 = QuestionGenerator.generate_paper(
            student_id=test_student.id, subject_id=math_sub.id,
            chapter_ids=chapter_ids, total_marks=30, duration_minutes=60, difficulty_preference="Mixed"
        )
        marks1 = {}
        for pq in paper1.paper_questions:
            if pq.question.chapter_id == trig_id:
                marks1[pq.id] = 0.0 # 0% -> Weak
            elif pq.question.chapter_id == prob_id:
                marks1[pq.id] = float(pq.marks_allocated) # 100% -> Strong
            else:
                marks1[pq.id] = float(pq.marks_allocated) * 0.5 # 50% -> Average
                
        PerformanceAnalyzer.submit_and_evaluate_paper(paper1.id, marks1)
        
        # Now calculate adaptive allocation for Paper 2
        allocated_marks, weights_info, explanations = AdaptiveEngine.allocate_topic_marks(
            student_id=test_student.id,
            chapter_ids=chapter_ids,
            total_marks=30
        )
        
        # Total must strictly equal 30
        assert sum(allocated_marks.values()) == 30
        
        # Weak topic (Trigonometry) must have the highest mark allocation
        assert allocated_marks[trig_id] > allocated_marks[stat_id]
        assert allocated_marks[trig_id] > allocated_marks[prob_id]
        
        # Strong topic (Probability) must still receive revision questions (> 0 marks, never dropped)
        assert allocated_marks[prob_id] > 0
        assert allocated_marks[prob_id] < allocated_marks[trig_id]
        
        # Verify explanations contain rationale for Trigonometry and Probability
        exp_text = " ".join(explanations)
        assert "Trigonometry" in exp_text
        assert "Remediation Focus" in exp_text
        assert "Retention Revision" in exp_text

def test_paper_generation_with_adapted_weights(app, test_student, math_chapters):
    """Test generating a second paper through QuestionGenerator respects adaptive weights and totals exactly."""
    with app.app_context():
        chapter_ids = list(math_chapters.values())
        math_sub = Subject.query.filter_by(name="Mathematics", class_level=10).first()
        
        # Manually create weak performance in Trigonometry
        perf = TopicPerformance(
            student_id=test_student.id,
            chapter_id=math_chapters["Trigonometry"],
            latest_score_percentage=20.0,
            mastery_score=20.0,
            number_of_attempts=1,
            status_classification='Weak'
        )
        app.extensions['sqlalchemy'].session.add(perf)
        app.extensions['sqlalchemy'].session.commit()
        
        paper = QuestionGenerator.generate_paper(
            student_id=test_student.id,
            subject_id=math_sub.id,
            chapter_ids=chapter_ids,
            total_marks=30,
            duration_minutes=60,
            difficulty_preference="Mixed"
        )
        
        assert paper.total_marks == 30
        actual_sum = sum(pq.marks_allocated for pq in paper.paper_questions)
        assert actual_sum == 30
        
        # Trigonometry should have more marks allocated than equal share (10)
        trig_allocated = sum(pq.marks_allocated for pq in paper.paper_questions if pq.question.chapter_id == math_chapters["Trigonometry"])
        assert trig_allocated >= 12
