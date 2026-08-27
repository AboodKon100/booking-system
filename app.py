from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_
import uuid, random, string, os, re, smtplib, json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'noomly-dev-key-change-in-prod')
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'noomly.db')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', f'sqlite:///{db_path}')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'error'

BUSINESS_TYPES = {
    'salon': {'name': 'Salon & Beauty', 'icon': 'scissors', 'features': ['Hair Styling', 'Coloring', 'Manicure', 'Pedicure', 'Facial', 'Waxing'], 'default_services': [('Haircut & Styling', 45, 35), ('Hair Coloring', 120, 85), ('Manicure', 30, 25), ('Pedicure', 45, 35), ('Facial Treatment', 60, 50), ('Waxing', 30, 20)]},
    'barbershop': {'name': 'Barbershop', 'icon': 'scissors', 'features': ['Haircut', 'Beard Trim', 'Hot Towel Shave', 'Kids Cut'], 'default_services': [('Classic Haircut', 30, 25), ('Beard Trim & Shape', 20, 15), ('Hot Towel Shave', 25, 20), ('Kids Haircut', 20, 15), ('Haircut + Beard Combo', 45, 35)]},
    'clinic': {'name': 'Medical Clinic', 'icon': 'heart', 'features': ['General Checkup', 'Dental', 'Eye Care', 'Dermatology', 'Pediatrics'], 'default_services': [('General Checkup', 30, 75), ('Dental Cleaning', 45, 120), ('Eye Examination', 30, 95), ('Dermatology Consult', 20, 150), ('Pediatric Visit', 20, 100)]},
    'dental': {'name': 'Dental Clinic', 'icon': 'heart', 'features': ['Cleaning', 'Whitening', 'Fillings', 'Root Canal', 'Consultation'], 'default_services': [('Dental Cleaning', 45, 120), ('Teeth Whitening', 60, 350), ('Cavity Filling', 45, 200), ('Root Canal', 90, 800), ('Consultation', 20, 75)]},
    'gym': {'name': 'Gym & Fitness', 'icon': 'bolt', 'features': ['Personal Training', 'Group Classes', 'Yoga', 'CrossFit'], 'default_services': [('Personal Training', 60, 80), ('Yoga Class', 60, 25), ('CrossFit Session', 60, 35), ('Group HIIT', 45, 20), ('Nutrition Consult', 30, 60)]},
    'spa': {'name': 'Spa & Wellness', 'icon': 'sparkles', 'features': ['Massage', 'Facial', 'Body Treatment', 'Aromatherapy'], 'default_services': [('Swedish Massage', 60, 90), ('Deep Tissue Massage', 90, 130), ('Hot Stone Massage', 75, 120), ('Luxury Facial', 60, 110), ('Body Wrap', 90, 150)]},
    'restaurant': {'name': 'Restaurant & Cafe', 'icon': 'cake', 'features': ['Table Reservation', 'Private Events', 'Catering'], 'default_services': [('Table for 2', 120, 0), ('Table for 4', 120, 0), ('Private Dining', 180, 250), ('Catering Consultation', 30, 0), ('Event Booking', 60, 0)]},
    'salon_pet': {'name': 'Pet Grooming', 'icon': 'heart', 'features': ['Dog Grooming', 'Cat Grooming', 'Nail Trimming', 'Bath'], 'default_services': [('Full Grooming - Small Dog', 90, 45), ('Full Grooming - Large Dog', 120, 65), ('Cat Grooming', 60, 55), ('Nail Trimming', 15, 15), ('Bath & Blow Dry', 30, 25)]},
    'studio': {'name': 'Photo/Video Studio', 'icon': 'camera', 'features': ['Portrait', 'Family', 'Event', 'Product'], 'default_services': [('Portrait Session', 60, 150), ('Family Photoshoot', 90, 250), ('Event Coverage', 180, 500), ('Product Photography', 60, 200), ('Headshots', 30, 100)]},
    'tutoring': {'name': 'Tutoring & Education', 'icon': 'book', 'features': ['Math', 'Science', 'Languages', 'Test Prep'], 'default_services': [('1-on-1 Tutoring', 60, 50), ('Group Session', 90, 25), ('Test Prep', 120, 75), ('Language Lesson', 60, 45), ('Online Session', 60, 35)]},
    'consulting': {'name': 'Business Consulting', 'icon': 'briefcase', 'features': ['Strategy', 'Marketing', 'Finance', 'Legal'], 'default_services': [('Initial Consultation', 30, 100), ('Strategy Session', 60, 250), ('Marketing Review', 90, 350), ('Financial Planning', 120, 500), ('Follow-up', 30, 75)]},
    'cleaning': {'name': 'Cleaning Services', 'icon': 'home', 'features': ['Home Cleaning', 'Office Cleaning', 'Deep Clean'], 'default_services': [('Standard Cleaning', 120, 80), ('Deep Cleaning', 240, 150), ('Office Cleaning', 180, 120), ('Move-in/Move-out', 240, 200), ('Express Clean', 60, 50)]},
    'auto': {'name': 'Auto Services', 'icon': 'cog', 'features': ['Oil Change', 'Tire Service', 'Detailing', 'Repair'], 'default_services': [('Oil Change', 30, 45), ('Tire Rotation', 30, 25), ('Full Detail', 180, 150), ('Brake Inspection', 45, 75), ('General Repair', 60, 100)]},
    'other': {'name': 'Other Business', 'icon': 'grid', 'features': ['Custom Service'], 'default_services': [('Consultation', 30, 0), ('Standard Service', 60, 50), ('Premium Service', 90, 100)]},
}

