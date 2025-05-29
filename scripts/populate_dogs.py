#!/usr/bin/env python
import argparse
import logging
import random
import sys
import getpass
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone, date
import string
import secrets
from typing import List, Optional, Callable, Any
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from models import (
    db, Dog, Appointment, Rescue, User, AppointmentType, MedicinePreset, 
    DogMedicine, Reminder, DogMedicineHistory, DogNote, AuditLog
)

# Configure logging
logger = logging.getLogger(__name__)

def configure_logging(debug=False):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logger.setLevel(level)

class SeedingConfig:
    """Configuration class for seeding parameters"""
    # Quantity settings
    DOGS_PER_BATCH_RANGE = (10, 50)
    DOGS_PER_BATCH = 30  # Number of dogs to seed
    MIN_RESCUES_REQUIRED = 3
    APPOINTMENTS_PER_DOG_RANGE = (1, 2)
    MEDICINES_PER_DOG_RANGE = (0, 2)
    NOTES_PER_DOG_RANGE = (1, 3)
    
    # User settings
    MIN_PASSWORD_LENGTH = 4
    
    # Date ranges
    MAX_INTAKE_DAYS_AGO = 5 * 365  # 5 years
    APPOINTMENT_DAYS_RANGE = (-10, 30)  # 10 days ago to 30 days future
    MEDICINE_START_DAYS_AGO = 30
    NOTE_DAYS_AGO = 30
    
    # Reminder settings
    REMINDER_24H_OFFSET = timedelta(hours=24)
    REMINDER_1H_OFFSET = timedelta(hours=1)
    MEDICINE_REMINDER_HOUR = 9  # 9 AM


