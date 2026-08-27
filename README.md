# Noomly — Never Miss Another Appointment

A premium SaaS booking platform for service businesses. 24/7 online booking, AI verification, secure payments, and automatic invoicing.

## Features

- **24/7 Online Booking** — Customers book anytime, from any device
- **AI Verification Agent** — Reduces no-shows by 80% via automated confirmation calls
- **Secure Payments** — Stripe-powered deposits and full payments with automatic invoicing
- **Business Dashboard** — Revenue analytics, calendar view, customer management
- **Public Booking Pages** — Shareable links for each business
- **Working Hours** — Configurable per-day availability
- **Responsive Design** — Premium Meta-level UI/UX

## Tech Stack

- **Backend:** Python 3.12, Flask
- **Database:** SQLAlchemy (SQLite dev / PostgreSQL production)
- **Frontend:** Tailwind CSS, Chart.js, FullCalendar
- **Payments:** Stripe
- **Hosting:** Render.com

## Quick Start

```bash
git clone https://github.com/AboodKon100/booking-system.git
cd booking-system
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000

## Deployment

Render.com:
- Build Command: `pip install -r requirements.txt`
- Start Command: `gunicorn app:app`

## Pricing

| Plan | Price | Features |
|------|-------|----------|
| Starter | Free | 1 service, 10 bookings/month |
| Professional | $29/mo | Unlimited everything, AI verification, custom branding |
| Business | $79/mo | Multiple staff, API access, dedicated manager |

## License

MIT License — Built by AboodKon100 (abdallah.biz100@gmail.com)
