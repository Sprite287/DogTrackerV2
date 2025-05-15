# DogTrackerV2/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, IntegerField, BooleanField, HiddenField, FieldList, FormField
from wtforms.validators import DataRequired, Optional, Length
from wtforms.fields import DateField # Correct import for DateField

class DogForm(FlaskForm):
    """Form for adding or editing a dog."""
    dog_id = HiddenField("Dog ID") 
    name = StringField(
        'Dog Name',
        validators=[
            DataRequired(message="Dog name is required."),
            Length(min=1, max=120, message="Dog name must be between 1 and 120 characters.")
        ],
        render_kw={"placeholder": "Enter dog's name"}
    )
    submit = SubmitField('Save Dog')

class AddDogForm(FlaskForm):
    name = StringField('Dog\'s Name', validators=[DataRequired(), Length(min=1, max=120)])
    approx_age = StringField('Approximate Age', validators=[Length(max=50)]) # Optional field
    submit = SubmitField('Add Dog')

class EditDogForm(FlaskForm):
    name = StringField('Dog Name', validators=[DataRequired(), Length(min=1, max=120)])
    approx_age = StringField('Approximate Age', validators=[Optional(), Length(max=50)]) # Changed to StringField
    submit = SubmitField('Save Changes')

# --- Medicine Forms ---
class MedicineForm(FlaskForm):
    """Base form for a single medicine entry, used in FieldList."""
    id = HiddenField("Medicine ID") # To identify existing medicines
    name = StringField('Medicine Name', validators=[DataRequired(), Length(max=100)])
    dosage = StringField('Dosage', validators=[Optional(), Length(max=100)])
    frequency = StringField('Frequency', validators=[Optional(), Length(max=100)])
    start_date = DateField('Start Date', validators=[Optional()])
    end_date = DateField('End Date', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])
    delete = BooleanField('Delete this medicine') # For marking for deletion in EditDogAndMedicinesForm

class AddMedicineForm(FlaskForm):
    """Form for adding a single new medicine to a dog."""
    name = StringField('Medicine Name', validators=[DataRequired(), Length(max=100)])
    dosage = StringField('Dosage', validators=[Optional(), Length(max=100)])
    frequency = StringField('Frequency', validators=[Optional(), Length(max=100)])
    start_date = DateField('Start Date', validators=[Optional()])
    end_date = DateField('End Date', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Add Medicine')

class EditDogAndMedicinesForm(EditDogForm): # Inherits name, approx_age, and submit from EditDogForm
    """Form for editing a dog and all their medicines."""
    medicines = FieldList(FormField(MedicineForm), min_entries=0)
    submit = SubmitField('Save All Changes') # Override submit button label
