from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask import jsonify
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy as sa
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from datetime import timedelta, datetime
import os
from dotenv import load_dotenv

# Flask app configured to serve static files using absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'public')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
app = Flask(__name__, static_folder=STATIC_DIR, template_folder=TEMPLATES_DIR)

# Database config: Use DATABASE_URL if provided (e.g., mysql+pymysql://user:pass@host/dbname)
load_dotenv()  # Load variables from .env if present
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    db_url = 'sqlite:///school.db'
app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# IMPORTANT: change this in production and/or load from environment variable
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'change-this-secret')
app.permanent_session_lifetime = timedelta(hours=8)

db = SQLAlchemy(app)

# Startup schema guard: ensure legacy 'section' columns exist (restore)
def _ensure_section_columns():
    try:
        insp = sa.inspect(db.engine)
        # Admissions
        adm_cols = {c['name'] for c in insp.get_columns('admissions')}
        if 'section' not in adm_cols:
            dialect = db.engine.url.get_dialect().name
            if dialect.startswith('mysql'):
                db.session.execute(sa.text('ALTER TABLE admissions ADD COLUMN section VARCHAR(10) NULL'))
            else:
                db.session.execute(sa.text('ALTER TABLE admissions ADD COLUMN section TEXT'))
            db.session.commit()
        # Students
        stu_cols = {c['name'] for c in insp.get_columns('students')}
        if 'section' not in stu_cols:
            dialect = db.engine.url.get_dialect().name
            if dialect.startswith('mysql'):
                db.session.execute(sa.text('ALTER TABLE students ADD COLUMN section VARCHAR(10) NULL'))
            else:
                db.session.execute(sa.text('ALTER TABLE students ADD COLUMN section TEXT'))
            db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass

with app.app_context():
    _ensure_section_columns()
# Lightweight schema guard: add admissions.password if missing
def _ensure_admissions_password_column():
    try:
        insp = sa.inspect(db.engine)
        cols = {c['name'] for c in insp.get_columns('admissions')}
        if 'password' not in cols:
            dialect = db.engine.url.get_dialect().name
            if dialect.startswith('mysql'):
                db.session.execute(sa.text('ALTER TABLE admissions ADD COLUMN password VARCHAR(128) NULL'))
            else:
                db.session.execute(sa.text('ALTER TABLE admissions ADD COLUMN password TEXT'))
            db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass

with app.app_context():
    _ensure_admissions_password_column()

# Ensure teacher initial_password column exists
def _ensure_teacher_initial_password_column():
    try:
        insp = sa.inspect(db.engine)
        cols = {c['name'] for c in insp.get_columns('teachers')}
        if 'initial_password' not in cols:
            dialect = db.engine.url.get_dialect().name
            if dialect.startswith('mysql'):
                db.session.execute(sa.text('ALTER TABLE teachers ADD COLUMN initial_password VARCHAR(128) NULL'))
            else:
                db.session.execute(sa.text('ALTER TABLE teachers ADD COLUMN initial_password TEXT'))
            db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass

with app.app_context():
    _ensure_teacher_initial_password_column()
    # Create tables if missing for newly added models
    try:
        db.create_all()
    except Exception:
        pass


class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    roll_no = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    admission_code = db.Column(db.String(50), nullable=True)

    # Optional profile fields
    class_name = db.Column(db.String(50), nullable=True)
    section = db.Column(db.String(10), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.Text, nullable=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Teacher(db.Model):
    __tablename__ = 'teachers'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    # Store the initially generated password for admin visibility
    initial_password = db.Column(db.String(128), nullable=True)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class ClassSection(db.Model):
    __tablename__ = 'class_sections'
    id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.String(50), nullable=False)
    section = db.Column(db.String(10), nullable=True)


class Subject(db.Model):
    __tablename__ = 'subjects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    class_section_id = db.Column(db.Integer, db.ForeignKey('class_sections.id'), nullable=True)


class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=True)
    date = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    status = db.Column(db.String(10), nullable=False)  # Present/Absent
    marked_by_teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)


class Result(db.Model):
    __tablename__ = 'results'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    term = db.Column(db.String(50), nullable=False)
    marks_obtained = db.Column(db.Float, nullable=False)
    max_marks = db.Column(db.Float, nullable=False)
    graded_by_teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)


class FeePayment(db.Model):
    __tablename__ = 'fee_payments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    mode = db.Column(db.String(30), nullable=True)  # UPI/Cash/Card/etc
    reference_no = db.Column(db.String(100), nullable=True)
    recorded_by_teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)


# --- Academic extensions ---
class StudentSubject(db.Model):
    __tablename__ = 'student_subjects'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('student_id', 'subject_id', name='uq_student_subject'),)


class Assessment(db.Model):
    __tablename__ = 'assessments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    component = db.Column(db.String(50), nullable=False)  # Unit Test, Term, Practical, Project, etc.
    term = db.Column(db.String(50), nullable=True)
    score = db.Column(db.Float, nullable=False)
    max_score = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=True)


class SportsActivity(db.Model):
    __tablename__ = 'sports_activities'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    activity = db.Column(db.String(100), nullable=False)  # e.g., Football, Athletics 100m
    level = db.Column(db.String(50), nullable=True)  # School/Zonal/District/State/National
    result = db.Column(db.String(100), nullable=True)  # Participated/1st/2nd/3rd
    date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.String(200), nullable=True)
    recorded_by_teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=True)


# Track admissions (applications and confirmations)
class Admission(db.Model):
    __tablename__ = 'admissions'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending | confirmed | rejected
    admission_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Basic applicant fields (for student creation upon confirm)
    roll_no = db.Column(db.String(50), unique=True, nullable=True)  # optional until confirmed
    name = db.Column(db.String(120), nullable=False)
    class_name = db.Column(db.String(50), nullable=True)
    section = db.Column(db.String(10), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.Text, nullable=True)
    password = db.Column(db.String(128), nullable=True)

    # Link to created student when confirmed
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=True)

