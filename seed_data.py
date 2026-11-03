import json
from datetime import datetime, timezone
from models import db, Student, Subject, Chapter, Question, PracticePaper, PaperQuestion, QuestionResponse, TopicPerformance

def seed_database():
    """Populates the database with initial demo students, subjects, chapters, and high quality question bank."""
    
    # Check if data already seeded
    if Student.query.first():
        return

    print("Seeding database with demo students and question bank...")

    # 1. Create Demo Students
    student1 = Student(name="Aarav Sharma", email="aarav.sharma@example.edu", class_level=10)
    student2 = Student(name="Priya Patel", email="priya.patel@example.edu", class_level=10)
    student3 = Student(name="Rohan Verma", email="rohan.verma@example.edu", class_level=12)
    student_google = Student(
        name="Aarav Sharma (Google User)",
        email="student.cbse@gmail.com",
        google_id="goog_1029384756",
        avatar_url="https://api.dicebear.com/7.x/bottts/svg?seed=Aarav",
        is_google_user=True,
        class_level=10
    )
    db.session.add_all([student1, student2, student3, student_google])
    db.session.flush()

    # 2. Create Subjects
    math10 = Subject(class_level=10, name="Mathematics")
    sci10 = Subject(class_level=10, name="Science")
    math12 = Subject(class_level=12, name="Mathematics")
    db.session.add_all([math10, sci10, math12])
    db.session.flush()

    # 3. Create Chapters for Class 10 Mathematics
    ch_trig = Chapter(subject_id=math10.id, name="Trigonometry")
    ch_stat = Chapter(subject_id=math10.id, name="Statistics")
    ch_prob = Chapter(subject_id=math10.id, name="Probability")
    
    # Science Chapters
    ch_elec = Chapter(subject_id=sci10.id, name="Electricity")
    ch_light = Chapter(subject_id=sci10.id, name="Light - Reflection and Refraction")
    
    # Class 12 Chapters
    ch_calc = Chapter(subject_id=math12.id, name="Integrals and Calculus")
    ch_mat = Chapter(subject_id=math12.id, name="Matrices and Determinants")

    db.session.add_all([ch_trig, ch_stat, ch_prob, ch_elec, ch_light, ch_calc, ch_mat])
    db.session.flush()

    questions = []

    # =========================================================================
    # CLASS 10 MATHEMATICS - TRIGONOMETRY (16 Questions)
    # =========================================================================
    trig_data = [
        # 1-Mark Questions (MCQ)
        {
            "text": "If sin θ = 1/2, then the value of (3 cos θ - 4 cos³ θ) is equal to:",
            "type": "MCQ", "marks": 1, "diff": "Easy",
            "opts": ["A) 0", "B) 1", "C) 1/2", "D) √3/2"],
            "ans": "A) 0",
            "sol": "sin θ = 1/2 ⇒ θ = 30°. cos 30° = √3/2. 3(√3/2) - 4(√3/2)³ = (3√3)/2 - 4(3√3/8) = (3√3)/2 - (3√3)/2 = 0."
        },
        {
            "text": "The value of (sin² 30° + cos² 30° + tan² 45°) is:",
            "type": "MCQ", "marks": 1, "diff": "Easy",
            "opts": ["A) 1", "B) 2", "C) 3", "D) 0"],
            "ans": "B) 2",
            "sol": "Using the identity sin² θ + cos² θ = 1 and tan 45° = 1: Value = 1 + 1² = 2."
        },
        {
            "text": "If tan θ = 4/3, find the value of (sin θ + cos θ)/(sin θ - cos θ):",
            "type": "MCQ", "marks": 1, "diff": "Medium",
            "opts": ["A) 7", "B) 1/7", "C) -7", "D) 1"],
            "ans": "A) 7",
            "sol": "Divide numerator and denominator by cos θ: (tan θ + 1)/(tan θ - 1) = (4/3 + 1)/(4/3 - 1) = (7/3)/(1/3) = 7."
        },
        {
            "text": "If sec θ + tan θ = p, what is the value of sec θ - tan θ?",
            "type": "MCQ", "marks": 1, "diff": "Medium",
            "opts": ["A) p", "B) 1/p", "C) p²", "D) 1 - p"],
            "ans": "B) 1/p",
            "sol": "Since sec² θ - tan² θ = 1 ⇒ (sec θ + tan θ)(sec θ - tan θ) = 1 ⇒ sec θ - tan θ = 1/p."
        },
        {
            "text": "A pole 6 m high casts a shadow 2√3 m long on the ground, then the sun's elevation is:",
            "type": "MCQ", "marks": 1, "diff": "Easy",
            "opts": ["A) 60°", "B) 45°", "C) 30°", "D) 90°"],
            "ans": "A) 60°",
            "sol": "tan θ = Height / Shadow = 6 / (2√3) = 3 / √3 = √3 ⇒ θ = 60°."
        },
        # 2-Mark Questions (Short Answer)
        {
            "text": "Prove that: (1 + tan² A) / (1 + cot² A) = tan² A.",
            "type": "Short Answer", "marks": 2, "diff": "Easy",
            "opts": None, "ans": "Proof: (1+tan² A)/(1+cot² A) = sec² A / cosec² A = (1/cos² A) / (1/sin² A) = sin² A / cos² A = tan² A.",
            "sol": "Step 1: Replace 1 + tan² A = sec² A and 1 + cot² A = cosec² A (1 Mark).\nStep 2: Convert to sin and cos: (1/cos² A) / (1/sin² A) = sin² A / cos² A = tan² A (1 Mark)."
        },
        {
            "text": "Evaluate: 2 tan² 45° + cos² 30° - sin² 60°.",
            "type": "Short Answer", "marks": 2, "diff": "Easy",
            "opts": None, "ans": "2",
            "sol": "Substitute values: tan 45° = 1, cos 30° = √3/2, sin 60° = √3/2.\nExpression = 2(1)² + (√3/2)² - (√3/2)² = 2 + 3/4 - 3/4 = 2 (2 Marks)."
        },
        {
            "text": "If sin (A - B) = 1/2 and cos (A + B) = 1/2 (where 0° < A + B ≤ 90° and A > B), find values of A and B.",
            "type": "Short Answer", "marks": 2, "diff": "Medium",
            "opts": None, "ans": "A = 45°, B = 15°",
            "sol": "sin (A - B) = 1/2 ⇒ A - B = 30° ... (1)\ncos (A + B) = 1/2 ⇒ A + B = 60° ... (2)\nAdding (1) and (2): 2A = 90° ⇒ A = 45°.\nSubstituting A: B = 15° (2 Marks)."
        },
        {
            "text": "If 4 tan θ = 3, evaluate: (4 sin θ - cos θ + 1) / (4 sin θ + cos θ - 1).",
            "type": "Short Answer", "marks": 2, "diff": "Medium",
            "opts": None, "ans": "13/11",
            "sol": "Given tan θ = 3/4 ⇒ sin θ = 3/5, cos θ = 4/5.\nNumerator = 4(3/5) - 4/5 + 1 = 12/5 - 4/5 + 5/5 = 13/5.\nDenominator = 4(3/5) + 4/5 - 1 = 12/5 + 4/5 - 5/5 = 11/5.\nRatio = (13/5) / (11/5) = 13/11 (2 Marks)."
        },
        # 3-Mark Questions (Short Answer II)
        {
            "text": "Prove that: (sin θ - 2 sin³ θ) / (2 cos³ θ - cos θ) = tan θ.",
            "type": "Short Answer", "marks": 3, "diff": "Medium",
            "opts": None, "ans": "Proof as shown in marking scheme.",
            "sol": "LHS = [sin θ(1 - 2 sin² θ)] / [cos θ(2 cos² θ - 1)] (1 Mark)\n= [sin θ(1 - 2(1 - cos² θ))] / [cos θ(2 cos² θ - 1)] (1 Mark)\n= [sin θ(2 cos² θ - 1)] / [cos θ(2 cos² θ - 1)] = sin θ / cos θ = tan θ = RHS (1 Mark)."
        },
        {
            "text": "Prove that: √((1 + sin A) / (1 - sin A)) = sec A + tan A.",
            "type": "Short Answer", "marks": 3, "diff": "Medium",
            "opts": None, "ans": "Proof complete.",
            "sol": "Multiply numerator and denominator inside root by (1 + sin A):\n= √[(1 + sin A)² / (1 - sin² A)] (1 Mark)\n= √[(1 + sin A)² / cos² A] = (1 + sin A) / cos A (1 Mark)\n= 1/cos A + sin A/cos A = sec A + tan A = RHS (1 Mark)."
        },
        {
            "text": "Prove that: (cosec θ - cot θ)² = (1 - cos θ) / (1 + cos θ).",
            "type": "Short Answer", "marks": 3, "diff": "Hard",
            "opts": None, "ans": "Proof complete.",
            "sol": "LHS = (1/sin θ - cos θ/sin θ)² = (1 - cos θ)² / sin² θ (1 Mark)\n= (1 - cos θ)² / (1 - cos² θ) = (1 - cos θ)² / [(1 - cos θ)(1 + cos θ)] (1 Mark)\n= (1 - cos θ) / (1 + cos θ) = RHS (1 Mark)."
        },
        # 4/5-Mark Questions (Long Answer)
        {
            "text": "From a point on a bridge across a river, the angles of depression of the banks on opposite sides of the river are 30° and 45° respectively. If the bridge is at a height of 3 m from the banks, find the width of the river (take √3 = 1.732).",
            "type": "Long Answer", "marks": 4, "diff": "Medium",
            "opts": None, "ans": "8.196 m (or 3(1 + √3) m)",
            "sol": "Let bridge point be P at height 3 m. Bank A has angle of depression 30°, Bank B has 45°.\nIn right triangle PAM: tan 30° = PM/AM ⇒ 1/√3 = 3/AM ⇒ AM = 3√3 m (1.5 Marks).\nIn right triangle PBM: tan 45° = PM/BM ⇒ 1 = 3/BM ⇒ BM = 3 m (1.5 Marks).\nWidth of river AB = AM + BM = 3√3 + 3 = 3(√3 + 1) = 3(2.732) = 8.196 m (1 Mark)."
        },
        {
            "text": "The angle of elevation of an aeroplane from a point on the ground is 60°. After a flight of 30 seconds, the angle of elevation changes to 30°. If the aeroplane is flying at a constant height of 3000√3 m, find the speed of the aeroplane in km/h.",
            "type": "Long Answer", "marks": 4, "diff": "Hard",
            "opts": None, "ans": "720 km/h",
            "sol": "Let initial position be A and final position after 30s be B at height h = 3000√3 m.\nIn triangle OAC: tan 60° = AC/OC ⇒ √3 = 3000√3/OC ⇒ OC = 3000 m (1.5 Marks).\nIn triangle OBD: tan 30° = BD/OD ⇒ 1/√3 = 3000√3/OD ⇒ OD = 9000 m (1.5 Marks).\nDistance CD = OD - OC = 9000 - 3000 = 6000 m.\nSpeed = 6000 m / 30 s = 200 m/s = 200 * (18/5) = 720 km/h (1 Mark)."
        },
        {
            "text": "Prove that: (sin θ + cosec θ)² + (cos θ + sec θ)² = 7 + tan² θ + cot² θ.",
            "type": "Long Answer", "marks": 5, "diff": "Hard",
            "opts": None, "ans": "Proof complete.",
            "sol": "Expand both squares: LHS = (sin² θ + cosec² θ + 2 sin θ cosec θ) + (cos² θ + sec² θ + 2 cos θ sec θ) (1.5 Marks)\n= (sin² θ + cos² θ) + 2(1) + 2(1) + cosec² θ + sec² θ (1.5 Marks)\n= 1 + 4 + (1 + cot² θ) + (1 + tan² θ) (1 Mark)\n= 7 + tan² θ + cot² θ = RHS (1 Mark)."
        },
        {
            "text": "As observed from the top of a 75 m high lighthouse from the sea-level, the angles of depression of two ships are 30° and 45°. If one ship is exactly behind the other on the same side of the lighthouse, find the distance between the two ships.",
            "type": "Long Answer", "marks": 5, "diff": "Hard",
            "opts": None, "ans": "75(√3 - 1) m ≈ 54.9 m",
            "sol": "Let lighthouse AB = 75 m. Let closer ship be D (45°) and farther ship be C (30°).\nIn triangle ABD: tan 45° = AB/BD ⇒ 1 = 75/BD ⇒ BD = 75 m (2 Marks).\nIn triangle ABC: tan 30° = AB/BC ⇒ 1/√3 = 75/BC ⇒ BC = 75√3 m (2 Marks).\nDistance between ships CD = BC - BD = 75√3 - 75 = 75(√3 - 1) ≈ 75(0.732) = 54.9 m (1 Mark)."
        }
    ]

    for q in trig_data:
        questions.append(Question(
            chapter_id=ch_trig.id,
            question_text=q["text"],
            question_type=q["type"],
            marks=q["marks"],
            difficulty=q["diff"],
            options_json=json.dumps(q["opts"]) if q["opts"] else None,
            correct_answer=q["ans"],
            explanation=q["sol"]
        ))

    # =========================================================================
    # CLASS 10 MATHEMATICS - STATISTICS (16 Questions)
    # =========================================================================
    stat_data = [
        # 1-Mark MCQs
        {
            "text": "The empirical relationship between the three measures of central tendency is:",
            "type": "MCQ", "marks": 1, "diff": "Easy",
            "opts": ["A) Mode = 3 Median - 2 Mean", "B) Mode = 2 Median - 3 Mean", "C) Median = 3 Mode - 2 Mean", "D) Mean = 3 Median - 2 Mode"],
            "ans": "A) Mode = 3 Median - 2 Mean",
            "sol": "The standard empirical formula connecting central tendencies is: Mode = 3 Median - 2 Mean."
        },
        {
            "text": "For a given frequency distribution, if Σfᵢxᵢ = 660 and Σfᵢ = 40, then the arithmetic mean is:",
            "type": "MCQ", "marks": 1, "diff": "Easy",
            "opts": ["A) 16.5", "B) 15.5", "C) 16.0", "D) 17.5"],
            "ans": "A) 16.5",
            "sol": "Mean = Σfᵢxᵢ / Σfᵢ = 660 / 40 = 16.5."
        },
        {
            "text": "The class mark of the class interval 40 - 55 is:",
            "type": "MCQ", "marks": 1, "diff": "Easy",
            "opts": ["A) 47.5", "B) 45.0", "C) 50.0", "D) 48.0"],
            "ans": "A) 47.5",
            "sol": "Class mark = (Upper limit + Lower limit) / 2 = (55 + 40) / 2 = 95 / 2 = 47.5."
        },
        {
            "text": "If the mean of 5 observations x, x+2, x+4, x+6, x+8 is 11, then the value of x is:",
            "type": "MCQ", "marks": 1, "diff": "Medium",
            "opts": ["A) 7", "B) 8", "C) 9", "D) 11"],
            "ans": "A) 7",
            "sol": "Sum = 5x + 20. Mean = (5x + 20)/5 = x + 4. Given x + 4 = 11 ⇒ x = 7."
        },
        {
            "text": "Which measure of central tendency is given by the x-coordinate of the point of intersection of more-than and less-than ogives?",
            "type": "MCQ", "marks": 1, "diff": "Medium",
            "opts": ["A) Median", "B) Mean", "C) Mode", "D) Range"],
            "ans": "A) Median",
            "sol": "The point of intersection of less-than and more-than ogives gives the Median at its x-coordinate."
        },
        # 2-Mark Short Answer
        {
            "text": "Find the mode of the following data: 14, 25, 14, 28, 18, 17, 18, 14, 23, 22, 14, 18.",
            "type": "Short Answer", "marks": 2, "diff": "Easy",
            "opts": None, "ans": "Mode = 14",
            "sol": "Count frequencies: 14 appears 4 times, 18 appears 3 times, others appear once.\nMode is the observation with maximum frequency = 14 (2 Marks)."
        },
        {
            "text": "Find the class width and class marks for the class intervals: 10-25, 25-40, 40-55, 55-70.",
            "type": "Short Answer", "marks": 2, "diff": "Easy",
            "opts": None, "ans": "Class width = 15; Class marks: 17.5, 32.5, 47.5, 62.5",
            "sol": "Class width = Upper Limit - Lower Limit = 25 - 10 = 15 (1 Mark).\nClass marks: (10+25)/2 = 17.5, (25+40)/2 = 32.5, (40+55)/2 = 47.5, (55+70)/2 = 62.5 (1 Mark)."
        },
        {
            "text": "If the median of a distribution is 26 and mean is 25, find the mode using the empirical formula.",
            "type": "Short Answer", "marks": 2, "diff": "Medium",
            "opts": None, "ans": "Mode = 28",
            "sol": "Empirical formula: Mode = 3 Median - 2 Mean (1 Mark)\nMode = 3(26) - 2(25) = 78 - 50 = 28 (1 Mark)."
        },
        {
            "text": "The marks obtained by 30 students in a test are given: Mean = 35. If each mark is increased by 5, what will be the new mean?",
            "type": "Short Answer", "marks": 2, "diff": "Medium",
            "opts": None, "ans": "New Mean = 40",
            "sol": "Property of arithmetic mean: If each observation is increased by a constant k, the mean increases by k.\nHere k = 5, so New Mean = 35 + 5 = 40 (2 Marks)."
        },
        # 3-Mark Short Answer II
        {
            "text": "Find the mean of the following grouped distribution: Classes: 0-10 (freq 3), 10-20 (freq 5), 20-30 (freq 9), 30-40 (freq 5), 40-50 (freq 3).",
            "type": "Short Answer", "marks": 3, "diff": "Medium",
            "opts": None, "ans": "Mean = 25",
            "sol": "Class marks xᵢ: 5, 15, 25, 35, 45.\nfᵢxᵢ products: 3*5=15, 5*15=75, 9*25=225, 5*35=175, 3*45=135 (1.5 Marks).\nΣfᵢ = 25, Σfᵢxᵢ = 625 (1 Mark).\nMean = 625 / 25 = 25 (0.5 Mark)."
        },
        {
            "text": "Calculate the median for the following frequency distribution: Classes: 10-20 (freq 4), 20-30 (freq 8), 30-40 (freq 10), 40-50 (freq 6), 50-60 (freq 2).",
            "type": "Short Answer", "marks": 3, "diff": "Medium",
            "opts": None, "ans": "Median = 33",
            "sol": "N = 30, N/2 = 15. Cumulative frequencies: 4, 12, 22, 28, 30 (1 Mark).\nMedian class is 30-40 (cf = 22 > 15), l = 30, cf_prev = 12, f = 10, h = 10 (1 Mark).\nMedian = l + [(N/2 - cf)/f] * h = 30 + [(15 - 12)/10] * 10 = 30 + 3 = 33 (1 Mark)."
        },
        {
            "text": "Find the mode of the distribution: Classes: 0-20 (freq 10), 20-40 (freq 35), 40-60 (freq 52), 60-80 (freq 61), 80-100 (freq 38), 100-120 (freq 29).",
            "type": "Short Answer", "marks": 3, "diff": "Hard",
            "opts": None, "ans": "Mode = 65.625",
            "sol": "Modal class is 60-80 (max frequency 61).\nl = 60, f₁ = 61, f₀ = 52, f₂ = 38, h = 20 (1 Mark).\nMode = l + [(f₁ - f₀) / (2f₁ - f₀ - f₂)] * h (1 Mark)\n= 60 + [(61 - 52) / (122 - 52 - 38)] * 20 = 60 + [9 / 32] * 20 = 60 + 5.625 = 65.625 (1 Mark)."
        },
        # 4/5-Mark Long Answer
        {
            "text": "The mean of the following distribution is 50, and total frequency is 120. Find the missing frequencies f₁ and f₂: Classes: 0-20 (freq 17), 20-40 (freq f₁), 40-60 (freq 32), 60-80 (freq f₂), 80-100 (freq 19).",
            "type": "Long Answer", "marks": 4, "diff": "Hard",
            "opts": None, "ans": "f₁ = 28, f₂ = 24",
            "sol": "Total frequency = 17 + f₁ + 32 + f₂ + 19 = 68 + f₁ + f₂ = 120 ⇒ f₁ + f₂ = 52 ... (1) (1.5 Marks)\nClass marks: 10, 30, 50, 70, 90.\nΣfᵢxᵢ = 170 + 30f₁ + 1600 + 70f₂ + 1710 = 3480 + 30f₁ + 70f₂.\nMean = Σfᵢxᵢ / 120 = 50 ⇒ 3480 + 30f₁ + 70f₂ = 6000 ⇒ 30f₁ + 70f₂ = 2520 ⇒ 3f₁ + 7f₂ = 252 ... (2) (1.5 Marks)\nMultiply (1) by 3: 3f₁ + 3f₂ = 156. Subtract from (2): 4f₂ = 96 ⇒ f₂ = 24.\nFrom (1): f₁ = 52 - 24 = 28 (1 Mark)."
        },
        {
            "text": "The median of the following data is 525. Find the values of x and y, if the total frequency is 100: Classes: 0-100(2), 100-200(5), 200-300(x), 300-400(12), 400-500(17), 500-600(20), 600-700(y), 700-800(9), 800-900(7), 900-1000(4).",
            "type": "Long Answer", "marks": 4, "diff": "Hard",
            "opts": None, "ans": "x = 9, y = 15",
            "sol": "Sum of frequencies = 76 + x + y = 100 ⇒ x + y = 24 ... (1) (1 Mark)\nMedian = 525 lies in class 500-600. So l = 500, f = 20, h = 100, cf preceding = 36 + x, N/2 = 50 (1.5 Marks)\nMedian = l + [(N/2 - cf)/f]*h ⇒ 525 = 500 + [(50 - (36 + x))/20]*100 (1 Mark)\n25 = (14 - x)*5 ⇒ 5 = 14 - x ⇒ x = 9.\nFrom (1), y = 24 - 9 = 15 (0.5 Mark)."
        },
        {
            "text": "Compute the Mean, Median, and Mode for the given grouped data and verify the empirical formula: Classes 0-10 (4), 10-20 (8), 20-30 (10), 30-40 (6), 40-50 (2).",
            "type": "Long Answer", "marks": 5, "diff": "Hard",
            "opts": None, "ans": "Mean = 22.67, Median = 23.0, Mode = 22.5. Verification: Mode ≈ 3(23.0) - 2(22.67) = 69 - 45.34 = 23.66.",
            "sol": "Step 1: Compute Mean: Σf = 30, Σfx = 4(5) + 8(15) + 10(25) + 6(35) + 2(45) = 20 + 120 + 250 + 210 + 90 = 690. Mean = 690/30 = 23.0 (1.5 Marks).\nStep 2: Compute Median: N/2 = 15. Median class 20-30. l=20, cf=12, f=10, h=10. Median = 20 + [(15-12)/10]*10 = 23.0 (1.5 Marks).\nStep 3: Compute Mode: Modal class 20-30. l=20, f1=10, f0=8, f2=6, h=10. Mode = 20 + [(10-8)/(20-8-6)]*10 = 20 + [2/6]*10 = 23.33 (1 Mark).\nStep 4: Empirical comparison: 3(Median) - 2(Mean) = 3(23) - 2(23) = 23 ≈ Mode (1 Mark)."
        },
        {
            "text": "During the medical check-up of 35 students of a class, their weights were recorded as less than 38 kg (0), less than 40 kg (3), less than 42 kg (5), less than 44 kg (9), less than 46 kg (14), less than 48 kg (28), less than 50 kg (32), less than 52 kg (35). Find the median weight by calculation.",
            "type": "Long Answer", "marks": 5, "diff": "Hard",
            "opts": None, "ans": "Median = 46.5 kg",
            "sol": "Convert cumulative distribution to continuous class intervals:\n38-40: 3, 40-42: 2, 42-44: 4, 44-46: 5, 46-48: 14, 48-50: 4, 50-52: 3 (2 Marks).\nTotal N = 35, N/2 = 17.5. Median class is 46-48 (cf = 28 > 17.5) (1 Mark).\nl = 46, cf = 14, f = 14, h = 2 (1 Mark).\nMedian = 46 + [(17.5 - 14)/14]*2 = 46 + [3.5/14]*2 = 46 + 0.5 = 46.5 kg (1 Mark)."
        }
    ]

    for q in stat_data:
        questions.append(Question(
            chapter_id=ch_stat.id,
            question_text=q["text"],
            question_type=q["type"],
            marks=q["marks"],
            difficulty=q["diff"],
            options_json=json.dumps(q["opts"]) if q["opts"] else None,
            correct_answer=q["ans"],
            explanation=q["sol"]
        ))

    # =========================================================================
    # CLASS 10 MATHEMATICS - PROBABILITY (16 Questions)
    # =========================================================================
    prob_data = [
        # 1-Mark MCQs
        {
            "text": "If P(E) = 0.05, what is the probability of 'not E'?",
            "type": "MCQ", "marks": 1, "diff": "Easy",
            "opts": ["A) 0.95", "B) 0.05", "C) 0.50", "D) 0.90"],
            "ans": "A) 0.95",
            "sol": "P(not E) = 1 - P(E) = 1 - 0.05 = 0.95."
        },
        {
            "text": "Which of the following cannot be the probability of an event?",
            "type": "MCQ", "marks": 1, "diff": "Easy",
            "opts": ["A) 2/3", "B) -1.5", "C) 15%", "D) 0.7"],
            "ans": "B) -1.5",
            "sol": "The probability of an event always satisfies 0 ≤ P(E) ≤ 1. It can never be negative."
        },
        {
            "text": "A card is drawn from a well-shuffled pack of 52 playing cards. The probability of getting a face card is:",
            "type": "MCQ", "marks": 1, "diff": "Easy",
            "opts": ["A) 3/13", "B) 1/13", "C) 4/13", "D) 9/52"],
            "ans": "A) 3/13",
            "sol": "Total face cards = 4 Kings + 4 Queens + 4 Jacks = 12. Probability = 12/52 = 3/13."
        },
        {
            "text": "A die is thrown once. The probability of getting a prime number is:",
            "type": "MCQ", "marks": 1, "diff": "Medium",
            "opts": ["A) 1/2", "B) 1/3", "C) 2/3", "D) 1/6"],
            "ans": "A) 1/2",
            "sol": "Prime numbers on a standard die are 2, 3, 5 (3 favorable outcomes). Probability = 3/6 = 1/2."
        },
        {
            "text": "Two coins are tossed simultaneously. What is the probability of getting at least one head?",
            "type": "MCQ", "marks": 1, "diff": "Medium",
            "opts": ["A) 3/4", "B) 1/4", "C) 1/2", "D) 1"],
            "ans": "A) 3/4",
            "sol": "Sample space S = {HH, HT, TH, TT} (4 outcomes). Favorable for at least one head = {HH, HT, TH} (3 outcomes). P = 3/4."
        },
        # 2-Mark Short Answer
        {
            "text": "A bag contains 3 red balls and 5 black balls. A ball is drawn at random from the bag. What is the probability that the ball drawn is (i) red, (ii) not red?",
            "type": "Short Answer", "marks": 2, "diff": "Easy",
            "opts": None, "ans": "(i) 3/8, (ii) 5/8",
            "sol": "Total balls = 3 + 5 = 8.\n(i) P(Red) = 3/8 (1 Mark).\n(ii) P(Not Red) = 1 - 3/8 = 5/8 (1 Mark)."
        },
        {
            "text": "A box contains 5 red marbles, 8 white marbles and 4 green marbles. One marble is taken out of the box at random. What is the probability that the marble taken out will be (i) white? (ii) not green?",
            "type": "Short Answer", "marks": 2, "diff": "Easy",
            "opts": None, "ans": "(i) 8/17, (ii) 13/17",
            "sol": "Total marbles = 5 + 8 + 4 = 17.\n(i) P(White) = 8/17 (1 Mark).\n(ii) P(Not green) = (5 + 8)/17 = 13/17 (1 Mark)."
        },
        {
            "text": "Two dice are rolled together. Find the probability that the sum of numbers appearing on the two dice is (i) 8, (ii) 13.",
            "type": "Short Answer", "marks": 2, "diff": "Medium",
            "opts": None, "ans": "(i) 5/36, (ii) 0",
            "sol": "Total possible outcomes = 36.\n(i) Sum 8 favorable pairs: (2,6), (3,5), (4,4), (5,3), (6,2) ⇒ 5 outcomes. P = 5/36 (1 Mark).\n(ii) Sum 13 is impossible (max sum is 6+6=12) ⇒ P = 0 (1 Mark)."
        },
        {
            "text": "A game consists of tossing a one-rupee coin 3 times and noting its outcome each time. Hanif wins if all the tosses give the same result (3 heads or 3 tails). Calculate the probability that Hanif will lose the game.",
            "type": "Short Answer", "marks": 2, "diff": "Medium",
            "opts": None, "ans": "3/4 (or 6/8)",
            "sol": "Total outcomes = 2³ = 8: {HHH, HHT, HTH, HTT, THH, THT, TTH, TTT}.\nWinning outcomes = {HHH, TTT} (2 outcomes).\nLosing outcomes = 8 - 2 = 6 outcomes. Probability of losing = 6/8 = 3/4 (2 Marks)."
        },
        # 3-Mark Short Answer II
        {
            "text": "One card is drawn from a well-shuffled deck of 52 cards. Find the probability of getting: (i) a king of red colour, (ii) a spade, (iii) the queen of diamonds.",
            "type": "Short Answer", "marks": 3, "diff": "Medium",
            "opts": None, "ans": "(i) 1/26, (ii) 1/4, (iii) 1/52",
            "sol": "(i) Red kings = 2 (King of Hearts, King of Diamonds). P = 2/52 = 1/26 (1 Mark).\n(ii) Spades in deck = 13. P = 13/52 = 1/4 (1 Mark).\n(iii) Queen of diamonds = 1. P = 1/52 (1 Mark)."
        },
        {
            "text": "A box contains 90 discs which are numbered from 1 to 90. If one disc is drawn at random, find the probability that it bears: (i) a two-digit number, (ii) a perfect square number, (iii) a number divisible by 5.",
            "type": "Short Answer", "marks": 3, "diff": "Medium",
            "opts": None, "ans": "(i) 9/10, (ii) 1/10, (iii) 1/5",
            "sol": "Total discs = 90.\n(i) Two digit numbers (10 to 90) = 81. P = 81/90 = 9/10 (1 Mark).\n(ii) Perfect squares {1, 4, 9, 16, 25, 36, 49, 64, 81} = 9. P = 9/90 = 1/10 (1 Mark).\n(iii) Numbers divisible by 5 {5, 10, ..., 90} = 18. P = 18/90 = 1/5 (1 Mark)."
        },
        {
            "text": "A lot consists of 144 ball pens of which 20 are defective and the others are good. Nuri will buy a pen if it is good, but will not buy if it is defective. The shopkeeper draws one pen at random and gives it to her. What is the probability that: (i) She will buy it? (ii) She will not buy it?",
            "type": "Short Answer", "marks": 3, "diff": "Hard",
            "opts": None, "ans": "(i) 31/36, (ii) 5/36",
            "sol": "Total pens = 144. Defective pens = 20. Good pens = 144 - 20 = 124 (1 Mark).\n(i) P(She will buy) = P(Good pen) = 124 / 144 = 31 / 36 (1 Mark).\n(ii) P(She will not buy) = P(Defective pen) = 20 / 144 = 5 / 36 (1 Mark)."
        },
        # 4/5-Mark Long Answer
        {
            "text": "Two dice, one blue and one grey, are thrown at the same time. (i) Write down all possible outcomes. (ii) What is the probability that the sum of the two numbers appearing on top of the dice is 8? (iii) What is the probability that the sum is less than or equal to 12? (iv) What is the probability of getting a doublet?",
            "type": "Long Answer", "marks": 4, "diff": "Medium",
            "opts": None, "ans": "(i) 36 outcomes, (ii) 5/36, (iii) 1, (iv) 1/6",
            "sol": "(i) Sample space has 6 x 6 = 36 outcomes: {(1,1), (1,2), ..., (6,6)} (1 Mark).\n(ii) Sum 8 = {(2,6), (3,5), (4,4), (5,3), (6,2)} (5 outcomes) ⇒ P = 5/36 (1 Mark).\n(iii) Sum ≤ 12 is a certain event (all 36 outcomes) ⇒ P = 36/36 = 1 (1 Mark).\n(iv) Doublets = {(1,1), (2,2), (3,3), (4,4), (5,5), (6,6)} (6 outcomes) ⇒ P = 6/36 = 1/6 (1 Mark)."
        },
        {
            "text": "Cards marked with numbers 3, 4, 5, ..., 50 are placed in a box and mixed thoroughly. One card is drawn at random from the box. Find the probability that the number on the drawn card is: (i) divisible by 7, (ii) a number which is a perfect square, (iii) a prime number less than 20, (iv) an odd number.",
            "type": "Long Answer", "marks": 4, "diff": "Hard",
            "opts": None, "ans": "(i) 7/48, (ii) 5/48, (iii) 7/48, (iv) 24/48 = 1/2",
            "sol": "Total cards from 3 to 50 = 50 - 3 + 1 = 48.\n(i) Divisible by 7: {7, 14, 21, 28, 35, 42, 49} (7 numbers) ⇒ P = 7/48 (1 Mark).\n(ii) Perfect squares: {4, 9, 16, 25, 36, 49} (6 numbers but note 1 not in set, so 4,9,16,25,36,49 = 6) ⇒ P = 6/48 = 1/8 (1 Mark).\n(iii) Primes < 20: {3, 5, 7, 11, 13, 17, 19} (7 numbers) ⇒ P = 7/48 (1 Mark).\n(iv) Odd numbers: 24 odd numbers from 3 to 50 ⇒ P = 24/48 = 1/2 (1 Mark)."
        },
        {
            "text": "A carton consists of 100 shirts of which 88 are good, 8 have minor defects and 4 have major defects. Jimmy, a trader, will only accept the shirts which are good, but Sujatha, another trader, will only reject the shirts which have major defects. One shirt is drawn at random from the carton. What is the probability that: (i) it is acceptable to Jimmy? (ii) it is acceptable to Sujatha?",
            "type": "Long Answer", "marks": 5, "diff": "Hard",
            "opts": None, "ans": "(i) 88/100 = 22/25 (0.88), (ii) 96/100 = 24/25 (0.96)",
            "sol": "Total shirts = 100.\n(i) Jimmy accepts only good shirts. Number of good shirts = 88.\nProbability acceptable to Jimmy = 88/100 = 22/25 = 0.88 (2.5 Marks).\n(ii) Sujatha accepts good shirts and shirts with minor defects (rejects major defects).\nAcceptable to Sujatha = 88 + 8 = 96 (or 100 - 4 = 96).\nProbability acceptable to Sujatha = 96/100 = 24/25 = 0.96 (2.5 Marks)."
        },
        {
            "text": "All kings, queens and aces are removed from a pack of 52 cards. The remaining cards are well shuffled and then a card is drawn from it. Find the probability that the drawn card is: (i) a black face card, (ii) a red card, (iii) a ten, (iv) a picture card.",
            "type": "Long Answer", "marks": 5, "diff": "Hard",
            "opts": None, "ans": "(i) 2/40 = 1/20, (ii) 20/40 = 1/2, (iii) 4/40 = 1/10, (iv) 4/40 = 1/10",
            "sol": "Cards removed: 4 Kings + 4 Queens + 4 Aces = 12 cards.\nRemaining cards = 52 - 12 = 40 cards (1 Mark).\n(i) Only Jacks remain as face cards. Black Jacks = 2. P = 2/40 = 1/20 (1 Mark).\n(ii) Red cards remaining = 26 - 6 (2 Kings, 2 Queens, 2 Aces) = 20. P = 20/40 = 1/2 (1 Mark).\n(iii) Tens in remaining pack = 4. P = 4/40 = 1/10 (1 Mark).\n(iv) Picture cards remaining = 4 Jacks. P = 4/40 = 1/10 (1 Mark)."
        }
    ]

    for q in prob_data:
        questions.append(Question(
            chapter_id=ch_prob.id,
            question_text=q["text"],
            question_type=q["type"],
            marks=q["marks"],
            difficulty=q["diff"],
            options_json=json.dumps(q["opts"]) if q["opts"] else None,
            correct_answer=q["ans"],
            explanation=q["sol"]
        ))

    # =========================================================================
    # CLASS 10 SCIENCE (Electricity & Light) - Bonus Real Questions
    # =========================================================================
    sci_data = [
        {
            "ch_id": ch_elec.id, "text": "What is the SI unit of electric potential difference?",
            "type": "MCQ", "marks": 1, "diff": "Easy", "opts": ["A) Ampere", "B) Volt", "C) Ohm", "D) Watt"],
            "ans": "B) Volt", "sol": "The SI unit of electric potential difference is the Volt (V)."
        },
        {
            "ch_id": ch_elec.id, "text": "State Ohm's Law and write its mathematical formula.",
            "type": "Short Answer", "marks": 2, "diff": "Easy", "opts": None,
            "ans": "V = IR", "sol": "Ohm's law states that current through a conductor between two points is directly proportional to voltage across the two points, provided temperature remains constant: V = IR."
        },
        {
            "ch_id": ch_elec.id, "text": "Three resistors of 2 Ω, 3 Ω and 6 Ω are connected in parallel. Calculate the equivalent resistance.",
            "type": "Short Answer", "marks": 3, "diff": "Medium", "opts": None,
            "ans": "1 Ω", "sol": "1/R = 1/2 + 1/3 + 1/6 = (3 + 2 + 1)/6 = 6/6 = 1 ⇒ R = 1 Ω."
        },
        {
            "ch_id": ch_elec.id, "text": "An electric heater rated 1000 W operates 2 hours daily. Find the cost of energy for 30 days at ₹ 5 per unit (kWh).",
            "type": "Long Answer", "marks": 4, "diff": "Medium", "opts": None,
            "ans": "₹ 300", "sol": "Energy per day = 1 kW * 2 h = 2 kWh. Total energy in 30 days = 2 * 30 = 60 kWh. Total cost = 60 * ₹5 = ₹300."
        },
        {
            "ch_id": ch_light.id, "text": "The focal length of a convex mirror is 20 cm. Its radius of curvature is:",
            "type": "MCQ", "marks": 1, "diff": "Easy", "opts": ["A) 10 cm", "B) 20 cm", "C) 40 cm", "D) 80 cm"],
            "ans": "C) 40 cm", "sol": "Radius of curvature R = 2f = 2 * 20 = 40 cm."
        },
        {
            "ch_id": ch_light.id, "text": "State Snell's Law of refraction of light.",
            "type": "Short Answer", "marks": 2, "diff": "Easy", "opts": None,
            "ans": "sin i / sin r = constant (refractive index n)", "sol": "Snell's law states that the ratio of sine of angle of incidence to sine of angle of refraction is a constant for a given pair of media."
        },
        {
            "ch_id": ch_light.id, "text": "An object 4 cm in size is placed at 25 cm in front of a concave mirror of focal length 15 cm. Find position and nature of image.",
            "type": "Short Answer", "marks": 3, "diff": "Medium", "opts": None,
            "ans": "v = -37.5 cm, Real and Inverted", "sol": "1/v + 1/u = 1/f ⇒ 1/v - 1/25 = -1/15 ⇒ 1/v = -1/15 + 1/25 = -2/75 ⇒ v = -37.5 cm."
        },
        {
            "ch_id": ch_light.id, "text": "Explain why the sky appears blue to an observer on Earth, but appears dark/black to an astronaut in space.",
            "type": "Long Answer", "marks": 4, "diff": "Medium", "opts": None,
            "ans": "Rayleigh scattering by atmosphere molecules; absence of atmosphere in space.",
            "sol": "Shorter wavelengths (blue) are scattered much more by gas molecules in Earth's atmosphere. In space, there is no atmosphere to scatter sunlight, so the sky appears black."
        }
    ]

    for q in sci_data:
        questions.append(Question(
            chapter_id=q["ch_id"],
            question_text=q["text"],
            question_type=q["type"],
            marks=q["marks"],
            difficulty=q["diff"],
            options_json=json.dumps(q["opts"]) if q["opts"] else None,
            correct_answer=q["ans"],
            explanation=q["sol"]
        ))

    db.session.add_all(questions)
    db.session.commit()

    # 4. Seed initial practice test history and topic performance for Google Student
    # to demonstrate weakness identification and mistake diagnosis
    trig_qs = Question.query.filter_by(chapter_id=ch_trig.id).order_by(Question.id.asc()).limit(3).all()
    stat_qs = Question.query.filter_by(chapter_id=ch_stat.id).order_by(Question.id.asc()).limit(2).all()
    
    if trig_qs and stat_qs:
        paper1 = PracticePaper(
            student_id=student_google.id,
            subject_id=math10.id,
            title="Class 10 Mathematics Diagnostic Practice Set",
            total_marks=7,
            duration_minutes=0,
            difficulty_preference="Mixed",
            generation_mode="Curriculum",
            selected_chapters_json=json.dumps([ch_trig.id, ch_stat.id]),
            status='submitted',
            total_score=3.0,
            percentage=42.9,
            submitted_at=datetime.now(timezone.utc)
        )
        db.session.add(paper1)
        db.session.flush()

        # Paper questions
        pq1 = PaperQuestion(paper_id=paper1.id, question_id=trig_qs[0].id, order_index=1, marks_allocated=trig_qs[0].marks)
        pq2 = PaperQuestion(paper_id=paper1.id, question_id=trig_qs[1].id, order_index=2, marks_allocated=trig_qs[1].marks)
        pq3 = PaperQuestion(paper_id=paper1.id, question_id=trig_qs[2].id, order_index=3, marks_allocated=trig_qs[2].marks)
        pq4 = PaperQuestion(paper_id=paper1.id, question_id=stat_qs[0].id, order_index=4, marks_allocated=stat_qs[0].marks)
        pq5 = PaperQuestion(paper_id=paper1.id, question_id=stat_qs[1].id, order_index=5, marks_allocated=stat_qs[1].marks)
        
        db.session.add_all([pq1, pq2, pq3, pq4, pq5])
        db.session.flush()

        # Responses with realistic mistakes in Trigonometry
        resp1 = QuestionResponse(
            paper_question_id=pq1.id,
            student_answer="B) 1",
            marks_obtained=0.0,
            feedback="Incorrect option chosen. Used wrong identity for cos 30°.",
            submitted_at=datetime.now(timezone.utc)
        )
        resp2 = QuestionResponse(
            paper_question_id=pq2.id,
            student_answer=trig_qs[1].correct_answer,
            marks_obtained=float(pq2.marks_allocated),
            feedback="Correct formula application.",
            submitted_at=datetime.now(timezone.utc)
        )
        resp3 = QuestionResponse(
            paper_question_id=pq3.id,
            student_answer="Calculation error: (sin θ + cos θ)/(sin θ - cos θ) = 5",
            marks_obtained=0.0,
            feedback="Calculation error in ratio simplification.",
            submitted_at=datetime.now(timezone.utc)
        )
        resp4 = QuestionResponse(
            paper_question_id=pq4.id,
            student_answer=stat_qs[0].correct_answer,
            marks_obtained=float(pq4.marks_allocated),
            feedback="Correct mean calculation.",
            submitted_at=datetime.now(timezone.utc)
        )
        resp5 = QuestionResponse(
            paper_question_id=pq5.id,
            student_answer=stat_qs[1].correct_answer,
            marks_obtained=float(pq5.marks_allocated),
            feedback="Accurate formula and calculation.",
            submitted_at=datetime.now(timezone.utc)
        )

        db.session.add_all([resp1, resp2, resp3, resp4, resp5])

        # Topic performances
        perf_trig = TopicPerformance(
            student_id=student_google.id,
            chapter_id=ch_trig.id,
            latest_score_percentage=33.3,
            mastery_score=33.3,
            total_marks_obtained=1.0,
            total_marks_available=3.0,
            number_of_attempts=1,
            status_classification='Weak'
        )
        perf_stat = TopicPerformance(
            student_id=student_google.id,
            chapter_id=ch_stat.id,
            latest_score_percentage=100.0,
            mastery_score=100.0,
            total_marks_obtained=4.0,
            total_marks_available=4.0,
            number_of_attempts=1,
            status_classification='Strong'
        )
        db.session.add_all([perf_trig, perf_stat])
        db.session.commit()

    print(f"Successfully seeded database with {len(questions)} high-quality questions across {Chapter.query.count()} chapters!")

if __name__ == '__main__':
    from flask import Flask
    from config import Config
    
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        seed_database()
