import json
import random
from datetime import datetime, timezone
from models import db, Question, PracticePaper, PaperQuestion, Chapter, Subject, Student
from services.adaptive_engine import AdaptiveEngine

def get_utc_now():
    return datetime.now(timezone.utc)

class QuestionGenerator:
    """
    Intelligent Question Paper Generation Engine.
    Employs adaptive topic weighting, combinatorial knapsack/backtracking question selection,
    anti-repetition heuristics, and standard board exam section ordering.
    """

    @staticmethod
    def get_recent_question_ids(student_id: int, limit_papers: int = 3) -> set:
        """Finds IDs of questions the student encountered in recent papers to minimize repetition."""
        recent_papers = PracticePaper.query.filter_by(student_id=student_id)\
            .order_by(PracticePaper.created_at.desc()).limit(limit_papers).all()
        
        recent_qids = set()
        for p in recent_papers:
            for pq in p.paper_questions:
                recent_qids.add(pq.question_id)
        return recent_qids

    @staticmethod
    def _rank_questions(questions: list, difficulty_pref: str, recent_qids: set) -> list:
        """
        Ranks candidate questions based on difficulty preference and recency penalty.
        Adds jitter/randomization to provide variety on repeated generations.
        """
        scored = []
        for q in questions:
            score = 0.0
            
            # Difficulty matching score
            if difficulty_pref == 'Easy':
                score += 3.0 if q.difficulty == 'Easy' else (1.5 if q.difficulty == 'Medium' else 0.5)
            elif difficulty_pref == 'Medium':
                score += 3.0 if q.difficulty == 'Medium' else (1.5 if q.difficulty == 'Easy' else 1.0)
            elif difficulty_pref == 'Hard':
                score += 3.0 if q.difficulty == 'Hard' else (1.5 if q.difficulty == 'Medium' else 0.5)
            else: # Mixed
                score += 2.0  # Equal base preference
                
            # Recency penalty
            if q.id in recent_qids:
                score -= 4.0
                
            # Random jitter
            score += random.uniform(0.0, 1.0)
            scored.append((score, q))
            
        scored.sort(key=lambda x: x[0], reverse=True)
        return [q for _, q in scored]

    @staticmethod
    def _find_subset_sum(questions: list, target_marks: int) -> list:
        """
        Backtracking solver to find a subset of distinct questions matching target_marks exactly.
        """
        result = []
        
        def backtrack(index: int, current_sum: int, current_pick: list):
            if current_sum == target_marks:
                result.append(list(current_pick))
                return True
            if current_sum > target_marks or index >= len(questions):
                return False
                
            # Try including questions[index]
            current_pick.append(questions[index])
            if backtrack(index + 1, current_sum + questions[index].marks, current_pick):
                return True
            current_pick.pop()
            
            # Try excluding questions[index]
            if backtrack(index + 1, current_sum, current_pick):
                return True
                
            return False

        backtrack(0, 0, [])
        return result[0] if result else None

    @staticmethod
    def _global_solver(chapter_candidates: dict, target_allocations: dict, total_marks: int) -> list:
        """
        Global backtracking solver if individual chapter exact sums need slight reconciliation.
        Guarantees exact total_marks and minimizes deviation from chapter targets.
        """
        all_questions = []
        for cid, qlist in chapter_candidates.items():
            all_questions.extend(qlist)
            
        # Sort questions
        random.shuffle(all_questions)
        
        best_selection = []
        best_loss = float('inf')
        
        def solve(index, current_marks, current_selection, chapter_counts):
            nonlocal best_selection, best_loss
            
            if current_marks == total_marks:
                # Compute loss = deviation from targets
                loss = 0.0
                for cid, target_m in target_allocations.items():
                    actual_m = chapter_counts.get(cid, 0)
                    loss += (actual_m - target_m) ** 2
                if loss < best_loss:
                    best_loss = loss
                    best_selection = list(current_selection)
                return
                
            if current_marks > total_marks or index >= len(all_questions) or (len(best_selection) > 0 and best_loss == 0):
                return
                
            q = all_questions[index]
            
            # Branch 1: include q
            current_selection.append(q)
            chapter_counts[q.chapter_id] = chapter_counts.get(q.chapter_id, 0) + q.marks
            solve(index + 1, current_marks + q.marks, current_selection, chapter_counts)
            
            # Backtrack
            current_selection.pop()
            chapter_counts[q.chapter_id] -= q.marks
            
            # Branch 2: exclude q
            solve(index + 1, current_marks, current_selection, chapter_counts)

        solve(0, 0, [], {})
        return best_selection

    @staticmethod
    def generate_paper(student_id: int, subject_id: int, chapter_ids: list,
                       total_marks: int = 30, duration_minutes: int = 0, difficulty_preference: str = 'Mixed') -> PracticePaper:
        """
        Generates and saves a complete practice question paper.
        """
        student = db.session.get(Student, student_id)
        if not student:
            raise ValueError(f"Student #{student_id} not found.")
            
        subject = db.session.get(Subject, subject_id)
        if not subject:
            raise ValueError(f"Subject #{subject_id} not found.")
            
        if not chapter_ids:
            raise ValueError("Please select at least one chapter.")
            
        if total_marks <= 0:
            raise ValueError("Total marks must be greater than zero.")
            
        # 1. Fetch available questions for selected chapters
        eligible_questions = Question.query.filter(
            Question.chapter_id.in_(chapter_ids)
        ).all()
        
        if not eligible_questions:
            raise ValueError("No questions found in the question bank for the selected chapters.")
            
        total_bank_marks = sum(q.marks for q in eligible_questions)
        if total_bank_marks < total_marks:
            raise ValueError(
                f"Insufficient question bank inventory. Selected chapters have {len(eligible_questions)} questions "
                f"totaling {total_bank_marks} marks, but {total_marks} marks were requested. "
                f"Please select more chapters or reduce the total marks."
            )

        # 2. Get adaptive mark allocation and rationale
        target_marks_dict, weights_info, explanations = AdaptiveEngine.allocate_topic_marks(
            student_id=student_id,
            chapter_ids=chapter_ids,
            total_marks=total_marks
        )
        
        recent_qids = QuestionGenerator.get_recent_question_ids(student_id)
        
        # 3. Group and rank questions per chapter
        chapter_candidates = {}
        for cid in chapter_ids:
            ch_qs = [q for q in eligible_questions if q.chapter_id == cid]
            ranked = QuestionGenerator._rank_questions(ch_qs, difficulty_preference, recent_qids)
            chapter_candidates[cid] = ranked

        # 4. Attempt per-chapter subset sum selection
        selected_questions = []
        all_chapters_matched = True
        
        for cid in chapter_ids:
            target_m = target_marks_dict[cid]
            candidates = chapter_candidates.get(cid, [])
            subset = QuestionGenerator._find_subset_sum(candidates, target_m)
            if subset:
                selected_questions.extend(subset)
            else:
                all_chapters_matched = False
                break
                
        # 5. If per-chapter exact subset sum failed due to mark granularity, run global solver
        if not all_chapters_matched or sum(q.marks for q in selected_questions) != total_marks:
            selected_questions = QuestionGenerator._global_solver(chapter_candidates, target_marks_dict, total_marks)

        if not selected_questions or sum(q.marks for q in selected_questions) != total_marks:
            raise ValueError(
                f"Could not construct a combination of questions summing exactly to {total_marks} marks "
                f"from the selected chapters. Try selecting another mark total (e.g. 20, 30, 40, 50) or adding more chapters."
            )
            
        # 6. Verify distinct questions
        selected_qids = [q.id for q in selected_questions]
        if len(selected_qids) != len(set(selected_qids)):
            raise ValueError("Duplicate questions detected in generation. Generation aborted.")

        # 7. Order questions by exam section (1 Mark MCQ, 2 Marks SA-I, 3 Marks SA-II, 4-5 Marks LA)
        def sort_key(q):
            type_prio = 0 if q.question_type == 'MCQ' else 1
            return (q.marks, type_prio, q.chapter_id, q.id)
            
        selected_questions.sort(key=sort_key)
        
        # 8. Compute actual distribution summary
        actual_distribution = {}
        for q in selected_questions:
            actual_distribution[q.chapter_id] = actual_distribution.get(q.chapter_id, 0) + q.marks

        # 9. Create PracticePaper record
        paper_title = f"{subject.name} (Class {subject.class_level}) - Adaptive Practice Paper"
        
        paper = PracticePaper(
            student_id=student_id,
            subject_id=subject_id,
            title=paper_title,
            total_marks=total_marks,
            duration_minutes=duration_minutes,
            difficulty_preference=difficulty_preference,
            selected_chapters_json=json.dumps(chapter_ids),
            target_weights_json=json.dumps({str(k): v for k, v in target_marks_dict.items()}),
            distribution_summary_json=json.dumps({str(k): v for k, v in actual_distribution.items()}),
            distribution_explanation="\n".join(explanations),
            status='generated',
            created_at=get_utc_now()
        )
        db.session.add(paper)
        db.session.flush()
        
        # 10. Create PaperQuestion mapping records
        for idx, q in enumerate(selected_questions, start=1):
            pq = PaperQuestion(
                paper_id=paper.id,
                question_id=q.id,
                order_index=idx,
                marks_allocated=q.marks
            )
            db.session.add(pq)
            
        db.session.commit()
        return paper