class SampleData:
    """Container for all sample data used in seeding"""
    
    DOG_NAMES = [
        'Baxter', 'Luna', 'Moose', 'Ziggy', 'Willow', 'Pepper', 'Finn', 'Olive', 'Milo', 'Sadie',
        'Charlie', 'Bella', 'Max', 'Daisy', 'Rocky', 'Molly', 'Buddy', 'Bailey', 'Coco', 'Ruby',
        'Scout', 'Harley', 'Riley', 'Toby', 'Sasha', 'Ginger', 'Murphy', 'Shadow', 'Lucky', 'Sam',
        'Rosie', 'Jake', 'Sophie', 'Chloe', 'Jack', 'Maggie', 'Oscar', 'Zeus', 'Abby', 'Louie', 'Penny',
        'Bentley', 'Hazel', 'Nala', 'Thor', 'Winston', 'Ellie', 'Archie', 'Remy', 'Nova', 'Rex',
        'Jasper', 'Maddie', 'Ace', 'Phoebe', 'Simba', 'Ranger', 'Piper', 'Tank', 'Maple', 'Indie',
        'Atlas', 'Cleo', 'Mocha', 'Buster', 'Sable', 'Indigo', 'Echo', 'Storm', 'Blaze', 'Aspen',
        'River', 'Sky', 'Tango', 'Pixel', 'Dash', 'Maverick', 'Socks', 'Peanut', 'Teddy', 'Blue',
        'Copper', 'Duke', 'Gizmo', 'Hank', 'Ivy', 'Juno', 'Koda', 'Lexi', 'Mochi', 'Nico', 'Ollie',
        'Poppy', 'Quinn', 'Rocco', 'Sage', 'Trixie', 'Uno', 'Violet', 'Willis', 'Xena', 'Yoshi', 'Zara',
        'Bingo', 'Cinnamon', 'Dottie', 'Ember', 'Fable', 'Gatsby', 'Harper', 'Izzy', 'Jasper', 'Kiki',
        'Loki', 'Milo', 'Nina', 'Opal', 'Pax', 'Queenie', 'Rufus', 'Suki', 'Toby', 'Uma', 'Vera', 'Waldo',
        'Xander', 'Yara', 'Zigzag', 'Amber', 'Basil', 'Clover', 'Duke', 'Elsa', 'Fritz', 'Ginger', 'Hugo',
        'Iris', 'Jett', 'Kane', 'Lacey', 'Mira', 'Nash', 'Oreo', 'Piper', 'Quincy', 'Raven', 'Sable', 'Tess',
        'Ulysses', 'Vixen', 'Wren', 'Xyla', 'Yeti', 'Zorro'
    ]
    
    BREEDS = [
        'Corgi', 'Shih Tzu', 'Great Dane', 'Dachshund', 'Boxer', 'Chihuahua', 'Golden Retriever',
        'Pug', 'French Bulldog', 'German Shepherd', 'Labrador', 'Beagle', 'Poodle', 'Bulldog',
        'Terrier', 'Spaniel', 'Shepherd', 'Collie', 'Mixed', 'Retriever', 'Akita', 'Mastiff',
        'Doberman', 'Rottweiler', 'Husky', 'Malamute', 'Whippet', 'Greyhound', 'Pointer', 'Setter', 
        'Dalmatian', 'Cavalier King Charles Spaniel', 'Boston Terrier', 'Bichon Frise', 
        'Bernese Mountain Dog', 'Shiba Inu', 'Australian Shepherd', 'Border Collie', 'Cane Corso', 
        'Papillon', 'Samoyed', 'Weimaraner', 'Basenji', 'Bloodhound', 'Saint Bernard', 'Newfoundland', 
        'Irish Setter', 'Great Pyrenees', 'Alaskan Klee Kai', 'Saluki', 'Afghan Hound', 'Pekingese', 
        'Lhasa Apso', 'Scottish Terrier', 'Bullmastiff', 'Chow Chow',
        'English Springer Spaniel', 'Miniature Schnauzer', 'Cocker Spaniel', 'Staffordshire Bull Terrier',
        'Great Swiss Mountain Dog', 'Norwegian Elkhound', 'Belgian Malinois', 'Tibetan Mastiff',
        'Japanese Chin', 'Finnish Spitz', 'Irish Wolfhound', 'Leonberger', 'Plott Hound', 'Rat Terrier',
        'Silky Terrier', 'Toy Fox Terrier', 'Wirehaired Pointing Griffon', 'Yorkshire Terrier',
        'American Eskimo Dog', 'Australian Cattle Dog', 'Basset Hound', 'Brittany', 'Catahoula Leopard Dog',
        'Chinese Crested', 'Dogo Argentino', 'English Setter', 'Field Spaniel', 'Glen of Imaal Terrier',
        'Havanese', 'Keeshond', 'Lowchen', 'Manchester Terrier', 'Neapolitan Mastiff', 'Otterhound',
        'Polish Lowland Sheepdog', 'Redbone Coonhound', 'Sealyham Terrier', 'Swedish Vallhund', 'Vizsla',
        'Appenzeller Sennenhund', 'Barbet', 'Canaan Dog', 'Dandie Dinmont Terrier', 'Estrela Mountain Dog',
        'French Spaniel', 'Greenland Dog', 'Hamiltonstovare', 'Icelandic Sheepdog', 'Jagdterrier',
        'Kai Ken', 'Lagotto Romagnolo', 'Mudi', 'Norfolk Terrier', 'Otterhound', 'Pumi', 'Pyrenean Shepherd',
        'Russian Toy', 'Sloughi', 'Tornjak', 'Utonagan', 'Volpino Italiano', 'West Siberian Laika',
        'Xoloitzcuintli', 'Yakutian Laika', 'Zerdava'
    ]
    
    ADOPTION_STATUSES = ['Adopted', 'Not Adopted', 'Pending', 'Fostered', 'Returned', 'Transferred']
    
    DOG_NOTES = [
        '', 'Very friendly and playful.', 'Needs special diet.', 'Good with children.',
        'Prefers quiet environments.', 'Enjoys long walks.', 'Has some anxiety around loud noises.',
        'House-trained.', 'Loves to play fetch.', 'Protective of family.', 'Gets along with other dogs.',
        'Shy at first but warms up quickly.', 'Energetic and loves to run.', 'Enjoys car rides.',
        'Loves belly rubs.', 'Prefers to sleep in a crate.', 'Can be food possessive.',
        'Enjoys swimming in the lake.', 'Needs more leash training.', 'Barks at delivery people.',
        'Gentle with small animals.', 'Has separation anxiety.', 'Loves squeaky toys.',
        'Can jump very high fences.', 'Prefers female handlers.', 'Sensitive to cold weather.',
        'Enjoys agility courses.', 'Needs daily brushing.', 'Can be stubborn at times.',
        'Loves to cuddle on the couch.', 'Prefers soft food.', 'Gets carsick easily.',
        'Enjoys sunbathing in the yard.', 'Can be shy around men.', 'Loves to dig holes.',
        'Does not like thunderstorms.', 'Enjoys playing in the snow.', 'Loves to chase squirrels.',
        'Prefers quiet music.', 'Enjoys being brushed.', 'Likes to sleep under the bed.',
        'Enjoys tug-of-war games.', 'Can be picky with food.', 'Loves to greet visitors.',
        'Enjoys hiking trips.', 'Likes to watch TV.', 'Prefers to drink from running water.',
        'Enjoys car rides with the window down.', 'Likes to nap in the sun.', 'Enjoys hide and seek.'
    ]
    
    MEDICAL_INFO = [
        '', 'Up to date on all vaccinations.', 'Requires daily medication.',
        'Recently treated for fleas.', 'Has a history of ear infections.', 'No known medical issues.',
        'Allergic to chicken.', 'Has arthritis in hind legs.', 'Needs regular dental care.',
        'Recovering from surgery.', 'Has a heart murmur.', 'Blind in one eye.', 'Deaf in left ear.',
        'Has skin allergies.', 'Prone to hot spots.', 'Has a sensitive stomach.', 'Recently spayed/neutered.',
        'Has a limp from old injury.', 'On prescription diet.', 'Has chronic dry eye.',
        'Has a benign tumor.', 'Missing several teeth.', 'Has mild hip dysplasia.',
        'Has a thyroid condition.', 'Has a history of seizures.', 'Has a food allergy.',
        'Has a chronic cough.', 'Has a history of pancreatitis.', 'Has a luxating patella.',
        'Has a history of mange.', 'Has a broken tail.', 'Has a history of kennel cough.',
        'Has a sensitive liver.', 'Has a history of bladder stones.', 'Has a history of anemia.',
        'Has a history of tick-borne disease.', 'Has a history of heartworm.'
    ]
    
    ADOPTER_NOTES = [
        '', 'Adopted by a loving family.', 'Now lives with a retired couple.',
        'Adopted by a family with children.', 'Adopted by a single owner.',
        'Moved to a farm after adoption.', 'Adopted by a college student.', 'Now lives in a city apartment.',
        'Adopted by a family with other pets.', 'Adopted by a couple with a large yard.',
        'Adopted by a first-time dog owner.', 'Adopted by a family who previously adopted from us.',
        'Adopted by a local veterinarian.', 'Adopted by a family with a special needs child.',
        'Adopted by a family who travels frequently.', 'Adopted by a family with a pool.',
        'Adopted by a family who loves hiking.', 'Adopted by a family with a cat.',
        'Adopted by a family who lives near the beach.', 'Adopted by a family who owns a pet store.',
        'Adopted by a family who lives on a boat.', 'Adopted by a family who runs a daycare.',
        'Adopted by a family who lives in the mountains.'
    ]
    
    APPOINTMENT_TYPES = [
        {'name': 'Vet Visit', 'color': '#d9534f'},
        {'name': 'Vaccination', 'color': '#5bc0de'},
        {'name': 'Grooming', 'color': '#5cb85c'},
        {'name': 'Adoption', 'color': '#f0ad4e'},
        {'name': 'General', 'color': '#007bff'},
        {'name': 'Medication Start', 'color': '#777777'}
    ]
    
    NOTE_CATEGORIES = [
        'Medical Observation', 'Behavioral Note', 'Training Update',
        'Foster Update', 'Adoption Process', 'General Care', 'Staff Communication',
        'Dietary Note', 'Exercise Log', 'Medication Log', 'Grooming Note',
        'Incident Report', 'Progress Update', 'Volunteer Feedback', 'Adopter Feedback',
        'Enrichment Note', 'Socialization Note', 'Adoption Follow-up', 'Medical Follow-up',
        'Behavioral Progress', 'Foster Feedback', 'Adoption Interview', 'Medical Alert'
    ]
    
    SAMPLE_NOTE_TEXTS = [
        "Observed limping on the left hind leg after playtime.",
        "Showed excellent recall during the training session today.",
        "Ate all food and seems to be settling in well with the foster family.",
        "Potential adopter visit scheduled for next week.",
        "Administered flea treatment as per schedule.",
        "Responded positively to new enrichment toy.",
        "Needs a follow-up vet visit for dental check.",
        "Barked excessively when left alone for a short period.",
        "Successfully learned the 'sit' and 'stay' commands.",
        "Foster reports dog is very affectionate and good with their children.",
        "Dog was nervous during thunderstorm but calmed with gentle petting.",
        "Refused breakfast but ate lunch and dinner.",
        "Showed signs of improvement after medication adjustment.",
        "Enjoyed a long walk in the park today.",
        "Had a positive interaction with another dog at the shelter.",
        "Exhibited resource guarding behavior with toys.",
        "Allowed nail trim without issue.",
        "Showed interest in agility equipment.",
        "Was startled by loud noises during walk.",
        "Slept through the night without barking.",
        "Enjoyed car ride to the vet.",
        "Showed no reaction to new foster sibling.",
        "Was calm during grooming session.",
        "Had mild diarrhea, monitoring for changes.",
        "Showed excitement when adopter visited.",
        "Allowed ear cleaning with minimal fuss.",
        "Played fetch for 30 minutes without tiring.",
        "Showed signs of separation anxiety when foster left the room.",
        "Ate new food without issue.",
        "Was friendly with children during meet and greet.",
        "Dog barked at the mail carrier but calmed quickly.",
        "Enjoyed a game of tug-of-war with staff.",
        "Was hesitant to enter the crate but settled after a treat.",
        "Showed interest in puzzle feeder.",
        "Had a positive reaction to new foster sibling.",
        "Was startled by vacuum cleaner noise.",
        "Enjoyed a bath and grooming session.",
        "Showed improvement in leash walking.",
        "Was calm during thunderstorm with music playing.",
        "Ate slowly but finished all food.",
        "Showed excitement for car rides.",
        "Allowed brushing without protest.",
        "Played well with other dogs in the yard.",
        "Showed curiosity about new toys.",
        "Was nervous at the vet but handled well.",
        "Enjoyed a nap in the sun.",
        "Showed no interest in chasing cats.",
        "Was friendly with all visitors today.",
        "Showed improvement in recall training.",
        "Allowed ear drops without fuss."
    ]
    
    RESCUE_MEDICINE_PRESETS = [
        {
            'name': 'RescueSpecial Dewormer',
            'default_unit': 'ml',
            'category': 'Parasite Control - Dewormer',
            'suggested_units': 'ml,cc',
            'notes': 'Special dewormer for this rescue.'
        },
        {
            'name': 'RescueComfort NSAID',
            'default_unit': 'tablet',
            'category': 'Anti-inflammatory & Pain Relief - NSAID',
            'suggested_units': 'tablet,chewable',
            'notes': 'Rescue-formulated pain relief.'
        },
        {
            'name': 'RescueVite Multivitamin',
            'default_unit': 'tablet',
            'category': 'Supplement',
            'suggested_units': 'tablet,chewable',
            'notes': 'Custom multivitamin for rescue dogs.'
        },
        {
            'name': 'RescueAllergy Relief',
            'default_unit': 'mg',
            'category': 'Allergy & Skin',
            'suggested_units': 'mg,tablet',
            'notes': 'Allergy relief for sensitive dogs.'
        },
        {
            'name': 'RescueDigest Probiotic',
            'default_unit': 'scoop',
            'category': 'Gastrointestinal Support',
            'suggested_units': 'scoop,packet',
            'notes': 'Probiotic supplement for digestive health.'
        },
        {
            'name': 'RescueCalm Sedative',
            'default_unit': 'mg',
            'category': 'Behavioral Support',
            'suggested_units': 'mg,tablet',
            'notes': 'For anxiety and stressful events.'
        },
        {
            'name': 'RescueOmega Oil',
            'default_unit': 'ml',
            'category': 'Supplement',
            'suggested_units': 'ml,teaspoon',
            'notes': 'Omega-3 oil for skin and coat.'
        }
    ]
    
    GLOBAL_MEDICINE_PRESETS = [
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
        {
            "name": "Diphenhydramine (Benadryl)",
            "category": "Allergy & Skin",
            "default_dosage_instructions": "Typical dose 1mg per pound of body weight, 2-3 times daily. Confirm with vet. Can cause drowsiness.",
            "suggested_units": "mg,tablet,capsule,ml",
            "notes": "Antihistamine for allergic reactions, itching. OTC, but vet guidance recommended for dosage."
        },
        {
            "name": "Trazodone",
            "category": "Behavioral Support",
            "default_dosage_instructions": "Used for anxiety or sedation. Dosage varies greatly. Given as needed or regularly.",
            "suggested_units": "mg,tablet",
            "notes": "Often used for situational anxiety (vet visits, thunderstorms). Prescription required."
        },
        {
            "name": "Loperamide (Imodium)",
            "category": "Gastrointestinal Support",
            "default_dosage_instructions": "Used for diarrhea. Dosage by weight. Use only under vet supervision.",
            "suggested_units": "mg,tablet,ml",
            "notes": "Anti-diarrheal. Use with caution."
        },
        {
            "name": "Metronidazole (Flagyl)",
            "category": "Antibiotic",
            "default_dosage_instructions": "Used for GI infections. Dosage by weight. Can cause bitter taste.",
            "suggested_units": "mg,tablet,ml",
            "notes": "Antibiotic for GI and some other infections."
        },
        {
            "name": "Hydroxyzine",
            "category": "Allergy & Skin",
            "default_dosage_instructions": "Used for itching/allergies. Dosage by weight. Can cause drowsiness.",
            "suggested_units": "mg,tablet",
            "notes": "Antihistamine for allergies and itching."
        },
        {
            "name": "Omeprazole (Prilosec)",
            "category": "Gastrointestinal Support",
            "default_dosage_instructions": "Used for acid reflux. Dosage by weight. Give before meals.",
            "suggested_units": "mg,tablet,ml",
            "notes": "Reduces stomach acid."
        },
        {
            "name": "Sucralfate (Carafate)",
            "category": "Gastrointestinal Support",
            "default_dosage_instructions": "Used for ulcers. Give on empty stomach. Dosage by weight.",
            "suggested_units": "mg,tablet,ml",
            "notes": "Protects stomach lining."
        },
        {
            "name": "Cefpodoxime (Simplicef)",
            "category": "Antibiotic",
            "default_dosage_instructions": "Used for skin infections. Dosage by weight. Once daily.",
            "suggested_units": "mg,tablet",
            "notes": "Antibiotic for skin and soft tissue infections."
        },
        {
            "name": "Prednisone",
            "category": "Anti-inflammatory & Pain Relief - Steroid",
            "default_dosage_instructions": "Used for inflammation/allergies. Dosage by weight. Taper as directed.",
            "suggested_units": "mg,tablet",
            "notes": "Steroid for inflammation and immune conditions."
        },
        {
            "name": "Amitriptyline",
            "category": "Behavioral Support",
            "default_dosage_instructions": "Used for anxiety/behavioral issues. Dosage by weight. May cause drowsiness.",
            "suggested_units": "mg,tablet",
            "notes": "Tricyclic antidepressant for anxiety and behavioral issues."
        }
    ]


