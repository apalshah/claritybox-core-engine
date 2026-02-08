# ClarityBox Core Engine – Claude Instructions

You are working inside **claritybox-core-engine**.

## Goal (Phase 1)
- Run locally
- Poll data from MarketVibes (local)
- Compute a simple score
- Store or print results
- NO reporting, NO UI, NO ML

## Tech
- Python 3.10+
- Django
- SQLite (local only)

## Ports
- MarketVibes (local): 8001
- ClarityBox Core Engine: 8002

## Setup (Local)
```bash
python3 -m venv venv
source venv/bin/activate
pip install django requests djangorestframework python-dotenv
django-admin startproject core_engine .
python manage.py startapp engine
python manage.py migrate
python manage.py runserver 8002

