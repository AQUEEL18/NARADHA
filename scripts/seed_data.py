"""
Seed script for NARADHA.

Creates demo departments, jurisdictions, categories and users so the
platform is immediately explorable after `migrate`.

Usage:
    python manage.py shell < scripts/seed_data.py
    # or
    python manage.py shell -c "exec(open('scripts/seed_data.py').read())"
"""
from apps.users.models import CustomUser, Department, Jurisdiction
from apps.complaints.models import ComplaintCategory

# --- Departments ---
departments = [
    ('Public Works Department', 'PWD', 'Roads, bridges and public infrastructure.'),
    ('Water Supply & Sanitation', 'WSS', 'Water supply, drainage and sanitation.'),
    ('Electricity Board', 'EB', 'Street lighting and power distribution.'),
    ('Waste Management', 'WM', 'Garbage collection and disposal.'),
    ('Parks & Recreation', 'PR', 'Public parks, playgrounds and greenery.'),
]
for name, code, desc in departments:
    Department.objects.get_or_create(
        code=code,
        defaults={'name': name, 'description': desc, 'default_sla_days': 14},
    )

# --- Jurisdictions ---
state, _ = Jurisdiction.objects.get_or_create(
    code='TS', defaults={'name': 'Demo State', 'jurisdiction_type': 'STATE'}
)
district, _ = Jurisdiction.objects.get_or_create(
    code='DT01', defaults={'name': 'Demo District', 'jurisdiction_type': 'DISTRICT', 'parent': state}
)
city, _ = Jurisdiction.objects.get_or_create(
    code='CT01', defaults={'name': 'Demo City', 'jurisdiction_type': 'CITY', 'parent': district}
)

# --- Complaint categories ---
categories = [
    ('Road Damage', 'RD', 'Potholes, cracked roads, broken pavements.', 'fa-road', '#3B82F6', 3),
    ('Water Leakage', 'WL', 'Pipe leaks, waterlogging, drainage issues.', 'fa-tint', '#06B6D4', 4),
    ('Street Light Outage', 'SL', 'Broken or non-functional street lights.', 'fa-lightbulb', '#F59E0B', 2),
    ('Garbage Accumulation', 'GA', 'Overflowing bins, illegal dumping.', 'fa-trash', '#10B981', 3),
    ('Public Safety Hazard', 'PS', 'Exposed wiring, open manholes, hazards.', 'fa-exclamation-triangle', '#EF4444', 5),
    ('Park Maintenance', 'PM', 'Broken equipment, unkempt parks.', 'fa-tree', '#84CC16', 1),
]
for name, code, desc, icon, color, weight in categories:
    ComplaintCategory.objects.get_or_create(
        code=code,
        defaults={
            'name': name, 'description': desc, 'icon': icon,
            'color': color, 'priority_weight': weight,
        },
    )

# --- Users (password: naradha123 on all demo accounts) ---
USERS = [
    ('admin@naradha.example', 'Site Admin', 'ADMIN', None),
    ('citizen@naradha.example', 'Ravi Kumar', 'CITIZEN', city),
    ('reviewer@naradha.example', 'Priya Sharma', 'REVIEWER', None),
    ('official@naradha.example', 'Anil Verma', 'OFFICIAL', city),
    ('minister@naradha.example', 'Sunita Rao', 'MINISTER', None),
    ('fieldworker@naradha.example', 'Kiran Das', 'FIELD_WORKER', city),
]
pwd = 'naradha123'
for email, first, role, jur in USERS:
    user, created = CustomUser.objects.get_or_create(
        email=email,
        defaults={
            'first_name': first.split()[0], 'last_name': first.split()[-1],
            'role': role, 'jurisdiction': jur, 'is_verified_user': True,
        },
    )
    if created:
        user.set_password(pwd)
        user.is_staff = role == 'ADMIN'
        user.is_superuser = role == 'ADMIN'
        user.save()

print('Seed data created.')
print('Demo accounts (all use the password: naradha123):')
for email, first, role, _ in USERS:
    print(f'  {role:<13} {email}')
