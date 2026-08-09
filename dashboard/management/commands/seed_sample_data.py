import random
from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from appointments.models import Appointment, AppointmentHistory
from dentists.models import Dentist, DentistAvailability
from patients.models import Patient
from services.models import DentalService


def random_name():
    first_names = ['Ava', 'Noah', 'Mia', 'Liam', 'Emma', 'Ethan', 'Olivia', 'Mason', 'Sophia', 'Logan', 'Isabella', 'Lucas', 'Amelia', 'Oliver', 'Harper', 'Elijah', 'Aria', 'Jackson', 'Luna', 'Aiden']
    last_names = ['Patel', 'Khan', 'Garcia', 'Wilson', 'Nguyen', 'Smith', 'Johnson', 'Lee', 'Martinez', 'Brown', 'Davis', 'Clark', 'Lewis', 'Walker', 'Hall', 'Allen', 'Young', 'King', 'Wright', 'Lopez']
    return random.choice(first_names), random.choice(last_names)


def random_phone():
    return f'+1-{random.randint(200,999)}-{random.randint(200,999)}-{random.randint(1000,9999)}'


def random_reason():
    reasons = [
        'Toothache and sensitivity',
        'Routine dental cleaning',
        'Wisdom tooth evaluation',
        'Cavity filling consultation',
        'Follow-up after root canal',
        'Orthodontic review',
        'Gum inflammation check',
        'Cosmetic consultation',
        'Emergency pain assessment',
        'Night guard fitting',
    ]
    return random.choice(reasons)


def create_services():
    services = [
        ('Cleaning', 'Professional dental cleaning and polish', 45, 120.00),
        ('Exam & X-Ray', 'Comprehensive oral exam and X-ray review', 30, 90.00),
        ('Filling', 'Tooth filling using composite material', 60, 220.00),
        ('Root Canal', 'Root canal treatment for infected tooth', 120, 650.00),
        ('Extraction', 'Simple tooth extraction', 45, 180.00),
        ('Whitening', 'In-office teeth whitening treatment', 75, 320.00),
        ('Crown', 'Dental crown preparation and placement', 90, 720.00),
        ('Consultation', 'Doctor consultation and treatment plan', 30, 70.00),
    ]
    created = []
    for name, desc, duration, price in services:
        service, _ = DentalService.objects.get_or_create(
            name=name,
            defaults={
                'description': desc,
                'duration': duration,
                'price': price,
                'active': True,
            }
        )
        created.append(service)
    return created


def create_doctors(count=10):
    doctors = []
    for idx in range(1, count + 1):
        first_name, last_name = random_name()
        username = f'dentist{idx:02d}'
        email = f'{username}@example.com'
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'role': 'dentist',
                'account_status': 'approved',
                'is_active': True,
            }
        )
        if created:
            user.set_password('Dental123!')
            user.save()
        else:
            user.role = 'dentist'
            user.account_status = 'approved'
            user.is_active = True
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.save()

        dentist, _ = Dentist.objects.get_or_create(
            user=user,
            defaults={
                'dentist_id': f'DNT-{user.pk:04d}',
                'specialization': random.choice(['General Dentistry', 'Cosmetic Dentistry', 'Endodontics', 'Pediatric Dentistry', 'Orthodontics']),
                'license_number': f'LIC-{user.pk:06d}',
                'phone': random_phone(),
                'biography': 'Experienced dental provider offering caring, evidence-based treatment.',
                'years_of_experience': random.randint(3, 25),
                'active': True,
            }
        )

        for day in range(1, 6):
            DentistAvailability.objects.get_or_create(
                dentist=dentist,
                day_of_week=day,
                defaults={
                    'start_time': '09:00',
                    'end_time': '17:00',
                    'break_start': '12:00',
                    'break_end': '13:00',
                    'active': True,
                }
            )
        doctors.append(dentist)
    return doctors


def create_patients(count=25):
    patients = []
    last_names = ['Patel', 'Khan', 'Garcia', 'Wilson', 'Nguyen', 'Smith', 'Johnson', 'Lee', 'Martinez', 'Brown', 'Davis', 'Clark', 'Lewis', 'Walker', 'Hall', 'Allen', 'Young', 'King', 'Wright', 'Lopez']
    for idx in range(1, count + 1):
        first_name, last_name = random_name()
        username = f'patient{idx:02d}'
        email = f'{username}@example.com'
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'role': 'patient',
                'account_status': 'approved',
                'is_active': True,
            }
        )
        if created:
            user.set_password('Patient123!')
            user.save()
        else:
            user.role = 'patient'
            user.account_status = 'approved'
            user.is_active = True
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.save()

        patient, _ = Patient.objects.get_or_create(
            user=user,
            defaults={
                'patient_id': f'PAT-{user.pk:04d}',
                'date_of_birth': date.today() - timedelta(days=random.randint(18*365, 55*365)),
                'gender': random.choice(['M', 'F', 'O']),
                'phone': random_phone(),
                'address': f'{random.randint(100,999)} Main St, Suite {random.randint(1,300)}',
                'emergency_contact': f'{random.choice(["Mom", "Dad", "Spouse", "Friend"])} {random.choice(last_names)}',
                'emergency_contact_phone': random_phone(),
                'medical_notes': 'No significant medical history.' if random.random() < 0.75 else 'Manages seasonal allergies.',
                'allergies': '' if random.random() < 0.7 else 'Penicillin',
            }
        )
        patients.append(patient)
    return patients


def random_time_slots(start='09:00', end='16:00', step_minutes=30):
    hours, minutes = map(int, start.split(':'))
    current = timedelta(hours=hours, minutes=minutes)
    end_time = timedelta(hours=int(end.split(':')[0]), minutes=int(end.split(':')[1]))
    while current <= end_time:
        yield (datetime.min + current).time()
        current += timedelta(minutes=step_minutes)


def create_appointments(doctors, patients, services, count=60):
    statuses = ['Pending', 'Confirmed', 'Completed', 'Cancelled', 'No-Show']
    created = 0
    for _ in range(count * 2):
        if created >= count:
            break
        dentist = random.choice(doctors)
        patient = random.choice(patients)
        service = random.choice(services)
        appointment_date = date.today() + timedelta(days=random.randint(-40, 20))
        slot_options = list(random_time_slots())
        random.shuffle(slot_options)
        duration = service.duration or 30
        chosen = None
        for slot_time in slot_options:
            end_time = (datetime.combine(appointment_date, slot_time) + timedelta(minutes=duration)).time()
            if end_time <= slot_time:
                continue
            conflict = Appointment.objects.filter(
                dentist=dentist,
                appointment_date=appointment_date,
                start_time__lt=end_time,
                end_time__gt=slot_time,
            ).exclude(status='Cancelled').exists()
            if not conflict:
                chosen = (slot_time, end_time)
                break
        if not chosen:
            continue
        start_time, end_time = chosen
        status = random.choices(statuses, weights=[10, 20, 40, 20, 10], k=1)[0]
        if appointment_date > date.today() and status in ['Completed', 'No-Show']:
            status = random.choice(['Pending', 'Confirmed'])
        if appointment_date < date.today() and status == 'Pending':
            status = 'Completed'
        appointment = Appointment.objects.create(
            appointment_id=f'APT-{datetime.now().strftime("%Y%m%d%H%M%S")}{created:03d}',
            patient=patient,
            dentist=dentist,
            service=service,
            appointment_date=appointment_date,
            start_time=start_time,
            end_time=end_time,
            reason=random_reason(),
            status=status,
        )
        AppointmentHistory.objects.create(
            appointment=appointment,
            previous_status='New',
            new_status=status,
            changed_by=None,
            reason='Seeded appointment data.',
        )
        created += 1
    return created


class Command(BaseCommand):
    help = 'Seed sample doctors, patients, services, and appointments.'

    def handle(self, *args, **options):
        with transaction.atomic():
            services = create_services()
            doctors = create_doctors(10)
            patients = create_patients(25)
            appointments = create_appointments(doctors, patients, services, count=60)

        self.stdout.write(self.style.SUCCESS(f'Created {len(doctors)} doctors, {len(patients)} patients, and {appointments} appointments.'))
