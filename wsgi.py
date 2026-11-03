"""Production entry point: gunicorn wsgi:app"""
import os

from app import create_app
from models import db
from seed_data import seed_database
from class12_questions import add_class12_questions

os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance'), exist_ok=True)

app = create_app()
with app.app_context():
    db.create_all()
    seed_database()
    add_class12_questions()
