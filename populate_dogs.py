#!/usr/bin/env python
import argparse
from DogTrackerV2.app import app
from DogTrackerV2.models import db, Dog, Appointment, Rescue, User, AppointmentType, MedicinePreset, DogMedicine, Reminder, DogMedicineHistory
from datetime import datetime, timedelta, timezone, date
import random
import sys

names = [
    'Baxter', 'Luna', 'Moose', 'Ziggy', 'Willow', 'Pepper', 'Finn', 'Olive', 'Milo', 'Sadie',
    'Charlie', 'Bella', 'Max', 'Daisy', 'Rocky', 'Molly', 'Buddy', 'Bailey', 'Coco', 'Ruby',
    'Scout', 'Harley', 'Riley', 'Toby', 'Sasha', 'Ginger', 'Murphy', 'Shadow', 'Lucky', 'Sam',
    'Rosie', 'Jake', 'Sophie', 'Chloe', 'Jack', 'Maggie', 'Oscar', 'Zeus', 'Abby', 'Louie', 'Penny',
    'Bentley', 'Hazel', 'Nala', 'Thor', 'Winston', 'Ellie', 'Archie', 'Remy', 'Nova', 'Rex',
    'Jasper', 'Maddie', 'Ace', 'Phoebe', 'Simba', 'Ranger', 'Piper', 'Tank', 'Maple', 'Indie'
]
breeds = [
    'Corgi', 'Shih Tzu', 'Great Dane', 'Dachshund', 'Boxer', 'Chihuahua', 'Golden Retriever',
    'Pug', 'French Bulldog', 'German Shepherd', 'Labrador', 'Beagle', 'Poodle', 'Bulldog',
    'Terrier', 'Spaniel', 'Shepherd', 'Collie', 'Mixed', 'Retriever', 'Akita', 'Mastiff',
    'Doberman', 'Rottweiler', 'Husky', 'Malamute', 'Whippet', 'Greyhound', 'Pointer', 'Setter', 'Dalmatian',
    'Cavalier King Charles Spaniel', 'Boston Terrier', 'Bichon Frise', 'Bernese Mountain Dog', 'Shiba Inu',
    'Australian Shepherd', 'Border Collie', 'Cane Corso', 'Papillon', 'Samoyed', 'Weimaraner', 'Basenji',
    'Bloodhound', 'Saint Bernard', 'Newfoundland', 'Irish Setter', 'Great Pyrenees', 'Alaskan Klee Kai',
    'Saluki', 'Afghan Hound', 'Pekingese', 'Lhasa Apso', 'Scottish Terrier', 'Bullmastiff', 'Chow Chow'
]
adoption_statuses = ['Adopted', 'Not Adopted']
notes_pool = [
    '',
    'Very friendly and playful.',
    'Needs special diet.',
    'Good with children.',
    'Prefers quiet environments.',
    'Enjoys long walks.',
    'Has some anxiety around loud noises.',
    'House-trained.',
    'Loves to play fetch.',
    'Protective of family.',
    'Gets along with other dogs.',
    'Shy at first but warms up quickly.',
    'Energetic and loves to run.',
    'Enjoys car rides.'
]
medical_info_pool = [
    '',
    'Up to date on all vaccinations.',
    'Requires daily medication.',
    'Recently treated for fleas.',
    'Has a history of ear infections.',
    'No known medical issues.',
    'Allergic to chicken.',
    'Has arthritis in hind legs.',
    'Needs regular dental care.',
    'Recovering from surgery.'
]
adopter_notes_pool = [
    '',
    'Adopted by a loving family.',
    'Now lives with a retired couple.',
    'Adopted by a family with children.',
    'Adopted by a single owner.',
    'Moved to a farm after adoption.'
]
appointment_type_names = ['Vet Visit', 'Vaccination', 'Grooming', 'Adoption', 'General', 'Medication Start']
# This list is now for rescue-specific example presets if any are still desired.
# For the main, common medicines, we'll use the global_medicine_presets_data below.
example_rescue_medicine_presets = [
    {'name': 'RescueSpecial Dewormer', 'default_unit': 'ml', 'category': 'Parasite Control - Dewormer', 'suggested_units': 'ml,cc', 'notes': 'Special dewormer for this rescue.'},
    {'name': 'RescueComfort NSAID', 'default_unit': 'tablet', 'category': 'Anti-inflammatory & Pain Relief - NSAID', 'suggested_units': 'tablet,chewable', 'notes': 'Rescue-formulated pain relief.'}
]

