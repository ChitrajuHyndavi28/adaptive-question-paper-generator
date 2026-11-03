import pytest
from app import create_app
from config import TestConfig
from models import db, Student, Subject, Chapter, Question
from seed_data import seed_database

@pytest.fixture
def app():
    """Create and configure a clean Flask test application."""
    app = create_app(TestConfig)
    
    with app.app_context():
        db.create_all()
        seed_database()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def test_student(app):
    """Retrieve the primary demo student."""
    with app.app_context():
        return Student.query.filter_by(name="Aarav Sharma").first()

@pytest.fixture
def math_chapters(app):
    """Retrieve the Class 10 Mathematics chapters."""
    with app.app_context():
        math_sub = Subject.query.filter_by(name="Mathematics", class_level=10).first()
        return {ch.name: ch.id for ch in math_sub.chapters}
