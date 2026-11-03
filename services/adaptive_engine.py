import math
from config import Config
from models import db, Chapter, TopicPerformance, PracticePaper

class AdaptiveEngine:
    """
    Deterministic rule-based adaptive learning engine.
    Calculates dynamic topic weighting and integer mark allocations based on student performance.
    """

    @staticmethod
    def get_topic_weights(student_id: int, chapter_ids: list) -> dict:
        """
        Computes the adaptive weight multiplier for each selected chapter.
        
        Rules:
        - Unattempted / New: 1.0x (Balanced base)
        - Weak (<40%): 1.8x (Intensive remediation)
        - Average (40-74%): 1.2x (Active reinforcement)
        - Strong (>=75%): 0.7x (Retention revision - never zero!)
        """
        weights = {}
        for cid in chapter_ids:
            perf = TopicPerformance.query.filter_by(student_id=student_id, chapter_id=cid).first()
            if not perf or perf.number_of_attempts == 0:
                weights[cid] = {
                    'multiplier': Config.WEIGHT_UNATTEMPTED,
                    'status': 'Unattempted',
                    'mastery': None,
                    'attempts': 0
                }
            else:
                mastery = perf.mastery_score
                if mastery < Config.WEAK_THRESHOLD:
                    mult = Config.WEIGHT_WEAK
                    status = 'Weak'
                elif mastery < Config.STRONG_THRESHOLD:
                    mult = Config.WEIGHT_AVERAGE
                    status = 'Average'
                else:
                    mult = Config.WEIGHT_STRONG
                    status = 'Strong'
                    
                weights[cid] = {
                    'multiplier': mult,
                    'status': status,
                    'mastery': round(mastery, 1),
                    'attempts': perf.number_of_attempts
                }
        return weights

    @staticmethod
    def allocate_topic_marks(student_id: int, chapter_ids: list, total_marks: int) -> tuple:
        """
        Converts adaptive weights into integer mark allocations summing EXACTLY to total_marks.
        Uses the Largest Remainder Method (Hare-Niemeyer) for fair integer mark distribution.
        
        Returns:
            (target_marks_dict, weights_dict, explanations_list)
        """
        if not chapter_ids:
            raise ValueError("At least one chapter must be selected.")
        if total_marks <= 0:
            raise ValueError("Total marks must be a positive integer.")
            
        num_chapters = len(chapter_ids)
        weights_info = AdaptiveEngine.get_topic_weights(student_id, chapter_ids)
        
        total_weight = sum(info['multiplier'] for info in weights_info.values())
        
        # Step 1: Guarantee minimum allocation of 1 mark per chapter if total_marks >= num_chapters
        min_mark_per_chapter = 1 if total_marks >= num_chapters else 0
        allocated_marks = {cid: min_mark_per_chapter for cid in chapter_ids}
        remaining_marks = total_marks - (min_mark_per_chapter * num_chapters)
        
        # Step 2: Calculate proportional raw shares from remaining marks
        fractional_parts = []
        for cid in chapter_ids:
            ratio = weights_info[cid]['multiplier'] / total_weight
            raw_share = remaining_marks * ratio
            base_share = int(raw_share)
            remainder = raw_share - base_share
            
            allocated_marks[cid] += base_share
            fractional_parts.append((remainder, cid))
            
        # Step 3: Distribute remaining marks by highest remainder
        current_sum = sum(allocated_marks.values())
        leftover = total_marks - current_sum
        
        # Sort by remainder descending
        fractional_parts.sort(key=lambda x: x[0], reverse=True)
        for i in range(leftover):
            cid = fractional_parts[i % len(fractional_parts)][1]
            allocated_marks[cid] += 1
            
        # Verification check
        assert sum(allocated_marks.values()) == total_marks, "Mark allocation must sum strictly to total_marks!"
        
        # Generate explanations
        explanations = AdaptiveEngine.explain_distribution(student_id, chapter_ids, allocated_marks, weights_info, total_marks)
        
        return allocated_marks, weights_info, explanations

    @staticmethod
    def explain_distribution(student_id: int, chapter_ids: list, allocated_marks: dict, weights_info: dict, total_marks: int) -> list:
        """
        Produces human-readable, auditable rationales for how and why marks are apportioned.
        """
        num_chapters = len(chapter_ids)
        equal_baseline_pct = 100.0 / num_chapters if num_chapters > 0 else 0
        
        explanations = []
        for cid in chapter_ids:
            ch = db.session.get(Chapter, cid)
            ch_name = ch.name if ch else f"Chapter {cid}"
            info = weights_info[cid]
            marks = allocated_marks[cid]
            pct = round((marks / total_marks) * 100.0, 1)
            
            diff_from_baseline = round(pct - equal_baseline_pct, 1)
            diff_str = f"+{diff_from_baseline}%" if diff_from_baseline > 0 else f"{diff_from_baseline}%"
            
            if info['status'] == 'Unattempted':
                reason = (
                    f"**{ch_name}**: Allocated **{marks} marks** ({pct}%). "
                    f"Baseline allocation (no prior attempts recorded). Multiplier: 1.0x."
                )
            elif info['status'] == 'Weak':
                reason = (
                    f"**{ch_name}**: Allocated **{marks} marks** ({pct}%, {diff_str} vs baseline). "
                    f"**Remediation Focus**: Current mastery is **{info['mastery']}%** across {info['attempts']} attempt(s). "
                    f"Weight boosted to **1.8x** to provide extra practice."
                )
            elif info['status'] == 'Average':
                reason = (
                    f"**{ch_name}**: Allocated **{marks} marks** ({pct}%, {diff_str} vs baseline). "
                    f"**Active Reinforcement**: Current mastery is **{info['mastery']}%** across {info['attempts']} attempt(s). "
                    f"Weight set to **1.2x** to strengthen fundamentals."
                )
            else: # Strong
                reason = (
                    f"**{ch_name}**: Allocated **{marks} marks** ({pct}%, {diff_str} vs baseline). "
                    f"**Retention Revision**: Current mastery is **{info['mastery']}%** across {info['attempts']} attempt(s). "
                    f"Weight reduced to **0.7x** to prioritize weaker areas while guaranteeing retention questions."
                )
            explanations.append(reason)
            
        return explanations

    @staticmethod
    def compare_distributions(previous_paper_id: int, new_distribution: dict, total_marks: int) -> dict:
        """
        Compares the previous paper's chapter allocation with the newly generated paper's allocation.
        """
        prev_paper = db.session.get(PracticePaper, previous_paper_id) if previous_paper_id else None
        if not prev_paper or not prev_paper.distribution_summary:
            return {}
            
        prev_dist = prev_paper.distribution_summary
        prev_total = prev_paper.total_marks
        
        comparison = {}
        all_cids = set(int(k) for k in prev_dist.keys()).union(set(new_distribution.keys()))
        
        for cid in all_cids:
            ch = db.session.get(Chapter, cid)
            ch_name = ch.name if ch else f"Chapter {cid}"
            
            prev_m = prev_dist.get(str(cid), prev_dist.get(cid, 0))
            prev_p = round((prev_m / prev_total * 100.0), 1) if prev_total > 0 else 0
            
            new_m = new_distribution.get(cid, new_distribution.get(str(cid), 0))
            new_p = round((new_m / total_marks * 100.0), 1) if total_marks > 0 else 0
            
            change_marks = new_m - prev_m
            change_pct = round(new_p - prev_p, 1)
            
            comparison[cid] = {
                'chapter_name': ch_name,
                'prev_marks': prev_m,
                'prev_pct': prev_p,
                'new_marks': new_m,
                'new_pct': new_p,
                'change_marks': change_marks,
                'change_pct': change_pct
            }
        return comparison