global_medicine_presets_data = [
    # Parasite Control
    {
        "name": "Fenbendazole (Panacur)",
        "category": "Parasite Control - Dewormer",
        "default_dosage_instructions": "Typically administered for 3-5 consecutive days. Dosage varies by weight. Consult vet.",
        "suggested_units": "mg,ml,packet,g",
        "notes": "Broad-spectrum dewormer for various intestinal worms."
    },
    {
        "name": "Praziquantel",
        "category": "Parasite Control - Dewormer",
        "default_dosage_instructions": "Specific for tapeworms. Dosage based on weight. May be given with or without food.",
        "suggested_units": "mg,tablet",
        "notes": "Often combined with other dewormers."
    },
    {
        "name": "Afoxolaner (NexGard)",
        "category": "Parasite Control - Flea & Tick",
        "default_dosage_instructions": "Administer orally once a month. Chewable tablet, give with or without food.",
        "suggested_units": "chew,tablet",
        "notes": "Kills fleas and ticks. Prescription required."
    },
    {
        "name": "Ivermectin (Heartgard Plus)",
        "category": "Parasite Control - Heartworm",
        "default_dosage_instructions": "Administer orally once a month. Ensure dog chews tablet.",
        "suggested_units": "chew,tablet",
        "notes": "Prevents heartworm disease, treats and controls roundworms and hookworms. Prescription required."
    },
    # Antibiotics
    {
        "name": "Amoxicillin/Clavulanate (Clavamox)",
        "category": "Antibiotic",
        "default_dosage_instructions": "Typically given twice daily. Dosage based on weight and infection type. Give with food to reduce GI upset.",
        "suggested_units": "mg,ml,tablet",
        "notes": "Broad-spectrum antibiotic for various bacterial infections."
    },
    {
        "name": "Doxycycline",
        "category": "Antibiotic",
        "default_dosage_instructions": "Typically given once or twice daily. Dosage varies. Can cause GI upset; give with food if needed. Avoid with dairy/antacids.",
        "suggested_units": "mg,tablet,capsule",
        "notes": "Used for various bacterial infections, including tick-borne diseases."
    },
    # Anti-inflammatory & Pain Relief
    {
        "name": "Carprofen (Rimadyl)",
        "category": "Anti-inflammatory & Pain Relief - NSAID",
        "default_dosage_instructions": "Typically given once or twice daily. Dosage based on weight. Administer with food. Monitor for side effects.",
        "suggested_units": "mg,tablet,caplet,chewable",
        "notes": "Non-steroidal anti-inflammatory drug for pain and inflammation. Prescription required."
    },
    {
        "name": "Meloxicam (Metacam)",
        "category": "Anti-inflammatory & Pain Relief - NSAID",
        "default_dosage_instructions": "Typically given once daily. Oral suspension or tablets. Administer with food.",
        "suggested_units": "mg,ml,tablet",
        "notes": "NSAID for pain and inflammation, often used for arthritis. Prescription required."
    },
    {
        "name": "Gabapentin",
        "category": "Anti-inflammatory & Pain Relief / Behavioral",
        "default_dosage_instructions": "Dosage and frequency vary widely based on use (pain, anxiety, seizures). Consult vet.",
        "suggested_units": "mg,capsule,tablet,ml",
        "notes": "Used for chronic pain, nerve pain, seizures, and anxiety/sedation."
    },
    # Gastrointestinal Support
    {
        "name": "Maropitant (Cerenia)",
        "category": "Gastrointestinal Support",
        "default_dosage_instructions": "Once daily for vomiting. Tablets or injectable. Dosage by weight.",
        "suggested_units": "mg,tablet,ml",
        "notes": "Anti-nausea and anti-vomiting medication. Prescription required."
    },
    {
        "name": "Probiotics (FortiFlora)",
        "category": "Gastrointestinal Support",
        "default_dosage_instructions": "Typically one packet daily mixed with food.",
        "suggested_units": "packet,sachet,scoop",
        "notes": "Nutritional supplement to support intestinal health."
    },
    # Allergy & Skin
    {
        "name": "Diphenhydramine (Benadryl)",
        "category": "Allergy & Skin",
        "default_dosage_instructions": "Typical dose 1mg per pound of body weight, 2-3 times daily. Confirm with vet. Can cause drowsiness.",
        "suggested_units": "mg,tablet,capsule,ml",
        "notes": "Antihistamine for allergic reactions, itching. OTC, but vet guidance recommended for dosage."
    },
    # Behavioral Support
    {
        "name": "Trazodone",
        "category": "Behavioral Support",
        "default_dosage_instructions": "Used for anxiety or sedation. Dosage varies greatly. Given as needed or regularly.",
        "suggested_units": "mg,tablet",
        "notes": "Often used for situational anxiety (vet visits, thunderstorms). Prescription required."
    }
]

