"""
Empathetic Messaging System for Phase 7B
Provides caring, supportive messages throughout the application
"""

from flask import flash
import random

class EmpatheticMessages:
    """Centralized empathetic messaging system"""
    
    # Contextual loading messages
    LOADING_MESSAGES = {
        'dog_details': lambda dog_name=None: f"Gathering {dog_name}'s care records..." if dog_name else "Loading care details...",
        'dog_history': lambda dog_name=None: f"Preparing {dog_name}'s journey timeline..." if dog_name else "Building care timeline...",
        'dashboard': lambda: "Preparing your care center overview...",
        'calendar': lambda: "Organizing care schedules...",
        'appointments': lambda: "Loading upcoming care visits...",
        'medicines': lambda dog_name=None: f"Reviewing {dog_name}'s treatment plan..." if dog_name else "Loading treatments...",
        'dogs_list': lambda: "Gathering information about dogs in care...",
        'staff': lambda: "Loading care team information...",
        'default': lambda: "Loading with care..."
    }
    
    # Enhanced success messages
    SUCCESS_MESSAGES = {
        'dog_created': "Welcome to our family, {dog_name}! 🌱 Their journey with us begins now.",
        'dog_updated': "{dog_name}'s information is safe with us and has been lovingly updated.",
        'dog_deleted': "We'll always remember {dog_name}. Their information has been carefully archived.",
        'appointment_created': "{dog_name}'s care visit is scheduled with love and attention.",
        'appointment_updated': "{dog_name}'s appointment details have been updated with care.",
        'appointment_deleted': "The appointment has been removed from {dog_name}'s schedule.",
        'note_added': "Your caring observation about {dog_name} has been recorded in their journey.",
        'medicine_added': "{dog_name}'s treatment plan is updated and secure in our care.",
        'medicine_updated': "{dog_name}'s medication information has been carefully updated.",
        'medicine_deleted': "The medication has been removed from {dog_name}'s treatment plan.",
        'reminder_acknowledged': "Thank you for your dedication to {dog_name}'s care.",
        'reminder_dismissed': "Reminder noted and set aside with understanding.",
        'staff_added': "Welcome {staff_name} to our caring team!",
        'staff_updated': "{staff_name}'s information has been updated with care.",
        'rescue_updated': "Your rescue's information reflects your continued dedication.",
        'login_success': "Welcome back! Your caring presence makes a difference.",
        'logout_success': "Thank you for your dedication today. Rest well.",
        'password_reset': "Your password has been updated. Your security and peace of mind matter to us."
    }
    
    # Gentle error messages
    ERROR_MESSAGES = {
        'form_validation': "Let's try that again - we want {dog_name}'s information to be just right.",
        'form_validation_general': "Let's review this together - your attention to detail shows you care.",
        'network_error': "Something didn't quite work - your dedication shows, let's fix this together.",
        'permission_denied': "We're protecting {resource}'s information - please check your access.",
        'permission_denied_general': "We're keeping things secure - your understanding is appreciated.",
        'server_error': "We're having a moment - your dedication means everything, bear with us.",
        'not_found': "We couldn't find what you're looking for - let's help you get back on track.",
        'database_error': "We're having trouble saving right now - your work matters, let's try again.",
        'file_upload_error': "The file couldn't be uploaded - we'll help you try another way.",
        'login_failed': "Those credentials don't quite match - your security is important to us.",
        'registration_failed': "We had trouble creating your account - your dedication to join us is appreciated.",
        'duplicate_entry': "This information already exists - thank you for being thorough.",
        'validation_required_field': "This information helps us care better - please fill it in.",
        'validation_invalid_format': "This format doesn't quite work - let's adjust it together.",
        'session_expired': "Your session has expired for security - we appreciate your understanding.",
        'access_denied': "This area is protected - your respect for boundaries is valued."
    }
    
    # Confirmation dialog messages
    CONFIRMATION_MESSAGES = {
        'delete_dog': {
            'title': 'A Difficult Goodbye',
            'message': "We understand this is difficult. This will permanently remove {dog_name}'s records from our care system.",
            'detail': "Their memory and the love you've shown will always matter.",
            'icon': 'bi-heart-break',
            'confirm_text': 'Remove with Care',
            'cancel_text': 'Keep Them With Us'
        },
        'delete_appointment': {
            'title': 'Remove Care Visit',
            'message': "This will remove {dog_name}'s appointment from their care schedule.",
            'detail': "This action shows your careful attention to their needs.",
            'icon': 'bi-calendar-x',
            'confirm_text': 'Remove Appointment',
            'cancel_text': 'Keep Appointment'
        },
        'delete_medicine': {
            'title': 'Update Treatment Plan',
            'message': "This will remove this medication from {dog_name}'s treatment plan.",
            'detail': "Your careful management of their health is appreciated.",
            'icon': 'bi-capsule',
            'confirm_text': 'Remove Medication',
            'cancel_text': 'Keep Medication'
        },
        'delete_note': {
            'title': 'Remove Care Note',
            'message': "This will remove this note from {dog_name}'s journey.",
            'detail': "Every observation you make shows your caring attention.",
            'icon': 'bi-journal-x',
            'confirm_text': 'Remove Note',
            'cancel_text': 'Keep Note'
        }
    }
    
    # Empty state messages
    EMPTY_STATES = {
        'no_dogs': {
            'icon': 'bi-heart',
            'title': 'Every rescue story begins with hope',
            'message': 'Add your first resident to start their journey',
            'action_text': 'Welcome First Dog',
            'action_class': 'btn-primary grow-in'
        },
        'no_appointments': {
            'icon': 'bi-calendar-heart',
            'title': 'Ready to schedule some care',
            'message': 'Create the first appointment to begin tracking {dog_name}\'s health journey',
            'action_text': 'Schedule First Visit',
            'action_class': 'btn-primary grow-in'
        },
        'no_medicines': {
            'icon': 'bi-capsule-pill',
            'title': 'Health care starts here',
            'message': 'Add the first medication to begin {dog_name}\'s treatment tracking',
            'action_text': 'Add First Medication',
            'action_class': 'btn-primary grow-in'
        },
        'no_history': {
            'icon': 'bi-journal-heart',
            'title': '{dog_name}\'s story is just beginning',
            'message': 'Every moment of care creates a meaningful chapter in their journey',
            'action_text': 'Add First Note',
            'action_class': 'btn-primary grow-in'
        },
        'no_reminders': {
            'icon': 'bi-check-circle-fill',
            'title': 'All caught up with love',
            'message': 'No pending reminders - you\'re staying on top of everyone\'s care beautifully',
            'action_text': None,
            'action_class': None
        },
        'no_staff': {
            'icon': 'bi-people-fill',
            'title': 'Building your care team',
            'message': 'Add your first team member to begin collaborating on animal care',
            'action_text': 'Add First Team Member',
            'action_class': 'btn-primary grow-in'
        }
    }
    
    @staticmethod
    def get_loading_message(context, **kwargs):
        """Get contextual loading message"""
        message_func = EmpatheticMessages.LOADING_MESSAGES.get(context, EmpatheticMessages.LOADING_MESSAGES['default'])
        return message_func(**kwargs)
    
    @staticmethod
    def flash_success(message_type, **kwargs):
        """Flash an empathetic success message"""
        template = EmpatheticMessages.SUCCESS_MESSAGES.get(message_type, "Action completed with care.")
        message = template.format(**kwargs)
        flash(message, 'success')
        return message
    
    @staticmethod
    def flash_error(error_type, **kwargs):
        """Flash an empathetic error message"""
        template = EmpatheticMessages.ERROR_MESSAGES.get(error_type, "Something didn't work as expected - we're here to help.")
        message = template.format(**kwargs)
        flash(message, 'danger')
        return message
    
    @staticmethod
    def flash_info(message, **kwargs):
        """Flash an empathetic info message"""
        formatted_message = message.format(**kwargs)
        flash(formatted_message, 'info')
        return formatted_message
    
    @staticmethod
    def get_confirmation_data(confirmation_type, **kwargs):
        """Get confirmation dialog data"""
        template = EmpatheticMessages.CONFIRMATION_MESSAGES.get(confirmation_type, {
            'title': 'Confirm Action',
            'message': 'Are you sure you want to proceed?',
            'detail': 'This action cannot be undone.',
            'icon': 'bi-question-circle',
            'confirm_text': 'Confirm',
            'cancel_text': 'Cancel'
        })
        
        # Format all text fields
        formatted = {}
        for key, value in template.items():
            if isinstance(value, str):
                formatted[key] = value.format(**kwargs)
            else:
                formatted[key] = value
        
        return formatted
    
    @staticmethod
    def get_empty_state(state_type, **kwargs):
        """Get empty state data"""
        template = EmpatheticMessages.EMPTY_STATES.get(state_type, EmpatheticMessages.EMPTY_STATES['no_dogs'])
        
        # Format all text fields
        formatted = {}
        for key, value in template.items():
            if isinstance(value, str) and value:
                formatted[key] = value.format(**kwargs)
            else:
                formatted[key] = value
        
        return formatted

# Convenience functions for easy importing
def flash_success(message_type, **kwargs):
    return EmpatheticMessages.flash_success(message_type, **kwargs)

def flash_error(error_type, **kwargs):
    return EmpatheticMessages.flash_error(error_type, **kwargs)

def flash_info(message, **kwargs):
    return EmpatheticMessages.flash_info(message, **kwargs)

def get_loading_message(context, **kwargs):
    return EmpatheticMessages.get_loading_message(context, **kwargs)

def get_confirmation_data(confirmation_type, **kwargs):
    return EmpatheticMessages.get_confirmation_data(confirmation_type, **kwargs)

def get_empty_state(state_type, **kwargs):
    return EmpatheticMessages.get_empty_state(state_type, **kwargs)