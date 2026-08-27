# Deployment Guide

## Option 1: Render.com (Easiest - Free)

### Steps:
1. Push code to GitHub
2. Go to render.com → New → Web Service
3. Connect your GitHub repo
4. Settings:
   - Name: booking-system
   - Runtime: Python
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app.py`
5. Click "Create Web Service"
6. Your app is live at: https://your-app.onrender.com

### Free tier includes:
- 750 hours/month
- Automatic deploys from GitHub
- Custom domain support

## Option 2: Railway.app (Free $5/month credit)

### Steps:
1. Install Railway CLI:
   ```bash
   npm install -g @railway/cli
   ```

2. Login:
   ```bash
   railway login
   ```

3. Init project:
   ```bash
   railway init
   ```

4. Add database:
   ```bash
   railway add postgresql
   ```

5. Deploy:
   ```bash
   railway up
   ```

6. Get your URL:
   ```bash
   railway open
   ```

## Option 3: PythonAnywhere (Free tier)

### Steps:
1. Go to pythonanywhere.com
2. Create free account
3. Upload your files
4. Set up virtual environment
5. Configure WSGI
6. Your app: yourusername.pythonanywhere.com

## Before Deploying

Create a requirements.txt file:

```bash
pip freeze > requirements.txt
```

## Environment Variables (Important!)

For production, set these:
- SECRET_KEY: random string
- DATABASE_URL: your database URL

## Quick Deploy Checklist

- [ ] Push code to GitHub
- [ ] Create requirements.txt
- [ ] Choose platform (Render recommended)
- [ ] Deploy
- [ ] Test booking link
- [ ] Share with clients

## Custom Domain (Optional)

1. Buy domain from Namecheap ($8-12/year)
2. Add CNAME record pointing to your app
3. Configure in your hosting platform

## Your Production URLs Will Be

- App: https://your-app.onrender.com
- Booking: https://your-app.onrender.com/book/your-business
- Sales: https://yoursite.com (if you add custom domain)
