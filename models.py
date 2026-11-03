import json
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def get_utc_now():
    return datetime.now(timezone.utc)

class Student(db.Model):
    """Represents a student user in the system."""
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    avatar_url = db.Column(db.String(300), nullable=True)
    google_id = db.Column(db.String(100), nullable=True)
    is_google_user = db.Column(db.Boolean, default=False, nullable=False)
    class_level = db.Column(db.Integer, default=10, nullable=False)
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)
    
    # Relationships
    papers = db.relationship('PracticePaper', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    topic_performances = db.relationship('TopicPerformance', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'avatar_url': self.avatar_url,
            'is_google_user': self.is_google_user,
            'class_level': self.class_level,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }


class Subject(db.Model):
    """Represents an academic subject for a particular class level."""
    __tablename__ = 'subjects'
    
    id = db.Column(db.Integer, primary_key=True)
    class_level = db.Column(db.Integer, nullable=False)  # 10 or 12
    name = db.Column(db.String(100), nullable=False)      # e.g., 'Mathematics'
    
    # Relationships
    chapters = db.relationship('Chapter', backref='subject', lazy='select', cascade='all, delete-orphan')
    papers = db.relationship('PracticePaper', backref='subject', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'class_level': self.class_level,
            'name': self.name,
            'chapters_count': len(self.chapters)
        }


class Chapter(db.Model):
    """Represents a curriculum chapter/topic within a subject."""
    __tablename__ = 'chapters'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # e.g., 'Trigonometry'
    
    # Relationships
    questions = db.relationship('Question', backref='chapter', lazy='select', cascade='all, delete-orphan')
    topic_performances = db.relationship('TopicPerformance', backref='chapter', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'subject_id': self.subject_id,
            'name': self.name,
            'questions_count': len(self.questions)
        }


class Question(db.Model):
    """Represents an exam question in the item bank."""
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.id', ondelete='CASCADE'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(30), nullable=False, default='Short Answer')  # MCQ, Short Answer, Long Answer, Numerical
    marks = db.Column(db.Integer, nullable=False, default=1)
    difficulty = db.Column(db.String(20), nullable=False, default='Medium')  # Easy, Medium, Hard
    options_json = db.Column(db.Text, nullable=True)  # JSON array for MCQs: ["A. ...", "B. ..."]
    correct_answer = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, nullable=True)  # Step-by-step marking scheme / explanation
    source = db.Column(db.String(50), default='Curriculum Bank', nullable=False)  # 'Curriculum Bank', 'AI (LLM Generated)'
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)
    
    # Relationships
    paper_questions = db.relationship('PaperQuestion', backref='question', lazy='dynamic')
    
    @property
    def options(self):
        if self.options_json:
            try:
                return json.loads(self.options_json)
            except Exception:
                return []
        return []
    
    @options.setter
    def options(self, value):
        if value is not None:
            self.options_json = json.dumps(value)
        else:
            self.options_json = None

    def to_dict(self):
        return {
            'id': self.id,
            'chapter_id': self.chapter_id,
            'chapter_name': self.chapter.name if self.chapter else '',
            'question_text': self.question_text,
            'question_type': self.question_type,
            'marks': self.marks,
            'difficulty': self.difficulty,
            'options': self.options,
            'correct_answer': self.correct_answer,
            'explanation': self.explanation,
            'source': self.source
        }


class PracticePaper(db.Model):
    """Represents a generated practice exam paper for a student."""
    __tablename__ = 'practice_papers'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    total_marks = db.Column(db.Integer, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False, default=60)
    difficulty_preference = db.Column(db.String(20), nullable=False, default='Mixed')  # Easy, Medium, Hard, Mixed
    generation_mode = db.Column(db.String(30), default='Curriculum', nullable=False)   # 'Curriculum', 'AI (LLM)', 'Hybrid'
    
    # Adaptive metadata
    selected_chapters_json = db.Column(db.Text, nullable=False)  # JSON list of chapter IDs
    target_weights_json = db.Column(db.Text, nullable=True)     # JSON dict of chapter_id -> weight/target marks
    distribution_summary_json = db.Column(db.Text, nullable=True) # JSON dict of chapter_id -> actual allocated marks
    distribution_explanation = db.Column(db.Text, nullable=True) # Human readable adaptation rationale
    
    status = db.Column(db.String(20), nullable=False, default='generated')  # 'generated', 'submitted'
    total_score = db.Column(db.Float, nullable=True)
    percentage = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    paper_questions = db.relationship(
        'PaperQuestion', 
        backref='paper', 
        lazy='select', 
        cascade='all, delete-orphan',
        order_by='PaperQuestion.order_index'
    )
    
    @property
    def selected_chapters(self):
        try:
            return json.loads(self.selected_chapters_json)
        except Exception:
            return []
            
    @property
    def target_weights(self):
        if self.target_weights_json:
            try:
                return json.loads(self.target_weights_json)
            except Exception:
                return {}
        return {}

    @property
    def distribution_summary(self):
        if self.distribution_summary_json:
            try:
                return json.loads(self.distribution_summary_json)
            except Exception:
                return {}
        return {}


class PaperQuestion(db.Model):
    """Maps a question to a practice paper with order and allocated marks."""
    __tablename__ = 'paper_questions'
    
    id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('practice_papers.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='RESTRICT'), nullable=False)
    order_index = db.Column(db.Integer, nullable=False, default=1)
    marks_allocated = db.Column(db.Integer, nullable=False)
    
    # Relationships
    response = db.relationship('QuestionResponse', backref='paper_question', uselist=False, cascade='all, delete-orphan')


class QuestionResponse(db.Model):
    """Stores student's attempt response and marks obtained for a paper question."""
    __tablename__ = 'question_responses'
    
    id = db.Column(db.Integer, primary_key=True)
    paper_question_id = db.Column(db.Integer, db.ForeignKey('paper_questions.id', ondelete='CASCADE'), unique=True, nullable=False)
    student_answer = db.Column(db.Text, nullable=True)
    marks_obtained = db.Column(db.Float, nullable=False)
    feedback = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(db.DateTime, default=get_utc_now, nullable=False)


class TopicPerformance(db.Model):
    """Tracks a student's rolling mastery and historical performance per topic/chapter."""
    __tablename__ = 'topic_performances'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id', ondelete='CASCADE'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapters.id', ondelete='CASCADE'), nullable=False)
    
    latest_score_percentage = db.Column(db.Float, nullable=False, default=0.0)
    mastery_score = db.Column(db.Float, nullable=False, default=0.0)  # Smoothed rolling score (0-100)
    total_marks_obtained = db.Column(db.Float, nullable=False, default=0.0)
    total_marks_available = db.Column(db.Float, nullable=False, default=0.0)
    number_of_attempts = db.Column(db.Integer, nullable=False, default=0)
    status_classification = db.Column(db.String(20), nullable=False, default='Weak')  # Weak, Average, Strong
    updated_at = db.Column(db.DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('student_id', 'chapter_id', name='uq_student_chapter_perf'),
    )

    def to_dict(self):
        return {
            'chapter_id': self.chapter_id,
            'chapter_name': self.chapter.name if self.chapter else '',
            'latest_score_percentage': round(self.latest_score_percentage, 1),
            'mastery_score': round(self.mastery_score, 1),
            'total_marks_obtained': self.total_marks_obtained,
            'total_marks_available': self.total_marks_available,
            'number_of_attempts': self.number_of_attempts,
            'status_classification': self.status_classification,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M')
        }
