from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta, timedelta as td
from sqlalchemy import func, and_, extract
import uuid, random, string, os, re, calendar as cal_mod

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'noomly-prod-key-2026-change')
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'noomly.db')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{db_path}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'error'

BUSINESS_TYPES = {
    'salon': {'name': 'Salon & Beauty', 'icon': '&#9986;', 'features': ['Hair Styling', 'Coloring', 'Manicure', 'Pedicure', 'Facial', 'Waxing'], 'default_services': [('Haircut & Styling', 45, 45), ('Hair Coloring', 120, 120), ('Manicure', 30, 30), ('Pedicure', 45, 45), ('Facial Treatment', 60, 65), ('Waxing', 30, 35)]},
    'barbershop': {'name': 'Barbershop', 'icon': '&#9986;', 'features': ['Haircut', 'Beard Trim', 'Hot Towel Shave', 'Kids Cut'], 'default_services': [('Classic Haircut', 30, 35), ('Beard Trim & Shape', 20, 20), ('Hot Towel Shave', 25, 30), ('Kids Haircut', 20, 20), ('Haircut + Beard Combo', 45, 50)]},
    'clinic': {'name': 'Medical Clinic', 'icon': '&#128138;', 'features': ['General Checkup', 'Dental', 'Eye Care', 'Dermatology'], 'default_services': [('General Checkup', 30, 80), ('Dental Cleaning', 45, 120), ('Eye Examination', 30, 95), ('Dermatology Consult', 20, 150)]},
    'dental': {'name': 'Dental Clinic', 'icon': '&#129463;', 'features': ['Cleaning', 'Whitening', 'Fillings', 'Root Canal'], 'default_services': [('Dental Cleaning', 45, 120), ('Teeth Whitening', 60, 350), ('Cavity Filling', 45, 200), ('Consultation', 20, 75)]},
    'gym': {'name': 'Gym & Fitness', 'icon': '&#127947;', 'features': ['Personal Training', 'Group Classes', 'Yoga', 'CrossFit'], 'default_services': [('Personal Training', 60, 80), ('Yoga Class', 60, 25), ('CrossFit Session', 60, 35), ('Group HIIT', 45, 20)]},
    'spa': {'name': 'Spa & Wellness', 'icon': '&#128134;', 'features': ['Massage', 'Facial', 'Body Treatment', 'Aromatherapy'], 'default_services': [('Swedish Massage', 60, 90), ('Deep Tissue Massage', 90, 130), ('Hot Stone Massage', 75, 120), ('Luxury Facial', 60, 110)]},
    'restaurant': {'name': 'Restaurant & Cafe', 'icon': '&#127860;', 'features': ['Table Reservation', 'Private Events', 'Catering'], 'default_services': [('Table for 2', 120, 0), ('Table for 4', 120, 0), ('Private Dining', 180, 250), ('Event Booking', 60, 0)]},
    'salon_pet': {'name': 'Pet Grooming', 'icon': '&#128049;', 'features': ['Dog Grooming', 'Cat Grooming', 'Nail Trimming', 'Bath'], 'default_services': [('Full Grooming - Small Dog', 90, 45), ('Full Grooming - Large Dog', 120, 65), ('Cat Grooming', 60, 55), ('Nail Trimming', 15, 15)]},
    'studio': {'name': 'Photo/Video Studio', 'icon': '&#128247;', 'features': ['Portrait', 'Family', 'Event', 'Product'], 'default_services': [('Portrait Session', 60, 150), ('Family Photoshoot', 90, 250), ('Event Coverage', 180, 500), ('Product Photography', 60, 200)]},
    'tutoring': {'name': 'Tutoring & Education', 'icon': '&#128218;', 'features': ['Math', 'Science', 'Languages', 'Test Prep'], 'default_services': [('1-on-1 Tutoring', 60, 50), ('Group Session', 90, 25), ('Test Prep', 120, 75), ('Language Lesson', 60, 45)]},
    'consulting': {'name': 'Business Consulting', 'icon': '&#128188;', 'features': ['Strategy', 'Marketing', 'Finance', 'Legal'], 'default_services': [('Initial Consultation', 30, 100), ('Strategy Session', 60, 250), ('Marketing Review', 90, 350), ('Follow-up', 30, 75)]},
    'cleaning': {'name': 'Cleaning Services', 'icon': '&#128719;', 'features': ['Home Cleaning', 'Office Cleaning', 'Deep Clean'], 'default_services': [('Standard Cleaning', 120, 80), ('Deep Cleaning', 240, 150), ('Office Cleaning', 180, 120), ('Express Clean', 60, 50)]},
    'auto': {'name': 'Auto Services', 'icon': '&#9881;', 'features': ['Oil Change', 'Tire Service', 'Detailing', 'Repair'], 'default_services': [('Oil Change', 30, 45), ('Tire Rotation', 30, 25), ('Full Detail', 180, 150), ('Brake Inspection', 45, 75)]},
    'other': {'name': 'Other Business', 'icon': '&#128736;', 'features': ['Custom Service'], 'default_services': [('Consultation', 30, 0), ('Standard Service', 60, 50), ('Premium Service', 90, 100)]},
}

