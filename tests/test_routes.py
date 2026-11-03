import json
from models import db, Subject, PracticePaper, Question, Student

def test_unauthenticated_redirect_to_login(client):
    """Test that accessing protected root / without login redirects to /login (first page is login)."""
    response = client.get('/', follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

def test_dashboard_route_authenticated(client, app, test_student):
    """Test that dashboard loads successfully when authenticated with weak topics and mistake analysis."""
    # Log in first
    login_res = client.post('/login', data={'student_id': str(test_student.id)}, follow_redirects=True)
    assert login_res.status_code == 200
    assert b"Your next step" in login_res.data
    assert b"Your chapters" in login_res.data
    assert b"Questions to look at again" in login_res.data

def test_login_and_google_auth(client, app):
    """Test login page, Google authentication flow, and logout."""
    # GET /login
    login_get = client.get('/login')
    assert login_get.status_code == 200
    assert b"Student Sign In" in login_get.data
    assert b"Sign in with Google" in login_get.data

    # POST /auth/google (Google Authentication)
    google_payload = {
        'name': 'Priya Google',
        'email': 'priya.student@gmail.com',
        'google_id': 'goog_9988776655',
        'avatar_url': 'https://example.com/avatar.png',
        'class_level': 10
    }
    google_res = client.post('/auth/google', data=google_payload, follow_redirects=True)
    assert google_res.status_code == 200
    assert b"Priya Google" in google_res.data

    with app.app_context():
        student = Student.query.filter_by(email='priya.student@gmail.com').first()
        assert student is not None
        assert student.is_google_user is True

    # GET /logout
    logout_res = client.get('/logout', follow_redirects=True)
    assert logout_res.status_code == 200
    assert b"Student Sign In" in logout_res.data

def test_generate_paper_curriculum_and_ai(client, app, test_student, math_chapters):
    """Test GET and POST on /generate endpoint for Curriculum and AI generation modes."""
    # Log in
    client.post('/login', data={'student_id': str(test_student.id)}, follow_redirects=True)

    # GET form
    get_res = client.get('/generate')
    assert get_res.status_code == 200
    assert b"Make my paper" in get_res.data
    
    with app.app_context():
        math_sub = Subject.query.filter_by(name="Mathematics", class_level=10).first()
        chapter_ids = list(math_chapters.values())
        
        # 1. Standard Curriculum Paper
        post_data = {
            'subject_id': str(math_sub.id),
            'chapter_ids': [str(cid) for cid in chapter_ids],
            'total_marks': '30',
            'difficulty_preference': 'Mixed',
            'generation_mode': 'Curriculum'
        }
        
        post_res = client.post('/generate', data=post_data, follow_redirects=True)
        assert post_res.status_code == 200
        assert b"Section A" in post_res.data
        assert b"30" in post_res.data

        # 2. AI Generated Paper
        ai_post_data = {
            'subject_id': str(math_sub.id),
            'chapter_ids': [str(cid) for cid in chapter_ids[:2]],
            'total_marks': '20',
            'difficulty_preference': 'Medium',
            'generation_mode': 'AI (LLM)',
            'custom_prompt': 'Focus on formulas and conceptual derivations'
        }
        ai_res = client.post('/generate', data=ai_post_data, follow_redirects=True)
        assert ai_res.status_code == 200
        # No Gemini key in tests, so AI mode must fall back to the question bank and tell the student
        assert b"question bank instead" in ai_res.data

def test_attempt_paper_and_view_results(client, app, test_student, math_chapters):
    """Test attempting a paper, self-grading, and viewing results page."""
    # Log in
    client.post('/login', data={'student_id': str(test_student.id)}, follow_redirects=True)

    with app.app_context():
        from services.question_generator import QuestionGenerator
        
        math_sub = Subject.query.filter_by(name="Mathematics", class_level=10).first()
        chapter_ids = list(math_chapters.values())
        
        paper = QuestionGenerator.generate_paper(
            student_id=test_student.id,
            subject_id=math_sub.id,
            chapter_ids=chapter_ids,
            total_marks=20,
            duration_minutes=0,
            difficulty_preference="Mixed"
        )
        paper_id = paper.id

    # GET attempt page
    attempt_get = client.get(f'/attempt/{paper_id}')
    assert attempt_get.status_code == 200
    assert b"Attempt Paper #" in attempt_get.data
    assert b"Show solution" in attempt_get.data

    # POST marks submission
    with app.app_context():
        paper = db.session.get(PracticePaper, paper_id)
        post_data = {}
        for pq in paper.paper_questions:
            post_data[f'marks_{pq.id}'] = str(pq.marks_allocated) # Full marks
            post_data[f'answer_{pq.id}'] = 'Correct solution'
            post_data[f'feedback_{pq.id}'] = 'Good attempt'

    attempt_post = client.post(f'/attempt/{paper_id}', data=post_data, follow_redirects=True)
    assert attempt_post.status_code == 200
    assert b"Your results" in attempt_post.data
    assert b"100.0%" in attempt_post.data or b"100%" in attempt_post.data

def test_api_ai_generate_and_evaluate(client, app, test_student, math_chapters):
    """Test AI Question Generation and AI Answer Evaluation APIs."""
    # Log in
    client.post('/login', data={'student_id': str(test_student.id)}, follow_redirects=True)
    trig_id = math_chapters["Trigonometry"]

    # 1. AI Question Generation API
    gen_payload = {
        'chapter_id': trig_id,
        'count': 2,
        'difficulty': 'Medium',
        'question_type': 'Mixed',
        'custom_prompt': 'Heights and Distances'
    }
    gen_res = client.post('/api/ai-generate-questions', json=gen_payload)
    assert gen_res.status_code == 200
    gen_data = gen_res.get_json()
    assert gen_data['success'] is True
    assert len(gen_data['questions']) == 2

    # 2. AI Answer Evaluation API
    eval_payload = {
        'question_text': 'What is tan 45 degrees?',
        'student_answer': '1',
        'correct_answer': '1',
        'explanation': 'tan 45 is 1.',
        'max_marks': 1.0
    }
    eval_res = client.post('/api/ai-evaluate-answer', json=eval_payload)
    assert eval_res.status_code == 200
    eval_data = eval_res.get_json()
    assert eval_data['success'] is True
    assert eval_data['evaluation']['marks_awarded'] == 1.0

def test_download_pdf_route(client, app, test_student, math_chapters):
    """Test PDF download endpoint returns application/pdf."""
    # Log in
    client.post('/login', data={'student_id': str(test_student.id)}, follow_redirects=True)

    with app.app_context():
        from services.question_generator import QuestionGenerator
        
        math_sub = Subject.query.filter_by(name="Mathematics", class_level=10).first()
        chapter_ids = list(math_chapters.values())
        
        paper = QuestionGenerator.generate_paper(
            student_id=test_student.id,
            subject_id=math_sub.id,
            chapter_ids=chapter_ids,
            total_marks=20,
            duration_minutes=0,
            difficulty_preference="Mixed"
        )
        paper_id = paper.id

    pdf_res = client.get(f'/paper/{paper_id}/pdf')
    assert pdf_res.status_code == 200
    assert pdf_res.mimetype == 'application/pdf'
    assert pdf_res.data.startswith(b'%PDF-')

def test_settings_and_profile_update(client, app, test_student):
    """Test Student Profile page and academic class preference update."""
    # Log in
    client.post('/login', data={'student_id': str(test_student.id)}, follow_redirects=True)

    # GET /settings
    res = client.get('/settings')
    assert res.status_code == 200
    assert b"Student Profile" in res.data
    assert b"Academic Standard" in res.data
    assert b"Save Class Standard" in res.data

    # POST /settings (update class level)
    post_res = client.post('/settings', data={'class_level': '12'}, follow_redirects=True)
    assert post_res.status_code == 200
    assert b"Academic standard updated to Class 12 CBSE" in post_res.data

    with app.app_context():
        student = db.session.get(Student, test_student.id)
        assert student.class_level == 12

