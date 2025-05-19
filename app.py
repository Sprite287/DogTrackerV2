from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, render_template_string, get_flashed_messages, make_response
import os
from extensions import db, migrate
import json

app = Flask(__name__)

# Configurations
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://doguser:dogpassword@localhost:5432/dogtracker')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')

db.init_app(app)
migrate.init_app(app, db)

# Import models after app and db are set up
from models import Dog

def render_dog_cards():
    dogs = Dog.query.order_by(Dog.name.asc()).all()
    return render_template('dog_cards.html', dogs=dogs)

def render_alert(message, category='success'):
    return render_template_string('<div class="alert alert-{{ category }} alert-dismissible fade show" role="alert" hx-swap-oob="true">{{ message }}<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div>', message=message, category=category)

@app.route('/')
def index():
    dogs = Dog.query.order_by(Dog.name.asc()).all()
    return render_template('index.html', dogs=dogs)

def render_dog_cards_html():
    return render_template('dog_cards.html', dogs=Dog.query.order_by(Dog.name.asc()).all())

@app.route('/dog/add', methods=['POST'])
def add_dog():
    name = request.form.get('name')
    if not name:
        if request.headers.get('HX-Request'):
            cards = render_dog_cards_html()
            resp = make_response(cards)
            resp.headers['HX-Trigger'] = json.dumps({"showAlert": {"message": "Dog name is required.", "category": "danger"}})
            return resp
        flash('Dog name is required.', 'danger')
        return redirect(url_for('index'))
    age = request.form.get('age')
    breed = request.form.get('breed')
    adoption_status = request.form.get('adoption_status')
    intake_date = request.form.get('intake_date')
    if not intake_date:
        intake_date = None
    microchip_id = request.form.get('microchip_id')
    notes = request.form.get('notes')
    medical_info = request.form.get('medical_info')
    dog = Dog(name=name, age=age, breed=breed, adoption_status=adoption_status,
              intake_date=intake_date, microchip_id=microchip_id, notes=notes,
              medical_info=medical_info, rescue_id=1)
    db.session.add(dog)
    db.session.commit()
    if request.headers.get('HX-Request'):
        cards = render_dog_cards_html()
        resp = make_response(cards)
        resp.headers['HX-Trigger'] = json.dumps({"showAlert": {"message": "Dog added successfully!", "category": "success"}})
        return resp
    flash('Dog added successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/dog/edit', methods=['POST'])
def edit_dog():
    print('--- Edit Dog Debug ---')
    print('Request method:', request.method)
    print('Request path:', request.path)
    print('Request headers:', dict(request.headers))
    print('Form data:', request.form)
    print('Request referrer:', request.referrer)
    dog_id = request.form.get('dog_id')
    dog = Dog.query.get_or_404(dog_id)
    print('Edit request received for dog:', dog_id)
    name = request.form.get('name')
    if not name:
        if request.headers.get('HX-Request'):
            cards = render_dog_cards_html()
            resp = make_response(cards)
            resp.headers['HX-Trigger'] = json.dumps({"showAlert": {"message": "Dog name is required.", "category": "danger"}})
            return resp
        flash('Dog name is required.', 'danger')
        return redirect(request.referrer or url_for('index'))
    dog.name = name
    dog.age = request.form.get('age')
    dog.breed = request.form.get('breed')
    dog.adoption_status = request.form.get('adoption_status')
    dog.intake_date = request.form.get('intake_date')
    if not dog.intake_date:
        dog.intake_date = None
    dog.microchip_id = request.form.get('microchip_id')
    dog.notes = request.form.get('notes')
    dog.medical_info = request.form.get('medical_info')
    db.session.commit()
    if request.headers.get('HX-Request'):
        if request.form.get('from_details') == 'details':
            from flask import make_response, request as flask_request
            flash('Dog updated successfully!', 'success')
            resp = make_response('')
            resp.headers['HX-Redirect'] = flask_request.referrer or '/'
            resp.headers['HX-Trigger'] = json.dumps({"showAlert": {"message": "Dog updated successfully!", "category": "success"}})
            return resp
        cards = render_dog_cards_html()
        resp = make_response(cards)
        resp.headers['HX-Trigger'] = json.dumps({"showAlert": {"message": "Dog updated successfully!", "category": "success"}})
        return resp
    flash('Dog updated successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/dog/<int:dog_id>/delete', methods=['POST'])
def delete_dog(dog_id):
    dog = Dog.query.get_or_404(dog_id)
    db.session.delete(dog)
    db.session.commit()
    if request.headers.get('HX-Request'):
        cards = render_dog_cards_html()
        resp = make_response(cards)
        resp.headers['HX-Trigger'] = json.dumps({"showAlert": {"message": "Dog deleted successfully!", "category": "success"}})
        return resp
    flash('Dog deleted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/test-edit', methods=['POST'])
def test_edit():
    print('Test edit route hit!')
    return 'OK'

@app.route('/dog/<int:dog_id>')
def dog_details(dog_id):
    dog = Dog.query.get_or_404(dog_id)
    return render_template('dog_details.html', dog=dog)

@app.cli.command('list-routes')
def list_routes():
    import urllib
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(sorted(rule.methods))
        line = urllib.parse.unquote(f"{rule.endpoint:30s} {methods:20s} {rule}")
        output.append(line)
    for line in sorted(output):
        print(line)

if __name__ == '__main__':
    print('--- ROUTES REGISTERED ---')
    for rule in app.url_map.iter_rules():
        print(rule, rule.methods)
    print('-------------------------')
    app.run(debug=True, host='0.0.0.0') 