# Database utility functions and context managers

@contextmanager
def db_transaction() -> Any:
    """Context manager for database transactions with automatic rollback on error"""
    try:
        yield db.session
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Database transaction failed: {e}")
        raise


def safe_db_operation(operation_name: str, operation_func: Callable[[], Any]) -> Any:
    """Wrapper for database operations with consistent error handling"""
    try:
        with db_transaction():
            result = operation_func()
            logger.info(f"{operation_name} completed successfully")
            return result
    except Exception as e:
        logger.error(f"Error in {operation_name}: {e}")
        return None


def ensure_data_available(data: Any, query_func: Callable[[], Any], data_name: str) -> Any:
    """Ensure required data is available, query if needed"""
    if data is None:
        logger.warning(f"{data_name} not available from previous step, querying database")
        return query_func()
    return data


# Helper functions

def generate_unique_microchip(existing_chips: set) -> str:
    """Generate a unique microchip ID"""
    while True:
        chip = str(random.randint(10000000, 99999999))
        if chip not in existing_chips:
            existing_chips.add(chip)
            return chip


def generate_random_datetime(days_range: tuple[int, int]) -> datetime:
    """Generate a random datetime within the specified day range"""
    days_offset = random.randint(*days_range)
    return datetime.now(timezone.utc) + timedelta(days=days_offset)


