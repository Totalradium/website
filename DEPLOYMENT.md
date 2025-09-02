# Deployment Guide

## Environment Variables Setup

### Required Environment Variables

Set these environment variables in your deployment platform:

#### Essential Configuration
- `SECRET_KEY`: Django secret key (generate a new one for production)
- `DEBUG`: Set to `False` for production
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts (e.g., `yourdomain.com,.render.com`)
- `DATABASE_URL`: Database connection string (e.g., `postgres://user:pass@host:port/dbname`)

#### Optional Configuration
- `CSRF_TRUSTED_ORIGINS`: Comma-separated list of trusted origins for CSRF
- `EMAIL_HOST`: SMTP server host
- `EMAIL_PORT`: SMTP server port
- `EMAIL_HOST_USER`: Email username
- `EMAIL_HOST_PASSWORD`: Email password
- `EMAIL_USE_TLS`: Enable TLS for email

### For Render.com Deployment

1. Set environment variables in Render dashboard:
   ```
   SECRET_KEY=your-production-secret-key
   DEBUG=False
   ALLOWED_HOSTS=yourdomain.com,.render.com
   DATABASE_URL=postgres://... (provided by Render)
   ```

2. Build Command: `./build.sh`
3. Start Command: `gunicorn website.wsgi:application`

### For Local Development

1. Copy `.env.example` to `.env`
2. Update values in `.env` file
3. Run: `python manage.py runserver`

### Security Notes

- Never commit `.env` files to version control
- Use strong, unique SECRET_KEY for production
- Set DEBUG=False in production
- Configure HTTPS and security headers for production