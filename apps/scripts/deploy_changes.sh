#!/bin/bash
set -e

echo "=== Step 1: Django Check ==="
cd /u01/app/LMS-Portal/apps
set -a && source /etc/lms-portal.env && set +a
/u01/app/LMS-Portal/venv/bin/python manage.py check
echo ""

echo "=== Step 2: Run Migrations ==="
/u01/app/LMS-Portal/venv/bin/python manage.py migrate
echo ""

echo "=== Step 3: Restart Gunicorn ==="
sudo systemctl restart gunicorn
sleep 3
systemctl is-active gunicorn
echo ""

echo "=== Step 4: Git Commit ==="
cd /u01/app/LMS-Portal
git add -A
git status --short
git commit -m "refactor: rename Category/Users tables, remove eduassist app, drop eduassist tables"
echo ""

echo "=== ALL DONE ==="