# Track login attempts for auditing
class LoginAudit(db.Model):
    __tablename__ = 'login_audit'
    id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.String(20), nullable=False)  # 'teacher' or 'student'
    username = db.Column(db.String(120), nullable=True)
    user_id = db.Column(db.Integer, nullable=True)
    success = db.Column(db.Boolean, default=False)
    ip_address = db.Column(db.String(100), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# Simple Admin model for RBAC
class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

# A unified users table for authentication across student/teacher/admin
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False)  # 'student' | 'teacher' | 'admin'
    username = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Optional student-centric fields (nullable to keep one-table design simple)
    admission_code = db.Column(db.String(50), nullable=True)
    class_name = db.Column(db.String(50), nullable=True)
    section = db.Column(db.String(10), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

# --------------- Utility helpers ---------------

def _mask_db_url(uri: str) -> str:
    """Mask password in DB URI for safe logging."""
    if not uri:
        return uri
    try:
        # Only mask patterns like scheme://user:password@host/...
        if '://' in uri and '@' in uri and ':' in uri.split('://', 1)[1].split('@', 1)[0]:
            scheme, rest = uri.split('://', 1)
            creds, tail = rest.split('@', 1)
            if ':' in creds:
                user, _ = creds.split(':', 1)
                creds_masked = f"{user}:***"
                return f"{scheme}://{creds_masked}@{tail}"
        return uri
    except Exception:
        return uri

def login_required(view_func):
    from functools import wraps

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if 'student_id' not in session:
            flash('Please login to continue', 'warning')
            return redirect(url_for('student_login'))
        return view_func(*args, **kwargs)

    return wrapper


def admin_required(view_func):
    from functools import wraps

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please login as admin to continue', 'warning')
            return redirect(url_for('admin_login'))
        return view_func(*args, **kwargs)

    return wrapper


# Teacher auth decorator (ensure available before any teacher routes)
def teacher_required(view_func):
    from functools import wraps

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if 'teacher_id' not in session:
            flash('Please login as teacher to continue', 'warning')
            return redirect(url_for('teacher_login'))
        return view_func(*args, **kwargs)

    return wrapper


# --------------- Routes ---------------

@app.route('/')
def home():
    # Serve your existing landing page in public/index.html
    return send_from_directory(app.static_folder, 'index.html')


# Explicit static route to serve assets from the public/ directory
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        roll_no = request.form.get('roll_no', '').strip()
        password = request.form.get('password', '')

        # 1) Try Admission-based authentication first (roll_no + Admission.password)
        adm = Admission.query.filter_by(roll_no=roll_no).first()
        if adm and adm.status == 'confirmed' and (adm.password or '') and password == adm.password:
            # Ensure Student exists/sync from Admission
            student = Student.query.filter_by(roll_no=roll_no).first()
            if not student:
                student = Student(
                    roll_no=roll_no,
                    name=adm.name or roll_no,
                    class_name=adm.class_name,
                    section=adm.section,
                    phone=adm.phone,
                    email=adm.email,
                    address=adm.address,
                )
                # Set student's password to match admission password for consistency
                student.set_password(adm.password)
                db.session.add(student)
                db.session.commit()

            # Ensure unified User exists/sync
            u = User.query.filter_by(role='student', username=roll_no).first()
            if not u:
                u = User(
                    role='student', username=roll_no, name=adm.name or roll_no, email=adm.email,
                    admission_code=None, class_name=adm.class_name, section=adm.section,
                    phone=adm.phone, address=adm.address,
                )
                u.password_hash = student.password_hash
                db.session.add(u)
                db.session.commit()

            session.permanent = True
            session['student_id'] = student.id
            # Audit success
            LoginAudit.query.filter_by(user_type='student', username=roll_no).delete()
            db.session.add(LoginAudit(
                user_type='student', username=roll_no, user_id=u.id if u else None,
                success=True, ip_address=request.remote_addr, user_agent=request.headers.get('User-Agent')
            ))
            db.session.commit()
            return redirect(url_for('student_dashboard'))

        # If admission exists but not confirmed, block login with a clear message
        if adm and adm.status != 'confirmed':
            LoginAudit.query.filter_by(user_type='student', username=roll_no).delete()
            db.session.add(LoginAudit(
                user_type='student', username=roll_no, user_id=None,
                success=False, ip_address=request.remote_addr, user_agent=request.headers.get('User-Agent')
            ))
            db.session.commit()
            flash('Your admission is not confirmed yet. Please contact the school.', 'warning')
            return redirect(url_for('student_login'))

        # 2) Fallback: legacy authentication against unified users table
        u = User.query.filter_by(role='student', username=roll_no).first()
        if u and u.check_password(password):
            student = Student.query.filter_by(roll_no=roll_no).first()
            if not student:
                student = Student(roll_no=roll_no, name=u.name or roll_no)
                student.password_hash = u.password_hash
                db.session.add(student)
                db.session.commit()

            session.permanent = True
            session['student_id'] = student.id
            LoginAudit.query.filter_by(user_type='student', username=roll_no).delete()
            db.session.add(LoginAudit(
                user_type='student', username=roll_no, user_id=u.id,
                success=True, ip_address=request.remote_addr, user_agent=request.headers.get('User-Agent')
            ))
            db.session.commit()
            return redirect(url_for('student_dashboard'))

        # If both methods fail, record failure and show message
        LoginAudit.query.filter_by(user_type='student', username=roll_no).delete()
        db.session.add(LoginAudit(
            user_type='student', username=roll_no, user_id=u.id if 'u' in locals() and u else None,
            success=False, ip_address=request.remote_addr, user_agent=request.headers.get('User-Agent')
        ))
        db.session.commit()
        flash('Invalid roll number or password', 'danger')
        return redirect(url_for('student_login'))

    return render_template('student_login.html')


@app.route('/student/dashboard')
@login_required
def student_dashboard():
    # Get the logged-in student
    sid = session.get('student_id')
    student = Student.query.get(sid)
    if not student:
        session.clear()
        flash('Session expired. Please login again.', 'warning')
        return redirect(url_for('student_login'))

    # Attendance percentage
    total_att = Attendance.query.filter_by(student_id=student.id).count()
    present_att = Attendance.query.filter_by(student_id=student.id, status='Present').count()
    attendance_pct = round((present_att / total_att) * 100, 1) if total_att else 0

    # Last score (most recent result)
    last_res = Result.query.filter_by(student_id=student.id).order_by(Result.id.desc()).first()
    if last_res and last_res.max_marks:
        last_score = f"{round((last_res.marks_obtained / last_res.max_marks) * 100)}%"
    elif last_res:
        last_score = str(int(last_res.marks_obtained))
    else:
        last_score = "-"

    # Total fees paid
    total_fees_paid = db.session.query(db.func.coalesce(db.func.sum(FeePayment.amount), 0)).filter(
        FeePayment.student_id == student.id
    ).scalar() or 0
    # Show as integer if whole number, else 2 decimals
    total_fees_paid = int(total_fees_paid) if float(total_fees_paid).is_integer() else round(float(total_fees_paid), 2)

    # Term label based on current month
    now = datetime.utcnow()
    term_label = ("SUMMER" if now.month in (4,5,6,7,8,9) else "WINTER") + f" {now.year}"

    return render_template(
        'student_dashboard.html',
        student=student,
        attendance_pct=attendance_pct,
        last_score=last_score,
        total_fees_paid=total_fees_paid,
        term_label=term_label,
    )


@app.route('/student/logout')
@login_required
def student_logout():
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect(url_for('student_login'))

@app.route('/teacher/assessments')
@teacher_required
def teacher_assessments():
    assessments = Assessment.query.order_by(Assessment.id.desc()).limit(200).all()
    return render_template('teacher_assessments.html', assessments=assessments)

@app.route('/teacher/assessment/<int:assessment_id>/edit', methods=['GET', 'POST'])
@teacher_required
def teacher_edit_assessment(assessment_id):
    assessment = Assessment.query.get(assessment_id)
    if not assessment:
        flash('Assessment not found', 'danger')
        return redirect(url_for('teacher_assessments'))

    if request.method == 'POST':
        assessment.marks_obtained = int(request.form.get('marks_obtained', '').strip())
        assessment.total_marks = int(request.form.get('total_marks', '').strip())

        try:
            db.session.commit()
            flash('Assessment updated successfully', 'success')
        except Exception:
            db.session.rollback()
            flash('Failed to update assessment', 'danger')
        return redirect(url_for('teacher_assessments'))
    return render_template('teacher_edit_assessment.html', assessment=assessment)

@app.route('/teacher/attendance/summary')
@teacher_required
def teacher_attendance_summary():
    attendance_summary = db.session.query(Attendance.student_id, db.func.count(Attendance.id), db.func.sum(db.case([(Attendance.status == 'Present', 1)], else_=0))).group_by(Attendance.student_id).all()
    return render_template('teacher_attendance_summary.html', attendance_summary=attendance_summary)

# (removed duplicate early definition of teacher_dashboard)


# -------- Helpers: Admission password generation --------
def _gen_admission_password(student_name: str | None, phone: str | None) -> str:
    try:
        import secrets, string
        # Take exactly 2 letters from name (A-Z), pad with 'X' if less
        name_raw = (student_name or '').strip().upper()
        name_part = ''.join(ch for ch in name_raw if ch.isalpha())[:2]
        if len(name_part) < 2:
            name_part = (name_part + 'X')[:2]
        # One digit from phone (last), or random digit if absent
        phone_digit = ''.join(ch for ch in (phone or '') if ch.isdigit())[-2:]
        if not phone_digit:
            phone_digit = secrets.choice(string.digits)
        # Pattern: TES + 2 letters + 1 digit = 6 chars total
        pwd = f"TES{name_part}{phone_digit}"
        # Ensure strictly 6 length
        return pwd[:7]
    except Exception:
        return 'TES1XX'

# -------- Public: Online Admission Application --------
@app.route('/admissions/apply', methods=['POST'])
def public_admission_apply():
    """Accept an online admission application and store it as a pending Admission.
    Expects JSON or form data from the public site.
    Maps fields from the public form to the Admission model.
    """
    try:
        data = request.get_json(silent=True) or request.form or {}

        name = (data.get('studentName') or data.get('name') or '').strip()
        class_name = (data.get('class') or data.get('class_name') or '').strip() or None
        section = (data.get('section') or '').strip() or None
        phone = (data.get('fatherPhone') or data.get('phone') or '').strip() or None
        email = (data.get('email') or '').strip() or None
        address = (data.get('address') or '').strip() or None
        status_in = (data.get('status') or '').strip().lower()
        status_val = 'pending'
        if status_in in ('pending','confirmed','rejected'):
            status_val = status_in

        # Generate password for online admissions when phone is present
        gen_password = _gen_admission_password(name, phone) if phone else None

        if not name:
            return jsonify({"success": False, "error": "studentName (name) is required"}), 400

        adm = Admission(
            name=name,
            class_name=class_name,
            section=section,
            phone=phone,
            email=email,
            address=address,
            status=status_val,
            password=gen_password,
        )
        db.session.add(adm)
        db.session.commit()

        return jsonify({"success": True, "admission_id": adm.id})
    except Exception as e:
        # Don't expose internals; log in real apps
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({"success": False, "error": "failed to save application"}), 500


# -------- Teacher auth helpers --------
def teacher_required(view_func):
    from functools import wraps

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if 'teacher_id' not in session:
            flash('Please login as teacher to continue', 'warning')
            return redirect(url_for('teacher_login'))
        return view_func(*args, **kwargs)

    return wrapper


@app.route('/teacher/login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        u = User.query.filter_by(role='teacher', username=username).first()
        if not u or not u.check_password(password):
            # Keep only the latest audit entry per user
            LoginAudit.query.filter_by(user_type='teacher', username=username).delete()
            db.session.add(LoginAudit(
                user_type='teacher', username=username, user_id=u.id if u else None,
                success=False, ip_address=request.remote_addr, user_agent=request.headers.get('User-Agent')
            ))
            db.session.commit()
            flash('Invalid username or password', 'danger')
            return redirect(url_for('teacher_login'))

        # Map to existing Teacher record for dashboard compatibility
        t = Teacher.query.filter_by(username=username).first()
        if not t:
            t = Teacher(username=username, name=u.name or username, email=u.email)
            t.password_hash = u.password_hash
            db.session.add(t)
            db.session.commit()

        session['teacher_id'] = t.id
        session.permanent = True
        # Keep only the latest audit entry per user
        LoginAudit.query.filter_by(user_type='teacher', username=username).delete()
        db.session.add(LoginAudit(
            user_type='teacher', username=username, user_id=u.id,
            success=True, ip_address=request.remote_addr, user_agent=request.headers.get('User-Agent')
        ))
        db.session.commit()
        return redirect(url_for('teacher_dashboard'))
    return render_template('teacher_login.html')


@app.route('/teacher/profile', methods=['GET', 'POST'])
@teacher_required
def teacher_update_profile():
    # View and update the logged-in teacher's profile
    t = Teacher.query.get(session.get('teacher_id'))
    if not t:
        flash('Session expired. Please login again.', 'warning')
        return redirect(url_for('teacher_login'))
    u = User.query.filter_by(role='teacher', username=t.username).first()

    if request.method == 'GET':
        return render_template('teacher_profile.html', teacher=t, user=u)

    # POST: update fields
    name = (request.form.get('name') or '').strip() or t.name
    email = (request.form.get('email') or '').strip() or None
    phone = (request.form.get('phone') or '').strip() or None

    t.name = name
    t.email = email
    if u:
        u.name = name
        u.email = email
        u.phone = phone

    # Optional password change
    new_password = (request.form.get('new_password') or '').strip()
    confirm_password = (request.form.get('confirm_password') or '').strip()
    if new_password:
        if new_password != confirm_password:
            db.session.rollback()
            flash('New password and confirm password do not match.', 'danger')
            return redirect(url_for('teacher_update_profile'))
        # Set password on both User and Teacher (hash kept in sync)
        if u:
            u.set_password(new_password)
            t.password_hash = u.password_hash
        else:
            t.set_password(new_password)

    try:
        db.session.commit()
        flash('Profile updated successfully.', 'success')
    except Exception:
        db.session.rollback()
        flash('Failed to update profile.', 'danger')
    return redirect(url_for('teacher_update_profile'))


@app.route('/teacher/students/new', methods=['POST'])
@teacher_required
def teacher_create_student():
    # Allow teachers to add a new student with minimal details
    roll_no = (request.form.get('roll_no') or '').strip()
    name = (request.form.get('name') or '').strip()
    class_name = (request.form.get('class_name') or '').strip() or None
    section = (request.form.get('section') or '').strip() or None
    phone = (request.form.get('phone') or '').strip() or None
    email = (request.form.get('email') or '').strip() or None
    address = (request.form.get('address') or '').strip() or None

    if not roll_no or not name:
        flash('Roll No and Name are required to create a student.', 'danger')
        return redirect(url_for('teacher_dashboard'))

    # Prevent duplicates across Student and User
    if Student.query.filter_by(roll_no=roll_no).first() or User.query.filter_by(username=roll_no).first():
        flash('A student with this Roll No already exists.', 'danger')
        return redirect(url_for('teacher_dashboard'))

    # Generate initial password similar to admissions pattern
    gen_password = _gen_admission_password(name, phone or roll_no)

    # Create Student
    s = Student(roll_no=roll_no, name=name, class_name=class_name, section=section, phone=phone, email=email, address=address)
    s.set_password(gen_password)
    db.session.add(s)
    db.session.commit()

    # Ensure unified User exists for the student
    u = User(role='student', username=roll_no, name=name, email=email, admission_code=None,
             class_name=class_name, section=section, phone=phone, address=address)
    u.password_hash = s.password_hash
    db.session.add(u)
    db.session.commit()

    flash(f'Student created. Initial password: {gen_password}', 'success')
    return redirect(url_for('teacher_dashboard'))
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        u = User.query.filter_by(role='admin', username=username).first()
        if not u or not u.check_password(password):
            # Keep only the latest audit entry per user
            LoginAudit.query.filter_by(user_type='admin', username=username).delete()
            db.session.add(LoginAudit(
                user_type='admin', username=username, user_id=u.id if u else None,
                success=False, ip_address=request.remote_addr, user_agent=request.headers.get('User-Agent')
            ))
            db.session.commit()
            flash('Invalid username or password', 'danger')
            return redirect(url_for('admin_login'))

        # Map to existing Admin record for dashboard compatibility
        a = Admin.query.filter_by(username=username).first()
        if not a:
            a = Admin(username=username, name=u.name or username, email=u.email)
            a.password_hash = u.password_hash
            db.session.add(a)
            db.session.commit()

        session['admin_id'] = a.id
        session.permanent = True
        # Keep only the latest audit entry per user
        LoginAudit.query.filter_by(user_type='admin', username=username).delete()
        db.session.add(LoginAudit(
            user_type='admin', username=username, user_id=u.id,
            success=True, ip_address=request.remote_addr, user_agent=request.headers.get('User-Agent')
        ))
        db.session.commit()
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_login.html')


@app.route('/admin/logout')
@admin_required
def admin_logout():
    session.pop('admin_id', None)
    flash('Logged out', 'info')
    return redirect(url_for('admin_login'))


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    # Simple overview for now
    teacher_count = Teacher.query.count()
    student_count = Student.query.count()
    last_logins = LoginAudit.query.order_by(LoginAudit.timestamp.desc()).limit(10).all()
    users_count = User.query.count()
    admissions_count = Admission.query.filter_by(status='confirmed').count()
    return render_template('admin_dashboard.html', teacher_count=teacher_count, student_count=student_count, users_count=users_count, admissions_count=admissions_count, last_logins=last_logins)


# ------- Admin: Students -------
@app.route('/admin/students')
@admin_required
def admin_students_list():
    page = max(int(request.args.get('page', 1) or 1), 1)
    per_page = 25
    q = (request.args.get('q') or '').strip()
    # If use_admissions=1 (default), we list from Admission table (all statuses),
    # so "whatever admission records are there" appear in the Students list view.
    use_admissions = (request.args.get('use_admissions', '1') or '1').strip()
    admissions_only = (request.args.get('admissions_only', '0') or '0').strip()

    if use_admissions in ('1','true','yes','on'):
        # Source rows from Admission table so every application shows, regardless of status
        query = Admission.query
        if q:
            like = f"%{q}%"
            query = query.filter(db.or_(Admission.name.ilike(like), Admission.roll_no.ilike(like)))
        total = query.count()
        rows = query.order_by(Admission.admission_date.desc()).offset((page-1)*per_page).limit(per_page).all()
        pages = (total + per_page - 1) // per_page
        # Render using the same template; it references fields (roll_no, name, class_name, section, phone, email) that Admission also has
        return render_template('admin_students.html', students=rows, page=page, pages=pages, total=total, q=q, admissions_only=use_admissions)
    else:
        # Legacy: list from Student table; optionally restrict to confirmed admissions
        query = Student.query
        if admissions_only in ('1', 'true', 'yes', 'on'):
            query = query.join(Admission, Admission.roll_no == Student.roll_no).filter(Admission.status == 'confirmed')
        if q:
            like = f"%{q}%"
            query = query.filter(
                db.or_(Student.roll_no.ilike(like), Student.name.ilike(like), Student.email.ilike(like))
            )
        total = query.count()
        students = query.order_by(Student.class_name, Student.section, Student.roll_no).offset((page-1)*per_page).limit(per_page).all()
        pages = (total + per_page - 1) // per_page
        return render_template('admin_students.html', students=students, page=page, pages=pages, total=total, q=q, admissions_only=admissions_only)


@app.route('/admin/students/export')
@admin_required
def admin_students_export():
    import csv
    from io import StringIO
    q = (request.args.get('q') or '').strip()
    query = Student.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(Student.roll_no.ilike(like), Student.name.ilike(like), Student.email.ilike(like))
        )
    rows = query.order_by(Student.roll_no).all()
    sio = StringIO()
    writer = csv.writer(sio)
    writer.writerow(['roll_no','name','class_name','section','phone','email','address'])
    for s in rows:
        writer.writerow([s.roll_no, s.name, s.class_name or '', s.section or '', s.phone or '', s.email or '', (s.address or '').replace('\n',' ')])
    out = sio.getvalue()
    from flask import Response
    return Response(out, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=students.csv'})


# ------- Admin: Teachers -------
@app.route('/admin/teachers')
@admin_required
def admin_teachers_list():
    page = max(int(request.args.get('page', 1) or 1), 1)
    per_page = 25
    q = (request.args.get('q') or '').strip()

    query = Teacher.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(Teacher.username.ilike(like), Teacher.name.ilike(like), Teacher.email.ilike(like))
        )
    total = query.count()
    teachers = query.order_by(Teacher.username).offset((page-1)*per_page).limit(per_page).all()
    # Build a username->User map to expose phone/email in template if needed
    usernames = [t.username for t in teachers]
    users = {u.username: u for u in User.query.filter(User.role=='teacher', User.username.in_(usernames)).all()}
    pages = (total + per_page - 1) // per_page
    return render_template('admin_teachers.html', teachers=teachers, users=users, page=page, pages=pages, total=total, q=q)


@app.route('/admin/teachers/new', methods=['GET', 'POST'])
@admin_required
def admin_teachers_new():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        name = (request.form.get('name') or '').strip() or username
        email = (request.form.get('email') or '').strip() or None
        phone = (request.form.get('phone') or '').strip() or None

        if not username:
            flash('Username is required', 'danger')
            return redirect(url_for('admin_teachers_new'))

        # Avoid duplicates (check across ALL users regardless of role)
        if Teacher.query.filter_by(username=username).first() or User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose a different username.', 'danger')
            return redirect(url_for('admin_teachers_new'))

        # Generate teacher password (reuse admission generator using phone if available, else username)
        contact = phone or username
        gen_password = _gen_admission_password(name, contact)

        # Create unified User first
        u = User(role='teacher', username=username, name=name, email=email, phone=phone)
        u.set_password(gen_password)
        db.session.add(u)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('Username already exists. Please choose a different username.', 'danger')
            return redirect(url_for('admin_teachers_new'))

        # Create Teacher record and sync password hash
        t = Teacher(username=username, name=name, email=email)
        t.password_hash = u.password_hash
        t.initial_password = gen_password
        db.session.add(t)
        db.session.commit()

        flash(f'Teacher created. Initial password: {gen_password}', 'success')
        return redirect(url_for('admin_teachers_list'))

    return render_template('admin_teacher_new.html')

@app.route('/admin/teachers/export')
@admin_required
def admin_teachers_export():
    import csv
    from io import StringIO
    q = (request.args.get('q') or '').strip()
    query = Teacher.query
    if q:
        like = f"%{q}%"
        query = query.filter(
            db.or_(Teacher.username.ilike(like), Teacher.name.ilike(like), Teacher.email.ilike(like))
        )
    rows = query.order_by(Teacher.username).all()
    sio = StringIO()
    writer = csv.writer(sio)
    # Join with user to include phone
    user_map = {u.username: u for u in User.query.filter(User.role=='teacher').all()}
    writer.writerow(['username','name','email','phone'])
    for t in rows:
        u = user_map.get(t.username)
        writer.writerow([t.username, t.name, t.email or '', (u.phone if u else '') or ''])
    out = sio.getvalue()
    from flask import Response
    return Response(out, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=teachers.csv'})


@app.route('/admin/teachers/<username>/edit', methods=['GET','POST'])
@admin_required
def admin_teachers_edit(username):
    t = Teacher.query.filter_by(username=username).first_or_404()
    u = User.query.filter_by(role='teacher', username=username).first()
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip() or t.name
        email = (request.form.get('email') or '').strip() or None
        phone = (request.form.get('phone') or '').strip() or None

        t.name = name
        t.email = email
        if u:
            u.name = name
            u.email = email
            u.phone = phone
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash('Failed to update teacher', 'danger')
            return redirect(url_for('admin_teachers_edit', username=username))

        flash('Teacher updated', 'success')
        return redirect(url_for('admin_teachers_list'))

    # GET
    return render_template('admin_teacher_edit.html', teacher=t, user=u)


@app.route('/admin/teachers/<username>/delete', methods=['POST'])
@admin_required
def admin_teachers_delete(username):
    t = Teacher.query.filter_by(username=username).first()
    u = User.query.filter_by(role='teacher', username=username).first()
    try:
        if t:
            db.session.delete(t)
        if u:
            db.session.delete(u)
        db.session.commit()
        flash('Teacher deleted', 'success')
    except Exception:
        db.session.rollback()
        flash('Failed to delete teacher', 'danger')
    return redirect(url_for('admin_teachers_list'))


@app.route('/admin/teachers/<username>/reset_password', methods=['POST'])
@admin_required
def admin_teachers_reset_password(username):
    t = Teacher.query.filter_by(username=username).first_or_404()
    u = User.query.filter_by(role='teacher', username=username).first()
    # Generate new password using name+phone (if known)
    contact = (u.phone if u else None) or username
    gen_password = _gen_admission_password(t.name, contact)
    try:
        if u:
            u.set_password(gen_password)
        # keep Teacher.password_hash in sync for dashboard compatibility
        t.password_hash = u.password_hash if u else t.password_hash
        db.session.commit()
        flash(f'Password reset. New password: {gen_password}', 'success')
    except Exception:
        db.session.rollback()
        flash('Failed to reset password', 'danger')
    return redirect(url_for('admin_teachers_list'))


# ------- Admin: Login Audit (filters + pagination) -------
@app.route('/admin/audit')
@admin_required
def admin_audit():
    page = max(int(request.args.get('page', 1) or 1), 1)
    per_page = 25
    q = (request.args.get('q') or '').strip()
    role = (request.args.get('role') or '').strip()  # 'student'|'teacher'|'admin'|''
    success_param = (request.args.get('success') or '').strip()  # '1'|'0'|''

    query = LoginAudit.query
    if q:
        like = f"%{q}%"
        query = query.filter(LoginAudit.username.ilike(like))
    if role:
        query = query.filter(LoginAudit.user_type == role)
    if success_param in ('0', '1'):
        query = query.filter(LoginAudit.success == (success_param == '1'))

    total = query.count()
    logs = query.order_by(LoginAudit.timestamp.desc()).offset((page-1)*per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page
    return render_template('admin_audit.html', logs=logs, page=page, pages=pages, total=total, q=q, role=role, success_param=success_param)


# ------- Admin: Admissions -------
@app.route('/admin/admissions')
@admin_required
def admin_admissions_list():
    page = max(int(request.args.get('page', 1) or 1), 1)
    per_page = 25
    q = (request.args.get('q') or '').strip()
    status = (request.args.get('status') or '').strip()

    query = Admission.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Admission.name.ilike(like), Admission.roll_no.ilike(like)))
    if status:
        query = query.filter(Admission.status == status)
    total = query.count()
    rows = query.order_by(Admission.admission_date.desc()).offset((page-1)*per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page
    return render_template('admin_admissions.html', rows=rows, page=page, pages=pages, total=total, q=q, status=status)


@app.route('/admin/admissions/new', methods=['GET', 'POST'])
@admin_required
def admin_admissions_new():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        class_name = (request.form.get('class_name') or '').strip() or None
        section = (request.form.get('section') or '').strip() or None
        phone = (request.form.get('phone') or '').strip() or None
        email = (request.form.get('email') or '').strip() or None
        address = (request.form.get('address') or '').strip() or None
        status = (request.form.get('status') or 'pending').strip()
        roll_no = (request.form.get('roll_no') or '').strip() or None

        if not name:
            flash('Name is required', 'danger')
            return redirect(url_for('admin_admissions_new'))

        # Prevent duplicate roll numbers at the Admission table level
        if roll_no:
            existing = Admission.query.filter(Admission.roll_no == roll_no).first()
            if existing:
                flash('Roll No already exists in another admission. Please use a unique Roll No.', 'danger')
                return redirect(url_for('admin_admissions_new'))

        # Generate password for admission using school name + student name + last digits of phone
        gen_password = _gen_admission_password(name, phone) if phone else None
        
        adm = Admission(name=name, class_name=class_name, section=section, phone=phone,
                        email=email, address=address, status=status, roll_no=roll_no,
                        password=gen_password)
        db.session.add(adm)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash('Failed to save admission (possible duplicate Roll No).', 'danger')
            return redirect(url_for('admin_admissions_new'))

        # If confirmed, create Student + User if not present
        if status == 'confirmed':
            if not roll_no:
                flash('Confirmed admission requires Roll No. Please edit and add roll no.', 'warning')
            else:
                student = Student.query.filter_by(roll_no=roll_no).first()
                if not student:
                    student = Student(roll_no=roll_no, name=name, class_name=class_name, section=section,
                                      phone=phone, email=email, address=address)
                    # Initialize from admission password if present; fallback to default
                    student.set_password(adm.password or 'password123')
                    db.session.add(student)
                    db.session.commit()
                adm.student_id = student.id
                # Ensure unified user exists
                u = User.query.filter_by(username=roll_no).first()
                if not u:
                    u = User(role='student', username=roll_no, name=name, email=email,
                             admission_code=None, class_name=class_name, section=section,
                             phone=phone, address=address)
                    u.password_hash = student.password_hash
                    db.session.add(u)
                    db.session.commit()
                db.session.commit()

        flash('Admission saved', 'success')
        return redirect(url_for('admin_admissions_list'))

    return render_template('admin_admissions_new.html')


@app.route('/admin/admissions/<int:adm_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_admissions_edit(adm_id):
    adm = Admission.query.get_or_404(adm_id)
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        class_name = (request.form.get('class_name') or '').strip() or None
        section = (request.form.get('section') or '').strip() or None
        phone = (request.form.get('phone') or '').strip() or None
        email = (request.form.get('email') or '').strip() or None
        address = (request.form.get('address') or '').strip() or None
        status = (request.form.get('status') or 'pending').strip()
        roll_no = (request.form.get('roll_no') or '').strip() or None

        if not name:
            flash('Name is required', 'danger')
            return redirect(url_for('admin_admissions_edit', adm_id=adm.id))

        adm.name = name
        adm.class_name = class_name
        adm.section = section
        adm.phone = phone
        adm.email = email
        adm.address = address
        adm.status = status
        # Auto-generate admission password if missing and phone is provided
        if not (adm.password or '').strip() and phone:
            adm.password = _gen_admission_password(name, phone)
        # Prevent duplicate roll numbers when editing
        if roll_no:
            dup = Admission.query.filter(Admission.roll_no == roll_no, Admission.id != adm.id).first()
            if dup:
                flash('Roll No already exists in another admission. Please use a unique Roll No.', 'danger')
                return redirect(url_for('admin_admissions_edit', adm_id=adm.id))
        adm.roll_no = roll_no
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash('Failed to update admission (possible duplicate Roll No).', 'danger')
            return redirect(url_for('admin_admissions_edit', adm_id=adm.id))

        # If moved/kept to confirmed, ensure student/user linkage
        if status == 'confirmed':
            if not roll_no:
                flash('Confirmed admission requires Roll No.', 'warning')
            else:
                student = Student.query.filter_by(roll_no=roll_no).first()
                if not student:
                    student = Student(roll_no=roll_no, name=name, class_name=class_name, section=section,
                                      phone=phone, email=email, address=address)
                    student.set_password(adm.password or 'password123')
                    db.session.add(student)
                    db.session.commit()
                adm.student_id = student.id
                u = User.query.filter_by(username=roll_no).first()
                if not u:
                    u = User(role='student', username=roll_no, name=name, email=email,
                             admission_code=None, class_name=class_name, section=section,
                             phone=phone, address=address)
                    u.password_hash = student.password_hash
                    db.session.add(u)
                    db.session.commit()
                db.session.commit()

        flash('Admission updated', 'success')
        return redirect(url_for('admin_admissions_list'))

    return render_template('admin_admissions_edit.html', adm=adm)


@app.route('/admin/admissions/<int:adm_id>/status', methods=['POST'])
@admin_required
def admin_admissions_status(adm_id):
    adm = Admission.query.get_or_404(adm_id)
    status = (request.form.get('status') or '').strip()
    roll_no = (request.form.get('roll_no') or '').strip() or adm.roll_no

    if status not in ('pending', 'confirmed', 'rejected'):
        flash('Invalid status', 'danger')
        return redirect(url_for('admin_admissions_list'))

    # Prevent duplicate roll numbers when updating status
    if roll_no:
        dup = Admission.query.filter(Admission.roll_no == roll_no, Admission.id != adm.id).first()
        if dup:
            flash('Roll No already exists in another admission. Please use a unique Roll No.', 'danger')
            return redirect(url_for('admin_admissions_list'))

    adm.status = status
    if roll_no:
        adm.roll_no = roll_no
    # Ensure we have an admission password if confirming and missing
    if status == 'confirmed' and (not (adm.password or '').strip()):
        adm.password = _gen_admission_password(adm.name, adm.phone)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        flash('Failed to update status (possible duplicate Roll No).', 'danger')
        return redirect(url_for('admin_admissions_list'))

    if status == 'confirmed':
        if not adm.roll_no:
            flash('Confirmed admission requires Roll No.', 'warning')
            return redirect(url_for('admin_admissions_list'))
        # Ensure student exists
        student = Student.query.filter_by(roll_no=adm.roll_no).first()
        if not student:
            student = Student(roll_no=adm.roll_no, name=adm.name, class_name=adm.class_name, section=adm.section,
                              phone=adm.phone, email=adm.email, address=adm.address)
            student.set_password(adm.password or 'password123')
            db.session.add(student)
            db.session.commit()
        adm.student_id = student.id
        # Ensure unified user exists
        u = User.query.filter_by(username=adm.roll_no).first()
        if not u:
            u = User(role='student', username=adm.roll_no, name=adm.name, email=adm.email,
                     admission_code=None, class_name=adm.class_name, section=adm.section,
                     phone=adm.phone, address=adm.address)
            u.password_hash = student.password_hash
            db.session.add(u)
            db.session.commit()
        db.session.commit()

    flash('Admission status updated', 'success')
    return redirect(url_for('admin_admissions_list'))


@app.route('/admin/admissions/<int:adm_id>/delete', methods=['POST'])
@admin_required
def admin_admissions_delete(adm_id):
    adm = Admission.query.get_or_404(adm_id)
    db.session.delete(adm)
    db.session.commit()
    flash('Admission deleted', 'info')
    return redirect(url_for('admin_admissions_list'))


@app.route('/admin/admissions/export')
@admin_required
def admin_admissions_export():
    import csv
    from io import StringIO
    q = (request.args.get('q') or '').strip()
    status = (request.args.get('status') or '').strip()

    query = Admission.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Admission.name.ilike(like), Admission.roll_no.ilike(like)))
    if status:
        query = query.filter(Admission.status == status)
    rows = query.order_by(Admission.admission_date.desc()).all()

    sio = StringIO()
    writer = csv.writer(sio)
    writer.writerow(['id','status','admission_date','roll_no','name','class_name','section','phone','email','address','student_id'])
    for a in rows:
        writer.writerow([
            a.id, a.status, a.admission_date.strftime('%Y-%m-%d %H:%M:%S') if a.admission_date else '',
            a.roll_no or '', a.name, a.class_name or '', a.section or '', a.phone or '', a.email or '',
            (a.address or '').replace('\n',' '), a.student_id or ''
        ])
    out = sio.getvalue()
    from flask import Response
    return Response(out, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=admissions.csv'})


# ------- Admin: Users list and export -------
@app.route('/admin/users')
@admin_required
def admin_users_list():
    page = max(int(request.args.get('page', 1) or 1), 1)
    per_page = 25
    q = (request.args.get('q') or '').strip()
    role = (request.args.get('role') or '').strip()

    query = User.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(User.username.ilike(like), User.name.ilike(like), User.email.ilike(like)))
    if role:
        query = query.filter(User.role == role)
    total = query.count()
    rows = query.order_by(User.role, User.username).offset((page-1)*per_page).limit(per_page).all()
    pages = (total + per_page - 1) // per_page
    return render_template('admin_users.html', rows=rows, page=page, pages=pages, total=total, q=q, role=role)


@app.route('/admin/users/export')
@admin_required
def admin_users_export():
    import csv
    from io import StringIO
    q = (request.args.get('q') or '').strip()
    role = (request.args.get('role') or '').strip()
    query = User.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(User.username.ilike(like), User.name.ilike(like), User.email.ilike(like)))
    if role:
        query = query.filter(User.role == role)
    rows = query.order_by(User.role, User.username).all()

    sio = StringIO()
    writer = csv.writer(sio)
    writer.writerow(['id','role','username','name','email','class_name','section','phone'])
    for u in rows:
        writer.writerow([u.id, u.role, u.username, u.name, u.email or '', u.class_name or '', u.section or '', u.phone or ''])
    out = sio.getvalue()
    from flask import Response
    return Response(out, mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=users.csv'})


# ------- Admin: Reset user password -------
@app.route('/admin/users/<int:user_id>/reset-password', methods=['GET', 'POST'])
@admin_required
def admin_user_reset_password(user_id):
    u = User.query.get_or_404(user_id)
    if request.method == 'POST':
        new_password = (request.form.get('new_password') or '')
        confirm_password = (request.form.get('confirm_password') or '')
        if not new_password or new_password != confirm_password:
            flash('Passwords do not match or empty', 'danger')
            return redirect(url_for('admin_user_reset_password', user_id=u.id))

        u.set_password(new_password)
        db.session.commit()

        # Sync to role-specific table for dashboard compatibility
        try:
            if u.role == 'student':
                s = Student.query.filter_by(roll_no=u.username).first()
                if s:
                    s.password_hash = u.password_hash
                    db.session.commit()
            elif u.role == 'teacher':
                t = Teacher.query.filter_by(username=u.username).first()
                if t:
                    t.password_hash = u.password_hash
                    db.session.commit()
            elif u.role == 'admin':
                a = Admin.query.filter_by(username=u.username).first()
                if a:
                    a.password_hash = u.password_hash
                    db.session.commit()
        except Exception:
            db.session.rollback()

        flash('Password updated successfully', 'success')
        return redirect(url_for('admin_users_list'))

    return render_template('admin_user_reset.html', user=u)


@app.route('/teacher/logout')
@teacher_required
def teacher_logout():
    session.pop('teacher_id', None)
    flash('Logged out', 'info')
    return redirect(url_for('teacher_login'))


@app.route('/teacher/workspace')
@teacher_required
def teacher_workspace():
    mode = (request.args.get('mode') or 'attendance').lower()  # attendance|results|sports
    class_name = (request.args.get('class') or '').strip()
    section = (request.args.get('section') or '').strip()
    subject_id = (request.args.get('subject_id') or '').strip()
    term = (request.args.get('term') or '').strip()
    date_str = (request.args.get('date') or '').strip()

    students_q = Student.query
    if class_name:
        students_q = students_q.filter(Student.class_name == class_name)
    if section:
        students_q = students_q.filter(Student.section == section)
    students = students_q.order_by(Student.roll_no).all()
    subjects = Subject.query.order_by(Subject.name).all()

    return render_template('teacher_workspace.html',
                           mode=mode, students=students, subjects=subjects,
                           class_name=class_name, section=section, subject_id=subject_id,
                           term=term, date_str=date_str)


@app.route('/teacher/workspace/attendance/bulk', methods=['POST'])
@teacher_required
def teacher_workspace_attendance_bulk():
    student_ids = request.form.getlist('student_id')
    statuses = request.form.getlist('status')
    subject_id = request.form.get('subject_id') or None
    date_str = request.form.get('date') or ''
    date_val = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.utcnow().date()

    for idx, sid in enumerate(student_ids):
        status = (statuses[idx] if idx < len(statuses) else 'Present') or 'Present'
        rec = Attendance(student_id=int(sid), status=status, subject_id=int(subject_id) if subject_id else None,
                         date=date_val, marked_by_teacher_id=session['teacher_id'])
        db.session.add(rec)
    db.session.commit()
    flash('Attendance saved for class', 'success')
    return redirect(url_for('teacher_workspace', mode='attendance', **{
        'class': request.form.get('class_name') or '', 'section': request.form.get('section') or ''
    }))


@app.route('/teacher/workspace/results/bulk', methods=['POST'])
@teacher_required
def teacher_workspace_results_bulk():
    student_ids = request.form.getlist('student_id')
    scores = request.form.getlist('score')
    max_scores = request.form.getlist('max_score')
    subject_id = request.form.get('subject_id')
    term = request.form.get('term')
    date_str = request.form.get('date') or ''
    date_val = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None

    for idx, sid in enumerate(student_ids):
        try:
            score_v = float(scores[idx]) if idx < len(scores) and scores[idx] else None
            max_v = float(max_scores[idx]) if idx < len(max_scores) and max_scores[idx] else None
        except ValueError:
            score_v, max_v = None, None
        if score_v is None or max_v is None:
            continue
        rec = Result(student_id=int(sid), subject_id=int(subject_id), term=term,
                     marks_obtained=score_v, max_marks=max_v, graded_by_teacher_id=session['teacher_id'])
        db.session.add(rec)
    db.session.commit()
    flash('Results saved for class', 'success')
    return redirect(url_for('teacher_workspace', mode='results', **{
        'class': request.form.get('class_name') or '', 'section': request.form.get('section') or ''
    }))


@app.route('/teacher/workspace/sports/bulk', methods=['POST'])
@teacher_required
def teacher_workspace_sports_bulk():
    student_ids = request.form.getlist('student_id')
    activities = request.form.getlist('activity')
    levels = request.form.getlist('level')
    results_f = request.form.getlist('result')
    date_str = request.form.get('date') or ''
    date_val = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
    notes_list = request.form.getlist('notes')

    for idx, sid in enumerate(student_ids):
        act = (activities[idx] if idx < len(activities) else '').strip()
        if not act:
            continue
        lvl = (levels[idx] if idx < len(levels) else '').strip() or None
        res = (results_f[idx] if idx < len(results_f) else '').strip() or None
        nts = (notes_list[idx] if idx < len(notes_list) else '').strip() or None
        rec = SportsActivity(student_id=int(sid), activity=act, level=lvl, result=res, date=date_val,
                             notes=nts, recorded_by_teacher_id=session['teacher_id'])
        db.session.add(rec)
    db.session.commit()
    flash('Sports activities saved for class', 'success')
    return redirect(url_for('teacher_workspace', mode='sports', **{
        'class': request.form.get('class_name') or '', 'section': request.form.get('section') or ''
    }))
@app.route('/teacher/dashboard')
@teacher_required
def teacher_dashboard():
    teacher = Teacher.query.get(session['teacher_id'])
    students = Student.query.order_by(Student.class_name, Student.section, Student.roll_no).all()
    subjects = Subject.query.order_by(Subject.name).all()
    return render_template('teacher_dashboard.html', teacher=teacher, students=students, subjects=subjects)


# ---- Teacher data submission endpoints ----
@app.route('/teacher/attendance', methods=['POST'])
@teacher_required
def submit_attendance():
    student_id = request.form.get('student_id')
    status = request.form.get('status')  # Present/Absent
    subject_id = request.form.get('subject_id') or None
    date_str = request.form.get('date')
    date_val = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.utcnow().date()
    rec = Attendance(student_id=student_id, status=status, subject_id=subject_id, date=date_val, marked_by_teacher_id=session['teacher_id'])
    db.session.add(rec)
    db.session.commit()
    flash('Attendance saved', 'success')
    return redirect(url_for('teacher_dashboard'))


@app.route('/teacher/result', methods=['POST'])
@teacher_required
def submit_result():
    student_id = request.form.get('student_id')
    subject_id = request.form.get('subject_id')
    term = request.form.get('term')
    marks_obtained = float(request.form.get('marks_obtained') or 0)
    max_marks = float(request.form.get('max_marks') or 100)
    rec = Result(student_id=student_id, subject_id=subject_id, term=term, marks_obtained=marks_obtained, max_marks=max_marks, graded_by_teacher_id=session['teacher_id'])
    db.session.add(rec)
    db.session.commit()
    flash('Result saved', 'success')
    return redirect(url_for('teacher_dashboard'))


@app.route('/teacher/fee', methods=['POST'])
@teacher_required
def submit_fee():
    student_id = request.form.get('student_id')
    amount = float(request.form.get('amount') or 0)
    mode = request.form.get('mode')
    reference_no = request.form.get('reference_no')
    description = request.form.get('description')
    rec = FeePayment(student_id=student_id, amount=amount, mode=mode, reference_no=reference_no, description=description, recorded_by_teacher_id=session['teacher_id'])
    db.session.add(rec)
    db.session.commit()
    flash('Fee payment recorded', 'success')
    return redirect(url_for('teacher_dashboard'))


# -------- Teacher workspace pages (GET) and bulk actions (POST) --------
@app.route('/teacher/attendance/sheet')
@teacher_required
def teacher_attendance_sheet():
    t = Teacher.query.get(session.get('teacher_id'))
    # Distinct classes/sections from students
    classes = db.session.query(Student.class_name).filter(Student.class_name.isnot(None)).distinct().order_by(Student.class_name).all()
    class_list = [c[0] for c in classes]

    cls = (request.args.get('class') or '').strip() or None
    date_str = (request.args.get('date') or '').strip()
    date_val = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.utcnow().date()

    # Build all days in the selected month
    first_day = date_val.replace(day=1)
    if first_day.month == 12:
        next_month = first_day.replace(year=first_day.year + 1, month=1)
    else:
        next_month = first_day.replace(month=first_day.month + 1)
    total_days = (next_month - first_day).days
    date_list = [first_day + timedelta(days=i) for i in range(total_days)]

    q = Student.query
    if cls:
        q = q.filter_by(class_name=cls)
    students = q.order_by(Student.roll_no).all()
    # Preload existing attendance for this class/section and month to pre-fill checkboxes
    student_ids = [s.id for s in students]
    present_keys = set()
    if student_ids:
        existing = Attendance.query.filter(
            Attendance.student_id.in_(student_ids),
            Attendance.date >= first_day,
            Attendance.date < next_month
        ).all()
        for a in existing:
            if (a.status or '').lower().startswith('present'):
                present_keys.add(f"{a.student_id}_{a.date.isoformat()}")

    return render_template('teacher_attendance.html', teacher=t, class_list=class_list,
                           selected_class=cls, date_val=date_val, date_list=date_list,
                           students=students, present_keys=present_keys)


@app.route('/teacher/attendance/bulk', methods=['POST'])
@teacher_required
def teacher_attendance_bulk():
    cls = (request.form.get('class_name') or '').strip() or None
    base_date_str = (request.form.get('date') or '').strip()
    base_date = datetime.strptime(base_date_str, '%Y-%m-%d').date() if base_date_str else datetime.utcnow().date()
    # Build the month dates from base_date
    first_day = base_date.replace(day=1)
    if first_day.month == 12:
        next_month = first_day.replace(year=first_day.year + 1, month=1)
    else:
        next_month = first_day.replace(month=first_day.month + 1)
    total_days = (next_month - first_day).days
    date_list = [first_day + timedelta(days=i) for i in range(total_days)]

    ids = request.form.getlist('student_id')
    for sid in ids:
        sid_int = int(sid)
        for d in date_list:
            key = f'status_{sid_int}_{d.isoformat()}'
            # Checkbox behavior: present only when checked; missing implies Absent
            status_val = 'Present' if (request.form.get(key) or '').strip() else 'Absent'
            # Remove any existing record for (student, date) to avoid duplicates
            Attendance.query.filter_by(student_id=sid_int, date=d).delete()
            rec = Attendance(student_id=sid_int, status=status_val, subject_id=None, date=d,
                             marked_by_teacher_id=session.get('teacher_id'))
            db.session.add(rec)
    db.session.commit()
    flash('Monthly attendance saved.', 'success')
    return redirect(url_for('teacher_attendance_sheet', **({'class': cls} if cls else {}), date=base_date.isoformat()))


@app.route('/teacher/results/upload')
@teacher_required
def teacher_results_upload():
    t = Teacher.query.get(session.get('teacher_id'))
    # Filters: class and section
    classes = db.session.query(Student.class_name).filter(Student.class_name.isnot(None)).distinct().order_by(Student.class_name).all()
    class_list = [c[0] for c in classes]
    sections = db.session.query(Student.section).filter(Student.section.isnot(None)).distinct().order_by(Student.section).all()
    section_list = [s[0] for s in sections]
    cls = (request.args.get('class') or '').strip() or None
    sec = (request.args.get('section') or '').strip() or None

    q = Student.query
    if cls:
        q = q.filter_by(class_name=cls)
    if sec:
        q = q.filter_by(section=sec)
    students = q.order_by(Student.roll_no).all()

    # Default six subjects (editable on page)
    default_subjects = []
    existing_subs = Subject.query.order_by(Subject.name).all()
    names = []
    for s in existing_subs:
        if s.name and s.name not in names:
            names.append(s.name)
        if len(names) >= 6:
            break
    default_subjects = names
    while len(default_subjects) < 6:
        default_subjects.append('')

    return render_template('teacher_results.html', teacher=t, class_list=class_list,
                           selected_class=cls, term='', students=students,
                           subjects_six=default_subjects, section_list=section_list, selected_section=sec)


@app.route('/teacher/results/bulk', methods=['POST'])
@teacher_required
def teacher_results_bulk():
    # Auto-generate term label based on current month
    now = datetime.utcnow()
    term = ("SUMMER" if now.month in (4,5,6,7,8,9) else "WINTER") + f" {now.year}"
    max_marks = float(request.form.get('max_marks') or 100)
    ids = request.form.getlist('student_id')

    # Collect up to 6 subject names from headers
    subject_names = []
    for i in range(1, 7):
        nm = (request.form.get(f'subject_name_{i}') or '').strip()
        subject_names.append(nm)

    # Helper: get or create Subject by name
    def get_or_create_subject(name: str):
        if not name:
            return None
        sub = Subject.query.filter_by(name=name).first()
        if not sub:
            sub = Subject(name=name, class_section_id=None)
            db.session.add(sub)
            db.session.flush()
        return sub

    # Upsert results per subject column
    for sid in ids:
        sid_int = int(sid)
        for idx, sub_name in enumerate(subject_names, start=1):
            if not sub_name:
                continue
            marks_val = request.form.get(f'marks_{sid}_{idx}')
            if marks_val is None or marks_val == '':
                continue
            marks = float(marks_val)
            sub = get_or_create_subject(sub_name)
            if not sub:
                continue
            # Remove existing result for (student, subject, term) to avoid duplicates
            Result.query.filter_by(student_id=sid_int, subject_id=sub.id, term=term).delete()
            rec = Result(student_id=sid_int, subject_id=sub.id, term=term,
                         marks_obtained=marks, max_marks=max_marks,
                         graded_by_teacher_id=session.get('teacher_id'))
            db.session.add(rec)

    db.session.commit()
    flash('Results saved for class', 'success')
    return redirect(url_for('teacher_results_upload', **{
        'class': cls or '',
        'term': term or ''
    }))


@app.route('/teacher/sports')
@teacher_required
def teacher_sports_page():
    t = Teacher.query.get(session.get('teacher_id'))
    classes = db.session.query(Student.class_name).filter(Student.class_name.isnot(None)).distinct().order_by(Student.class_name).all()
    sections = db.session.query(Student.section).filter(Student.section.isnot(None)).distinct().order_by(Student.section).all()
    class_list = [c[0] for c in classes]
    section_list = [s[0] for s in sections]

    cls = (request.args.get('class') or '').strip() or None
    sec = (request.args.get('section') or '').strip() or None
    q = Student.query
    if cls:
        q = q.filter_by(class_name=cls)
    if sec:
        q = q.filter_by(section=sec)
    students = q.order_by(Student.roll_no).all()

    return render_template('teacher_sports.html', teacher=t, class_list=class_list, section_list=section_list,
                           selected_class=cls, selected_section=sec, students=students)


@app.route('/teacher/sports/bulk', methods=['POST'])
@teacher_required
def teacher_sports_bulk():
    ids = request.form.getlist('student_id')
    activity = (request.form.get('activity') or '').strip()
    level = (request.form.get('level') or '').strip() or None
    result_val = (request.form.get('result') or '').strip() or None
    date_str = (request.form.get('date') or '').strip()
    date_val = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
    notes = (request.form.get('notes') or '').strip() or None
    for sid in ids:
        if not activity:
            continue
        rec = SportsActivity(student_id=int(sid), activity=activity, level=level, result=result_val,
                             date=date_val, notes=notes, recorded_by_teacher_id=session.get('teacher_id'))
        db.session.add(rec)
    db.session.commit()
    flash('Sports achievements recorded', 'success')
    return redirect(url_for('teacher_sports_page', **{
        'class': request.form.get('class_name') or '',
        'section': request.form.get('section') or ''
    }))


# --------------- CLI/Init Helpers ---------------

def ensure_db_and_sample():
    """Create tables and a sample student if the database is empty.
    WARNING: This is for development/demo only. Remove in production.
    """
    db.create_all()
    # Use raw COUNT to avoid selecting all columns via ORM during initialization
    try:
        student_count = db.session.execute(sa.text('SELECT COUNT(*) AS c FROM students')).scalar() or 0
    except Exception:
        student_count = 0
    if student_count == 0:
        s = Student(
            roll_no='2024001',
            name='Rajesh Kumar',
            admission_code='ADM-EXAMPLE-2024',
            class_name='10',
            section='A',
            phone='+91 98765 43210',
            email='rajesh@student.tes.edu',
            address='Panchwad, Maharashtra',
        )
        s.set_password('password123')
        db.session.add(s)
        print('Seeded sample student: roll_no=2024001, password=password123')

    if Teacher.query.count() == 0:
        t = Teacher(username='teacher1', name='Ms. Patel', email='teacher1@tes.edu')
        t.set_password('teachpass')
        db.session.add(t)
        print('Seeded sample teacher: username=teacher1, password=teachpass')

    if Admin.query.count() == 0:
        a = Admin(username='admin', name='School Admin', email='admin@tes.edu')
        a.set_password('adminpass')
        db.session.add(a)
        print('Seeded admin: username=admin, password=adminpass')

    if ClassSection.query.count() == 0:
        cs = ClassSection(class_name='10', section='A')
        db.session.add(cs)
        print('Seeded class section 10-A')

    db.session.commit()

    # Ensure unified users table has seed entries
    if User.query.count() == 0:
        # Student user (username is roll_no)
        u_student = User(role='student', username='2024001', name='Rajesh Kumar', email='rajesh@student.tes.edu',
                         admission_code='ADM-EXAMPLE-2024', class_name='10', section='A', phone='+91 98765 43210', address='Panchwad, Maharashtra')
        u_student.set_password('password123')
        db.session.add(u_student)

        # Teacher user
        u_teacher = User(role='teacher', username='teacher1', name='Ms. Patel', email='teacher1@tes.edu')
        u_teacher.set_password('teachpass')
        db.session.add(u_teacher)

        # Admin user
        u_admin = User(role='admin', username='admin', name='School Admin', email='admin@tes.edu')
        u_admin.set_password('adminpass')
        db.session.add(u_admin)

        db.session.commit()

    if Subject.query.count() == 0:
        # assign to any available class_section
        cs_any = ClassSection.query.first()
        for name in ['Mathematics', 'Science', 'English']:
            db.session.add(Subject(name=name, class_section_id=cs_any.id if cs_any else None))
        db.session.commit()
        print('Seeded subjects: Mathematics, Science, English')


if __name__ == '__main__':
    with app.app_context():
        # Log which database is in use (masked for safety)
        try:
            print('Using database:', _mask_db_url(app.config.get('SQLALCHEMY_DATABASE_URI')))
        except Exception:
            pass
        ensure_db_and_sample()
    app.run(host='0.0.0.0', port=5000, debug=True)
