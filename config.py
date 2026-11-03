import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'adaptive-exam-generator-secret-key-2026')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', f'sqlite:///{os.path.join(BASE_DIR, "instance", "adaptive_exam.sqlite3")}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Adaptive Algorithm Thresholds (Configurable project parameters)
    WEAK_THRESHOLD = 40.0       # Scores below 40% are Weak
    STRONG_THRESHOLD = 75.0     # Scores 75% and above are Strong
    
    # Adaptive Weight Multipliers
    WEIGHT_WEAK = 1.8           # 1.8x base weight for targeted remediation
    WEIGHT_AVERAGE = 1.2        # 1.2x base weight for reinforcement
    WEIGHT_STRONG = 0.7         # 0.7x base weight for retention revision
    WEIGHT_UNATTEMPTED = 1.0    # 1.0x balanced baseline
    
    # Rolling Mastery Smoothing (0.6 * latest + 0.4 * previous)
    MASTERY_ALPHA = 0.6

    # Google Auth Configuration
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', 'demo-google-client-id.apps.googleusercontent.com')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')

    # AI / LLM Configuration (Gemini API)
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY', '')
    GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.1-flash-lite')

class TestConfig(Config):
    """Testing configuration with in-memory SQLite."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