def gen_id():
    return str(uuid.uuid4())
def gen_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

class Business(UserMixin, db.Model):
    id = db.Column(db.String(36), primary_key=True, default=gen_id)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    city = db.Column(db.String(100))
    country = db.Column(db.String(100))
    slug = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    business_type = db.Column(db.String(30), default='other')
    plan = db.Column(db.String(20), default='free')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    services = db.relationship('Service', backref='biz', lazy=True, cascade='all,delete-orphan')
    appointments = db.relationship('Appointment', backref='biz', lazy=True, cascade='all,delete-orphan')

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

class WorkingHours(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.String(36), db.ForeignKey('business.id'), nullable=False)
    day = db.Column(db.Integer, nullable=False)
    is_open = db.Column(db.Boolean, default=True)
    open_time = db.Column(db.String(5), default='09:00')
    close_time = db.Column(db.String(5), default='17:00')

@login_manager.user_loader
def load_user(uid):
    return Business.query.get(uid)

@app.context_processor
def inject_business_types():
    return dict(BUSINESS_TYPES=BUSINESS_TYPES)

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
        country = request.form.get('country','')
        btype = request.form.get('business_type','other')
        if not name or not email or len(pwd) < 6:
            flash('Please fill all required fields. Password min 6 chars.','error')
            return render_template('register.html', step=2, business_type=btype, btypes=BUSINESS_TYPES)
        if Business.query.filter_by(email=email).first():
            flash('Email already registered.','error')
            return render_template('register.html', step=2, business_type=btype, btypes=BUSINESS_TYPES)
        slug = re.sub(r'[^a-z0-9-]','',name.lower().replace(' ','-'))
        if Business.query.filter_by(slug=slug).first():
            slug += '-' + str(int(datetime.utcnow().timestamp()))
        b = Business(name=name,email=email,password=generate_password_hash(pwd),
                     phone=phone,city=city,country=country,slug=slug,business_type=btype)
        db.session.add(b)
        db.session.flush()
        for d in range(7):
            db.session.add(WorkingHours(business_id=b.id, day=d, is_open=d<5))
        btype_data = BUSINESS_TYPES.get(btype, BUSINESS_TYPES['other'])
        for svc_name, dur, price in btype_data['default_services']:
            db.session.add(Service(business_id=b.id, name=svc_name, duration=dur, price=price,
                                   color=random.choice(['#6366f1','#8b5cf6','#ec4899','#14b8a6','#f97316','#22c55e'])))
        db.session.commit()
        login_user(b)
        flash(f'Welcome to Noomly! Your {btype_data["name"]} booking system is ready.','success')
        return redirect(url_for('dashboard'))
    return render_template('register.html', step=1, btypes=BUSINESS_TYPES)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        pwd = request.form.get('password','')
        b = Business.query.filter_by(email=email).first()
        if b and check_password_hash(b.password, pwd):
            login_user(b)
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
    stats = {
        'today': Appointment.query.filter(and_(Appointment.business_id==current_user.id, Appointment.date==today)).count(),
        'pending': Appointment.query.filter(and_(Appointment.business_id==current_user.id, Appointment.status=='pending')).count(),
        'confirmed': Appointment.query.filter(and_(Appointment.business_id==current_user.id, Appointment.status=='confirmed')).count(),
        'completed': Appointment.query.filter(and_(Appointment.business_id==current_user.id, Appointment.status=='completed')).count(),
        'total': Appointment.query.filter_by(business_id=current_user.id).count(),
        'revenue': float(db.session.query(func.sum(Appointment.payment_amount)).filter(and_(Appointment.business_id==current_user.id, Appointment.payment_status=='completed')).scalar() or 0),
        'customers': db.session.query(func.count(func.distinct(Appointment.cust_email))).filter_by(business_id=current_user.id).scalar() or 0,
    }
    upcoming = Appointment.query.filter(and_(Appointment.business_id==current_user.id, Appointment.date>=today, Appointment.status.in_(['pending','confirmed']))).order_by(Appointment.date, Appointment.time).limit(10).all()
    recent = Appointment.query.filter_by(business_id=current_user.id).order_by(Appointment.created_at.desc()).limit(5).all()
    return render_template('dashboard.html', stats=stats, upcoming=upcoming, recent=recent)

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
        db.session.commit()
        flash(f'Appointment {new_status}.','success')
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
        flash('Service created!','success')
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
        flash('Service updated!','success')
        return redirect(url_for('services_list'))
    return render_template('edit_service.html', service=s)