# Helper functions

def generate_unique_microchip(existing):
    while True:
        chip = str(random.randint(10000000, 99999999))
        if chip not in existing:
            existing.add(chip)
            return chip

def get_or_create_rescues():
    rescues = Rescue.query.all()
    needed = 3 - len(rescues)
    created = []
    for i in range(needed):
        rescue = Rescue(
            name=f"Rescue {len(rescues) + i + 1}",
            address=f"{100 + i} Main St",
            phone=f"555-000{i}",
            email=f"rescue{len(rescues) + i + 1}@example.com"
        )
        db.session.add(rescue)
        db.session.flush()
        created.append(rescue)
    db.session.commit()
    all_rescues = Rescue.query.all()
    return all_rescues

def seed_users(rescues):
    users = []
    for rescue in rescues:
        owner = User(name=f"{rescue.name} Owner", role='owner', device_id=None, invite_code=None, can_edit=True, rescue_id=rescue.id)
        staff = User(name=f"{rescue.name} Staff", role='staff', device_id=None, invite_code='INVITE123', can_edit=True, rescue_id=rescue.id)
        db.session.add(owner)
        db.session.add(staff)
        users.extend([owner, staff])
    db.session.commit()
    return users

def seed_appointment_types(rescues):
    types = []
    # Define specific colors for certain types
    type_colors = {
        "Vet Visit": "#d9534f",  # A shade of red
        "Vaccination": "#5bc0de", # A shade of blue/info
        "Grooming": "#5cb85c",    # A shade of green/success
        "Adoption": "#f0ad4e",    # A shade of orange/warning
        "Medication Start": "#777777", # A shade of grey
        "General": "#007bff"      # Default blue
    }
    for rescue in rescues:
        for name in appointment_type_names:
            color = type_colors.get(name, '#007bff') # Get specific color or default
            # Check if this type already exists for this rescue
            existing_type = AppointmentType.query.filter_by(rescue_id=rescue.id, name=name).first()
            if not existing_type:
                t = AppointmentType(rescue_id=rescue.id, name=name, color=color)
                db.session.add(t)
                types.append(t)
            else:
                types.append(existing_type) # Add existing to the list to be returned
    db.session.commit()
    return types

def seed_global_medicine_presets():
    print("Seeding global medicine presets...")
    presets_created = []
    for preset_data in global_medicine_presets_data:
        existing_preset = MedicinePreset.query.filter_by(name=preset_data['name'], rescue_id=None).first()
        if not existing_preset:
            m = MedicinePreset(
                rescue_id=None, # Global
                name=preset_data['name'],
                category=preset_data.get('category'),
                default_dosage_instructions=preset_data.get('default_dosage_instructions'),
                suggested_units=preset_data.get('suggested_units'),
                default_unit=preset_data.get('default_unit'), # Keep if still provided, though suggested_units is preferred
                notes=preset_data.get('notes')
            )
            db.session.add(m)
            presets_created.append(m)
            print(f"  Created global preset: {m.name}")
        else:
            print(f"  Global preset '{preset_data['name']}' already exists. Skipping.")
    db.session.commit()
    print(f"Finished seeding global medicine presets. {len(presets_created)} created.")
    return presets_created

