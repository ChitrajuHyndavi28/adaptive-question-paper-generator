import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from models import db, PracticePaper
from services.performance_analyzer import PerformanceAnalyzer

class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print total page count."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#4B5563"))
        
        # Draw header line
        self.setStrokeColor(colors.HexColor("#D1D5DB"))
        self.setLineWidth(0.5)
        self.line(40, letter[1] - 40, letter[0] - 40, letter[1] - 40)
        self.drawString(40, letter[1] - 35, "Adaptive Question Paper Generator — Board Practice Series")
        
        # Draw footer line
        self.line(40, 45, letter[0] - 40, 45)
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(letter[0] - 40, 32, page_text)
        self.drawString(40, 32, "Confidential — Generated for Local Student Self-Practice")
        self.restoreState()


class PDFGenerator:
    """Generates high quality, printable PDF examination question papers."""

    @staticmethod
    def generate_question_paper_pdf(paper_id: int) -> io.BytesIO:
        paper = db.session.get(PracticePaper, paper_id)
        if not paper:
            raise ValueError(f"Paper #{paper_id} not found.")

        previous = PerformanceAnalyzer.get_previous_attempts(paper)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=40,
            rightMargin=40,
            topMargin=55,
            bottomMargin=55
        )

        styles = getSampleStyleSheet()
        
        # Custom typography styles
        title_style = ParagraphStyle(
            'ExamTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=15,
            leading=18,
            alignment=1, # Center
            textColor=colors.HexColor('#0F172A'),
            spaceAfter=4
        )
        
        sub_title_style = ParagraphStyle(
            'ExamSubTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=14,
            alignment=1, # Center
            textColor=colors.HexColor('#2563EB'),
            spaceAfter=12
        )
        
        meta_label_style = ParagraphStyle(
            'MetaLabel',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor('#1E293B')
        )
        
        instruction_style = ParagraphStyle(
            'Instructions',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor('#334155')
        )
        
        section_heading_style = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=14,
            textColor=colors.HexColor('#1E293B'),
            spaceBefore=12,
            spaceAfter=6
        )
        
        q_num_style = ParagraphStyle(
            'QNum',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor('#0F172A')
        )
        
        q_text_style = ParagraphStyle(
            'QText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor('#0F172A')
        )
        
        q_marks_style = ParagraphStyle(
            'QMarks',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9.5,
            leading=13,
            alignment=2, # Right
            textColor=colors.HexColor('#2563EB')
        )
        
        option_style = ParagraphStyle(
            'OptionStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#334155')
        )

        elements = []

        # 1. Main Header
        elements.append(Paragraph("CENTRAL BOARD PRACTICE EXAMINATION", title_style))
        elements.append(Paragraph(f"{paper.subject.name.upper()} — CLASS {paper.subject.class_level}", sub_title_style))
        
        # 2. Metadata Box Table
        created_date = paper.created_at.strftime("%d %B %Y")
        meta_data = [
            [
                Paragraph(f"<b>Subject:</b> {paper.subject.name} (Class {paper.subject.class_level})", meta_label_style),
                Paragraph(f"<b>Maximum Marks:</b> {paper.total_marks} Marks", meta_label_style)
            ],
            [
                Paragraph(f"<b>Date:</b> {created_date}", meta_label_style),
                Paragraph(f"<b>Paper ID:</b> #{paper.id}", meta_label_style)
            ]
        ]
        meta_table = Table(meta_data, colWidths=[260, 260])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#CBD5E1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 8))

        # 3. General Instructions
        instructions_text = (
            "<b>General Instructions:</b><br/>"
            "1. This question paper contains <b>" + str(len(paper.paper_questions)) + " questions</b>. All questions are compulsory.<br/>"
            "2. Section A consists of 1-mark objective/MCQ questions.<br/>"
            "3. Section B consists of 2-mark short answer questions.<br/>"
            "4. Section C consists of 3-mark short answer questions.<br/>"
            "5. Section D consists of 4-5 mark long answer questions.<br/>"
            "6. Use of calculators is not permitted. Write neat and legible steps for all questions."
        )
        elements.append(Paragraph(instructions_text, instruction_style))
        elements.append(Spacer(1, 6))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E1'), spaceBefore=4, spaceAfter=8))

        # 4. Group questions into Sections
        sections = {
            'Section A (1 Mark Questions)': [pq for pq in paper.paper_questions if pq.marks_allocated == 1],
            'Section B (2 Mark Questions)': [pq for pq in paper.paper_questions if pq.marks_allocated == 2],
            'Section C (3 Mark Questions)': [pq for pq in paper.paper_questions if pq.marks_allocated == 3],
            'Section D (Long Answer Questions - 4/5 Marks)': [pq for pq in paper.paper_questions if pq.marks_allocated >= 4],
        }

        for sec_title, pqs in sections.items():
            if not pqs:
                continue
                
            elements.append(Paragraph(f"<b>{sec_title}</b>", section_heading_style))
            
            for pq in pqs:
                q = pq.question
                q_num_text = f"Q{pq.order_index}."
                q_text = q.question_text
                if q.id in previous:
                    q_text += f' <font color="#8a5a00" size="8"><i>[Previously solved on {previous[q.id]["date"]}]</i></font>'
                marks_text = f"[{pq.marks_allocated} {'Mark' if pq.marks_allocated == 1 else 'Marks'}]"

                # Row with Question Number, Question Text, and Marks
                q_row = [
                    Paragraph(q_num_text, q_num_style),
                    Paragraph(q_text, q_text_style),
                    Paragraph(marks_text, q_marks_style)
                ]
                
                # Build table for this question
                q_table_data = [q_row]
                
                # If question has MCQ options, append options rows
                if q.options and len(q.options) >= 2:
                    opt_pairs = []
                    for i in range(0, len(q.options), 2):
                        opt1 = q.options[i]
                        opt2 = q.options[i+1] if i+1 < len(q.options) else ""
                        opt_pairs.append((opt1, opt2))
                        
                    for opt1, opt2 in opt_pairs:
                        opt_row = [
                            "",
                            Table(
                                [[Paragraph(opt1, option_style), Paragraph(opt2, option_style)]],
                                colWidths=[210, 210]
                            ),
                            ""
                        ]
                        q_table_data.append(opt_row)

                q_table = Table(q_table_data, colWidths=[30, 430, 60])
                q_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ]))
                
                elements.append(KeepTogether([q_table, Spacer(1, 5)]))

        # Build Document
        doc.build(elements, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer
