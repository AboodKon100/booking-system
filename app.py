from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta, timedelta as td
from sqlalchemy import func, and_, extract, or_
import uuid, random, string, os, re, calendar as cal_mod, threading

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'noomly-prod-key-2026-change')
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'noomly.db')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{db_path}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXT = {'png','jpg','jpeg','gif','webp'}

app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'Noomly <noreply@noomly.com>')

db = SQLAlchemy(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'error'

def is_email_configured():
    return bool(app.config.get('MAIL_USERNAME') and app.config.get('MAIL_PASSWORD'))

def send_email_async(app, msg):
    with app.app_context():
        try:
            mail.send(msg)
            return True
        except Exception as e:
            print(f'Email send failed: {e}')
            return False

def send_email(subject, recipient, html_body, sender=None):
    if not is_email_configured():
        print(f'[DEMO EMAIL] To: {recipient} | Subject: {subject}')
        print(f'[DEMO EMAIL] SMTP not configured. Set MAIL_USERNAME and MAIL_PASSWORD env vars.')
        return False
    msg = Message(subject=subject, recipients=[recipient], html_body=html_body, sender=sender or app.config['MAIL_DEFAULT_SENDER'])
    thread = threading.Thread(target=send_email_async, args=(app, msg))
    thread.daemon = True
    thread.start()
    return True

def send_booking_confirmation(appointment, business):
    svc_name = appointment.service.name if appointment.service else 'service'
    html = render_template('email/booking_confirmation.html',
                          business=business, appointment=appointment, service_name=svc_name)
    send_email(f'Booking Confirmed - {business.name}', appointment.cust_email, html)

def send_ai_confirmation(appointment, business):
    svc_name = appointment.service.name if appointment.service else 'service'
    html = render_template('email/ai_confirmation.html',
                          business=business, appointment=appointment, service_name=svc_name)
    send_email(f'Appointment Confirmed by AI - {business.name}', appointment.cust_email, html)

def send_postpone_notification(appointment, business):
    svc_name = appointment.service.name if appointment.service else 'service'
    html = render_template('email/postpone_notification.html',
                          business=business, appointment=appointment, service_name=svc_name)
    send_email(f'Appointment Postponed - {business.name}', appointment.cust_email, html)

BUSINESS_TYPES = {
    'salon': {'name': 'Salon & Beauty', 'icon': '✂️', 'color': 'from-pink-500 to-rose-500', 'features': ['Hair Styling', 'Coloring', 'Manicure', 'Pedicure'], 'default_services': [('Haircut & Styling', 45, 45), ('Hair Coloring', 120, 120), ('Manicure', 30, 30), ('Pedicure', 45, 45), ('Facial Treatment', 60, 65)]},
    'barbershop': {'name': 'Barbershop', 'icon': '💈', 'color': 'from-blue-500 to-indigo-500', 'features': ['Haircut', 'Beard Trim', 'Hot Shave', 'Kids Cut'], 'default_services': [('Classic Haircut', 30, 35), ('Beard Trim', 20, 20), ('Hot Towel Shave', 25, 30), ('Kids Haircut', 20, 20), ('Combo', 45, 50)]},
    'clinic': {'name': 'Medical Clinic', 'icon': '🏥', 'color': 'from-red-500 to-pink-500', 'features': ['General Checkup', 'Dental', 'Eye Care', 'Dermatology'], 'default_services': [('General Checkup', 30, 80), ('Dental Cleaning', 45, 120), ('Eye Exam', 30, 95), ('Dermatology', 20, 150)]},
    'dental': {'name': 'Dental Clinic', 'icon': '🦷', 'color': 'from-cyan-500 to-blue-500', 'features': ['Cleaning', 'Whitening', 'Fillings', 'Consultation'], 'default_services': [('Dental Cleaning', 45, 120), ('Teeth Whitening', 60, 350), ('Cavity Filling', 45, 200), ('Consultation', 20, 75)]},
    'gym': {'name': 'Gym & Fitness', 'icon': '🏋️', 'color': 'from-orange-500 to-red-500', 'features': ['Personal Training', 'Group Classes', 'Yoga', 'CrossFit'], 'default_services': [('Personal Training', 60, 80), ('Yoga Class', 60, 25), ('CrossFit', 60, 35), ('Group HIIT', 45, 20)]},
    'spa': {'name': 'Spa & Wellness', 'icon': '💆', 'color': 'from-purple-500 to-indigo-500', 'features': ['Massage', 'Facial', 'Body Treatment', 'Aromatherapy'], 'default_services': [('Swedish Massage', 60, 90), ('Deep Tissue', 90, 130), ('Hot Stone', 75, 120), ('Luxury Facial', 60, 110)]},
    'restaurant': {'name': 'Restaurant & Cafe', 'icon': '🍽️', 'color': 'from-amber-500 to-orange-500', 'features': ['Table Reservation', 'Private Events', 'Catering'], 'default_services': [('Table for 2', 120, 0), ('Table for 4', 120, 0), ('Private Dining', 180, 250), ('Event Booking', 60, 0)]},
    'salon_pet': {'name': 'Pet Grooming', 'icon': '🐾', 'color': 'from-teal-500 to-green-500', 'features': ['Dog Grooming', 'Cat Grooming', 'Nail Trim', 'Bath'], 'default_services': [('Full Groom - Small', 90, 45), ('Full Groom - Large', 120, 65), ('Cat Grooming', 60, 55), ('Nail Trim', 15, 15)]},
    'studio': {'name': 'Photo/Video Studio', 'icon': '📸', 'color': 'from-violet-500 to-purple-500', 'features': ['Portrait', 'Family', 'Event', 'Product'], 'default_services': [('Portrait Session', 60, 150), ('Family Shoot', 90, 250), ('Event Coverage', 180, 500), ('Product Photo', 60, 200)]},
    'tutoring': {'name': 'Tutoring & Education', 'icon': '📚', 'color': 'from-emerald-500 to-teal-500', 'features': ['Math', 'Science', 'Languages', 'Test Prep'], 'default_services': [('1-on-1 Tutoring', 60, 50), ('Group Session', 90, 25), ('Test Prep', 120, 75), ('Language Lesson', 60, 45)]},
    'consulting': {'name': 'Business Consulting', 'icon': '💼', 'color': 'from-slate-600 to-slate-800', 'features': ['Strategy', 'Marketing', 'Finance', 'Legal'], 'default_services': [('Consultation', 30, 100), ('Strategy Session', 60, 250), ('Marketing Review', 90, 350), ('Follow-up', 30, 75)]},
    'cleaning': {'name': 'Cleaning Services', 'icon': '🧹', 'color': 'from-sky-500 to-blue-500', 'features': ['Home Cleaning', 'Office Cleaning', 'Deep Clean'], 'default_services': [('Standard Clean', 120, 80), ('Deep Clean', 240, 150), ('Office Clean', 180, 120), ('Express Clean', 60, 50)]},
    'auto': {'name': 'Auto Services', 'icon': '🔧', 'color': 'from-gray-600 to-gray-800', 'features': ['Oil Change', 'Tire Service', 'Detailing', 'Repair'], 'default_services': [('Oil Change', 30, 45), ('Tire Rotation', 30, 25), ('Full Detail', 180, 150), ('Brake Check', 45, 75)]},
    'other': {'name': 'Other Business', 'icon': '⚙️', 'color': 'from-brand-500 to-purple-500', 'features': ['Custom Service'], 'default_services': [('Consultation', 30, 0), ('Standard Service', 60, 50), ('Premium Service', 90, 100)]},
}

PLAN_LIMITS = {
    'free': {'max_services': 1, 'max_bookings_month': 10, 'ai_agent': False, 'payments': False, 'analytics': False, 'sms': False, 'custom_branding': False, 'multi_staff': False, 'api_access': False},
    'professional': {'max_services': -1, 'max_bookings_month': -1, 'ai_agent': True, 'payments': True, 'analytics': True, 'sms': True, 'custom_branding': True, 'multi_staff': False, 'api_access': False},
    'business': {'max_services': -1, 'max_bookings_month': -1, 'ai_agent': True, 'payments': True, 'analytics': True, 'sms': True, 'custom_branding': True, 'multi_staff': True, 'api_access': True},
}

def can_add_service(business):
    limits = PLAN_LIMITS.get(business.plan, PLAN_LIMITS['free'])
    if limits['max_services'] == -1: return True
    count = Service.query.filter_by(business_id=business.id).count()
    return count < limits['max_services']

def can_add_booking(business):
    limits = PLAN_LIMITS.get(business.plan, PLAN_LIMITS['free'])
    if limits['max_bookings_month'] == -1: return True
    month_start = date.today().replace(day=1)
    count = Appointment.query.filter(and_(Appointment.business_id==business.id, Appointment.created_at >= month_start)).count()
    return count < limits['max_bookings_month']

def gen_id():
    return str(uuid.uuid4())
def gen_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
def gen_slug(name):
    slug = re.sub(r'[^a-z0-9-]', '', name.lower().replace(' ', '-'))
    return slug or 'biz'
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT
def save_upload(file):
    if file and file.filename and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        fname = f'{gen_id()}.{ext}'
        file.save(os.path.join(UPLOAD_FOLDER, fname))
        return fname
    return None

class Business(UserMixin, db.Model):
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    city = db.Column(db.String(100))
    country = db.Column(db.String(100), default='Saudi Arabia')
    slug = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    business_type = db.Column(db.String(30), default='other')
    plan = db.Column(db.String(20), default='free')
    logo = db.Column(db.String(200))
    cover = db.Column(db.String(200))
    address = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    services = db.relationship('Service', backref='biz', lazy=True, cascade='all,delete-orphan')
    appointments = db.relationship('Appointment', backref='biz', lazy=True, cascade='all,delete-orphan')
    working_hours = db.relationship('WorkingHours', backref='biz', lazy=True, cascade='all,delete-orphan')

class Service(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    business_id = db.Column(db.String(36), db.ForeignKey('business.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    duration = db.Column(db.Integer, nullable=False, default=30)
    price = db.Column(db.Float, nullable=False, default=0)
    color = db.Column(db.String(7), default='#6366f1')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    appointments = db.relationship('Appointment', backref='service', lazy=True)

class Appointment(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    business_id = db.Column(db.String(36), db.ForeignKey('business.id'), nullable=False)
    service_id = db.Column(db.String(36), db.ForeignKey('service.id'), nullable=False)
    customer_id = db.Column(db.String(36), db.ForeignKey('customer.id'), nullable=True)
    cust_name = db.Column(db.String(100), nullable=False)
    cust_email = db.Column(db.String(100), nullable=False)
    cust_phone = db.Column(db.String(20))
    cust_notes = db.Column(db.Text)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(5), nullable=False)
    status = db.Column(db.String(20), default='pending')
    payment_status = db.Column(db.String(20), default='unpaid')
    payment_amount = db.Column(db.Float, default=0)
    confirmation_code = db.Column(db.String(8))
    ai_verified = db.Column(db.Boolean, default=False)
    ai_call_status = db.Column(db.String(20), default='pending')
    email_sent = db.Column(db.Boolean, default=False)
    email_sent_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Customer(UserMixin, db.Model):
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    city = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    appointments = db.relationship('Appointment', backref='customer', lazy=True)

class WorkingHours(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.String(36), db.ForeignKey('business.id'), nullable=False)
    day = db.Column(db.Integer, nullable=False)
    is_open = db.Column(db.Boolean, default=True)
    open_time = db.Column(db.String(5), default='09:00')
    close_time = db.Column(db.String(5), default='17:00')

@login_manager.user_loader
def load_user(uid):
    u = Business.query.get(uid)
    if u: return u
    return Customer.query.get(uid)

@app.context_processor
def inject_globals():
    return dict(BUSINESS_TYPES=BUSINESS_TYPES, now=datetime.utcnow())

@app.route('/')
def index():
    businesses = Business.query.order_by(Business.created_at.desc()).limit(12).all()
    return render_template('landing.html', businesses=businesses)

@app.route('/businesses')
def business_directory():
    btype = request.args.get('type', '')
    city = request.args.get('city', '')
    q = request.args.get('q', '')
    query = Business.query
    if btype:
        query = query.filter_by(business_type=btype)
    if city:
        query = query.filter(Business.city.ilike(f'%{city}%'))
    if q:
        query = query.filter(or_(Business.name.ilike(f'%{q}%'), Business.description.ilike(f'%{q}%'), Business.city.ilike(f'%{q}%')))
    businesses = query.order_by(Business.created_at.desc()).all()
    cities = db.session.query(Business.city).distinct().filter(Business.city.isnot(None), Business.city != '').all()
    cities = sorted(set(c[0] for c in cities if c[0]))
    return render_template('directory.html', businesses=businesses, selected_type=btype, selected_city=city, search_q=q, cities=cities)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        step = request.form.get('step','1')
        if step == '1':
            btype = request.form.get('business_type','other')
            return render_template('register.html', step=2, business_type=btype, btypes=BUSINESS_TYPES)
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip().lower()
        pwd = request.form.get('password','')
        phone = request.form.get('phone','')
        city = request.form.get('city','')
        address = request.form.get('address','')
        btype = request.form.get('business_type','other')
        if not name or not email or len(pwd) < 6:
            flash('Please fill all required fields. Password min 6 chars.','error')
            return render_template('register.html', step=2, business_type=btype, btypes=BUSINESS_TYPES)
        if Business.query.filter_by(email=email).first():
            flash('Email already registered.','error')
            return render_template('register.html', step=2, business_type=btype, btypes=BUSINESS_TYPES)
        slug = gen_slug(name)
        if Business.query.filter_by(slug=slug).first():
            slug += '-' + str(int(datetime.utcnow().timestamp()))
        logo = save_upload(request.files.get('logo'))
        cover = save_upload(request.files.get('cover'))
        b = Business(name=name, email=email, password=generate_password_hash(pwd),
                     phone=phone, city=city, address=address, slug=slug,
                     business_type=btype, country='Saudi Arabia', logo=logo, cover=cover)
        db.session.add(b)
        db.session.flush()
        for d in range(7):
            db.session.add(WorkingHours(business_id=b.id, day=d, is_open=d < 5,
                                        open_time='09:00' if d < 5 else '10:00',
                                        close_time='18:00' if d < 5 else '15:00'))
        btype_data = BUSINESS_TYPES.get(btype, BUSINESS_TYPES['other'])
        colors = ['#6366f1','#8b5cf6','#ec4899','#14b8a6','#f97316','#22c55e','#3b82f6','#eab308']
        for svc_name, dur, price in btype_data['default_services']:
            db.session.add(Service(business_id=b.id, name=svc_name, duration=dur, price=price,
                                   color=random.choice(colors),
                                   description=f'Professional {svc_name.lower()} service'))
        db.session.commit()
        login_user(b)
        flash(f'Welcome to Noomly! Your {btype_data["name"]} system is ready.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('register.html', step=1, btypes=BUSINESS_TYPES)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        pwd = request.form.get('password','')
        b = Business.query.filter_by(email=email).first()
        if b and check_password_hash(b.password, pwd):
            login_user(b, remember=True)
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.','error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    month_start = today.replace(day=1)
    stats = {
        'today': Appointment.query.filter(and_(Appointment.business_id==current_user.id, Appointment.date==today)).count(),
        'pending': Appointment.query.filter(and_(Appointment.business_id==current_user.id, Appointment.status=='pending')).count(),
        'confirmed': Appointment.query.filter(and_(Appointment.business_id==current_user.id, Appointment.status=='confirmed')).count(),
        'completed': Appointment.query.filter(and_(Appointment.business_id==current_user.id, Appointment.status=='completed')).count(),
        'total': Appointment.query.filter_by(business_id=current_user.id).count(),
        'revenue': float(db.session.query(func.sum(Appointment.payment_amount)).filter(and_(Appointment.business_id==current_user.id, Appointment.payment_status=='completed')).scalar() or 0),
        'month_revenue': float(db.session.query(func.sum(Appointment.payment_amount)).filter(and_(Appointment.business_id==current_user.id, Appointment.payment_status=='completed', Appointment.created_at >= month_start)).scalar() or 0),
        'customers': db.session.query(func.count(func.distinct(Appointment.cust_email))).filter_by(business_id=current_user.id).scalar() or 0,
        'month_bookings': Appointment.query.filter(and_(Appointment.business_id==current_user.id, Appointment.created_at >= month_start)).count(),
    }
    stats['conversion_rate'] = round((stats['completed'] / stats['total'] * 100)) if stats['total'] > 0 else 0
    revenue_7d, labels_7d = [], []
    for i in range(6, -1, -1):
        d = today - td(days=i)
        rev = float(db.session.query(func.sum(Appointment.payment_amount)).filter(and_(
            Appointment.business_id==current_user.id, Appointment.payment_status=='completed',
            func.date(Appointment.date) == d)).scalar() or 0)
        revenue_7d.append(rev)
        labels_7d.append(d.strftime('%a'))
    status_data = [stats['pending'], stats['confirmed'], stats['completed'],
                   Appointment.query.filter(and_(Appointment.business_id==current_user.id, Appointment.status=='cancelled')).count()]
    upcoming = Appointment.query.filter(and_(
        Appointment.business_id==current_user.id, Appointment.date >= today,
        Appointment.status.in_(['pending','confirmed']))
    ).order_by(Appointment.date, Appointment.time).limit(8).all()
    recent = Appointment.query.filter_by(business_id=current_user.id).order_by(Appointment.created_at.desc()).limit(6).all()
    top_services = db.session.query(
        Service.name, func.count(Appointment.id).label('cnt'), func.sum(Appointment.payment_amount).label('rev')
    ).join(Service, Appointment.service_id == Service.id).filter(
        and_(Appointment.business_id==current_user.id, Appointment.payment_status=='completed')
    ).group_by(Service.name).order_by(func.count(Appointment.id).desc()).limit(5).all()
    return render_template('dashboard.html', stats=stats, upcoming=upcoming, recent=recent,
                           revenue_7d=revenue_7d, labels_7d=labels_7d, status_data=status_data, top_services=top_services)

@app.route('/dashboard/appointments')
@login_required
def all_appointments():
    status = request.args.get('status','all')
    q = Appointment.query.filter_by(business_id=current_user.id)
    if status != 'all': q = q.filter_by(status=status)
    appts = q.order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    return render_template('appointments.html', appointments=appts, current_status=status)

@app.route('/dashboard/appointments/<aid>/status', methods=['POST'])
@login_required
def update_status(aid):
    a = Appointment.query.filter_by(id=aid, business_id=current_user.id).first_or_404()
    ns = request.form.get('status')
    if ns in ['confirmed','completed','cancelled']:
        a.status = ns
        if ns == 'confirmed':
            a.ai_verified = True
            a.ai_call_status = 'completed'
            if a.payment_amount > 0: a.payment_status = 'completed'
        db.session.commit()
        flash(f'Appointment {ns}.', 'success')
    return redirect(url_for('all_appointments'))

@app.route('/dashboard/services')
@login_required
def services_list():
    services = Service.query.filter_by(business_id=current_user.id).order_by(Service.created_at.desc()).all()
    return render_template('services.html', services=services)

@app.route('/dashboard/services/create', methods=['GET','POST'])
@login_required
def create_service():
    if request.method == 'POST':
        if not can_add_service(current_user):
            flash('Free plan limited to 1 service. Upgrade to add more.', 'error')
            return redirect(url_for('services_list'))
        s = Service(business_id=current_user.id, name=request.form['name'],
                    description=request.form.get('description',''), duration=int(request.form.get('duration',30)),
                    price=float(request.form.get('price',0)), color=request.form.get('color','#6366f1'))
        db.session.add(s)
        db.session.commit()
        flash('Service created!', 'success')
        return redirect(url_for('services_list'))
    return render_template('create_service.html')

@app.route('/dashboard/services/<sid>/edit', methods=['GET','POST'])
@login_required
def edit_service(sid):
    s = Service.query.filter_by(id=sid, business_id=current_user.id).first_or_404()
    if request.method == 'POST':
        s.name = request.form['name']
        s.description = request.form.get('description','')
        s.duration = int(request.form.get('duration',30))
        s.price = float(request.form.get('price',0))
        s.color = request.form.get('color','#6366f1')
        db.session.commit()
        flash('Service updated!', 'success')
        return redirect(url_for('services_list'))
    return render_template('edit_service.html', service=s)

@app.route('/dashboard/services/<sid>/delete', methods=['POST'])
@login_required
def delete_service(sid):
    s = Service.query.filter_by(id=sid, business_id=current_user.id).first_or_404()
    db.session.delete(s)
    db.session.commit()
    flash('Service deleted.', 'info')
    return redirect(url_for('services_list'))

@app.route('/dashboard/calendar')
@login_required
def calendar_view():
    return render_template('calendar.html')

@app.route('/dashboard/customers')
@login_required
def customers_view():
    rows = db.session.query(
        Appointment.cust_name, Appointment.cust_email, Appointment.cust_phone,
        func.count(Appointment.id).label('count'),
        func.sum(Appointment.payment_amount).label('spent'),
        func.max(Appointment.date).label('last_visit')
    ).filter_by(business_id=current_user.id).group_by(Appointment.cust_email).order_by(func.count(Appointment.id).desc()).all()
    return render_template('customers.html', customers=rows)

@app.route('/dashboard/settings', methods=['GET','POST'])
@login_required
def settings():
    if request.method == 'POST':
        current_user.name = request.form.get('name','')
        current_user.phone = request.form.get('phone','')
        current_user.city = request.form.get('city','')
        current_user.country = request.form.get('country','')
        current_user.description = request.form.get('description','')
        current_user.address = request.form.get('address','')
        if request.files.get('logo'):
            logo = save_upload(request.files.get('logo'))
            if logo: current_user.logo = logo
        if request.files.get('cover'):
            cover = save_upload(request.files.get('cover'))
            if cover: current_user.cover = cover
        db.session.commit()
        flash('Settings saved!', 'success')
        return redirect(url_for('settings'))
    hours = WorkingHours.query.filter_by(business_id=current_user.id).order_by(WorkingHours.day).all()
    return render_template('settings.html', hours=hours)

@app.route('/dashboard/settings/hours', methods=['POST'])
@login_required
def update_hours():
    for d in range(7):
        h = WorkingHours.query.filter_by(business_id=current_user.id, day=d).first()
        if h:
            h.is_open = request.form.get(f'day_{d}_open') == 'on'
            h.open_time = request.form.get(f'day_{d}_start','09:00')
            h.close_time = request.form.get(f'day_{d}_end','17:00')
    db.session.commit()
    flash('Hours updated!', 'success')
    return redirect(url_for('settings'))

@app.route('/dashboard/reports')
@login_required
def reports():
    today = date.today()
    month_start = today.replace(day=1)
    revenue = float(db.session.query(func.sum(Appointment.payment_amount)).filter(and_(
        Appointment.business_id==current_user.id, Appointment.payment_status=='completed',
        Appointment.created_at >= month_start)).scalar() or 0)
    appt_count = Appointment.query.filter(and_(Appointment.business_id==current_user.id, Appointment.created_at >= month_start)).count()
    top = db.session.query(Service.name, func.count(Appointment.id).label('c')).join(Appointment).filter(
        and_(Appointment.business_id==current_user.id, Appointment.created_at >= month_start)
    ).group_by(Service.name).order_by(func.count(Appointment.id).desc()).limit(5).all()
    monthly_rev, monthly_labels = [], []
    for i in range(5, -1, -1):
        m, y = today.month - i, today.year
        if m <= 0: m += 12; y -= 1
        rev = float(db.session.query(func.sum(Appointment.payment_amount)).filter(and_(
            Appointment.business_id==current_user.id, Appointment.payment_status=='completed',
            extract('year', Appointment.date) == y, extract('month', Appointment.date) == m
        )).scalar() or 0)
        monthly_rev.append(rev)
        monthly_labels.append(cal_mod.month_abbr[m])
    return render_template('reports.html', revenue=revenue, appt_count=appt_count, top_services=top,
                           monthly_rev=monthly_rev, monthly_labels=monthly_labels)

@app.route('/dashboard/notifications')
@login_required
def notifications():
    recent_appts = Appointment.query.filter_by(business_id=current_user.id).order_by(Appointment.created_at.desc()).limit(20).all()
    notifs = []
    for a in recent_appts:
        nm = f'{a.cust_name} booked {a.service.name if a.service else "a service"}'
        if a.status == 'confirmed': nm = f'AI confirmed {a.cust_name}'
        elif a.status == 'completed': nm = f'{a.cust_name} completed their visit'
        elif a.status == 'cancelled': nm = f'{a.cust_name} cancelled'
        notifs.append({'status': a.status, 'title': a.status.capitalize(), 'desc': nm, 'time': a.created_at.strftime('%b %d, %H:%M')})
    return render_template('notifications.html', notifs=notifs)

@app.route('/dashboard/ai-agent')
@login_required
def ai_agent():
    pending_calls = Appointment.query.filter(and_(
        Appointment.business_id==current_user.id, Appointment.status=='pending',
        Appointment.ai_call_status=='pending')).all()
    total_calls = Appointment.query.filter(and_(
        Appointment.business_id==current_user.id, Appointment.ai_call_status=='completed')).count()
    confirmed_by_ai = Appointment.query.filter(and_(
        Appointment.business_id==current_user.id, Appointment.ai_verified==True)).count()
    confirm_rate = round((confirmed_by_ai / total_calls * 100)) if total_calls > 0 else 0
    emails_sent = Appointment.query.filter(and_(
        Appointment.business_id==current_user.id, Appointment.email_sent==True)).count()
    return render_template('ai_agent.html', pending_calls=pending_calls, confirm_rate=confirm_rate,
                           total_calls=total_calls, stats={'emails_sent': emails_sent})

@app.route('/dashboard/ai-agent/<aid>/call', methods=['POST'])
@login_required
def simulate_call(aid):
    a = Appointment.query.filter_by(id=aid, business_id=current_user.id).first_or_404()
    a.ai_call_status = 'completed'
    a.ai_verified = True
    a.status = 'confirmed'
    if a.payment_amount > 0: a.payment_status = 'completed'
    a.email_sent = True
    a.email_sent_at = datetime.utcnow()
    db.session.commit()
    sent = send_ai_confirmation(a, current_user)
    if sent:
        flash(f'AI confirmed appointment with {a.cust_name}. Email sent. Code: {a.confirmation_code}', 'success')
    else:
        flash(f'AI confirmed {a.cust_name}. (Demo mode - configure SMTP for real emails). Code: {a.confirmation_code}', 'info')
    return redirect(url_for('ai_agent'))

@app.route('/dashboard/appointments/<aid>/postpone', methods=['POST'])
@login_required
def postpone_appointment(aid):
    a = Appointment.query.filter_by(id=aid, business_id=current_user.id).first_or_404()
    new_date = request.form.get('new_date')
    new_time = request.form.get('new_time')
    if new_date and new_time:
        a.date = datetime.strptime(new_date, '%Y-%m-%d').date()
        a.time = new_time
        a.status = 'postponed'
        db.session.commit()
        send_postpone_notification(a, current_user)
        flash(f'Appointment with {a.cust_name} has been postponed to {a.date.strftime("%b %d")} at {a.time}. AI agent will call to notify.', 'success')
    else:
        flash('Please provide new date and time.', 'error')
    return redirect(url_for('all_appointments'))

@app.route('/dashboard/ai-agent/<aid>/email', methods=['POST'])
@login_required
def send_agent_email(aid):
    a = Appointment.query.filter_by(id=aid, business_id=current_user.id).first_or_404()
    sent = send_booking_confirmation(a, current_user)
    a.email_sent = True
    a.email_sent_at = datetime.utcnow()
    db.session.commit()
    if sent:
        flash(f'Confirmation email sent to {a.cust_email}', 'success')
    else:
        flash(f'Email logged (demo mode). Configure MAIL_USERNAME & MAIL_PASSWORD on Render to send real emails.', 'info')
    return redirect(url_for('ai_agent'))

@app.route('/dashboard/invoices')
@login_required
def invoices():
    appts = Appointment.query.filter(and_(
        Appointment.business_id==current_user.id, Appointment.payment_amount > 0
    )).order_by(Appointment.created_at.desc()).all()
    return render_template('invoices.html', appointments=appts)

# ─── PUBLIC BOOKING ──────────────────────────────────────────
@app.route('/book/<slug>')
def book_page(slug):
    b = Business.query.filter_by(slug=slug).first_or_404()
    svcs = Service.query.filter_by(business_id=b.id, is_active=True).all()
    btype = BUSINESS_TYPES.get(b.business_type, BUSINESS_TYPES['other'])
    hours = WorkingHours.query.filter_by(business_id=b.id).order_by(WorkingHours.day).all()
    return render_template('book.html', business=b, services=svcs, btype=btype, hours=hours)

@app.route('/book/<slug>/confirm', methods=['POST'])
def book_confirm(slug):
    b = Business.query.filter_by(slug=slug).first_or_404()
    if not can_add_booking(b):
        flash('This business has reached their monthly booking limit.', 'error')
        return redirect(url_for('book_page', slug=slug))
    svc_id = request.form.get('service_id')
    if not svc_id:
        flash('Please select a service.', 'error')
        return redirect(url_for('book_page', slug=slug))
    svc = Service.query.get(svc_id)
    if not svc or svc.business_id != b.id:
        flash('Invalid service.', 'error')
        return redirect(url_for('book_page', slug=slug))
    d = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
    t = request.form.get('time', '')
    if not t:
        flash('Please select a time slot.', 'error')
        return redirect(url_for('book_page', slug=slug))
    exists = Appointment.query.filter(and_(
        Appointment.business_id==b.id, Appointment.service_id==svc.id,
        Appointment.date==d, Appointment.time==t,
        Appointment.status.in_(['pending','confirmed']))).first()
    if exists:
        flash('This time slot is already booked.', 'error')
        return redirect(url_for('book_page', slug=slug))
    cust_name = request.form['name'].strip()
    cust_email = request.form['email'].strip().lower()
    cust = Customer.query.filter_by(email=cust_email).first()
    if not cust:
        cust = Customer(name=cust_name, email=cust_email,
                        password=generate_password_hash(str(random.randint(100000,999999))),
                        phone=request.form.get('phone',''))
        db.session.add(cust)
        db.session.flush()
    a = Appointment(business_id=b.id, service_id=svc.id, customer_id=cust.id,
                    cust_name=cust_name, cust_email=cust_email,
                    cust_phone=request.form.get('phone',''),
                    cust_notes=request.form.get('notes',''),
                    date=d, time=t, confirmation_code=gen_code(),
                    payment_amount=svc.price, status='pending')
    db.session.add(a)
    db.session.commit()
    sent = send_booking_confirmation(a, b)
    if sent:
        flash('Confirmation email sent to your email address.', 'success')
    else:
        flash('Booking confirmed! (Email demo mode - configure SMTP to send real emails)', 'info')
    return redirect(url_for('booking_confirmed', slug=slug, aid=a.id))

@app.route('/book/<slug>/confirmed/<aid>')
def booking_confirmed(slug, aid):
    b = Business.query.filter_by(slug=slug).first_or_404()
    a = Appointment.query.filter_by(id=aid, business_id=b.id).first_or_404()
    return render_template('confirmed.html', business=b, appointment=a)

@app.route('/api/slots/<slug>/<date_str>')
def api_slots(slug, date_str):
    b = Business.query.filter_by(slug=slug).first_or_404()
    d = datetime.strptime(date_str, '%Y-%m-%d').date()
    svc_id = request.args.get('service_id')
    if not svc_id: return jsonify([])
    svc = Service.query.get(svc_id)
    if not svc: return jsonify([])
    wh = WorkingHours.query.filter_by(business_id=b.id, day=d.weekday()).first()
    if not wh or not wh.is_open: return jsonify([])
    booked = Appointment.query.filter(and_(
        Appointment.business_id==b.id, Appointment.date==d,
        Appointment.status.in_(['pending','confirmed']))).all()
    booked_times = {a.time for a in booked}
    oh, om = map(int, wh.open_time.split(':'))
    ch, cm = map(int, wh.close_time.split(':'))
    cur = datetime(d.year, d.month, d.day, oh, om)
    end = datetime(d.year, d.month, d.day, ch, cm)
    slots = []
    while cur + td(minutes=svc.duration) <= end:
        ts = cur.strftime('%H:%M')
        if ts not in booked_times: slots.append(ts)
        cur += td(minutes=30)
    return jsonify(slots)

@app.route('/api/ai-answer', methods=['POST'])
def ai_answer_call():
    data = request.get_json() or {}
    caller_phone = data.get('phone', '')
    business_slug = data.get('business_slug', '')
    reason = data.get('reason', 'general')
    
    b = Business.query.filter_by(slug=business_slug).first()
    if not b:
        return jsonify({'error': 'Business not found'}), 404
    
    customer_name = data.get('name', 'Customer')
    
    response = {
        'greeting': f'Thank you for calling {b.name}! I\'m Noomly AI assistant.',
        'options': [
            {'id': 'appointment', 'text': 'I want to know about my upcoming appointment'},
            {'id': 'reschedule', 'text': 'I want to reschedule my appointment'},
            {'id': 'cancel', 'text': 'I want to cancel my appointment'},
            {'id': 'employee', 'text': 'I want to speak with an employee'},
            {'id': 'hours', 'text': 'What are your business hours?'},
            {'id': 'other', 'text': 'I have a different question'}
        ],
        'message': f'Hello {customer_name}, how can I help you today?'
    }
    
    if reason == 'appointment':
        appt = Appointment.query.filter(and_(
            Appointment.cust_phone == caller_phone,
            Appointment.business_id == b.id,
            Appointment.status.in_(['pending', 'confirmed'])
        )).order_by(Appointment.date.desc()).first()
        if appt:
            response['message'] = f'Your next appointment is on {appt.date.strftime("%B %d, %Y")} at {appt.time} for {appt.service.name if appt.service else "your service"}. Your confirmation code is {appt.confirmation_code}.'
        else:
            response['message'] = 'I don\'t see any upcoming appointments under that phone number. Would you like to book a new appointment?'
    
    return jsonify(response)

@app.route('/api/calendar/events')
@login_required
def cal_events():
    appts = Appointment.query.filter_by(business_id=current_user.id).all()
    colors = {'pending':'#f59e0b','confirmed':'#10b981','completed':'#6366f1','cancelled':'#ef4444'}
    return jsonify([{
        'id': a.id, 'title': f'{a.cust_name} - {a.service.name if a.service else "N/A"}',
        'start': f'{a.date.isoformat()}T{a.time}', 'color': colors.get(a.status, '#6366f1')
    } for a in appts])

@app.route('/api/businesses/search')
def api_business_search():
    q = request.args.get('q', '')
    btype = request.args.get('type', '')
    query = Business.query
    if q: query = query.filter(or_(Business.name.ilike(f'%{q}%'), Business.city.ilike(f'%{q}%')))
    if btype: query = query.filter_by(business_type=btype)
    results = query.limit(20).all()
    return jsonify([{
        'id': b.id, 'name': b.name, 'slug': b.slug, 'city': b.city,
        'type': b.business_type, 'logo': b.logo,
        'url': url_for('book_page', slug=b.slug)
    } for b in results])

# ─── CUSTOMER AUTH & PORTAL ──────────────────────────────────
@app.route('/customer/register', methods=['GET','POST'])
def customer_register():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip().lower()
        pwd = request.form.get('password','')
        phone = request.form.get('phone','')
        city = request.form.get('city','')
        if not name or not email or len(pwd) < 6:
            flash('Please fill all fields. Password min 6 chars.', 'error')
            return render_template('cust_register.html')
        if Customer.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('cust_register.html')
        c = Customer(name=name, email=email, password=generate_password_hash(pwd), phone=phone, city=city)
        db.session.add(c)
        db.session.commit()
        login_user(c)
        flash(f'Welcome, {name.split()[0]}!', 'success')
        return redirect(url_for('customer_dashboard'))
    return render_template('cust_register.html')

@app.route('/customer/login', methods=['GET','POST'])
def customer_login():
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        pwd = request.form.get('password','')
        c = Customer.query.filter_by(email=email).first()
        if c and check_password_hash(c.password, pwd):
            login_user(c, remember=True)
            return redirect(url_for('customer_dashboard'))
        flash('Invalid email or password.', 'error')
    return render_template('cust_login.html')

@app.route('/customer/dashboard')
@login_required
def customer_dashboard():
    if not isinstance(current_user, Customer): return redirect(url_for('dashboard'))
    today = date.today()
    upcoming = Appointment.query.filter(and_(
        Appointment.customer_id==current_user.id, Appointment.date >= today,
        Appointment.status.in_(['pending','confirmed']))
    ).order_by(Appointment.date, Appointment.time).all()
    past = Appointment.query.filter(and_(
        Appointment.customer_id==current_user.id, Appointment.date < today
    )).order_by(Appointment.date.desc(), Appointment.time.desc()).limit(10).all()
    total_bookings = Appointment.query.filter_by(customer_id=current_user.id).count()
    total_spent = float(db.session.query(func.sum(Appointment.payment_amount)).filter(
        and_(Appointment.customer_id==current_user.id, Appointment.payment_status=='completed')).scalar() or 0)
    return render_template('cust_dashboard.html', upcoming=upcoming, past=past,
                           total_bookings=total_bookings, total_spent=total_spent)

@app.route('/customer/bookings')
@login_required
def customer_bookings():
    if not isinstance(current_user, Customer): return redirect(url_for('dashboard'))
    status = request.args.get('status', 'all')
    q = Appointment.query.filter_by(customer_id=current_user.id)
    if status != 'all': q = q.filter_by(status=status)
    appts = q.order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    return render_template('cust_bookings.html', appointments=appts, current_status=status)

@app.route('/customer/bookings/<aid>/cancel', methods=['POST'])
@login_required
def customer_cancel_booking(aid):
    if not isinstance(current_user, Customer): return redirect(url_for('dashboard'))
    a = Appointment.query.filter_by(id=aid, customer_id=current_user.id).first_or_404()
    if a.status in ['pending','confirmed']:
        a.status = 'cancelled'
        db.session.commit()
        flash('Appointment cancelled.', 'info')
    return redirect(url_for('customer_bookings'))

@app.route('/customer/profile', methods=['GET','POST'])
@login_required
def customer_profile():
    if not isinstance(current_user, Customer): return redirect(url_for('dashboard'))
    if request.method == 'POST':
        current_user.name = request.form.get('name','')
        current_user.phone = request.form.get('phone','')
        current_user.city = request.form.get('city','')
        db.session.commit()
        flash('Profile updated!', 'success')
        return redirect(url_for('customer_profile'))
    return render_template('cust_profile.html')

@app.route('/customer/logout')
@login_required
def customer_logout():
    logout_user()
    return redirect(url_for('index'))

# ─── ERROR PAGES ─────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, message='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', code=500, message='Something went wrong'), 500

# ─── INIT ────────────────────────────────────────────────────
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