def seed_rescue_specific_medicine_presets(rescues):
    print("Seeding rescue-specific example medicine presets...")
    presets = []
    # Using the renamed 'example_rescue_medicine_presets' list
    for rescue in rescues:
        for preset_data in example_rescue_medicine_presets: # iterate over the example list
            # Check if this preset already exists for this rescue
            existing_preset = MedicinePreset.query.filter_by(rescue_id=rescue.id, name=preset_data['name']).first()
            if not existing_preset:
                m = MedicinePreset(
                    rescue_id=rescue.id,
                    name=preset_data['name'],
                    category=preset_data.get('category'),
                    default_dosage_instructions=preset_data.get('default_dosage_instructions'),
                    suggested_units=preset_data.get('suggested_units'),
                    default_unit=preset_data.get('default_unit'),
                    notes=preset_data.get('notes')
                )
                db.session.add(m)
                presets.append(m)
                print(f"  Created rescue-specific preset '{m.name}' for rescue '{rescue.name}'")
            else:
                print(f"  Rescue-specific preset '{preset_data['name']}' for rescue '{rescue.name}' already exists. Skipping.")

    db.session.commit()
    print(f"Finished seeding rescue-specific medicine presets. {len(presets)} created.")
    return presets

def seed_dogs(rescues):
    microchip_ids = set()
    dogs = []
    for i in range(10):
        name = random.choice(names)
        breed = random.choice(breeds)
        status = random.choice(adoption_statuses)
        rescue = random.choice(rescues)
        now = datetime.now(timezone.utc)
        days_ago = random.randint(0, 5 * 365)
        intake_date = (now - timedelta(days=days_ago)).date()
        microchip_id = generate_unique_microchip(microchip_ids)
        notes = random.choice(notes_pool)
        medical_info = random.choice(medical_info_pool)
        dog = Dog(
            name=name,
            age=f"{random.randint(1, 12)} Years",
            breed=breed,
            adoption_status=status,
            intake_date=intake_date,
            microchip_id=microchip_id,
            notes=notes,
            medical_info=medical_info,
            rescue_id=rescue.id
        )
        db.session.add(dog)
        dogs.append(dog)
    db.session.commit()
    return dogs

