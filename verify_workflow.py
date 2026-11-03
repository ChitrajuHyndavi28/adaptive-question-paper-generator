from app import create_app
from models import db, Student, Subject, Chapter, PracticePaper, TopicPerformance
from services.question_generator import QuestionGenerator
from services.performance_analyzer import PerformanceAnalyzer
from services.adaptive_engine import AdaptiveEngine

app = create_app()
with app.app_context():
    db.create_all()
    from seed_data import seed_database
    seed_database()
    
    student = Student.query.first()
    math_sub = Subject.query.filter_by(name='Mathematics', class_level=10).first()
    chapters = Chapter.query.filter_by(subject_id=math_sub.id).all()
    chapter_ids = [c.id for c in chapters]
    trig_id = [c.id for c in chapters if c.name == 'Trigonometry'][0]
    stat_id = [c.id for c in chapters if c.name == 'Statistics'][0]
    prob_id = [c.id for c in chapters if c.name == 'Probability'][0]

    print("=== STEP 1: Generate Paper 1 (30 Marks, Balanced Baseline) ===")
    paper1 = QuestionGenerator.generate_paper(
        student_id=student.id, subject_id=math_sub.id,
        chapter_ids=chapter_ids, total_marks=30, duration_minutes=60, difficulty_preference='Mixed'
    )
    print(f"Paper 1 ID: #{paper1.id}, Total Marks: {paper1.total_marks}")
    sum1 = sum(pq.marks_allocated for pq in paper1.paper_questions)
    print(f"Paper 1 Question Marks Sum: {sum1}")
    assert sum1 == 30

    print("\n=== STEP 2: Attempt Paper 1 (Simulate Weak in Trigonometry, Average in Statistics, Strong in Probability) ===")
    marks1 = {}
    for pq in paper1.paper_questions:
        if pq.question.chapter_id == trig_id:
            marks1[pq.id] = 0.0 # 0% (Weak)
        elif pq.question.chapter_id == prob_id:
            marks1[pq.id] = float(pq.marks_allocated) # 100% (Strong)
        else:
            marks1[pq.id] = float(pq.marks_allocated) * 0.5 # 50% (Average)
            
    eval_res1 = PerformanceAnalyzer.submit_and_evaluate_paper(paper1.id, marks1)
    print(f"Paper 1 Score: {eval_res1['total_score']}/{eval_res1['total_marks']} ({eval_res1['percentage']}%)")
    for cr in eval_res1['chapter_results']:
        print(f"  - {cr['chapter_name']}: Attempt {cr['attempt_percentage']}%, Mastery {cr['mastery_score']}%, Classification: {cr['classification']}")

    print("\n=== STEP 3: Generate Paper 2 (30 Marks, Adaptive Distribution) ===")
    paper2 = QuestionGenerator.generate_paper(
        student_id=student.id, subject_id=math_sub.id,
        chapter_ids=chapter_ids, total_marks=30, duration_minutes=60, difficulty_preference='Mixed'
    )
    print(f"Paper 2 ID: #{paper2.id}, Total Marks: {paper2.total_marks}")
    sum2 = sum(pq.marks_allocated for pq in paper2.paper_questions)
    print(f"Paper 2 Question Marks Sum: {sum2}")
    assert sum2 == 30

    print("\n=== STEP 4: Distribution Comparison (Paper 1 vs Paper 2) ===")
    p1_dist = paper1.distribution_summary
    p2_dist = paper2.distribution_summary
    for cid in chapter_ids:
        ch = db.session.get(Chapter, cid)
        m1 = p1_dist.get(str(cid), 0)
        m2 = p2_dist.get(str(cid), 0)
        diff = m2 - m1
        diff_str = f"+{diff}" if diff > 0 else f"{diff}"
        print(f"  - {ch.name}: Paper 1 = {m1}M ({(m1/30)*100:.1f}%) --> Paper 2 = {m2}M ({(m2/30)*100:.1f}%) [Diff: {diff_str} Marks]")

    print("\n=== STEP 5: Explanations for Paper 2 ===")
    print(paper2.distribution_explanation)
    print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")