def generate_past_date(max_days_ago: int) -> date:
    """Generate a random past date within the specified range"""
    days_ago = random.randint(0, max_days_ago)
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).date()


# Seeding functions

def get_or_create_rescues() -> Optional[List['Rescue']]:
    """Ensure minimum number of rescues exist, create if needed (idempotent)"""
    def _create_rescues():
        rescues = Rescue.query.all()
        needed = SeedingConfig.MIN_RESCUES_REQUIRED - len(rescues)
        created = []
        for i in range(needed):
            name = f"Rescue {len(rescues) + i + 1}"
            existing = Rescue.query.filter_by(name=name).first()
            if existing:
                logger.debug(f"Skipped creating rescue '{name}': already exists.")
                continue
            rescue = Rescue(
                name=name,
                address=f"{100 + i} Main St",
                phone=f"555-000{i}",
                email=f"rescue{len(rescues) + i + 1}@example.com",
                status='approved'  # Ensure test rescues are approved by default
            )
            db.session.add(rescue)
            db.session.flush()
            created.append(rescue)
        all_rescues = Rescue.query.all()
        logger.info(f"Ensured {len(all_rescues)} rescues exist ({len(created)} created)")
        return all_rescues
    return safe_db_operation("Rescue creation", _create_rescues)


def seed_users(rescues: List['Rescue']) -> Optional[List['User']]:
    """Create owner and staff users for each rescue, with random passwords and logins written to seeded_logins.txt (idempotent)"""
    credentials = []
    def random_password(length=12):
        chars = string.ascii_letters + string.digits
        return ''.join(secrets.choice(chars) for _ in range(length))

    def _create_users():
        users = []
        for idx, rescue in enumerate(rescues, 1):
            owner_email = f"{rescue.name.lower().replace(' ', '_')}_owner@example.com"
            staff_email = f"{rescue.name.lower().replace(' ', '_')}_staff@example.com"
            owner_password = random_password()
            staff_password = random_password()
            # Only create if not exists
            owner = User.query.filter_by(email=owner_email).first()
            if not owner:
                owner = User(
                    name=f"{rescue.name} Owner",
                    email=owner_email,
                    role='owner',
                    device_id=None,
                    invite_code=None,
                    can_edit=True,
                    rescue_id=rescue.id
                )
                owner.set_password(owner_password)
                db.session.add(owner)
                users.append(owner)
                credentials.append({
                    'name': owner.name,
                    'email': owner.email,
                    'role': owner.role,
                    'password': owner_password
                })
                logger.debug(f"Created owner user: {owner.name}, email: {owner.email}, password: {owner_password}")
            else:
                logger.debug(f"Skipped creating user with email {owner_email}: already exists.")
            staff = User.query.filter_by(email=staff_email).first()
            if not staff:
                staff = User(
                    name=f"{rescue.name} Staff",
                    email=staff_email,
                    role='staff',
                    device_id=None,
                    invite_code='INVITE123',
                    can_edit=True,
                    rescue_id=rescue.id
                )
                staff.set_password(staff_password)
                db.session.add(staff)
                users.append(staff)
                credentials.append({
                    'name': staff.name,
                    'email': staff.email,
                    'role': staff.role,
                    'password': staff_password
                })
                logger.debug(f"Created staff user: {staff.name}, email: {staff.email}, password: {staff_password}")
            else:
                logger.debug(f"Skipped creating user with email {staff_email}: already exists.")
        logger.info(f"Created {len(users)} new users (idempotent)")
        return users

    result = safe_db_operation("User creation", _create_users)
    if credentials:
        with open(os.path.join(os.path.dirname(__file__), '..', "seeded_logins.txt"), "w", encoding="utf-8") as f:
            f.write("# WARNING: This file contains plaintext test credentials. DELETE BEFORE DEPLOYMENT!\n\n")
            f.write("# Seeded User Logins (Owner/Staff)\n\n")
            for cred in credentials:
                f.write(f"Name: {cred['name']}\n")
                f.write(f"Email: {cred['email']}\n")
                f.write(f"Role: {cred['role']}\n")
                f.write(f"Password: {cred['password']}\n")
                f.write("---\n")
        logger.info("Seeded user credentials written to seeded_logins.txt")
    return result