def seed_appointments(dogs, appointment_types, users):
    for dog in dogs:
        for _ in range(random.randint(1, 2)):
            appt_type = random.choice(appointment_types)
            start_dt = datetime.now(timezone.utc) + timedelta(days=random.randint(-10, 30))
            appt = Appointment(
                dog_id=dog.id,
                rescue_id=dog.rescue_id,
                type_id=appt_type.id,
                title=f"{appt_type.name} for {dog.name}",
                description=f"Auto-generated {appt_type.name} appointment.",
                start_datetime=start_dt,
                end_datetime=start_dt + timedelta(hours=1),
                recurrence=None,
                recurrence_value=None,
                status='scheduled',
                created_by=random.choice(users).id
            )
            db.session.add(appt)
            # Reminder generation for this appointment (mirroring app.py logic)
            try:
                user = User.query.get(appt.created_by) # Fetch the user who created it

                # Reminder 1: Info
                reminder_message_info = f"{dog.name}'s appointment for '{appt.title if appt.title else appt_type.name}' is scheduled on {appt.start_datetime.strftime('%Y-%m-%d at %I:%M %p')}."
                new_reminder_info = Reminder(
                    message=reminder_message_info,
                    due_datetime=appt.start_datetime,
                    status='pending',
                    reminder_type='appointment_info',
                    dog_id=dog.id,
                    appointment_id=appt.id,
                    user_id=user.id if user else None # Assign to creator or leave null if user not found
                )
                db.session.add(new_reminder_info)

                # Reminder 2: 24 hours before
                if appt.start_datetime > datetime.now(timezone.utc) + timedelta(hours=23):
                    due_24h = appt.start_datetime - timedelta(hours=24)
                    reminder_message_24h = f"REMINDER: {dog.name}'s appointment '{appt.title if appt.title else appt_type.name}' is in 24 hours ({due_24h.strftime('%Y-%m-%d at %I:%M %p')})."
                    new_reminder_24h = Reminder(
                        message=reminder_message_24h,
                        due_datetime=due_24h,
                        status='pending',
                        reminder_type='appointment_upcoming_24h',
                        dog_id=dog.id,
                        appointment_id=appt.id,
                        user_id=user.id if user else None
                    )
                    db.session.add(new_reminder_24h)

                # Reminder 3: 1 hour before
                if appt.start_datetime > datetime.now(timezone.utc) + timedelta(minutes=59):
                    due_1h = appt.start_datetime - timedelta(hours=1)
                    reminder_message_1h = f"REMINDER: {dog.name}'s appointment '{appt.title if appt.title else appt_type.name}' is in 1 hour ({due_1h.strftime('%Y-%m-%d at %I:%M %p')})."
                    new_reminder_1h = Reminder(
                        message=reminder_message_1h,
                        due_datetime=due_1h,
                        status='pending',
                        reminder_type='appointment_upcoming_1h',
                        dog_id=dog.id,
                        appointment_id=appt.id,
                        user_id=user.id if user else None
                    )
                    db.session.add(new_reminder_1h)
            except Exception as e:
                # Not rolling back here as appointment itself is important
                print(f"Skipping reminder generation for appointment {appt.id} due to error: {e}")

    db.session.commit() # Commit appointments and their reminders
    # Return all created appointments to be consistent with how other seed functions might use the result
    return Appointment.query.filter(Appointment.id.in_([a.id for a in Appointment.query.all() if hasattr(a, 'dog_id')])).all() # A bit convoluted to get newly added appts
                                                                                                                    # Better to collect appt objects in a list and return that.