CUSTOMER_FIRST = ['Emma','Liam','Olivia','Noah','Ava','William','Sophia','James','Isabella','Oliver','Mia','Benjamin','Charlotte','Lucas','Amelia','Henry','Harper','Alexander','Evelyn','Daniel','Luna','Michael','Camila','Ethan','Gianna','Sebastian','Aria','Jack','Scarlett','Aiden','Penelope','Owen','Layla','Samuel','Chloe','Ryan','Victoria','Nathan','Madison','Caleb','Eleanor']
CUSTOMER_LAST = ['Smith','Johnson','Williams','Brown','Jones','Garcia','Miller','Davis','Rodriguez','Martinez','Hernandez','Lopez','Gonzalez','Wilson','Anderson','Thomas','Taylor','Moore','Jackson','Martin','Lee','Perez','Thompson','White','Harris','Sanchez','Clark','Ramirez','Lewis','Robinson','Walker','Young','Allen','King','Wright','Scott','Torres','Nguyen','Hill','Flores']
CUSTOMER_CITIES = ['Riyadh','Jeddah','Dammam','Mecca','Medina','Al Khobar','Dhahran','Tabuk','Buraidah','Khamis Mushait','Abha','Najran','Jizan','Hail','Al Jubail']

def gen_id():
    return str(uuid.uuid4())
def gen_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
def gen_slug(name):
    slug = re.sub(r'[^a-z0-9-]', '', name.lower().replace(' ', '-'))
    return slug

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
    plan = db.Column(db.String(20), default='professional')
    logo_url = db.Column(db.String(500))
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
    if u:
        return u
    return Customer.query.get(uid)

@app.context_processor
def inject_globals():
    return dict(BUSINESS_TYPES=BUSINESS_TYPES, now=datetime.utcnow())

# ─── SEED DATA ──────────────────────────────────────────────
def seed_demo_data(business):
    services = Service.query.filter_by(business_id=business.id).all()
    if not services:
        return
    first_names = random.sample(CUSTOMER_FIRST, min(12, len(CUSTOMER_FIRST)))
    last_names = random.sample(CUSTOMER_LAST, min(12, len(CUSTOMER_LAST)))
    statuses = ['completed','completed','completed','completed','confirmed','confirmed','pending','pending','cancelled']
    today = date.today()
    appointments = []
    for i in range(20):
        svc = random.choice(services)
        day_offset = random.randint(-30, 14)
        appt_date = today + td(days=day_offset)
        if appt_date.weekday() >= 5:
            appt_date += td(days=(7 - appt_date.weekday()))
        hour = random.randint(9, 16)
        minute = random.choice([0, 15, 30, 45])
        appt_time = f'{hour:02d}:{minute:02d}'
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        cust_name = f'{fn} {ln}'
        cust_email = f'{fn.lower()}.{ln.lower()}@email.com'
        status = random.choice(statuses)
        if appt_date > today:
            status = random.choice(['pending','confirmed'])
        if appt_date < today - td(days=3) and status == 'pending':
            status = random.choice(['completed','cancelled'])
        is_paid = status in ['confirmed','completed'] and svc.price > 0
        created = appt_date - td(days=random.randint(1, 7))
        a = Appointment(
            business_id=business.id,
            service_id=svc.id,
            cust_name=cust_name,
            cust_email=cust_email,
            cust_phone=f'+966 5{random.randint(0,9)} {random.randint(100,999)} {random.randint(1000,9999)}',
            date=appt_date,
            time=appt_time,
            status=status,
            payment_status='completed' if is_paid else ('unpaid' if svc.price > 0 else 'free'),
            payment_amount=svc.price if is_paid else 0,
            confirmation_code=gen_code(),
            ai_verified=(status in ['confirmed','completed']),
            ai_call_status='completed' if status in ['confirmed','completed'] else 'pending',
            created_at=created,
        )
        appointments.append(a)
    db.session.add_all(appointments)
    db.session.commit()

