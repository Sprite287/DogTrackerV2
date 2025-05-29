## 3. Project Setup & Installation

### 3.1. Prerequisites

- Python 3.8+
- PostgreSQL server installed and running
- `pip` and `virtualenv` (or `venv`)

### 3.2. Initial Setup

**1. Clone the Repository (if applicable):**
```bash
git clone <your-repository-url>
cd DogTrackerV2
```

**2. Create and Activate a Virtual Environment:**
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

**3. Install Dependencies:**
```bash
pip install -r requirements.txt
```
*(Ensure `requirements.txt` is up-to-date with all necessary packages: Flask, SQLAlchemy, Flask-Migrate, psycopg2-binary, etc.)*

**4. Configure Environment Variables:**

Create a `.env` file in the project root (DogTrackerV2) or set system environment variables:
```env
DATABASE_URL="postgresql://doguser:dogpassword@localhost:5432/dogtracker"
SECRET_KEY="a_very_secret_random_key_for_sessions"
FLASK_APP="app" # Or your app entry point
FLASK_DEBUG="True" # For development
```

- **`DATABASE_URL`**: Update with your PostgreSQL connection details (user, password, host, port, database name)
- **`SECRET_KEY`**: Generate a strong, random secret key

**5. Create the Database (if it doesn't exist):**

Connect to your PostgreSQL server and create the database specified in `DATABASE_URL` (e.g., `dogtracker`).
```sql
-- Example psql command
CREATE USER doguser WITH PASSWORD 'dogpassword';
GRANT ALL PRIVILEGES ON DATABASE dogtracker TO doguser;
```

**6. Initialize Database and Run Migrations:**
```bash
flask db init  # Only if you haven't initialized migrations before
flask db migrate -m "Initial migration" # Or a descriptive message
flask db upgrade
```

**7. Populate Initial Data (Optional but Recommended):**

If you have a script like `populate_dogs.py` or similar for seeding initial data:
```bash
python populate_dogs.py # Or flask <command_name> if it's a CLI command
```

### 3.3. Running the Application

**1. Activate Virtual Environment (if not already active):**
```bash
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

**2. Run the Flask Development Server:**

The project includes batch files for convenience:
- `start_server.bat` (Windows)

Alternatively, use the Flask CLI:
```bash
flask run
```

The application should typically be available at `http://127.0.0.1:5000/`.

### 3.4. Project Structure

```
DogTrackerV2/
├── static/               # Static files (CSS, JS, images)
│   └── dog_details.js    # Custom JavaScript for dog details functionality
├── templates/            # Jinja2 templates
│   ├── partials/         # Reusable template snippets (modals, lists)
│   │   ├── add_edit_modal.html         # Generic add/edit modal template
│   │   ├── appointments_list.html      # Appointments display partial
│   │   ├── medicines_list.html         # Medicines display partial
│   │   ├── modal_form_error.html       # Error display partial for modals
│   │   └── history_timeline.html       # History timeline partial (Phase 5)
│   ├── base.html         # Base layout template with navigation
│   ├── index.html        # Dog listing page (redirects to dashboard)
│   ├── dashboard.html    # Main dashboard (Phase 4 - landing page)
│   ├── dog_details.html  # Individual dog details, appointments, medicines
│   ├── dog_history.html  # Comprehensive dog history page (Phase 5)
│   ├── dog_list.html     # Dog management listing page
│   └── calendar.html     # Calendar view with reminders (Phase 3)
├── migrations/           # Flask-Migrate (Alembic) migration scripts
│   └── versions/         # Database migration version files
├── app.py                # Main Flask application, routes, logic
├── extensions.py         # Flask extension instantiations (db, migrate)
├── models.py             # SQLAlchemy database models
│   # Current models: User, Rescue, Dog, AppointmentType, Appointment,
│   # MedicinePreset, DogMedicine, Reminder, DogNote (Phase 5)
├── populate_dogs.py      # Comprehensive data seeding script
├── requirements.txt      # Python package dependencies
├── README.md             # This documentation file
├── .env.example          # Environment variables template
├── .gitignore           # Git ignore rules
├── start_server.bat      # Windows server start script
├── stop_server.bat       # Windows server stop script
└── restart_server.bat    # Windows server restart script
```

**Key Directories & Files:**
- **`templates/`**: All HTML templates with Jinja2 templating
- **`templates/partials/`**: Reusable components for HTMX functionality
- **`static/`**: Client-side assets (minimal due to CDN usage)
- **`models.py`**: Database schema with 9 core models across 5 phases
- **`app.py`**: ~800+ lines of Flask routes and business logic
- **`populate_dogs.py`**: Sample data generation for testing and demos

# ... (copy all content from the '3. Project Setup & Installation' section, including all subsections and code blocks, from docs/README.md) ... 