def seed_appointment_types(rescues: List['Rescue']) -> Optional[List['AppointmentType']]:
    """Create appointment types for each rescue"""
    def _create_appointment_types():
        types = []
        for rescue in rescues:
            for type_data in SampleData.APPOINTMENT_TYPES:
                existing_type = AppointmentType.query.filter_by(
                    rescue_id=rescue.id, 
                    name=type_data['name']
                ).first()
                
                if not existing_type:
                    appt_type = AppointmentType(
                        rescue_id=rescue.id,
                        name=type_data['name'],
                        color=type_data['color']
                    )
                    db.session.add(appt_type)
                    types.append(appt_type)
                else:
                    types.append(existing_type)
        
        logger.info(f"Created/verified {len(types)} appointment types")
        return types
    
    return safe_db_operation("Appointment type creation", _create_appointment_types)


def seed_global_medicine_presets() -> Optional[List['MedicinePreset']]:
    """Create global medicine presets"""
    def _create_global_presets():
        presets_created = []
        for preset_data in SampleData.GLOBAL_MEDICINE_PRESETS:
            existing_preset = MedicinePreset.query.filter_by(
                name=preset_data['name'], 
                rescue_id=None
            ).first()
            
            if not existing_preset:
                preset = MedicinePreset(
                    rescue_id=None,  # Global
                    name=preset_data['name'],
                    category=preset_data.get('category'),
                    default_dosage_instructions=preset_data.get('default_dosage_instructions'),
                    suggested_units=preset_data.get('suggested_units'),
                    default_unit=preset_data.get('default_unit'),
                    notes=preset_data.get('notes')
                )
                db.session.add(preset)
                presets_created.append(preset)
        
        logger.info(f"Created {len(presets_created)} global medicine presets")
        return presets_created
    
    return safe_db_operation("Global medicine preset creation", _create_global_presets)


def seed_rescue_specific_medicine_presets(rescues: List['Rescue']) -> Optional[List['MedicinePreset']]:
    """Create rescue-specific medicine presets"""
    def _create_rescue_presets():
        presets = []
        for rescue in rescues:
            for preset_data in SampleData.RESCUE_MEDICINE_PRESETS:
                existing_preset = MedicinePreset.query.filter_by(
                    rescue_id=rescue.id, 
                    name=preset_data['name']
                ).first()
                
                if not existing_preset:
                    preset = MedicinePreset(
                        rescue_id=rescue.id,
                        name=preset_data['name'],
                        category=preset_data.get('category'),
                        default_dosage_instructions=preset_data.get('default_dosage_instructions'),
                        suggested_units=preset_data.get('suggested_units'),
                        default_unit=preset_data.get('default_unit'),
                        notes=preset_data.get('notes')
                    )
                    db.session.add(preset)
                    presets.append(preset)
        
        logger.info(f"Created {len(presets)} rescue-specific medicine presets")
        return presets
    
    return safe_db_operation("Rescue-specific medicine preset creation", _create_rescue_presets)


def seed_dogs(rescues: List['Rescue']) -> Optional[List['Dog']]:
    """Create dogs for rescues (idempotent)"""
    def _create_dogs():
        microchip_ids = set(d.microchip_id for d in Dog.query.all())
        dogs = []
        for i in range(SeedingConfig.DOGS_PER_BATCH):
            name = random.choice(SampleData.DOG_NAMES)
            breed = random.choice(SampleData.BREEDS)
            status = random.choice(SampleData.ADOPTION_STATUSES)
            rescue = random.choice(rescues)
            intake_date = generate_past_date(SeedingConfig.MAX_INTAKE_DAYS_AGO)
            microchip_id = generate_unique_microchip(microchip_ids)
            logger.debug(f"Selected dog name: {name}, breed: {breed}, status: {status}, microchip_id: {microchip_id}")
            if Dog.query.filter_by(microchip_id=microchip_id).first():
                logger.debug(f"Skipped creating dog with microchip_id {microchip_id}: already exists.")
                continue
            dog = Dog(
                name=name,
                age=f"{random.randint(1, 12)} Years",
                breed=breed,
                adoption_status=status,
                intake_date=intake_date,
                microchip_id=microchip_id,
                notes=random.choice(SampleData.DOG_NOTES),
                medical_info=random.choice(SampleData.MEDICAL_INFO),
                rescue_id=rescue.id
            )
            db.session.add(dog)
            dogs.append(dog)
        logger.info(f"Created {len(dogs)} new dogs (idempotent)")
        return dogs
    return safe_db_operation("Dog creation", _create_dogs)


def create_appointment_reminders(appointment: 'Appointment', user: Optional['User']) -> List['Reminder']:
    """Create reminders for an appointment"""
    reminders = []
    
    try:
        # Info reminder
        info_message = (
            f"{appointment.dog.name}'s appointment for '{appointment.title or appointment.type.name}' "
            f"is scheduled on {appointment.start_datetime.strftime('%Y-%m-%d at %I:%M %p')}."
        )
        info_reminder = Reminder(
            message=info_message,
            due_datetime=appointment.start_datetime,
            status='pending',
            reminder_type='appointment_info',
            dog_id=appointment.dog_id,
            appointment_id=appointment.id,
            user_id=user.id if user else None
        )
        db.session.add(info_reminder)
        reminders.append(info_reminder)
        
        # 24-hour reminder
        if appointment.start_datetime > datetime.now(timezone.utc) + timedelta(hours=23):
            due_24h = appointment.start_datetime - SeedingConfig.REMINDER_24H_OFFSET
            reminder_24h = Reminder(
                message=f"REMINDER: {appointment.dog.name}'s appointment '{appointment.title or appointment.type.name}' is in 24 hours.",
                due_datetime=due_24h,
                status='pending',
                reminder_type='appointment_upcoming_24h',
                dog_id=appointment.dog_id,
                appointment_id=appointment.id,
                user_id=user.id if user else None
            )
            db.session.add(reminder_24h)
            reminders.append(reminder_24h)
        
        # 1-hour reminder
        if appointment.start_datetime > datetime.now(timezone.utc) + timedelta(minutes=59):
            due_1h = appointment.start_datetime - SeedingConfig.REMINDER_1H_OFFSET
            reminder_1h = Reminder(
                message=f"REMINDER: {appointment.dog.name}'s appointment '{appointment.title or appointment.type.name}' is in 1 hour.",
                due_datetime=due_1h,
                status='pending',
                reminder_type='appointment_upcoming_1h',
                dog_id=appointment.dog_id,
                appointment_id=appointment.id,
                user_id=user.id if user else None
            )
            db.session.add(reminder_1h)
            reminders.append(reminder_1h)
    
    except Exception as e:
        logger.error(f"Error creating reminders for appointment {appointment.id}: {e}")
    
    return reminders