def seed_medicines(dogs, medicine_presets, users, appointment_types):
    if not users: # Ensure users list is not empty
        print("Warning: No users available for assigning 'created_by'. Skipping medicine seeding.")
        return

    med_start_appt_type_name = "Medication Start"
    
    for dog in dogs:
        num_medicines_to_seed = random.randint(0, 2)
        if num_medicines_to_seed == 0:
            continue

        # Ensure we have appointment types for this dog's rescue
        dog_appointment_types = [at for at in appointment_types if at.rescue_id == dog.rescue_id]
        if not dog_appointment_types:
            print(f"Warning: No appointment types found for rescue {dog.rescue_id}. Skipping medicine event for dog {dog.name}")
            continue

        med_start_appt_type = next((at for at in dog_appointment_types if at.name == med_start_appt_type_name), None)

        if not med_start_appt_type:
            print(f"Warning: '{med_start_appt_type_name}' appointment type not found for rescue {dog.rescue_id}. Cannot create calendar events for medicine starts.")
            # Optionally, create it here if critical, or ensure it's created in seed_appointment_types
            # For now, we'll skip creating the calendar event for this medicine if type is missing
            # This assumes seed_appointment_types has run and included "Medication Start"

        for _ in range(num_medicines_to_seed):
            if not medicine_presets: # Should not happen if seeded correctly
                print("Warning: No medicine presets available. Skipping a medicine seed.")
                continue
            preset = random.choice(medicine_presets)
            start_date_val = date.today() - timedelta(days=random.randint(0, 30))
            
            # Determine a valid user for created_by
            # Fallback to the first user if the random choice somehow fails or if users list is modified unexpectedly
            creator = random.choice(users) if users else None
            if not creator and users: # Should not happen if users list is not empty
                creator = users[0] 
            
            if not creator: # If still no creator, we cannot proceed
                print(f"Critical: No user available to be creator for medicine for dog {dog.name}. Skipping this medicine record.")
                continue


            med = DogMedicine(
                dog_id=dog.id,
                rescue_id=dog.rescue_id,
                medicine_id=preset.id,
                custom_name=None,
                dosage=str(random.randint(1, 3)),
                unit=preset.default_unit,
                frequency='daily',
                frequency_value=None,
                start_date=start_date_val,
                end_date=None,
                notes=f"Auto-generated {preset.name} prescription.",
                status='active',
                created_by=creator.id 
            )
            db.session.add(med)
            # We need to commit here so med.id is available for the reminder
            # Or, flush and then create the appointment and reminder before a final commit.
            # For simplicity in seeding, a commit here is okay.
            try:
                db.session.commit() # Commit the medicine first to get its ID for potential linking
            except Exception as e:
                db.session.rollback()
                print(f"Error committing medicine for dog {dog.name}: {e}. Skipping this medicine and its event/reminder.")
                continue # Skip to next medicine if this one fails

            # Reminder generation for this medicine (mirroring app.py logic)
            if med.start_date:
                try:
                    user_for_reminder = User.query.get(med.created_by) 
                    reminder_due_dt = datetime.combine(med.start_date, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=9)
                    medicine_name = med.custom_name
                    if not medicine_name and med.medicine_id:
                        preset_obj = MedicinePreset.query.get(med.medicine_id)
                        if preset_obj:
                            medicine_name = preset_obj.name
                    if not medicine_name: 
                        medicine_name = "Medicine"
                    reminder_message = f"{dog.name}'s prescription for '{medicine_name}' is scheduled to start on {med.start_date.strftime('%Y-%m-%d')}."
                    start_reminder = Reminder(
                        message=reminder_message,
                        due_datetime=reminder_due_dt,
                        status='pending',
                        reminder_type='medicine_start',
                        dog_id=dog.id,
                        dog_medicine_id=med.id,
                        user_id=user_for_reminder.id if user_for_reminder else None 
                    )
                    db.session.add(start_reminder)
                except Exception as e:
                    db.session.rollback() 
                    print(f"Error creating reminder for medicine {med.id} for dog {dog.name}: {e}")

    try:
        db.session.commit() # Final commit for any pending DogMedicines and their Reminders
    except Exception as e:
        db.session.rollback()
        print(f"Error during final commit in seed_medicines: {e}")

def seed_reminders(users, appointments, medicines):
    # This function is now largely handled by direct reminder creation
    # in seed_appointments and seed_medicines for better test data alignment
    # with app.py logic.
    # It can be re-purposed later if specific additional reminder seeding is needed.
    print("Skipping dedicated reminder seeding as it's now part of appointment/medicine seeding.")
    pass
    # Old logic (removed):
    # for appt in appointments:
    #     for user in users:
    #         if random.choice([True, False]):
    #             rem = Reminder(
    #                 appointment_id=appt.id,
    #                 dog_medicine_id=None,
    #                 user_id=user.id,
    #                 reminder_time='1d_before',
    #                 custom_offset=None,
    #                 sent=False
    #             )
    #             db.session.add(rem)
    # for med in medicines:
    #     for user in users:
    #         if random.choice([True, False]):
    #             rem = Reminder(
    #                 appointment_id=None,
    #                 dog_medicine_id=med.id,
    #                 user_id=user.id,
    #                 reminder_time='1d_before',
    #                 custom_offset=None,
    #                 sent=False
    #             )
    #             db.session.add(rem)
    # db.session.commit()

def clear_data():
    print("Clearing existing data...")
    # Clear data in an order that respects foreign key constraints (children before parents)
    models_to_clear_in_order = [
        Reminder, 
        DogMedicineHistory,
        DogMedicine, 
        Appointment, 
        Dog, 
        User, 
        AppointmentType, 
        MedicinePreset, 
        Rescue
    ]

    with app.app_context():
        for model in models_to_clear_in_order:
            try:
                num_rows_deleted = db.session.query(model).delete()
                print(f"Deleted {num_rows_deleted} rows from {model.__tablename__}")
            except Exception as e:
                db.session.rollback()
                print(f"Error clearing {model.__tablename__}: {e}")
                # Optionally, re-raise or handle more gracefully
                # For development, printing the error might be sufficient
                return # Stop if one fails, to avoid further FK issues
    db.session.commit()
    print("Data clearing complete.")

