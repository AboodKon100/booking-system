from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///booking.db'
db = SQLAlchemy(app)

class Business(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    slug = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # minutes
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20))
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(5), nullable=False)  # HH:MM
    status = db.Column(db.String(20), default='confirmed')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    service = db.relationship('Service', backref='appointments')

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form.get('phone', '')
        address = request.form.get('address', '')
        slug = name.lower().replace(' ', '-').replace("'", '')

        if Business.query.filter_by(email=email).first():
            return 'Email already exists'

        if Business.query.filter_by(slug=slug).first():
            slug += '-' + str(datetime.now().timestamp())

        business = Business(name=name, email=email, password=password,
                          phone=phone, address=address, slug=slug)
        db.session.add(business)
        db.session.commit()
        session['business_id'] = business.id
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        business = Business.query.filter_by(email=email, password=password).first()
        if business:
            session['business_id'] = business.id
            return redirect(url_for('dashboard'))
        return 'Invalid credentials'
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'business_id' not in session:
        return redirect(url_for('login'))
    business = Business.query.get(session['business_id'])
    services = Service.query.filter_by(business_id=business.id).all()
    today = datetime.now().date()
    appointments = Appointment.query.filter_by(business_id=business.id)\
        .filter(Appointment.date >= today)\
        .order_by(Appointment.date, Appointment.time).limit(10).all()
    return render_template('dashboard.html', business=business,
                         services=services, appointments=appointments)

@app.route('/add-service', methods=['POST'])
def add_service():
    if 'business_id' not in session:
        return redirect(url_for('login'))
    service = Service(
        business_id=session['business_id'],
        name=request.form['name'],
        duration=int(request.form['duration']),
        price=float(request.form['price']),
        description=request.form.get('description', '')
    )
    db.session.add(service)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/delete-service/<int:service_id>')
def delete_service(service_id):
    if 'business_id' not in session:
        return redirect(url_for('login'))
    service = Service.query.get_or_404(service_id)
    if service.business_id == session['business_id']:
        db.session.delete(service)
        db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/book/<slug>')
def book(slug):
    business = Business.query.filter_by(slug=slug).first_or_404()
    services = Service.query.filter_by(business_id=business.id).all()
    return render_template('book.html', business=business, services=services)

@app.route('/book/<slug>/confirm', methods=['POST'])
def confirm_booking(slug):
    business = Business.query.filter_by(slug=slug).first_or_404()
    service = Service.query.get(int(request.form['service_id']))

    appointment = Appointment(
        business_id=business.id,
        service_id=service.id,
        customer_name=request.form['name'],
        customer_email=request.form['email'],
        customer_phone=request.form.get('phone', ''),
        date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
        time=request.form['time']
    )
    db.session.add(appointment)
    db.session.commit()
    return redirect(url_for('booking_confirmed', slug=slug))

@app.route('/book/<slug>/confirmed')
def booking_confirmed(slug):
    business = Business.query.filter_by(slug=slug).first_or_404()
    return render_template('confirmed.html', business=business)

@app.route('/api/slots/<slug>/<date_str>')
def get_slots(slug, date_str):
    business = Business.query.filter_by(slug=slug).first_or_404()
    date = datetime.strptime(date_str, '%Y-%m-%d').date()
    service_id = request.args.get('service_id', type=int)

    booked = Appointment.query.filter_by(business_id=business.id, date=date)\
        .filter(Appointment.status != 'cancelled').all()
    booked_times = [a.time for a in booked]

    slots = []
    for hour in range(9, 21):
        for minute in [0, 30]:
            time_str = f"{hour:02d}:{minute:02d}"
            if time_str not in booked_times:
                slots.append(time_str)

    return jsonify(slots)

@app.route('/logout')
def logout():
    session.pop('business_id', None)
    return redirect(url_for('home'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
