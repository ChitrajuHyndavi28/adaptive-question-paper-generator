from datetime import datetime, timezone
from config import Config
from models import db, PracticePaper, PaperQuestion, QuestionResponse, TopicPerformance, Chapter, Subject, Question

def get_utc_now():
    return datetime.now(timezone.utc)

class PerformanceAnalyzer:
    """Service to evaluate student paper submissions and compute topic mastery metrics."""

    @staticmethod
    def classify_score(score_pct: float) -> str:
        """Classify a performance percentage into Weak, Average, or Strong."""
        if score_pct < Config.WEAK_THRESHOLD:
            return 'Weak'
        elif score_pct < Config.STRONG_THRESHOLD:
            return 'Average'
        else:
            return 'Strong'

    @staticmethod
    def submit_and_evaluate_paper(paper_id: int, marks_dict: dict, answers_dict: dict = None, feedback_dict: dict = None) -> dict:
        """
        Processes a student's attempt for a paper.
        
        marks_dict: {paper_question_id: marks_obtained_float}
        answers_dict: {paper_question_id: student_text_answer} (optional)
        feedback_dict: {paper_question_id: feedback_text} (optional)
        """
        paper = db.session.get(PracticePaper, paper_id)
        if not paper:
            raise ValueError(f"Practice paper #{paper_id} not found.")
            
        if paper.status == 'submitted':
            raise ValueError("This paper has already been submitted and evaluated.")

        answers_dict = answers_dict or {}
        feedback_dict = feedback_dict or {}
        
        total_obtained = 0.0
        total_available = 0.0
        
        # Track per-chapter stats for this specific attempt: {chapter_id: {'obtained': 0.0, 'available': 0.0}}
        chapter_attempt_stats = {}
        
        for pq in paper.paper_questions:
            pq_id = pq.id
            if pq_id not in marks_dict:
                raise ValueError(f"Missing marks entry for Question #{pq.order_index}.")
                
            try:
                marks_obtained = float(marks_dict[pq_id])
            except (ValueError, TypeError):
                raise ValueError(f"Invalid marks value for Question #{pq.order_index}. Must be a valid number.")
                
            if marks_obtained < 0 or marks_obtained > pq.marks_allocated:
                raise ValueError(
                    f"Marks for Question #{pq.order_index} must be between 0 and {pq.marks_allocated}. Received: {marks_obtained}"
                )
                
            # Create or update QuestionResponse
            response = QuestionResponse(
                paper_question_id=pq.id,
                student_answer=answers_dict.get(pq_id, ''),
                marks_obtained=marks_obtained,
                feedback=feedback_dict.get(pq_id, ''),
                submitted_at=get_utc_now()
            )
            db.session.add(response)
            
            total_obtained += marks_obtained
            total_available += pq.marks_allocated
            
            # Aggregate per chapter
            cid = pq.question.chapter_id
            if cid not in chapter_attempt_stats:
                chapter_attempt_stats[cid] = {
                    'chapter_name': pq.question.chapter.name,
                    'obtained': 0.0,
                    'available': 0.0
                }
            chapter_attempt_stats[cid]['obtained'] += marks_obtained
            chapter_attempt_stats[cid]['available'] += pq.marks_allocated

        # Calculate overall paper score and percentage
        paper.total_score = round(total_obtained, 2)
        paper.percentage = round((total_obtained / total_available) * 100.0, 2) if total_available > 0 else 0.0
        paper.status = 'submitted'
        paper.submitted_at = get_utc_now()
        
        # Update topic mastery for each chapter attempted
        student_id = paper.student_id
        alpha = Config.MASTERY_ALPHA  # 0.6 smoothing factor
        
        chapter_results = []
        for cid, stats in chapter_attempt_stats.items():
            avail = stats['available']
            obt = stats['obtained']
            attempt_pct = (obt / avail * 100.0) if avail > 0 else 0.0
            
            perf = TopicPerformance.query.filter_by(student_id=student_id, chapter_id=cid).first()
            if not perf:
                perf = TopicPerformance(
                    student_id=student_id,
                    chapter_id=cid,
                    latest_score_percentage=attempt_pct,
                    mastery_score=attempt_pct,
                    total_marks_obtained=obt,
                    total_marks_available=avail,
                    number_of_attempts=1,
                    status_classification=PerformanceAnalyzer.classify_score(attempt_pct)
                )
                db.session.add(perf)
            else:
                # Rolling smoothed update
                previous_mastery = perf.mastery_score
                new_mastery = (alpha * attempt_pct) + ((1.0 - alpha) * previous_mastery)
                
                perf.latest_score_percentage = attempt_pct
                perf.mastery_score = new_mastery
                perf.total_marks_obtained += obt
                perf.total_marks_available += avail
                perf.number_of_attempts += 1
                perf.status_classification = PerformanceAnalyzer.classify_score(new_mastery)
                perf.updated_at = get_utc_now()
                
            chapter_results.append({
                'chapter_id': cid,
                'chapter_name': stats['chapter_name'],
                'marks_obtained': round(obt, 1),
                'marks_allocated': round(avail, 1),
                'attempt_percentage': round(attempt_pct, 1),
                'mastery_score': round(perf.mastery_score, 1),
                'classification': perf.status_classification
            })

        db.session.commit()
        
        return {
            'paper_id': paper.id,
            'total_score': paper.total_score,
            'total_marks': paper.total_marks,
            'percentage': paper.percentage,
            'overall_classification': PerformanceAnalyzer.classify_score(paper.percentage),
            'chapter_results': chapter_results
        }

    @staticmethod
    def get_previous_attempts(paper) -> dict:
        """
        Finds questions in `paper` that the same student already solved in an earlier submitted paper.

        Returns {question_id: {'paper_id', 'date', 'obtained', 'available'}} using the most recent earlier attempt.
        For a paper that is itself submitted, only papers submitted before it count as "earlier".
        """
        question_ids = [pq.question_id for pq in paper.paper_questions]
        if not question_ids:
            return {}

        def naive(dt):
            return dt.replace(tzinfo=None) if dt else None

        cutoff = naive(paper.submitted_at)

        rows = db.session.query(PaperQuestion, PracticePaper, QuestionResponse)\
            .join(PracticePaper, PaperQuestion.paper_id == PracticePaper.id)\
            .join(QuestionResponse, QuestionResponse.paper_question_id == PaperQuestion.id)\
            .filter(
                PracticePaper.student_id == paper.student_id,
                PracticePaper.status == 'submitted',
                PracticePaper.id != paper.id,
                PaperQuestion.question_id.in_(question_ids)
            )\
            .order_by(PracticePaper.submitted_at.asc()).all()

        previous = {}
        for pq, earlier_paper, response in rows:
            if cutoff and naive(earlier_paper.submitted_at) >= cutoff:
                continue
            previous[pq.question_id] = {
                'paper_id': earlier_paper.id,
                'date': earlier_paper.submitted_at.strftime('%d %b %Y'),
                'obtained': round(response.marks_obtained, 1),
                'available': pq.marks_allocated
            }
        return previous

    @staticmethod
    def get_student_topic_summary(student_id: int, subject_id: int = None) -> list:
        """
        Retrieves all chapters for the student's subject, attaching their current
        mastery score, classification, and attempt count.
        """
        query = Chapter.query
        if subject_id:
            query = query.filter_by(subject_id=subject_id)
        chapters = query.all()
        
        summary = []
        for ch in chapters:
            perf = TopicPerformance.query.filter_by(student_id=student_id, chapter_id=ch.id).first()
            if perf and perf.number_of_attempts > 0:
                summary.append({
                    'chapter_id': ch.id,
                    'chapter_name': ch.name,
                    'subject_name': ch.subject.name if ch.subject else '',
                    'class_level': ch.subject.class_level if ch.subject else 10,
                    'mastery_score': round(perf.mastery_score, 1),
                    'latest_score_percentage': round(perf.latest_score_percentage, 1),
                    'total_marks_obtained': perf.total_marks_obtained,
                    'total_marks_available': perf.total_marks_available,
                    'number_of_attempts': perf.number_of_attempts,
                    'status': perf.status_classification,
                    'has_data': True
                })
            else:
                summary.append({
                    'chapter_id': ch.id,
                    'chapter_name': ch.name,
                    'subject_name': ch.subject.name if ch.subject else '',
                    'class_level': ch.subject.class_level if ch.subject else 10,
                    'mastery_score': None,
                    'latest_score_percentage': None,
                    'total_marks_obtained': 0,
                    'total_marks_available': 0,
                    'number_of_attempts': 0,
                    'status': 'Unattempted',
                    'has_data': False
                })
        return summary

    @staticmethod
    def get_student_weakness_analysis(student_id: int) -> list:
        """
        Identifies and provides detailed diagnostic information on topics
        where the student is struggling or scored below the weak threshold.
        """
        topic_summary = PerformanceAnalyzer.get_student_topic_summary(student_id)
        weak_topics = []
        for t in topic_summary:
            if t['has_data'] and t['status'] == 'Weak':
                marks_lost = max(0.0, t['total_marks_available'] - t['total_marks_obtained'])
                weak_topics.append({
                    'chapter_id': t['chapter_id'],
                    'chapter_name': t['chapter_name'],
                    'subject_name': t['subject_name'],
                    'class_level': t['class_level'],
                    'mastery_score': t['mastery_score'],
                    'latest_score_percentage': t['latest_score_percentage'],
                    'attempts': t['number_of_attempts'],
                    'marks_lost': round(marks_lost, 1),
                    'total_marks_available': t['total_marks_available'],
                    'recommendation': f"Prioritize revision on {t['chapter_name']}. You scored {t['latest_score_percentage']}% in recent attempts."
                })
        # Sort by lowest mastery score first
        weak_topics.sort(key=lambda x: x['mastery_score'] if x['mastery_score'] is not None else 0)
        return weak_topics

    @staticmethod
    def get_student_mistakes_log(student_id: int, limit: int = 8) -> list:
        """
        Retrieves specific questions where the student lost marks in past practice tests,
        providing clear mistake identification, student's attempt, and correct solution.
        """
        responses = (
            QuestionResponse.query
            .join(PaperQuestion, QuestionResponse.paper_question_id == PaperQuestion.id)
            .join(PracticePaper, PaperQuestion.paper_id == PracticePaper.id)
            .join(Question, PaperQuestion.question_id == Question.id)
            .filter(PracticePaper.student_id == student_id)
            .filter(PracticePaper.status == 'submitted')
            .filter(QuestionResponse.marks_obtained < PaperQuestion.marks_allocated)
            .order_by(QuestionResponse.submitted_at.desc())
            .limit(limit)
            .all()
        )

        mistakes = []
        for resp in responses:
            pq = resp.paper_question
            q = pq.question
            paper = pq.paper
            marks_lost = pq.marks_allocated - resp.marks_obtained
            mistakes.append({
                'response_id': resp.id,
                'paper_id': paper.id,
                'paper_title': paper.title if hasattr(paper, 'title') else f"Paper #{paper.id}",
                'submitted_at': resp.submitted_at.strftime('%d %b %Y, %H:%M'),
                'chapter_name': q.chapter.name if q.chapter else 'General',
                'question_text': q.question_text,
                'question_type': q.question_type,
                'marks_allocated': pq.marks_allocated,
                'marks_obtained': resp.marks_obtained,
                'marks_lost': round(marks_lost, 1),
                'student_answer': resp.student_answer if resp.student_answer else 'No answer provided / Incorrect selection',
                'correct_answer': q.correct_answer,
                'explanation': q.explanation or 'Review the official formula and step-by-step marking rubric.'
            })
        return mistakes

    @staticmethod
    def get_student_dashboard_metrics(student_id: int) -> dict:
        """Computes comprehensive statistics, identified weaknesses, mistakes, and history for the dashboard."""
        papers = PracticePaper.query.filter_by(student_id=student_id).all()
        total_papers = len(papers)
        submitted_papers = [p for p in papers if p.status == 'submitted']
        
        avg_score = 0.0
        if submitted_papers:
            avg_score = round(sum(p.percentage for p in submitted_papers) / len(submitted_papers), 1)
            
        topic_summary = PerformanceAnalyzer.get_student_topic_summary(student_id)
        attempted_topics = [t for t in topic_summary if t['has_data']]
        
        weak_count = sum(1 for t in attempted_topics if t['status'] == 'Weak')
        average_count = sum(1 for t in attempted_topics if t['status'] == 'Average')
        strong_count = sum(1 for t in attempted_topics if t['status'] == 'Strong')
        
        # Weakness diagnosis
        weak_topics = PerformanceAnalyzer.get_student_weakness_analysis(student_id)
        
        # Mistakes log
        mistakes_log = PerformanceAnalyzer.get_student_mistakes_log(student_id, limit=8)
        
        # Complete recent submitted attempts
        all_attempts = PracticePaper.query.filter_by(student_id=student_id, status='submitted')\
            .order_by(PracticePaper.submitted_at.desc()).all()

        return {
            'total_papers_generated': total_papers,
            'total_attempts_completed': len(submitted_papers),
            'average_score_percentage': avg_score,
            'weak_topics_count': weak_count,
            'average_topics_count': average_count,
            'strong_topics_count': strong_count,
            'topic_summary': topic_summary,
            'weak_topics': weak_topics,
            'mistakes_log': mistakes_log,
            'recent_attempts': all_attempts[:5],
            'all_attempts': all_attempts,
            'latest_attempt': all_attempts[0] if all_attempts else None
        }
