from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_
import uuid, random, string, os, re

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///noomly.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

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

@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip().lower()
        pwd = request.form.get('password','')
        phone = request.form.get('phone','')
        city = request.form.get('city','')
        country = request.form.get('country','')
        if not name or not email or len(pwd) < 6:
            flash('Please fill all fields. Password min 6 chars.','error')
            return redirect(url_for('register'))
        if Business.query.filter_by(email=email).first():
            flash('Email already registered.','error')
            return redirect(url_for('register'))
        slug = re.sub(r'[^a-z0-9-]','',name.lower().replace(' ','-'))
        if Business.query.filter_by(slug=slug).first():
            slug += '-' + str(int(datetime.utcnow().timestamp()))
        b = Business(name=name,email=email,password=generate_password_hash(pwd),
                     phone=phone,city=city,country=country,slug=slug)
        db.session.add(b)
        db.session.flush()
        for d in range(7):
            db.session.add(WorkingHours(business_id=b.id, day=d, is_open=d<5))
        db.session.commit()
        login_user(b)
        flash('Welcome to Noomly!','success')
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        pwd = request.form.get('password','')
        b = Business.query.filter_by(email=email).first()
        if b and check_password_hash(b.password, pwd):
            login_user(b)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.','error')
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
        'total': Appointment.query.filter_by(business_id=current_user.id).count(),
        'revenue': float(db.session.query(func.sum(Appointment.payment_amount)).filter(and_(Appointment.business_id==current_user.id, Appointment.payment_status=='completed')).scalar() or 0),
        'customers': db.session.query(func.count(func.distinct(Appointment.cust_email))).filter_by(business_id=current_user.id).scalar() or 0,
    }
    upcoming = Appointment.query.filter(and_(Appointment.business_id==current_user.id, Appointment.date>=today, Appointment.status.in_(['pending','confirmed']))).order_by(Appointment.date, Appointment.time).limit(10).all()
    recent = Appointment.query.filter_by(business_id=current_user.id).order_by(Appointment.created_at.desc()).limit(5).all()
    services = Service.query.filter_by(business_id=current_user.id, is_active=True).all()
    return render_template('dashboard.html', stats=stats, upcoming=upcoming, recent=recent, services=services)

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
    rows = db.session.query(Appointment.cust_name, Appointment.cust_email, Appointment.cust_phone, func.count(Appointment.id).label('count'), func.sum(Appointment.payment_amount).label('spent')).filter_by(business_id=current_user.id).group_by(Appointment.cust_email).order_by(func.count(Appointment.id).desc()).all()
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

@app.route('/book/<slug>')
def book_page(slug):
    b = Business.query.filter_by(slug=slug).first_or_404()
    svcs = Service.query.filter_by(business_id=b.id, is_active=True).all()
    return render_template('book.html', business=b, services=svcs)

@app.route('/book/<slug>/confirm', methods=['POST'])
def book_confirm(slug):
    b = Business.query.filter_by(slug=slug).first_or_404()
    svc = Service.query.get(request.form.get('service_id'))
    if not svc or svc.business_id != b.id:
        flash('Invalid service.','error')
        return redirect(url_for('book_page', slug=slug))
    d = datetime.strptime(request.form['date'],'%Y-%m-%d').date()
    t = request.form['time']
    exists = Appointment.query.filter(and_(Appointment.business_id==b.id, Appointment.service_id==svc.id, Appointment.date==d, Appointment.time==t, Appointment.status.in_(['pending','confirmed']))).first()
    if exists:
        flash('Time slot taken.','error')
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

@app.route('/api/stats')
@login_required
def api_stats():
    today = date.today()
    return jsonify({
        'today': Appointment.query.filter(and_(Appointment.business_id==current_user.id, Appointment.date==today)).count(),
        'pending': Appointment.query.filter(and_(Appointment.business_id==current_user.id, Appointment.status=='pending')).count(),
        'confirmed': Appointment.query.filter(and_(Appointment.business_id==current_user.id, Appointment.status=='confirmed')).count(),
        'revenue': float(db.session.query(func.sum(Appointment.payment_amount)).filter(and_(Appointment.business_id==current_user.id, Appointment.payment_status=='completed')).scalar() or 0),
        'customers': db.session.query(func.count(func.distinct(Appointment.cust_email))).filter_by(business_id=current_user.id).scalar() or 0,
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