def main():
    parser = argparse.ArgumentParser(description='Seed database for DogTrackerV2 or clear data.')
    parser.add_argument('--clear', action='store_true', help='Clear all data from the tables.')
    parser.add_argument('--seed', nargs='*', help='Specify parts to seed by number (e.g., 1 3 5) or seed all if no numbers.')
    args = parser.parse_args()

    if args.clear:
        with app.app_context():
            clear_data()
        sys.exit(0)

    # Define seeding options (ensure this list matches the interactive part if kept)
    options = [
        ("Rescues", get_or_create_rescues),
        ("Users", seed_users),
        ("Appointment Types", seed_appointment_types),
        ("Global Medicine Presets", seed_global_medicine_presets),
        ("Rescue-Specific Medicine Presets", seed_rescue_specific_medicine_presets),
        ("Dogs", seed_dogs),
        ("Appointments", seed_appointments),
        ("Medicines", seed_medicines),
        ("Reminders", seed_reminders)
    ]

    if args.seed is not None: # If --seed is present
        selected_options_indices = []
        if not args.seed: # --seed with no numbers means seed all
            selected_options_indices = list(range(len(options)))
        else:
            try:
                selected_options_indices = [int(x) - 1 for x in args.seed]
            except ValueError:
                print("Invalid selection for --seed. Please provide numbers.")
                sys.exit(1)
        
        # Execute selected seeding functions
        with app.app_context():
            rescues, users, appointment_types_list, global_presets, rescue_specific_presets, dogs_list, appointments_list, medicines_list = [], [], [], [], [], [], []
            for i, (name, func) in enumerate(options):
                if i in selected_options_indices:
                    print(f"\nSeeding {name}...")
                    if name == "Rescues":
                        rescues = func()
                    elif name == "Users":
                        if not rescues: rescues = Rescue.query.all() # Ensure rescues are loaded if not seeded in this run
                        users = func(rescues)
                    elif name == "Appointment Types":
                        if not rescues: rescues = Rescue.query.all()
                        appointment_types_list = func(rescues)
                    elif name == "Global Medicine Presets":
                        global_presets = func()
                    elif name == "Rescue-Specific Medicine Presets":
                        if not rescues: rescues = Rescue.query.all()
                        rescue_specific_presets = func(rescues)
                    elif name == "Dogs":
                        if not rescues: rescues = Rescue.query.all()
                        dogs_list = func(rescues)
                    elif name == "Appointments":
                        if not dogs_list: dogs_list = Dog.query.all()
                        if not appointment_types_list: appointment_types_list = AppointmentType.query.all()
                        if not users: users = User.query.all()
                        appointments_list = func(dogs_list, appointment_types_list, users)
                    elif name == "Medicines":
                        if not dogs_list: dogs_list = Dog.query.all()
                        if not global_presets: global_presets = MedicinePreset.query.filter_by(rescue_id=None).all()
                        if not rescue_specific_presets: rescue_specific_presets = MedicinePreset.query.filter_by(rescue_id=rescues[0].id).all()
                        if not users: users = User.query.all()
                        if not appointment_types_list: appointment_types_list = AppointmentType.query.all()
                        medicines_list = func(dogs_list, global_presets + rescue_specific_presets, users, appointment_types_list)
                    elif name == "Reminders": # Ensure this gets updated arguments if seed_reminders changes
                        if not users: users = User.query.all()
                        # This part needs careful handling of what appointments_list and medicines_list are
                        # If not seeded in this run, they would be empty lists. Query them if empty.
                        if not appointments_list: appointments_list = Appointment.query.all()
                        if not medicines_list: medicines_list = DogMedicine.query.all()
                        func(users, appointments_list, medicines_list)
                    print(f"{name} seeding complete.")
            print("\nSelected seeding complete.")
        sys.exit(0)

    # Fallback to interactive menu if no arguments are given
    print("\nWhat would you like to seed or clear?")
    print("[0] Clear All Data") # New option
    for i, (name, _) in enumerate(options, 1):
        print(f"[{i}] {name}")
    print(f"[{len(options)+1}] Seed EVERYTHING")
    selection = input("\nEnter numbers separated by commas (e.g., 1,3,5), 0 to clear, or press Enter to seed everything: ").strip()
    
    if selection == '0':
        with app.app_context():
            clear_data()
        sys.exit(0)

    if not selection: # Enter for seed everything
        selected = list(range(len(options)))
    else:
        try:
            selected = [int(x) - 1 for x in selection.split(',') if x]
        except ValueError:
            print("Invalid selection. Exiting.")
            sys.exit(1)

    with app.app_context():
        # Initialize lists/variables to store results from seeding functions for explicit passing
        s_rescues, s_users, s_appointment_types, s_global_presets, s_rescue_specific_presets, s_dogs, s_appointments, s_medicines = None, None, None, None, None, None, None, None
        
        # If seeding everything, ensure fixed order for dependencies
        # The `options` list already defines a sensible order.
        # The `selected` list for "seed everything" will be [0, 1, 2, 3, 4, 5, 6, 7]

        for i in selected:
            if i < 0 or i >= len(options):
                print(f"Skipping invalid option index: {i+1}")
                continue
            
            name, func = options[i]
            print(f"\nSeeding {name}...")

            if name == "Rescues":
                s_rescues = func()
            elif name == "Users":
                if s_rescues is None: # Check if previous step ran and returned rescues
                    print("Warning: Rescues not available from previous seeding step, querying DB for Users seeding.")
                    s_rescues = Rescue.query.all()
                s_users = func(s_rescues)
            elif name == "Appointment Types":
                if s_rescues is None:
                    print("Warning: Rescues not available from previous seeding step, querying DB for Appointment Types seeding.")
                    s_rescues = Rescue.query.all()
                s_appointment_types = func(s_rescues)
            elif name == "Global Medicine Presets":
                s_global_presets = func()
            elif name == "Rescue-Specific Medicine Presets":
                if s_rescues is None:
                    print("Warning: Rescues not available from previous seeding step, querying DB for Rescue-Specific Medicine Presets seeding.")
                    s_rescues = Rescue.query.all()
                s_rescue_specific_presets = func(s_rescues)
            elif name == "Dogs":
                if s_rescues is None:
                    print("Warning: Rescues not available from previous seeding step, querying DB for Dogs seeding.")
                    s_rescues = Rescue.query.all()
                s_dogs = func(s_rescues)
            elif name == "Appointments":
                if s_dogs is None: s_dogs = Dog.query.all()
                if s_appointment_types is None: s_appointment_types = AppointmentType.query.all()
                if s_users is None: s_users = User.query.all()
                s_appointments = func(s_dogs, s_appointment_types, s_users)
            elif name == "Medicines":
                if s_dogs is None: s_dogs = Dog.query.all()
                if s_global_presets is None: s_global_presets = MedicinePreset.query.filter_by(rescue_id=None).all()
                if s_rescue_specific_presets is None: s_rescue_specific_presets = MedicinePreset.query.filter_by(rescue_id=s_rescues[0].id).all()
                if s_users is None: s_users = User.query.all()
                if s_appointment_types is None: s_appointment_types = AppointmentType.query.all()
                s_medicines = func(s_dogs, s_global_presets + s_rescue_specific_presets, s_users, s_appointment_types)
            elif name == "Reminders": # This function currently does a 'pass'
                if s_users is None: s_users = User.query.all()
                if s_appointments is None: s_appointments = Appointment.query.all() # Get all if not seeded in this run
                if s_medicines is None: s_medicines = DogMedicine.query.all() # Get all if not seeded in this run
                func(s_users, s_appointments, s_medicines)
            
            print(f"{name} seeding complete.")

    print("\nDatabase seeding/clearing complete.")

if __name__ == '__main__':
    main() 