@app.route('/dashboard/services/<sid>/delete', methods=['POST'])
@login_required
def delete_service(sid):
    s = Service.query.filter_by(id=sid, business_id=current_user.id).first_or_404()
    db.session.delete(s)
    db.session.commit()
    flash('Service deleted.','info')
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
        func.sum(Appointment.payment_amount).label('spent')
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
        flash('Settings saved!','success')
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
    flash('Hours updated!','success')
    return redirect(url_for('settings'))

@app.route('/dashboard/reports')
@login_required
def reports():
    today = date.today()
    month_start = today.replace(day=1)
    revenue = float(db.session.query(func.sum(Appointment.payment_amount)).filter(and_(Appointment.business_id==current_user.id, Appointment.payment_status=='completed', Appointment.created_at>=month_start)).scalar() or 0)
    appt_count = Appointment.query.filter(and_(Appointment.business_id==current_user.id, Appointment.created_at>=month_start)).count()
    top = db.session.query(Service.name, func.count(Appointment.id).label('c')).join(Appointment).filter(and_(Appointment.business_id==current_user.id, Appointment.created_at>=month_start)).group_by(Service.name).order_by(func.count(Appointment.id).desc()).limit(5).all()
    return render_template('reports.html', revenue=revenue, appt_count=appt_count, top_services=top)

@app.route('/dashboard/notifications')
@login_required
def notifications():
    return render_template('notifications.html')

@app.route('/dashboard/ai-agent')
@login_required
def ai_agent():
    pending_calls = Appointment.query.filter(and_(Appointment.business_id==current_user.id, Appointment.status=='pending', Appointment.ai_call_status=='pending')).all()
    return render_template('ai_agent.html', pending_calls=pending_calls)

@app.route('/dashboard/ai-agent/<aid>/call', methods=['POST'])
@login_required
def simulate_call(aid):
    a = Appointment.query.filter_by(id=aid, business_id=current_user.id).first_or_404()
    a.ai_call_status = 'completed'
    a.ai_verified = True
    a.status = 'confirmed'
    db.session.commit()
    flash(f'AI confirmed appointment with {a.cust_name}. Confirmation code: {a.confirmation_code}','success')
    return redirect(url_for('ai_agent'))

@app.route('/dashboard/invoices')
@login_required
def invoices():
    appts = Appointment.query.filter(and_(Appointment.business_id==current_user.id, Appointment.payment_amount > 0)).order_by(Appointment.created_at.desc()).all()
    return render_template('invoices.html', appointments=appts)

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
        flash('Please select a service.','error')
        return redirect(url_for('book_page', slug=slug))
    svc = Service.query.get(svc_id)
    if not svc or svc.business_id != b.id:
        flash('Invalid service.','error')
        return redirect(url_for('book_page', slug=slug))
    d = datetime.strptime(request.form['date'],'%Y-%m-%d').date()
    t = request.form['time']
    if not t:
        flash('Please select a time slot.','error')
        return redirect(url_for('book_page', slug=slug))
    exists = Appointment.query.filter(and_(Appointment.business_id==b.id, Appointment.service_id==svc.id, Appointment.date==d, Appointment.time==t, Appointment.status.in_(['pending','confirmed']))).first()
    if exists:
        flash('This time slot is already booked.','error')
        return redirect(url_for('book_page', slug=slug))
    a = Appointment(business_id=b.id, service_id=svc.id, cust_name=request.form['name'],
                    cust_email=request.form['email'], cust_phone=request.form.get('phone',''),
                    cust_notes=request.form.get('notes',''), date=d, time=t,
                    confirmation_code=gen_code(), payment_amount=svc.price, status='pending')
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
    d = datetime.strptime(date_str,'%Y-%m-%d').date()
    svc_id = request.args.get('service_id')
    if not svc_id:
        return jsonify([])
    svc = Service.query.get(svc_id)
    if not svc:
        return jsonify([])
    wh = WorkingHours.query.filter_by(business_id=b.id, day=d.weekday()).first()
    if not wh or not wh.is_open:
        return jsonify([])
    booked = Appointment.query.filter(and_(Appointment.business_id==b.id, Appointment.date==d, Appointment.status.in_(['pending','confirmed']))).all()
    booked_times = {a.time for a in booked}
    oh,om = map(int, wh.open_time.split(':'))
    ch,cm = map(int, wh.close_time.split(':'))
    cur = datetime(d.year,d.month,d.day,oh,om)
    end = datetime(d.year,d.month,d.day,ch,cm)
    slots = []
    while cur + timedelta(minutes=svc.duration) <= end:
        ts = cur.strftime('%H:%M')
        if ts not in booked_times:
            slots.append(ts)
        cur += timedelta(minutes=30)
    return jsonify(slots)

@app.route('/api/calendar/events')
@login_required
def cal_events():
    appts = Appointment.query.filter_by(business_id=current_user.id).all()
    colors = {'pending':'#f59e0b','confirmed':'#10b981','completed':'#6366f1','cancelled':'#ef4444'}
    return jsonify([{'id':a.id,'title':f'{a.cust_name} - {a.service.name if a.service else "N/A"}','start':f'{a.date.isoformat()}T{a.time}','color':colors.get(a.status,'#6366f1')} for a in appts])

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
