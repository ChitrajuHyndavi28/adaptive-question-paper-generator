import os
import json
from datetime import datetime, timezone
from flask import (
    Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session
)
from config import Config
from models import db, Student, Subject, Chapter, Question, PracticePaper, PaperQuestion, QuestionResponse, TopicPerformance
from seed_data import seed_database
from class12_questions import add_class12_questions
from services.performance_analyzer import PerformanceAnalyzer
from services.adaptive_engine import AdaptiveEngine
from services.question_generator import QuestionGenerator
from services.pdf_generator import PDFGenerator
from services.llm_service import LLMService

def get_utc_now():
    return datetime.now(timezone.utc)

def create_app(config_class=Config):
    """Application factory for Flask app."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure instance folder exists
    os.makedirs(os.path.join(app.root_path, 'instance'), exist_ok=True)

    db.init_app(app)

    @app.before_request
    def ensure_current_student():
        """
        Ensure unauthenticated requests are redirected to /login.
        The Login page is the first landing page when unauthenticated.
        """
        public_endpoints = {'login', 'auth_google', 'static'}
        if request.endpoint in public_endpoints or (request.endpoint and request.endpoint.startswith('static')):
            return
            
        student_id = session.get('student_id')
        if not student_id:
            return redirect(url_for('login'))
            
        student = db.session.get(Student, student_id)
        if not student:
            session.pop('student_id', None)
            return redirect(url_for('login'))

    @app.context_processor
    def inject_globals():
        """Inject current student, system constants, and Google OAuth Client ID into all templates."""
        student_id = session.get('student_id')
        current_student = db.session.get(Student, student_id) if student_id else None
        all_students = Student.query.all()
        return {
            'current_student': current_student,
            'all_students': all_students,
            'google_client_id': app.config.get('GOOGLE_CLIENT_ID', 'demo-google-client-id.apps.googleusercontent.com'),
            'has_gemini_key': bool(app.config.get('GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')),
            'now': get_utc_now()
        }

    # =========================================================================
    # AUTHENTICATION ROUTES (Google Auth & Profile Switcher)
    # =========================================================================

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Student login with Google Sign-In and 1-tap profile selection."""
        # If user is already logged in and not explicitly requesting to switch, redirect to dashboard
        if request.method == 'GET' and session.get('student_id') and not request.args.get('switch'):
            student = db.session.get(Student, session['student_id'])
            if student:
                return redirect(url_for('dashboard'))

        if request.method == 'POST':
            student_id = request.form.get('student_id')
            if student_id:
                student = db.session.get(Student, int(student_id))
                if student:
                    session['student_id'] = student.id
                    flash(f'Welcome back, {student.name}!', 'success')
                    return redirect(url_for('dashboard'))

        all_students = Student.query.all()
        return render_template('login.html', all_students=all_students)

    @app.route('/auth/google', methods=['POST'])
    def auth_google():
        """
        Handles Google Authentication.
        Receives Google OAuth profile, GIS credential JWT, or verified Google payload.
        """
        try:
            import base64
            data = request.get_json(silent=True) or request.form
            
            email = (data.get('email') or '').strip().lower()
            name = (data.get('name') or '').strip()
            avatar_url = (data.get('avatar_url') or '').strip()
            google_id = (data.get('google_id') or '').strip()
            class_level = int(data.get('class_level', 10))

            # Decode Google Identity Services (GIS) Credential JWT if provided
            cred = data.get('credential')
            if cred and isinstance(cred, str) and '.' in cred:
                try:
                    payload_b64 = cred.split('.')[1]
                    payload_b64 += '=' * (-len(payload_b64) % 4)
                    jwt_data = json.loads(base64.urlsafe_b64decode(payload_b64).decode('utf-8'))
                    email = jwt_data.get('email', email).strip().lower()
                    name = jwt_data.get('name', name).strip()
                    avatar_url = jwt_data.get('picture', avatar_url).strip()
                    google_id = jwt_data.get('sub', google_id).strip()
                except Exception:
                    pass

            if not email:
                email = 'student.cbse@gmail.com'
                name = name or 'Aarav Sharma (Google)'

            if not name:
                name = email.split('@')[0].replace('.', ' ').title()

            student = Student.query.filter(
                (Student.email == email) | 
                (Student.google_id == google_id if google_id else False)
            ).first()

            if not student:
                student = Student(
                    name=name,
                    email=email,
                    avatar_url=avatar_url or f"https://api.dicebear.com/7.x/bottts/svg?seed={name}",
                    google_id=google_id,
                    is_google_user=True,
                    class_level=class_level
                )
                db.session.add(student)
                db.session.commit()
            else:
                student.name = name
                student.is_google_user = True
                if avatar_url:
                    student.avatar_url = avatar_url
                if google_id:
                    student.google_id = google_id
                db.session.commit()

            session['student_id'] = student.id
            
            if request.is_json:
                return jsonify({'success': True, 'redirect_url': url_for('dashboard')})
            
            flash(f'Successfully signed in with Google as {student.name}!', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            if request.is_json:
                return jsonify({'success': False, 'error': str(e)}), 400
            flash(f'Google Sign-In failed: {str(e)}', 'danger')
            return redirect(url_for('login'))

    @app.route('/logout')
    def logout():
        """Clears student session and redirects to login."""
        session.clear()
        flash('You have been signed out successfully.', 'info')
        return redirect(url_for('login'))

    # =========================================================================
    # CORE DASHBOARD & PAPER WORKFLOW ROUTES
    # =========================================================================

    @app.route('/')
    def dashboard():
        """Student dashboard displaying analytics, mastery levels, and recommendations."""
        student_id = session.get('student_id')
        if not student_id:
            student = Student.query.first()
            if not student:
                return redirect(url_for('login'))
            session['student_id'] = student.id
            student_id = student.id

        metrics = PerformanceAnalyzer.get_student_dashboard_metrics(student_id)
        
        chart_labels = []
        chart_mastery = []
        chart_colors = []
        
        for t in metrics['topic_summary']:
            chart_labels.append(t['chapter_name'])
            m_score = t['mastery_score'] if t['mastery_score'] is not None else 0.0
            chart_mastery.append(m_score)
            
            if t['status'] == 'Weak':
                chart_colors.append('#EF4444')
            elif t['status'] == 'Average':
                chart_colors.append('#F59E0B')
            elif t['status'] == 'Strong':
                chart_colors.append('#10B981')
            else:
                chart_colors.append('#94A3B8')

        trend_papers = PracticePaper.query.filter_by(student_id=student_id, status='submitted')\
            .order_by(PracticePaper.submitted_at.asc()).all()
            
        trend_dates = [p.submitted_at.strftime('%d %b') if p.submitted_at else p.created_at.strftime('%d %b') for p in trend_papers]
        trend_scores = [p.percentage for p in trend_papers]

        status_order = {'Weak': 0, 'Average': 1, 'Unattempted': 2, 'Strong': 3}
        chapters_sorted = sorted(metrics['topic_summary'], key=lambda t: status_order.get(t['status'], 2))
        pending_paper = PracticePaper.query.filter_by(student_id=student_id, status='generated')\
            .order_by(PracticePaper.created_at.desc()).first()

        return render_template(
            'dashboard.html',
            metrics=metrics,
            chapters_sorted=chapters_sorted,
            pending_paper=pending_paper,
            chart_labels=json.dumps(chart_labels),
            chart_mastery=json.dumps(chart_mastery),
            chart_colors=json.dumps(chart_colors),
            trend_dates=json.dumps(trend_dates),
            trend_scores=json.dumps(trend_scores)
        )

    def repeat_note(paper):
        """Short sentence telling the student how many questions they have already solved before."""
        repeats = len(PerformanceAnalyzer.get_previous_attempts(paper))
        if not repeats:
            return ' All questions are new to you.'
        noun = 'question was' if repeats == 1 else 'questions were'
        return f' {repeats} {noun} already solved in an earlier paper and marked "Previously solved".'

    @app.route('/generate', methods=['GET', 'POST'])
    def generate_paper():
        """Question paper generation configuration and submission."""
        student_id = session.get('student_id')
        
        if request.method == 'POST':
            try:
                subject_id = int(request.form.get('subject_id', 0))
                chapter_ids = [int(cid) for cid in request.form.getlist('chapter_ids')]
                total_marks = int(request.form.get('total_marks', 30))
                duration_minutes = 0  # Duration concept removed from UI
                difficulty_preference = request.form.get('difficulty_preference', 'Mixed')
                generation_mode = request.form.get('generation_mode', 'Curriculum')
                custom_prompt = request.form.get('custom_prompt', '').strip()

                if not chapter_ids:
                    flash('Please select at least one chapter.', 'danger')
                    return redirect(url_for('generate_paper'))

                if generation_mode == 'AI (LLM)':
                    paper = LLMService.generate_ai_paper(
                        student_id=student_id,
                        subject_id=subject_id,
                        chapter_ids=chapter_ids,
                        total_marks=total_marks,
                        duration_minutes=duration_minutes,
                        difficulty_preference=difficulty_preference,
                        custom_prompt=custom_prompt
                    )
                    ai_note = getattr(paper, 'ai_note', None)
                    if ai_note:
                        flash(ai_note, 'warning')
                    flash(f'Practice paper #{paper.id} created ({paper.total_marks} marks).' + repeat_note(paper), 'success')
                else:
                    paper = QuestionGenerator.generate_paper(
                        student_id=student_id,
                        subject_id=subject_id,
                        chapter_ids=chapter_ids,
                        total_marks=total_marks,
                        duration_minutes=duration_minutes,
                        difficulty_preference=difficulty_preference
                    )
                    flash(f'Practice paper #{paper.id} created ({paper.total_marks} marks).' + repeat_note(paper), 'success')

                return redirect(url_for('view_paper', paper_id=paper.id))

            except ValueError as ve:
                flash(str(ve), 'danger')
                return redirect(url_for('generate_paper'))
            except Exception as e:
                flash(f"An unexpected error occurred during generation: {str(e)}", 'danger')
                return redirect(url_for('generate_paper'))

        subjects = Subject.query.all()
        topic_summary = PerformanceAnalyzer.get_student_topic_summary(student_id)
        topic_perf_map = {t['chapter_id']: t for t in topic_summary}

        return render_template(
            'generate_paper.html',
            subjects=subjects,
            topic_perf_map=topic_perf_map
        )

    @app.route('/paper/<int:paper_id>')
    def view_paper(paper_id):
        """Displays the generated question paper."""
        paper = db.session.get(PracticePaper, paper_id)
        if not paper:
            flash(f"Paper #{paper_id} not found.", "danger")
            return redirect(url_for('history'))
        
        chapter_distribution = []
        if paper.distribution_summary:
            for cid_str, marks in paper.distribution_summary.items():
                ch = db.session.get(Chapter, int(cid_str))
                if ch:
                    chapter_distribution.append({
                        'chapter_name': ch.name,
                        'marks': marks,
                        'percentage': round((marks / paper.total_marks) * 100.0, 1)
                    })

        return render_template(
            'question_paper.html',
            paper=paper,
            chapter_distribution=chapter_distribution,
            previous=PerformanceAnalyzer.get_previous_attempts(paper)
        )

    @app.route('/paper/<int:paper_id>/pdf')
    def download_pdf(paper_id):
        """Generates and streams a downloadable PDF of the practice paper."""
        try:
            pdf_buffer = PDFGenerator.generate_question_paper_pdf(paper_id)
            paper = db.session.get(PracticePaper, paper_id)
            if not paper:
                flash(f"Paper #{paper_id} not found.", "danger")
                return redirect(url_for('history'))
                
            safe_filename = f"Practice_Paper_{paper.subject.name}_Class{paper.subject.class_level}_ID{paper.id}.pdf".replace(' ', '_')
            
            return send_file(
                pdf_buffer,
                as_attachment=True,
                download_name=safe_filename,
                mimetype='application/pdf'
            )
        except Exception as e:
            flash(f"Error generating PDF: {str(e)}", 'danger')
            return redirect(url_for('view_paper', paper_id=paper_id))

    @app.route('/attempt/<int:paper_id>', methods=['GET', 'POST'])
    def attempt_paper(paper_id):
        """
        Interactive student attempt and self-assessment page.
        Allows students to see solutions, auto-check answers, evaluate with AI, and submit marks.
        """
        paper = db.session.get(PracticePaper, paper_id)
        if not paper:
            flash(f"Paper #{paper_id} not found.", "danger")
            return redirect(url_for('history'))
        
        if paper.status == 'submitted':
            flash('This paper has already been submitted. Viewing results.', 'info')
            return redirect(url_for('results', paper_id=paper.id))

        if request.method == 'POST':
            try:
                marks_dict = {}
                answers_dict = {}
                feedback_dict = {}
                
                for pq in paper.paper_questions:
                    mark_key = f'marks_{pq.id}'
                    ans_key = f'answer_{pq.id}'
                    feedback_key = f'feedback_{pq.id}'
                    
                    if mark_key not in request.form:
                        raise ValueError(f"Marks input missing for Question #{pq.order_index}.")
                    
                    marks_dict[pq.id] = float(request.form.get(mark_key))
                    answers_dict[pq.id] = request.form.get(ans_key, '').strip()
                    feedback_dict[pq.id] = request.form.get(feedback_key, '').strip()

                PerformanceAnalyzer.submit_and_evaluate_paper(
                    paper_id=paper.id,
                    marks_dict=marks_dict,
                    answers_dict=answers_dict,
                    feedback_dict=feedback_dict
                )
                
                flash(f'🎉 Paper #{paper.id} submitted! You scored {paper.total_score}/{paper.total_marks} ({paper.percentage}%). Topic mastery has been updated!', 'success')
                return redirect(url_for('results', paper_id=paper.id))

            except ValueError as ve:
                flash(str(ve), 'danger')
            except Exception as e:
                flash(f"Error submitting paper: {str(e)}", 'danger')

        return render_template('attempt_paper.html', paper=paper, previous=PerformanceAnalyzer.get_previous_attempts(paper))

    @app.route('/results/<int:paper_id>')
    def results(paper_id):
        """Comprehensive submission results, topic mastery impact, and question solutions."""
        paper = db.session.get(PracticePaper, paper_id)
        if not paper:
            flash(f"Paper #{paper_id} not found.", "danger")
            return redirect(url_for('history'))
            
        if paper.status != 'submitted':
            flash('This paper has not been submitted yet.', 'warning')
            return redirect(url_for('attempt_paper', paper_id=paper.id))

        chapter_breakdown = {}
        for pq in paper.paper_questions:
            cid = pq.question.chapter_id
            if cid not in chapter_breakdown:
                perf = TopicPerformance.query.filter_by(student_id=paper.student_id, chapter_id=cid).first()
                chapter_breakdown[cid] = {
                    'chapter_name': pq.question.chapter.name,
                    'obtained': 0.0,
                    'available': 0.0,
                    'mastery_score': perf.mastery_score if perf else 0.0,
                    'status': perf.status_classification if perf else 'Weak'
                }
            resp_marks = pq.response.marks_obtained if pq.response else 0.0
            chapter_breakdown[cid]['obtained'] += resp_marks
            chapter_breakdown[cid]['available'] += pq.marks_allocated

        for cid, data in chapter_breakdown.items():
            avail = data['available']
            obt = data['obtained']
            data['attempt_pct'] = round((obt / avail * 100.0), 1) if avail > 0 else 0.0
            data['obtained'] = round(obt, 1)
            data['available'] = round(avail, 1)

        return render_template(
            'results.html',
            paper=paper,
            chapter_breakdown=chapter_breakdown,
            previous=PerformanceAnalyzer.get_previous_attempts(paper)
        )

    @app.route('/history')
    def history():
        """Displays complete chronological practice paper and attempt history."""
        student_id = session.get('student_id')
        status_filter = request.args.get('status', 'all')
        subject_filter = request.args.get('subject_id', 'all')

        query = PracticePaper.query.filter_by(student_id=student_id)
        if status_filter != 'all':
            query = query.filter_by(status=status_filter)
        if subject_filter != 'all':
            query = query.filter_by(subject_id=int(subject_filter))
            
        papers = query.order_by(PracticePaper.created_at.desc()).all()
        subjects = Subject.query.all()

        return render_template(
            'history.html',
            papers=papers,
            subjects=subjects,
            status_filter=status_filter,
            subject_filter=subject_filter
        )

    @app.route('/question-bank')
    def question_bank():
        """Curriculum and AI question bank view with search and multi-criteria filtering."""
        class_filter = request.args.get('class_level', 'all')
        subject_filter = request.args.get('subject_id', 'all')
        chapter_filter = request.args.get('chapter_id', 'all')
        difficulty_filter = request.args.get('difficulty', 'all')
        type_filter = request.args.get('question_type', 'all')
        source_filter = request.args.get('source', 'all')
        
        query = Question.query.join(Chapter).join(Subject)
        
        if class_filter != 'all':
            query = query.filter(Subject.class_level == int(class_filter))
        if subject_filter != 'all':
            query = query.filter(Subject.id == int(subject_filter))
        if chapter_filter != 'all':
            query = query.filter(Chapter.id == int(chapter_filter))
        if difficulty_filter != 'all':
            query = query.filter(Question.difficulty == difficulty_filter)
        if type_filter != 'all':
            query = query.filter(Question.question_type == type_filter)
        if source_filter != 'all':
            query = query.filter(Question.source == source_filter)
            
        questions = query.order_by(Question.chapter_id, Question.marks, Question.id).all()
        subjects = Subject.query.all()
        chapters = Chapter.query.all()

        return render_template(
            'question_bank.html',
            questions=questions,
            subjects=subjects,
            chapters=chapters,
            filters={
                'class_level': class_filter,
                'subject_id': subject_filter,
                'chapter_id': chapter_filter,
                'difficulty': difficulty_filter,
                'question_type': type_filter,
                'source': source_filter
            }
        )

    @app.route('/question-bank/add', methods=['POST'])
    def add_question():
        """Adds a new question to the question bank."""
        try:
            chapter_id = int(request.form.get('chapter_id', 0))
            question_text = request.form.get('question_text', '').strip()
            question_type = request.form.get('question_type', 'Short Answer')
            marks = int(request.form.get('marks', 1))
            difficulty = request.form.get('difficulty', 'Medium')
            correct_answer = request.form.get('correct_answer', '').strip()
            explanation = request.form.get('explanation', '').strip()
            source = request.form.get('source', 'Curriculum Bank')
            
            if not question_text or not correct_answer:
                flash('Question text and correct answer are required.', 'danger')
                return redirect(url_for('question_bank'))

            options = None
            if question_type == 'MCQ':
                opt_list = [
                    request.form.get(f'opt_{i}', '').strip() for i in range(1, 5)
                ]
                options = [opt for opt in opt_list if opt]
                if len(options) < 2:
                    flash('MCQ questions require at least 2 options.', 'danger')
                    return redirect(url_for('question_bank'))

            new_q = Question(
                chapter_id=chapter_id,
                question_text=question_text,
                question_type=question_type,
                marks=marks,
                difficulty=difficulty,
                options_json=json.dumps(options) if options else None,
                correct_answer=correct_answer,
                explanation=explanation,
                source=source
            )
            db.session.add(new_q)
            db.session.commit()
            
            flash('New question successfully added to the item bank!', 'success')
        except Exception as e:
            flash(f"Error adding question: {str(e)}", 'danger')

        return redirect(url_for('question_bank'))

    @app.route('/settings', methods=['GET', 'POST'])
    def settings():
        """Student Google Profile view and academic class settings."""
        student_id = session.get('student_id')
        if not student_id:
            student = Student.query.first()
            if student:
                session['student_id'] = student.id
                student_id = student.id

        current_student = db.session.get(Student, student_id) if student_id else None
        
        if request.method == 'POST':
            class_level = int(request.form.get('class_level', 10))
            if current_student:
                current_student.class_level = class_level
                db.session.commit()
                flash(f'Academic standard updated to Class {class_level} CBSE.', 'success')
            return redirect(url_for('settings'))

        metrics = PerformanceAnalyzer.get_student_dashboard_metrics(student_id) if student_id else None
        return render_template('settings.html', current_student=current_student, metrics=metrics)

    @app.route('/settings/switch-student', methods=['POST'])
    def switch_student():
        """Switches active student profile."""
        student_id = int(request.form.get('student_id', 1))
        student = db.session.get(Student, student_id)
        if student:
            session['student_id'] = student.id
            flash(f'Active profile switched to {student.name} (Class {student.class_level}).', 'success')
        return redirect(url_for('settings'))

    @app.route('/settings/create-student', methods=['POST'])
    def create_student():
        """Creates a new student profile."""
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        class_level = int(request.form.get('class_level', 10))
        avatar_url = request.form.get('avatar_url', '').strip()
        
        if not name:
            flash('Student name is required.', 'danger')
            return redirect(url_for('settings'))
            
        student = Student(
            name=name,
            email=email,
            avatar_url=avatar_url or f"https://api.dicebear.com/7.x/bottts/svg?seed={name}",
            class_level=class_level
        )
        db.session.add(student)
        db.session.commit()
        
        session['student_id'] = student.id
        flash(f'New student profile for {name} created and activated!', 'success')
        return redirect(url_for('dashboard'))

    @app.route('/settings/reset-data', methods=['POST'])
    def reset_data():
        """Resets database and re-seeds original curriculum question bank."""
        try:
            db.drop_all()
            db.create_all()
            seed_database()
            add_class12_questions()
            session.clear()
            flash('Database has been successfully reset and re-seeded with demo data.', 'info')
        except Exception as e:
            flash(f"Error resetting database: {str(e)}", 'danger')
        return redirect(url_for('dashboard'))

    # =========================================================================
    # JSON & AI ASSISTANT APIs
    # =========================================================================

    @app.route('/api/preview-adaptive-allocation', methods=['POST'])
    def preview_adaptive_allocation():
        """Calculates and returns dynamic topic weight preview for the generator UI."""
        try:
            student_id = session.get('student_id')
            data = request.get_json() or {}
            chapter_ids = [int(x) for x in data.get('chapter_ids', [])]
            total_marks = int(data.get('total_marks', 30))
            
            if not chapter_ids or total_marks <= 0:
                return jsonify({'success': False, 'error': 'Invalid parameters'})
                
            allocated_marks, weights_info, explanations = AdaptiveEngine.allocate_topic_marks(
                student_id=student_id,
                chapter_ids=chapter_ids,
                total_marks=total_marks
            )
            
            allocation_data = []
            for cid in chapter_ids:
                ch = db.session.get(Chapter, cid)
                info = weights_info[cid]
                allocation_data.append({
                    'chapter_id': cid,
                    'chapter_name': ch.name if ch else f'Chapter {cid}',
                    'allocated_marks': allocated_marks[cid],
                    'percentage': round((allocated_marks[cid] / total_marks) * 100.0, 1),
                    'status': info['status'],
                    'mastery': info['mastery'],
                    'attempts': info['attempts'],
                    'multiplier': info['multiplier']
                })
                
            return jsonify({
                'success': True,
                'total_marks': total_marks,
                'allocations': allocation_data,
                'explanations': explanations
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    @app.route('/api/ai-generate-questions', methods=['POST'])
    def api_ai_generate_questions():
        """Generates AI questions on-demand using Gemini / LLM Service."""
        try:
            data = request.get_json() or {}
            chapter_id = int(data.get('chapter_id', 0))
            chapter = db.session.get(Chapter, chapter_id)
            if not chapter:
                return jsonify({'success': False, 'error': 'Chapter not found'}), 404

            count = min(10, max(1, int(data.get('count', 3))))
            difficulty = data.get('difficulty', 'Medium')
            question_type = data.get('question_type', 'Mixed')
            custom_prompt = data.get('custom_prompt', '')

            questions = LLMService.generate_questions_llm(
                subject_name=chapter.subject.name,
                chapter_name=chapter.name,
                class_level=chapter.subject.class_level,
                difficulty=difficulty,
                count=count,
                question_type=question_type,
                custom_prompt=custom_prompt
            )

            return jsonify({
                'success': True,
                'chapter_id': chapter.id,
                'chapter_name': chapter.name,
                'questions': questions
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/ai-evaluate-answer', methods=['POST'])
    def api_ai_evaluate_answer():
        """Evaluates student's answer using AI LLM and provides grading and feedback."""
        try:
            data = request.get_json() or {}
            question_text = data.get('question_text', '')
            student_answer = data.get('student_answer', '')
            correct_answer = data.get('correct_answer', '')
            explanation = data.get('explanation', '')
            max_marks = float(data.get('max_marks', 1))

            evaluation = LLMService.evaluate_student_answer(
                question_text=question_text,
                student_answer=student_answer,
                correct_answer=correct_answer,
                explanation=explanation,
                max_marks=max_marks
            )

            return jsonify({
                'success': True,
                'evaluation': evaluation
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/ai-save-generated-question', methods=['POST'])
    def api_ai_save_generated_question():
        """Saves an AI-generated question directly into the repository."""
        try:
            data = request.get_json() or {}
            chapter_id = int(data.get('chapter_id', 0))
            q_data = data.get('question', {})
            
            new_q = Question(
                chapter_id=chapter_id,
                question_text=q_data.get('question_text', '').strip(),
                question_type=q_data.get('question_type', 'Short Answer'),
                marks=int(q_data.get('marks', 1)),
                difficulty=q_data.get('difficulty', 'Medium'),
                options_json=json.dumps(q_data.get('options')) if q_data.get('options') else None,
                correct_answer=q_data.get('correct_answer', '').strip(),
                explanation=q_data.get('explanation', '').strip(),
                source='AI (LLM Generated)'
            )
            db.session.add(new_q)
            db.session.commit()
            return jsonify({'success': True, 'question_id': new_q.id})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
        seed_database()
        add_class12_questions()
    app.run(host='127.0.0.1', port=5000, debug=True)