def seed_appointments(dogs: List['Dog'], appointment_types: List['AppointmentType'], users: List['User']) -> Optional[List['Appointment']]:
    """Create appointments for dogs (idempotent)"""
    def _create_appointments():
        if not users:
            logger.warning("No users available for appointment creation")
            return []
        appointments = []
        for dog in dogs:
            dog_appointment_types = [at for at in appointment_types if at.rescue_id == dog.rescue_id]
            if not dog_appointment_types:
                logger.warning(f"No appointment types found for dog {dog.name}'s rescue")
                continue
            num_appointments = random.randint(*SeedingConfig.APPOINTMENTS_PER_DOG_RANGE)
            for _ in range(num_appointments):
                appt_type = random.choice(dog_appointment_types)
                start_dt = generate_random_datetime(SeedingConfig.APPOINTMENT_DAYS_RANGE)
                creator = random.choice(users)
                logger.debug(f"Attempting to create appointment for dog_id={dog.id}, type_id={appt_type.id}, start_datetime={start_dt}")
                exists = Appointment.query.filter_by(
                    dog_id=dog.id,
                    type_id=appt_type.id,
                    start_datetime=start_dt
                ).first()
                if exists:
                    logger.debug(f"Skipped creating appointment for dog_id={dog.id}, type_id={appt_type.id}, start_datetime={start_dt}: already exists.")
                    continue
                appointment = Appointment(
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
                    created_by=creator.id
                )
                db.session.add(appointment)
                db.session.flush()  # Get the ID for reminders
                create_appointment_reminders(appointment, creator)
                appointments.append(appointment)
        logger.info(f"Created {len(appointments)} new appointments with reminders (idempotent)")
        return appointments
    return safe_db_operation("Appointment creation", _create_appointments)


def create_medicine_reminders(medicine: 'DogMedicine', user: Optional['User']) -> None:
    """Create reminders for a medicine"""
    if not medicine.start_date:
        return
    
    try:
        reminder_due_dt = datetime.combine(
            medicine.start_date, 
            datetime.min.time(), 
            tzinfo=timezone.utc
        ) + timedelta(hours=SeedingConfig.MEDICINE_REMINDER_HOUR)
        
        # Get medicine name
        medicine_name = medicine.custom_name
        if not medicine_name and medicine.medicine_id:
            preset = MedicinePreset.query.get(medicine.medicine_id)
            if preset:
                medicine_name = preset.name
        if not medicine_name:
            medicine_name = "Medicine"
        
        reminder_message = (
            f"{medicine.dog.name}'s prescription for '{medicine_name}' "
            f"is scheduled to start on {medicine.start_date.strftime('%Y-%m-%d')}."
        )
        
        reminder = Reminder(
            message=reminder_message,
            due_datetime=reminder_due_dt,
            status='pending',
            reminder_type='medicine_start',
            dog_id=medicine.dog_id,
            dog_medicine_id=medicine.id,
            user_id=user.id if user else None
        )
        db.session.add(reminder)
        
    except Exception as e:
        logger.error(f"Error creating reminder for medicine {medicine.id}: {e}")


def create_medicines_for_dog(dog: 'Dog', medicine_presets: List['MedicinePreset'], users: List['User']) -> List['DogMedicine']:
    """Create medicines for a single dog (idempotent)"""
    if not medicine_presets or not users:
        return []
    medicines = []
    num_medicines = random.randint(*SeedingConfig.MEDICINES_PER_DOG_RANGE)
    for _ in range(num_medicines):
        preset = random.choice(medicine_presets)
        start_date_val = generate_past_date(SeedingConfig.MEDICINE_START_DAYS_AGO)
        creator = random.choice(users)
        logger.debug(f"Attempting to create medicine for dog_id={dog.id}, medicine_id={preset.id}, start_date={start_date_val}")
        exists = DogMedicine.query.filter_by(
            dog_id=dog.id,
            medicine_id=preset.id,
            start_date=start_date_val
        ).first()
        if exists:
            logger.debug(f"Skipped creating medicine for dog_id={dog.id}, medicine_id={preset.id}, start_date={start_date_val}: already exists.")
            continue
        medicine = DogMedicine(
            dog_id=dog.id,
            rescue_id=dog.rescue_id,
            medicine_id=preset.id,
            custom_name=None,
            dosage=str(random.randint(1, 3)),
            unit=preset.default_unit or 'mg',
            frequency='daily',
            frequency_value=None,
            start_date=start_date_val,
            end_date=None,
            notes=f"Auto-generated {preset.name} prescription.",
            status='active',
            created_by=creator.id
        )
        db.session.add(medicine)
        db.session.flush()  # Get ID for reminders
        create_medicine_reminders(medicine, creator)
        medicines.append(medicine)
    return medicines


def seed_medicines(dogs: List['Dog'], medicine_presets: List['MedicinePreset'], users: List['User'], appointment_types: List['AppointmentType']) -> Optional[List['DogMedicine']]:
    """Create medicines for dogs (idempotent)"""
    def _create_medicines():
        if not users:
            logger.warning("No users available for medicine assignment")
            return []
        all_medicines = []
        for dog in dogs:
            medicines = create_medicines_for_dog(dog, medicine_presets, users)
            all_medicines.extend(medicines)
        logger.info(f"Created {len(all_medicines)} new medicines with reminders (idempotent)")
        return all_medicines
    return safe_db_operation("Medicine creation", _create_medicines)


