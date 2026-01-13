# Deployment Documentation

This document provides guidance for deploying the SFD application to production environments.

## Production Checklist

Before deploying to production, ensure:

- [ ] `DEBUG = False` in settings
- [ ] Strong `SECRET_KEY` configured
- [ ] Database configured (PostgreSQL/MySQL)
- [ ] Static files collected
- [ ] Environment variables secured
- [ ] HTTPS enabled
- [ ] ALLOWED_HOSTS configured
- [ ] Logging configured
- [ ] Backups configured
- [ ] Monitoring set up

## Environment Configuration

### Environment Variables

Create a `.env` file for production (or use system environment variables):

```env
# Django Settings
SECRET_KEY=your-production-secret-key-here-make-it-long-and-random
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
# If running on the same server:
DATABASE_URL=postgresql://user:password@localhost:5432/sfd_production
# If running in a container updates:
# DATABASE_URL=postgresql://user:password@db:5432/sfd_production

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password

# Static/Media Files
STATIC_ROOT=/var/www/sfd/static
MEDIA_ROOT=/var/www/sfd/media
STATIC_URL=/static/
MEDIA_URL=/media/

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/sfd/sfd.log
```

### Production Settings

Update `sfd_prj/settings.py` for production:

```python
import os
from decouple import config

# Security Settings
DEBUG = config('DEBUG', default=False, cast=bool)
SECRET_KEY = config('SECRET_KEY')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=lambda v: [s.strip() for s in v.split(',')])

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
        'CONN_MAX_AGE': 600,
    }
}

# Security Headers
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=True, cast=bool)
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Static Files
STATIC_ROOT = config('STATIC_ROOT', default=os.path.join(BASE_DIR, 'staticfiles'))
MEDIA_ROOT = config('MEDIA_ROOT', default=os.path.join(BASE_DIR, 'media'))

# Logging - Production configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'user_info': {
            'class': 'sfd.common.logging.UserInfoFilter',
        },
        'require_debug_false': {
            'class': 'django.utils.log.RequireDebugFalse',
        },
    },
    'formatters': {
        'verbose': {
            'format': '[{levelname}] [{asctime}] [{username}] [{ip_address}] [{name}:{lineno}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': config('LOG_FILE', default='/var/log/sfd/sfd.log'),
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            'filters': ['user_info'],
            'formatter': 'verbose'
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        },
    },
    'loggers': {
        'sfd': {
            'handlers': ['file', 'mail_admins'],
            'level': config('LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'django': {
            'handlers': ['file', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
    }
}
```

## Database Setup

### PostgreSQL

#### Installation (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

#### Create Database and User

```bash
sudo -u postgres psql

CREATE DATABASE sfd_production;
CREATE USER sfd_user WITH PASSWORD 'secure_password';
ALTER ROLE sfd_user SET client_encoding TO 'utf8';
ALTER ROLE sfd_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE sfd_user SET timezone TO 'Asia/Tokyo';
GRANT ALL PRIVILEGES ON DATABASE sfd_production TO sfd_user;
\q
```

#### Run Migrations

```bash
python manage.py migrate
```

### MySQL

#### Installation

```bash
sudo apt install mysql-server
```

#### Create Database

```bash
mysql -u root -p

CREATE DATABASE sfd_production CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'sfd_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON sfd_production.* TO 'sfd_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

## Web Server Setup

### Using Gunicorn + Nginx

#### Install Gunicorn

```bash
pip install gunicorn
```

#### Create Gunicorn Configuration

Create `gunicorn_config.py`:

```python
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "/var/log/sfd/gunicorn-access.log"
errorlog = "/var/log/sfd/gunicorn-error.log"
loglevel = "info"

# Process naming
proc_name = "sfd"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
```

#### Create Systemd Service

Create `/etc/systemd/system/sfd.service`:

```ini
[Unit]
Description=SFD Gunicorn Service
After=network.target

[Service]
Type=notify
User=sfd
Group=www-data
WorkingDirectory=/var/www/sfd
Environment="PATH=/var/www/sfd/.venv/bin"
ExecStart=/var/www/sfd/.venv/bin/gunicorn \
    --config /var/www/sfd/gunicorn_config.py \
    sfd_prj.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

#### Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable sfd
sudo systemctl start sfd
sudo systemctl status sfd
```

### Nginx Configuration

Create `/etc/nginx/sites-available/sfd`:

```nginx
upstream sfd_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Logging
    access_log /var/log/nginx/sfd-access.log;
    error_log /var/log/nginx/sfd-error.log;

    # Client body size
    client_max_body_size 10M;

    # Static files
    location /static/ {
        alias /var/www/sfd/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /var/www/sfd/media/;
        expires 30d;
    }

    # Django application
    location / {
        proxy_pass http://sfd_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}
```

#### Enable Site and Restart Nginx

```bash
sudo ln -s /etc/nginx/sites-available/sfd /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## SSL/TLS Certificate

### Using Let's Encrypt (Certbot)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### Auto-Renewal

```bash
sudo systemctl status certbot.timer
sudo certbot renew --dry-run
```

## Static Files

### Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### Configure Storage (Optional: AWS S3)

Install dependencies:

```bash
pip install boto3 django-storages
```

Update settings:

```python
# settings.py
if not DEBUG:
    # AWS S3 Settings
    AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = config('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = config('AWS_S3_REGION_NAME', default='ap-northeast-1')
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    
    # Static files
    STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/static/'
    
    # Media files
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/media/'
```

## Database Backups

### PostgreSQL Backup Script

Create `/usr/local/bin/backup_sfd_db.sh`:

```bash
#!/bin/bash

# Configuration
DB_NAME="sfd_production"
DB_USER="sfd_user"
BACKUP_DIR="/var/backups/sfd"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/sfd_backup_$DATE.sql.gz"
KEEP_DAYS=7

# Create backup directory
mkdir -p $BACKUP_DIR

# Perform backup
pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_FILE

# Remove old backups
find $BACKUP_DIR -name "sfd_backup_*.sql.gz" -mtime +$KEEP_DAYS -delete

echo "Backup completed: $BACKUP_FILE"
```

### Schedule with Cron

```bash
sudo chmod +x /usr/local/bin/backup_sfd_db.sh

# Add to crontab (daily at 2 AM)
sudo crontab -e
0 2 * * * /usr/local/bin/backup_sfd_db.sh
```

### Restore from Backup

```bash
gunzip < backup_file.sql.gz | psql -U sfd_user -d sfd_production
```

## Monitoring

### Application Monitoring

Install and configure monitoring tools:

```bash
pip install sentry-sdk
```

Update settings:

```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=config('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,
    send_default_pii=True,
    environment=config('ENVIRONMENT', default='production')
)
```

### Server Monitoring

```bash
# Install monitoring tools
sudo apt install htop iotop nethogs

# Check system resources
htop

# Monitor Django logs
tail -f /var/log/sfd/sfd.log

# Monitor Nginx access
tail -f /var/log/nginx/sfd-access.log

# Monitor Gunicorn
tail -f /var/log/sfd/gunicorn-error.log
```

## Performance Optimization

### Database Connection Pooling

Install pgbouncer:

```bash
sudo apt install pgbouncer
```

Configure `/etc/pgbouncer/pgbouncer.ini`:

```ini
[databases]
sfd_production = host=localhost port=5432 dbname=sfd_production

[pgbouncer]
listen_port = 6432
listen_addr = 127.0.0.1
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 100
default_pool_size = 20
```

Update Django database settings:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': '127.0.0.1',
        'PORT': '6432',  # pgbouncer port
        ...
    }
}
```

### Caching with Redis

Install Redis:

```bash
sudo apt install redis-server
pip install redis django-redis
```

Configure caching:

```python
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
```

## Deployment Workflow

### Manual Deployment

```bash
# 1. Pull latest code
cd /var/www/sfd
git pull origin main

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run migrations
python manage.py migrate

# 5. Collect static files
python manage.py collectstatic --noinput

# 6. Restart services
sudo systemctl restart sfd
sudo systemctl restart nginx
```

### Automated Deployment (Example)

Create `deploy.sh`:

```bash
#!/bin/bash

set -e

echo "Starting deployment..."

# Pull latest code
git pull origin main

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput

# Run tests
pytest

# Restart Gunicorn
sudo systemctl restart sfd

echo "Deployment completed successfully!"
```

## Health Checks

### Create Health Check Endpoint

```python
# sfd/views/health.py
from django.http import JsonResponse
from django.db import connection

def health_check(request):
    """Health check endpoint"""
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=500)

# Add to urls.py
path('health/', health_check, name='health_check'),
```

## Troubleshooting

### Common Issues

#### Static Files Not Loading

```bash
# Check static files collected
python manage.py collectstatic --noinput

# Check Nginx configuration
sudo nginx -t

# Check file permissions
sudo chown -R www-data:www-data /var/www/sfd/staticfiles
```

#### Database Connection Errors

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check connection from Python
python manage.py dbshell
```

#### Application Not Starting

```bash
# Check Gunicorn logs
sudo journalctl -u sfd -n 50

# Check for syntax errors
python manage.py check

# Test Gunicorn manually
gunicorn sfd_prj.wsgi:application
```

## Security Best Practices

1. **Keep secrets secret**: Never commit `.env` files or secrets to version control
2. **Use HTTPS**: Always redirect HTTP to HTTPS
3. **Keep dependencies updated**: Regularly update packages
4. **Limit database access**: Use least privilege principle
5. **Enable security headers**: Configure Nginx and Django security settings
6. **Monitor logs**: Watch for suspicious activity
7. **Regular backups**: Automate database and media backups
8. **Use strong passwords**: For all accounts and services
9. **Firewall configuration**: Only open necessary ports
10. **Regular security audits**: Review configurations periodically

## Maintenance

### Regular Tasks

- **Daily**: Check logs for errors
- **Weekly**: Review monitoring dashboards
- **Monthly**: Update dependencies, review security
- **Quarterly**: Database optimization, backup testing

### Updating Dependencies

```bash
# Check outdated packages
pip list --outdated

# Update specific package
pip install --upgrade package-name

# Update all packages (carefully)
pip install --upgrade -r requirements.txt

# Run tests after updates
pytest
```

## Rollback Procedure

If deployment fails:

```bash
# 1. Revert to previous git commit
git revert HEAD

# 2. Restore database from backup (if needed)
gunzip < backup.sql.gz | psql -U sfd_user -d sfd_production

# 3. Restart services
sudo systemctl restart sfd
sudo systemctl restart nginx
```

## Support and Documentation

- Monitor application logs: `/var/log/sfd/`
- Check Nginx logs: `/var/log/nginx/`
- Review systemd logs: `sudo journalctl -u sfd`
- Django admin: `https://yourdomain.com/admin/`