# ─── BUSINESS AUTH ───────────────────────────────────────────
@app.route('/')
def index():
    return render_template('landing.html')

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
        b = Business(name=name, email=email, password=generate_password_hash(pwd),
                     phone=phone, city=city, slug=slug, business_type=btype, country='Saudi Arabia')
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
        seed_demo_data(b)
        login_user(b)
        flash(f'Welcome to Noomly! Your {btype_data["name"]} system is ready with demo data.', 'success')
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

# ─── BUSINESS DASHBOARD ──────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    month_start = today.replace(day=1)
    week_start = today - td(days=today.weekday())
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
        'conversion_rate': 0,
    }
    total_appts = stats['total']
    if total_appts > 0:
        stats['conversion_rate'] = round((stats['completed'] / total_appts) * 100)
    revenue_7d = []
    labels_7d = []
    for i in range(6, -1, -1):
        d = today - td(days=i)
        rev = float(db.session.query(func.sum(Appointment.payment_amount)).filter(and_(
            Appointment.business_id==current_user.id,
            Appointment.payment_status=='completed',
            func.date(Appointment.date) == d
        )).scalar() or 0)
        revenue_7d.append(rev)
        labels_7d.append(d.strftime('%a'))
    status_data = [stats['pending'], stats['confirmed'], stats['completed'],
                   Appointment.query.filter(and_(Appointment.business_id==current_user.id, Appointment.status=='cancelled')).count()]
    upcoming = Appointment.query.filter(and_(
        Appointment.business_id==current_user.id,
        Appointment.date >= today,
        Appointment.status.in_(['pending','confirmed'])
    )).order_by(Appointment.date, Appointment.time).limit(8).all()
    recent = Appointment.query.filter_by(business_id=current_user.id).order_by(Appointment.created_at.desc()).limit(6).all()
    top_services = db.session.query(
        Service.name, func.count(Appointment.id).label('cnt'), func.sum(Appointment.payment_amount).label('rev')
    ).join(Service, Appointment.service_id == Service.id).filter(
        and_(Appointment.business_id==current_user.id, Appointment.payment_status=='completed')
    ).group_by(Service.name).order_by(func.count(Appointment.id).desc()).limit(5).all()
    return render_template('dashboard.html', stats=stats, upcoming=upcoming, recent=recent,
                           revenue_7d=revenue_7d, labels_7d=labels_7d, status_data=status_data,
                           top_services=top_services)

@app.route('/dashboard/appointments')
@login_required
def all_appointments():
    status = request.args.get('status','all')
    q = Appointment.query.filter_by(business_id=current_user.id)
    if status != 'all':
        q = q.filter_by(status=status)
    appts = q.order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    return render_template('appointments.html', appointments=appts, current_status=status)

