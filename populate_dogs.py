from app import app
from models import db, Dog, Appointment
from datetime import datetime, timedelta

sample_dogs = [
    dict(name='Maggie', age='9 Years', breed='Labrador', adoption_status='Adopted'),
    dict(name='Drea', age='7 Years', breed='Beagle', adoption_status='Adopted'),
    dict(name='Hannah', age='5 Years', breed='Poodle', adoption_status='Adopted'),
    dict(name='Phoebe', age='7 Years', breed='Bulldog', adoption_status='Adopted'),
    dict(name='Ellie', age='2 Years', breed='Terrier', adoption_status='Not Adopted'),
    dict(name='Flitter', age='4 Years', breed='Spaniel', adoption_status='Adopted'),
    dict(name='Alicia', age='10 Years', breed='Shepherd', adoption_status='Adopted'),
    dict(name='Hellen', age='6 Years', breed='Collie', adoption_status='Adopted'),
    dict(name='Roxane', age='20 Years', breed='Mixed', adoption_status='Adopted'),
    dict(name='Sparky', age='7 Years', breed='Retriever', adoption_status='Adopted'),
]

with app.app_context():
    for i, dog in enumerate(sample_dogs):
        d = Dog(**dog, rescue_id=1)
        db.session.add(d)
        db.session.flush()  # Get dog.id before commit
        # Add a sample appointment for each dog
        appt = Appointment(
            dog_id=d.id,
            type='vet' if i % 2 == 0 else 'medication',
            date=datetime.utcnow() + timedelta(days=i),
            description=f"Sample appointment for {d.name}",
            recurring=False
        )
        db.session.add(appt)
    db.session.commit()
    print(f"Added {len(sample_dogs)} sample dogs, each with an appointment.") 