def seed_dog_notes(dogs: List['Dog'], users: List['User']) -> Optional[int]:
    """Create notes for dogs (idempotent)"""
    def _create_dog_notes():
        if not users or not dogs:
            logger.warning("Insufficient data for dog note creation")
            return
        notes_created = 0
        for dog in dogs:
            num_notes = random.randint(*SeedingConfig.NOTES_PER_DOG_RANGE)
            for _ in range(num_notes):
                user = random.choice(users)
                timestamp = datetime.now(timezone.utc) - timedelta(
                    days=random.randint(0, SeedingConfig.NOTE_DAYS_AGO),
                    hours=random.randint(0, 23)
                )
                note_text = random.choice(SampleData.SAMPLE_NOTE_TEXTS)
                category = random.choice(SampleData.NOTE_CATEGORIES)
                logger.debug(f"Attempting to create note for dog_id={dog.id}, user_id={user.id}, timestamp={timestamp}, note_text={note_text}")
                exists = DogNote.query.filter_by(
                    dog_id=dog.id,
                    user_id=user.id,
                    timestamp=timestamp,
                    note_text=note_text
                ).first()
                if exists:
                    logger.debug(f"Skipped creating note for dog_id={dog.id}, user_id={user.id}, timestamp={timestamp}: already exists.")
                    continue
                note = DogNote(
                    dog_id=dog.id,
                    rescue_id=dog.rescue_id,
                    user_id=user.id,
                    timestamp=timestamp,
                    note_text=note_text,
                    category=category
                )
                db.session.add(note)
                notes_created += 1
        logger.info(f"Created {notes_created} new dog notes (idempotent)")
        return notes_created
    return safe_db_operation("Dog note creation", _create_dog_notes)


def clear_data() -> Optional[int]:
    """Clear all data from database tables in proper order, but preserve superadmin users"""
    def _clear_tables():
        # Set rescue_id to None for all superadmins to avoid FK constraint
        db.session.query(User).filter(User.role == 'superadmin').update({User.rescue_id: None})
        db.session.commit()

        # Delete all dependent tables first
        models_to_clear_first = [
            AuditLog, Reminder, DogNote, DogMedicineHistory, DogMedicine,
            Appointment, Dog
        ]
        total_deleted = 0
        for model in models_to_clear_first:
            num_deleted = db.session.query(model).delete()
            total_deleted += num_deleted
            logger.info(f"Deleted {num_deleted} rows from {model.__tablename__}")

        # Now delete all non-superadmin users
        num_deleted_users = db.session.query(User).filter(User.role != 'superadmin').delete()
        db.session.commit()
        total_deleted += num_deleted_users

        # Now delete tables that depend on rescues
        models_to_clear_second = [
            AppointmentType, MedicinePreset, Rescue
        ]
        for model in models_to_clear_second:
            num_deleted = db.session.query(model).delete()
            total_deleted += num_deleted
            logger.info(f"Deleted {num_deleted} rows from {model.__tablename__}")

        num_superadmins = User.query.filter_by(role='superadmin').count()
        logger.info(f"Deleted {num_deleted_users} users (excluding {num_superadmins} superadmin(s)) from user table")
        logger.info(f"Total rows deleted: {total_deleted}")
        return total_deleted
    return safe_db_operation("Data clearing", _clear_tables)


def prompt_password(prompt: str) -> str:
    return input(prompt)


def create_or_update_superadmin() -> None:
    """Create or update superadmin user interactively"""
    with app.app_context():
        existing_superadmin = User.query.filter_by(role='superadmin').first()
        
        if existing_superadmin:
            print(f"Superadmin already exists: {existing_superadmin.email}")
            update = input("Do you want to update this superadmin? (y/n): ").strip().lower()
            if update != 'y':
                print("No changes made.")
                return
            
            name = input(f"Enter new name [{existing_superadmin.name}]: ").strip() or existing_superadmin.name
            email = input(f"Enter new email [{existing_superadmin.email}]: ").strip() or existing_superadmin.email
            password = prompt_password("Enter new password (leave blank to keep current): ").strip()
            
            if password:
                if len(password) < SeedingConfig.MIN_PASSWORD_LENGTH:
                    print(f"Password must be at least {SeedingConfig.MIN_PASSWORD_LENGTH} characters long.")
                    return
                existing_superadmin.set_password(password)
            
            existing_superadmin.name = name
            existing_superadmin.email = email
            db.session.commit()
            print("Superadmin updated successfully!")
        else:
            print("Creating superadmin user...")
            name = input("Enter superadmin name: ").strip()
            email = input("Enter superadmin email: ").strip()
            
            if not email or '@' not in email:
                print("Invalid email address.")
                return
            
            if User.query.filter_by(email=email).first():
                print(f"User with email {email} already exists.")
                return
            
            password = prompt_password("Enter superadmin password: ").strip()
            password_confirm = prompt_password("Confirm password: ").strip()
            
            if password != password_confirm:
                print("Passwords do not match.")
                return
            
            if len(password) < SeedingConfig.MIN_PASSWORD_LENGTH:
                print(f"Password must be at least {SeedingConfig.MIN_PASSWORD_LENGTH} characters long.")
                return
            
            superadmin = User(
                name=name,
                email=email,
                role='superadmin',
                rescue_id=None,
                is_active=True,
                email_verified=True,
                data_consent=True,
                marketing_consent=False
            )
            superadmin.set_password(password)
            db.session.add(superadmin)
            db.session.commit()
            print(f"Superadmin user created successfully!\nName: {name}\nEmail: {email}\nRole: superadmin")


def ensure_default_superadmin() -> None:
    """Ensure a superadmin exists, but do not create one automatically."""
    with app.app_context():
        superadmin = User.query.filter_by(role='superadmin').first()
        if superadmin:
            logger.info('A superadmin user already exists')
        else:
            logger.warning('No superadmin user exists! Please use the interactive menu option to create one.')


# Main execution functions