@app.route('/dashboard/appointments/<aid>/status', methods=['POST'])
@login_required
def update_status(aid):
    a = Appointment.query.filter_by(id=aid, business_id=current_user.id).first_or_404()
    new_status = request.form.get('status')
    if new_status in ['confirmed','completed','cancelled']:
        a.status = new_status
        if new_status == 'confirmed':
            a.ai_verified = True
            a.ai_call_status = 'completed'
            if a.payment_amount > 0:
                a.payment_status = 'completed'
        db.session.commit()
        flash(f'Appointment {new_status}.', 'success')
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
    monthly_rev = []
    monthly_labels = []
    for i in range(5, -1, -1):
        m = today.month - i
        y = today.year
        if m <= 0:
            m += 12
            y -= 1
        rev = float(db.session.query(func.sum(Appointment.payment_amount)).filter(and_(
            Appointment.business_id==current_user.id,
            Appointment.payment_status=='completed',
            extract('year', Appointment.date) == y,
            extract('month', Appointment.date) == m
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
        if a.status == 'pending':
            notifs.append({'icon': 'calendar', 'color': 'bg-amber-500', 'title': 'New Booking', 'desc': f'{a.cust_name} booked {a.service.name if a.service else "a service"}', 'time': a.created_at.strftime('%b %d, %H:%M')})
        elif a.status == 'confirmed':
            notifs.append({'icon': 'check', 'color': 'bg-green-500', 'title': 'Appointment Confirmed', 'desc': f'AI confirmed {a.cust_name}', 'time': a.created_at.strftime('%b %d, %H:%M')})
        elif a.status == 'completed':
            notifs.append({'icon': 'star', 'color': 'bg-brand-500', 'title': 'Appointment Completed', 'desc': f'{a.cust_name} completed their visit', 'time': a.created_at.strftime('%b %d, %H:%M')})
        elif a.status == 'cancelled':
            notifs.append({'icon': 'x', 'color': 'bg-red-500', 'title': 'Appointment Cancelled', 'desc': f'{a.cust_name} cancelled', 'time': a.created_at.strftime('%b %d, %H:%M')})
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
    return render_template('ai_agent.html', pending_calls=pending_calls, confirm_rate=confirm_rate, total_calls=total_calls)

@app.route('/dashboard/ai-agent/<aid>/call', methods=['POST'])
@login_required
def simulate_call(aid):
    a = Appointment.query.filter_by(id=aid, business_id=current_user.id).first_or_404()
    a.ai_call_status = 'completed'
    a.ai_verified = True
    a.status = 'confirmed'
    if a.payment_amount > 0:
        a.payment_status = 'completed'
    db.session.commit()
    flash(f'AI confirmed appointment with {a.cust_name}. Code: {a.confirmation_code}', 'success')
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
    return render_template('book.html', business=b, services=svcs, btype=btype)

@app.route('/book/<slug>/confirm', methods=['POST'])
def book_confirm(slug):
    b = Business.query.filter_by(slug=slug).first_or_404()
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
    if not svc_id:
        return jsonify([])
    svc = Service.query.get(svc_id)
    if not svc:
        return jsonify([])
    wh = WorkingHours.query.filter_by(business_id=b.id, day=d.weekday()).first()
    if not wh or not wh.is_open:
        return jsonify([])
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
        if ts not in booked_times:
            slots.append(ts)
        cur += td(minutes=30)
    return jsonify(slots)

@app.route('/api/calendar/events')
@login_required
def cal_events():
    appts = Appointment.query.filter_by(business_id=current_user.id).all()
    colors = {'pending':'#f59e0b','confirmed':'#10b981','completed':'#6366f1','cancelled':'#ef4444'}
    return jsonify([{
        'id': a.id,
        'title': f'{a.cust_name} - {a.service.name if a.service else "N/A"}',
        'start': f'{a.date.isoformat()}T{a.time}',
        'color': colors.get(a.status, '#6366f1')
    } for a in appts])

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
    if not isinstance(current_user, Customer):
        return redirect(url_for('dashboard'))
    today = date.today()
    upcoming = Appointment.query.filter(and_(
        Appointment.customer_id==current_user.id,
        Appointment.date >= today,
        Appointment.status.in_(['pending','confirmed'])
    )).order_by(Appointment.date, Appointment.time).all()
    past = Appointment.query.filter(and_(
        Appointment.customer_id==current_user.id,
        Appointment.date < today
    )).order_by(Appointment.date.desc(), Appointment.time.desc()).limit(10).all()
    total_bookings = Appointment.query.filter_by(customer_id=current_user.id).count()
    total_spent = float(db.session.query(func.sum(Appointment.payment_amount)).filter(
        and_(Appointment.customer_id==current_user.id, Appointment.payment_status=='completed')).scalar() or 0)
    return render_template('cust_dashboard.html', upcoming=upcoming, past=past,
                           total_bookings=total_bookings, total_spent=total_spent)

@app.route('/customer/bookings')
@login_required
def customer_bookings():
    if not isinstance(current_user, Customer):
        return redirect(url_for('dashboard'))
    status = request.args.get('status', 'all')
    q = Appointment.query.filter_by(customer_id=current_user.id)
    if status != 'all':
        q = q.filter_by(status=status)
    appts = q.order_by(Appointment.date.desc(), Appointment.time.desc()).all()
    return render_template('cust_bookings.html', appointments=appts, current_status=status)

@app.route('/customer/bookings/<aid>/cancel', methods=['POST'])
@login_required
def customer_cancel_booking(aid):
    if not isinstance(current_user, Customer):
        return redirect(url_for('dashboard'))
    a = Appointment.query.filter_by(id=aid, customer_id=current_user.id).first_or_404()
    if a.status in ['pending','confirmed']:
        a.status = 'cancelled'
        db.session.commit()
        flash('Appointment cancelled.', 'info')
    return redirect(url_for('customer_bookings'))

@app.route('/customer/profile', methods=['GET','POST'])
@login_required
def customer_profile():
    if not isinstance(current_user, Customer):
        return redirect(url_for('dashboard'))
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
