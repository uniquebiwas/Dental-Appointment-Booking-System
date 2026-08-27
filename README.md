# Dental Clinic Appointment Booking and Reminder System

A Django-based academic project for managing dental appointments, patients, dentists, reminders, and reporting.

## Run locally

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000/ in your browser.




need to craete docker and docker compose for this application
when patient or staff book and appoinment the specific doctor should get the notification live 