import io
from models import Subject
from services.question_generator import QuestionGenerator
from services.pdf_generator import PDFGenerator

def test_generate_pdf_valid_stream(app, test_student, math_chapters):
    """Test generating a printable PDF question paper with ReportLab."""
    with app.app_context():
        chapter_ids = list(math_chapters.values())
        math_sub = Subject.query.filter_by(name="Mathematics", class_level=10).first()
        
        paper = QuestionGenerator.generate_paper(
            student_id=test_student.id,
            subject_id=math_sub.id,
            chapter_ids=chapter_ids,
            total_marks=30,
            duration_minutes=60,
            difficulty_preference="Mixed"
        )
        
        pdf_buffer = PDFGenerator.generate_question_paper_pdf(paper.id)
        assert isinstance(pdf_buffer, io.BytesIO)
        
        pdf_bytes = pdf_buffer.getvalue()
        assert len(pdf_bytes) > 1000 # Valid non-empty PDF
        assert pdf_bytes.startswith(b'%PDF-') # Valid standard PDF header signature