def execute_seeding_operations(selected_indices: List[int]) -> None:
    """Execute selected seeding operations in proper order"""
    seeding_options = [
        ("Rescues", get_or_create_rescues, lambda: Rescue.query.all()),
        ("Users", seed_users, lambda: User.query.all()),
        ("Appointment Types", seed_appointment_types, lambda: AppointmentType.query.all()),
        ("Global Medicine Presets", seed_global_medicine_presets, lambda: MedicinePreset.query.filter_by(rescue_id=None).all()),
        ("Rescue-Specific Medicine Presets", seed_rescue_specific_medicine_presets, lambda: MedicinePreset.query.filter(MedicinePreset.rescue_id.isnot(None)).all()),
        ("Dogs", seed_dogs, lambda: Dog.query.all()),
        ("Appointments", seed_appointments, lambda: Appointment.query.all()),
        ("Medicines", seed_medicines, lambda: DogMedicine.query.all()),
        ("Dog Notes", seed_dog_notes, lambda: None),
        ("Reminders", lambda *args: logger.info("Reminders are created automatically with appointments and medicines"), lambda: None)
    ]
    
    # Storage for results between operations
    results = {}
    
    with app.app_context():
        for i in selected_indices:
            if i < 0 or i >= len(seeding_options):
                logger.warning(f"Skipping invalid option index: {i+1}")
                continue
            
            name, func, query_func = seeding_options[i]
            logger.info(f"Starting {name} seeding...")
            
            # Prepare arguments based on dependencies
            args = []
            if name == "Users":
                rescues = ensure_data_available(results.get('rescues'), lambda: Rescue.query.all(), "Rescues")
                args = [rescues]
            elif name == "Appointment Types":
                rescues = ensure_data_available(results.get('rescues'), lambda: Rescue.query.all(), "Rescues")
                args = [rescues]
            elif name == "Rescue-Specific Medicine Presets":
                rescues = ensure_data_available(results.get('rescues'), lambda: Rescue.query.all(), "Rescues")
                args = [rescues]
            elif name == "Dogs":
                rescues = ensure_data_available(results.get('rescues'), lambda: Rescue.query.all(), "Rescues")
                args = [rescues]
            elif name == "Appointments":
                dogs = ensure_data_available(results.get('dogs'), lambda: Dog.query.all(), "Dogs")
                appointment_types = ensure_data_available(results.get('appointment_types'), lambda: AppointmentType.query.all(), "Appointment Types")
                users = ensure_data_available(results.get('users'), lambda: User.query.all(), "Users")
                args = [dogs, appointment_types, users]
            elif name == "Medicines":
                dogs = ensure_data_available(results.get('dogs'), lambda: Dog.query.all(), "Dogs")
                global_presets = ensure_data_available(results.get('global_presets'), lambda: MedicinePreset.query.filter_by(rescue_id=None).all(), "Global Presets")
                rescue_presets = ensure_data_available(results.get('rescue_presets'), lambda: MedicinePreset.query.filter(MedicinePreset.rescue_id.isnot(None)).all(), "Rescue Presets")
                users = ensure_data_available(results.get('users'), lambda: User.query.all(), "Users")
                appointment_types = ensure_data_available(results.get('appointment_types'), lambda: AppointmentType.query.all(), "Appointment Types")
                args = [dogs, global_presets + rescue_presets, users, appointment_types]
            elif name == "Dog Notes":
                dogs = ensure_data_available(results.get('dogs'), lambda: Dog.query.all(), "Dogs")
                users = ensure_data_available(results.get('users'), lambda: User.query.all(), "Users")
                args = [dogs, users]
            
            # Execute the seeding function
            result = func(*args) if args else func()
            
            # Store result for future operations
            result_key = name.lower().replace(' ', '_').replace('-', '_')
            results[result_key] = result
            
            logger.info(f"{name} seeding completed")
        
        ensure_default_superadmin()
        logger.info("All selected seeding operations completed successfully")


def main() -> None:
    """Main entry point for the seeding script"""
    parser = argparse.ArgumentParser(description='Seed database for DogTrackerV2 or clear data.')
    parser.add_argument('--clear', action='store_true', help='Clear all data from the tables.')
    parser.add_argument('--seed', nargs='*', help='Specify parts to seed by number (e.g., 1 3 5) or seed all if no numbers.')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging.')
    args = parser.parse_args()

    configure_logging(debug=args.debug)

    if args.clear:
        with app.app_context():
            clear_data()
        sys.exit(0)

    seeding_options = [
        "Rescues", "Users", "Appointment Types", "Global Medicine Presets",
        "Rescue-Specific Medicine Presets", "Dogs", "Appointments", "Medicines",
        "Dog Notes", "Reminders"
    ]

    if args.seed is not None:
        if not args.seed:  # --seed with no numbers means seed all
            selected_indices = list(range(len(seeding_options)))
        else:
            try:
                selected_indices = [int(x) - 1 for x in args.seed]
            except ValueError:
                logger.error("Invalid selection for --seed. Please provide numbers.")
                sys.exit(1)
        
        execute_seeding_operations(selected_indices)
        sys.exit(0)

    # Interactive menu
    print("\nWhat would you like to seed or clear?")
    print("[0] Clear All Data")
    for i, name in enumerate(seeding_options, 1):
        print(f"[{i}] {name}")
    print(f"[{len(seeding_options)+1}] Seed EVERYTHING")
    print(f"[{len(seeding_options)+2}] Create or Edit Superadmin User")
    
    selection = input("\nEnter numbers separated by commas (e.g., 1,3,5), 0 to clear, or press Enter to seed everything: ").strip()
    
    if selection == '0':
        with app.app_context():
            clear_data()
        sys.exit(0)
    
    if selection == str(len(seeding_options)+2):
        create_or_update_superadmin()
        sys.exit(0)
    
    if not selection:  # Enter for seed everything
        selected_indices = list(range(len(seeding_options)))
    else:
        try:
            selected_indices = [int(x) - 1 for x in selection.split(',') if x]
        except ValueError:
            logger.error("Invalid selection. Exiting.")
            sys.exit(1)
    
    execute_seeding_operations(selected_indices)
    print("\nDatabase seeding completed successfully!")


if __name__ == '__main__':
    main()