# DogTrackerV2 - Dog Rescue Management Application

## 1. Project Overview

DogTrackerV2 is a web application designed to help dog rescue organizations manage their dogs, including tracking their status, medical information, appointments, and medication schedules. The application aims to provide a user-friendly interface for staff and volunteers to efficiently manage rescue operations and ensure the well-being of the animals in their care.

The system features robust CRUD (Create, Read, Update, Delete) functionalities for dogs, appointments, and medicines, utilizing modern web technologies like Flask, SQLAlchemy, HTMX, and Bootstrap to deliver a responsive and dynamic user experience without requiring full page reloads for most interactions.

## 2. Technology Stack

*   **Backend:**
    *   **Framework:** Flask (Python)
    *   **Database ORM:** SQLAlchemy
    *   **Database:** PostgreSQL (default, configurable via `DATABASE_URL`)
    *   **Migrations:** Flask-Migrate (Alembic)
    *   **Authentication:** Basic session management (details depend on user implementation, e.g., Flask-Login)
*   **Frontend:**
    *   **Templating:** Jinja2
    *   **Styling:** Bootstrap 5.3
    *   **Dynamic Interactions:** HTMX 1.9.2
    *   **JavaScript:** Vanilla JavaScript for Bootstrap component interaction and custom enhancements.
*   **Development Environment:**
    *   Python 3.x
    *   `pip` for package management (`requirements.txt`)
    *   Virtual environment (e.g., `venv`)

## 3. Project Setup & Installation

### 3.1. Prerequisites

*   Python 3.8+
*   PostgreSQL server installed and running.
*   `pip` and `virtualenv` (or `venv`)

### 3.2. Initial Setup

1.  **Clone the Repository (if applicable):**
    ```bash
    git clone <your-repository-url>
    cd DogTrackerV2
    ```

2.  **Create and Activate a Virtual Environment:**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Ensure `requirements.txt` is up-to-date with all necessary packages: Flask, SQLAlchemy, Flask-Migrate, psycopg2-binary, etc.)*

4.  **Configure Environment Variables:**
    Create a `.env` file in the project root (DogTrackerV2) or set system environment variables:
    ```env
    DATABASE_URL="postgresql://doguser:dogpassword@localhost:5432/dogtracker"
    SECRET_KEY="a_very_secret_random_key_for_sessions"
    FLASK_APP="DogTrackerV2.app:app" # Or your app entry point
    FLASK_DEBUG="True" # For development
    ```
    *   **`DATABASE_URL`**: Update with your PostgreSQL connection details (user, password, host, port, database name).
    *   **`SECRET_KEY`**: Generate a strong, random secret key.

5.  **Create the Database (if it doesn't exist):**
    Connect to your PostgreSQL server and create the database specified in `DATABASE_URL` (e.g., `dogtracker`).
    ```sql
    -- Example psql command
    CREATE DATABASE dogtracker;
    CREATE USER doguser WITH PASSWORD 'dogpassword';
    GRANT ALL PRIVILEGES ON DATABASE dogtracker TO doguser;
    ```

6.  **Initialize Database and Run Migrations:**
    ```bash
    flask db init  # Only if you haven't initialized migrations before
    flask db migrate -m "Initial migration" # Or a descriptive message
    flask db upgrade
    ```

7.  **Populate Initial Data (Optional but Recommended):**
    If you have a script like `populate_dogs.py` or similar for seeding initial data (e.g., appointment types, medicine presets, admin users, sample dogs):
    ```bash
    python populate_dogs.py # Or flask <command_name> if it's a CLI command
    ```

### 3.3. Running the Application

1.  **Activate Virtual Environment (if not already active):**
    ```bash
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

2.  **Run the Flask Development Server:**
    The project includes batch files for convenience:
    *   `start_server.bat` (Windows)
    Alternatively, use the Flask CLI:
    ```bash
    flask run
    ```
    The application should typically be available at `http://127.0.0.1:5000/`.

### 3.4. Project Structure

```
DogTrackerV2/
├── DogTrackerV2/             # Main application package
│   ├── static/               # Static files (CSS, JS images - if any beyond CDN)
│   │   └── dog_details.js    # (Currently unused/commented out from base)
│   ├── templates/            # Jinja2 templates
│   │   ├── partials/         # Reusable template snippets (modals, lists)
│   │   │   ├── add_edit_modal.html
│   │   │   ├── appointments_list.html
│   │   │   ├── medicines_list.html
│   │   │   └── modal_form_error.html
│   │   ├── base.html         # Base layout template
│   │   ├── index.html        # Dog listing page
│   │   └── dog_details.html  # Individual dog details, appointments, medicines
│   ├── __init__.py           # Application factory (if used) or app initialization
│   ├── app.py                # Main Flask application, routes, logic
│   ├── extensions.py         # Flask extension instantiations (db, migrate)
│   └── models.py             # SQLAlchemy database models
├── migrations/               # Flask-Migrate (Alembic) migration scripts
│   └── versions/
├── .env                      # (Example, not committed) Environment variables
├── populate_dogs.py          # Script to seed database with initial/test data
├── requirements.txt          # Python package dependencies
├── README.md                 # This file
├── start_server.bat          # Convenience script to start server (Windows)
├── stop_server.bat           # Convenience script (details TBD)
└── restart_server.bat        # Convenience script (details TBD)
```

## 4. Project Development Phases & Current Status

This project is being developed in phases. Below is the current status:

---

### **Phase 1: Core Dog Management & Basic Setup (COMPLETE)**

*   **Objective:** Establish the foundational Flask application, database structure for dogs, and implement full CRUD (Create, Read, Update, Delete) operations for dogs using HTMX for a single-page application feel.
*   **Key Deliverables:**
    *   Flask application structure with Blueprints (if applicable, currently monolithic `app.py`). (DONE)
    *   Database models: `User`, `Rescue`, `Dog`. (DONE, `Rescue` and `User` are basic for now)
    *   SQLAlchemy integration and Flask-Migrate setup. (DONE)
    *   Bootstrap 5 for frontend styling. (DONE)
    *   HTMX integration for dynamic page updates. (DONE)
    *   Basic user authentication structure (assumed, login/logout stubs present). (DONE)
    *   **Dog CRUD UI:**
        *   Display a list of dogs on the homepage (`index.html`), serving as the main dog listing and management page. (DONE)
        *   "Add Dog" functionality via a Bootstrap modal, submitted with HTMX, updating the dog list dynamically. (DONE)
        *   "Edit Dog" functionality via a Bootstrap modal:
            *   Accessible from the dog list. (DONE)
            *   Accessible from the `dog_details.html` page. (DONE)
            *   Form pre-filled with dog's current data. (DONE)
            *   Submitted with HTMX, updating the relevant view (dog list or details page) dynamically. (DONE)
        *   "Delete Dog" functionality with a confirmation step, submitted with HTMX, updating the dog list dynamically. (DONE)
        *   Display of flashed messages/alerts for CRUD operation success/failure (e.g., using `HX-Trigger` to show Bootstrap alerts). (DONE)
    *   **Dog Details Page (`dog_details.html`):**
        *   Route to display detailed information for a single dog. (DONE)
        *   Displays all core attributes of the dog. (DONE)
        *   Foundation for adding Appointments and Medicines sections. (DONE)

---

### **Phase 2: Appointments & Medicines CRUD (COMPLETE)**

*   **Objective:** Extend the Dog Details page to manage appointments and medications for each dog, again using HTMX-powered modals and dynamic list updates.
*   **Key Deliverables:**
    *   **Database Models & Migrations:**
        *   `AppointmentType` model (e.g., Vet Visit, Grooming, Vaccination). (DONE)
        *   `Appointment` model (linking to Dog, AppointmentType, datetime, notes, status). (DONE)
        *   `MedicinePreset` model (predefined list of common medicines, e.g., Heartgard, NexGard). (DONE)
        *   `DogMedicine` model (linking Dog to a MedicinePreset or a custom medicine name, dosage, frequency, start/end dates, status, notes). (DONE)
    *   **Appointments CRUD on Dog Details Page:**
        *   Display a table/list of appointments for the current dog. (DONE)
        *   "Add Appointment" modal:
            *   Form fields: Appointment Type (dropdown from `AppointmentType`), Title, Start Date/Time, End Date/Time, Status (e.g., Scheduled, Completed, Canceled), Notes. (DONE)
            *   HTMX submission, dynamically updates the appointments list. (DONE)
        *   "Edit Appointment" modal:
            *   Accessible from each appointment entry. (DONE)
            *   Form pre-filled with existing appointment data. (DONE)
            *   HTMX submission, dynamically updates the appointments list. (DONE)
        *   "Delete Appointment" functionality with confirmation, using HTMX. (DONE)
        *   Correct modal closing behavior and scroll restoration after HTMX swaps. (DONE)
        *   Dropdowns for `AppointmentType` in edit modals remain populated after add/edit operations. (DONE)
    *   **Medicines CRUD on Dog Details Page:**
        *   Display a table/list of medicines for the current dog. (DONE)
        *   "Add Medicine" modal:
            *   Form fields: Medicine (dropdown from `MedicinePreset`), Dosage, Unit, Frequency, Start Date, End Date (optional), Status (e.g., Active, Completed, Stopped), Notes. (DONE, Custom Name field explicitly removed)
            *   HTMX submission, dynamically updates the medicines list. (DONE)
        *   "Edit Medicine" modal:
            *   Accessible from each medicine entry. (DONE)
            *   Form pre-filled with existing medicine data. (DONE)
            *   HTMX submission, dynamically updates the medicines list. (DONE)
        *   "Delete Medicine" functionality with confirmation, using HTMX. (DONE)
        *   Server-side validation for required medicine fields (Preset, Dosage, Unit, Frequency, Start Date, Status). (DONE)
        *   Correct modal closing behavior and scroll restoration after HTMX swaps. (DONE)
        *   Dropdowns for `MedicinePreset` in edit modals remain populated after add/edit operations. (DONE)
    *   **UI/UX (Phase 2 Specific):**
        *   Removal of temporary test forms/buttons from `dog_details.html`. (DONE)
        *   *Basic server-side validation returns 400 errors (plain text or basic HTML error partial for `add_appointment`). In-depth, field-specific in-modal error messages deferred to Polish Phase.*

---

### **Phase 3: Calendar Integration & Reminder System (COMPLETED)**

*   **Objective:** Develop a visual calendar, a robust reminder generation system, and the interface for users to see and manage these reminders, including integrating appointments and medicine schedules into a unified calendar view.
*   **Key Deliverables:**
    *   **1. Core Reminder System (COMPLETED):**
        *   **1.1. Reminder Model & Migrations:**
            *   Defined a new, robust `Reminder` model (`id`, `message`, `due_datetime`, `status`, `reminder_type`, `dog_id`, `user_id`, `appointment_id`, `dog_medicine_id`, `created_at`, `updated_at`). (DONE)
            *   Established relationships to `Dog`, `User`, `Appointment`, and `DogMedicine`. (DONE)
            *   Successfully generated and applied database migrations, resolving initial issues with `NOT NULL` constraints (e.g., using `DROP TABLE IF EXISTS reminder CASCADE;` in migrations). (DONE)
        *   **1.2. Reminder Generation Logic (`DogTrackerV2/app.py`):**
            *   Implemented automatic `Reminder` creation in `add_appointment` and `edit_appointment` for appointment info, 24-hour prior, and 1-hour prior warnings. (DONE)
            *   `edit_appointment` correctly deletes old appointment reminders. (DONE)
            *   Implemented automatic `Reminder` creation in `add_medicine` and `edit_medicine` for medicine start dates. (DONE)
            *   `edit_medicine` correctly deletes old medicine reminders. (DONE)
            *   Resolved `IntegrityError` for UI-triggered operations with a `get_first_user_id()` helper function for `created_by` and `user_id` fields. (DONE)
    *   **2. Reminder Display & Interaction (COMPLETED):**
        *   **2.1. Consolidated Calendar & Reminders View:**
            *   Removed separate `/reminders` route and `reminders_page.html`. (DONE)
            *   `/calendar` route (`calendar_view` function) now fetches and groups pending reminders (Vet Reminders, Medication Reminders, Other Reminders) for the next 7 days. (DONE)
        *   **2.2. Interactive Reminder Management:**
            *   Integrated "Acknowledge" and "Dismiss" buttons for reminders on `calendar_view.html` using HTMX. (DONE)
            *   Endpoints `/reminder/<id>/acknowledge` and `/reminder/<id>/dismiss` update reminder status and UI. (DONE)
        *   **2.3. Navigation Update:**
            *   Single "Calendar & Reminders" navigation link in `base.html` pointing to `/calendar`. (DONE)
    *   **3. Calendar Implementation (COMPLETED):**
        *   **3.1. FullCalendar Integration:**
            *   Successfully added FullCalendar library (v6.1.11) via CDN to `base.html`. (DONE)
            *   Resolved initial JavaScript errors (e.g., "FullCalendar is not defined" by using `index.global.min.js`). (DONE)
        *   **3.2. Calendar View & API:**
            *   Created `/calendar` route and `DogTrackerV2/templates/calendar_view.html`. (DONE)
            *   Established and then refactored the API endpoint `/api/calendar/events` to fetch `DogMedicine` data directly and merge it with `Appointment` data, eliminating "shadow appointments." (DONE)
    *   **4. Data Seeding & Utility Updates (COMPLETED):**
        *   **4.1. `populate_dogs.py` Enhancements:**
            *   Added `clear_data()` function. (DONE)
            *   Updated `main()` with `--clear` and `--seed` arguments. (DONE)
            *   `seed_appointments` and `seed_medicines` directly create associated `Reminder` instances. (DONE)
            *   Updated `populate_dogs.py` to stop creating "shadow appointments" for medicines, aligning with the refactored calendar API. (DONE)
            *   Ensured `created_by` for seeded data uses valid user IDs. (DONE)
    *   **5. Polish & Refinements (COMPLETED):**
        *   **5.1. UI Enhancements:**
            *   Added `favicon.ico` and linked in `base.html`. (DONE)

---

### **New Phase 4: Dashboard, Reporting & User-Rescue Link (PLANNED)**

*   **Objective:** Implement the central user dashboard, associated reporting, and solidify user-rescue data links, leveraging the reminder system from Phase 3.
*   **Key Deliverables:**
    *   **Refine and Confirm User-Rescue Link:** Ensure the `User` model has a robust and populated link to the `Rescue` model (e.g., `user.rescue_id`). This is foundational for personalization and multi-tenancy.
    *   **Central Home Page / Dashboard (Primary Deliverable):**
        *   Develop a new primary landing page for authenticated users.
        *   Display a summary of all overdue scheduled items (e.g., appointments, medication doses), sourced from the reminder system.
        *   Display a summary of all scheduled items due "today" (e.g., appointments, medication doses), sourced from the reminder system.
    *   **Reporting/Analytics (Basic, Supporting Dashboard):**
        *   Develop simple server-side queries to gather statistics relevant to the dashboard and overall operations.
        *   Display basic reports/stats on the new dashboard or a dedicated section, for example:
            *   Number of dogs by adoption status.
            *   List of upcoming appointments across all dogs for the next X days.
            *   List of active medications needing refills (based on end dates, if applicable).
    *   **Usability Testing:** Conduct informal usability tests for the new dashboard and related functionalities.

---

### **New Phase 5: Multi-Tenancy & Security (PLANNED)**

*   **Objective:** Adapt the application to support multiple independent rescue organizations and implement robust security measures.
*   **Key Deliverables:**
    *   **User Roles & Permissions:**
        *   Refine `User` model to include roles (e.g., 'admin', 'staff' per rescue).
        *   Implement logic to restrict access to CRUD operations and specific data views based on user role and their affiliated rescue.
        *   Consider using Flask-Principal or similar for role management.
    *   **Rescue Privacy (Data Isolation / Multi-Tenancy):**
        *   Ensure `Rescue` model is fully utilized.
        *   Update all database models (Dog, Appointment, Medicine, etc.) to have a mandatory `rescue_id` foreign key.
        *   Modify **all** database queries (SQLAlchemy) to filter by the `current_user.rescue_id` to ensure users from one rescue cannot see or modify data from another. This is critical and affects nearly all routes.
        *   Develop a mechanism for super-admin to manage rescues, or for rescues to sign up (if applicable).
    *   **Public Welcome/Landing Page:**
        *   Create a page for unauthenticated users providing an overview of the application, and leading to login/registration portals.
    *   **Security Hardening:**
        *   Thorough review for common web vulnerabilities (XSS, CSRF - ensure forms have CSRF protection if not already handled by Flask-WTF or similar, SQL Injection - SQLAlchemy provides good protection but review custom query constructs).
        *   Ensure consistent and proper input sanitization for all user-provided data.
        *   Review and enhance session management security (e.g., secure cookie flags, session timeout).
        *   Implement rate limiting for login attempts and sensitive API endpoints.
        *   Review file upload security if that feature is added later.
    *   **Usability Testing:** Conduct informal usability tests to identify pain points and areas for improvement in workflows.

---

### **New Phase 6: UI/UX Polish & Finalization (PLANNED)**

*   **Objective:** Refine the user interface and user experience for a polished, professional, and highly usable application.
*   **Key Deliverables:**
    *   **Personalized Authenticated Welcome Screen:**
        *   Create an initial screen for logged-in users after authentication.
        *   Display a personalized welcome message incorporating their rescue organization's name.
        *   Include an engaging animated button that links to the "Central Home Page / Dashboard".
    *   **Responsive Navigation System:**
        *   Implement a main application navigation system.
        *   For mobile and tablet views: Use a hamburger menu icon on the left to toggle navigation.
        *   For desktop/laptop views: Use a persistent sidebar navigation on the left.
    *   **Consistent Styling & Layout:** Review all pages for visual consistency, adherence to Bootstrap best practices, and appealing design.
    *   **Enhanced Error Handling & User Feedback:**
        *   Implement detailed, user-friendly, in-modal error messages for all form validation failures (revisiting the `modal_form_error.html` concept and applying it thoroughly).
        *   Consider client-side validation hints in addition to server-side validation.
        *   Improve global alert/notification system for clarity and user guidance.
    *   **Accessibility (A11y):** Review application against WCAG guidelines (e.g., keyboard navigation, ARIA attributes for dynamic content, color contrast).
    *   **Mobile Responsiveness:** Thoroughly test and refine layouts on various screen sizes (phones, tablets).
    *   **Cross-Browser Compatibility:** Test on major modern browsers.
    *   **Branding:** Incorporate rescue-specific branding elements if multi-tenancy is implemented (e.g., logo display). Add a general favicon.
    *   **Final Usability Review:** Conduct a final round of usability testing across the polished application.
*   **Recommended Tools & Approaches for Polish:**
    *   **Theming/Inspiration:** Explore Bootswatch (or similar) themes for initial visual direction or inspiration.
    *   **Iconography:** Integrate a comprehensive icon library (e.g., Bootstrap Icons, Font Awesome) for clear visual communication.
    *   **Typography:** Utilize Google Fonts (or similar services) for refined and web-optimized typography.
    *   **Animations:** Employ CSS Animations & Transitions for most UI enhancements. Consider LottieFiles for complex vector animations on key interactive elements (e.g., animated welcome button).
    *   **Styling Foundation:** Leverage Bootstrap 5 as the base, with extensive custom CSS to tailor the appearance, ensuring a unique and cohesive design.

---

### **New Phase 7: System Testing & Stabilization (PLANNED)**

*   **Objective:** Conduct comprehensive testing of the application to ensure stability, identify and fix bugs, and verify all features before preparing for deployment.
*   **Key Deliverables:**
    *   **End-to-End Feature Testing:** Thoroughly test all user stories and functional requirements across the entire application.
    *   **Integration Testing:** Verify that different modules and components work together correctly.
    *   **Bug Fixing:** Prioritize and address issues identified during testing.
    *   **Performance & Stability Checks:** Basic checks to ensure the application performs adequately under normal load and remains stable.
    *   **Cross-Browser & Responsiveness Re-validation:** Final checks on major browsers and device sizes after all features and UI polish are in place.

---

### **New Phase 8: Deployment Preparation & Launch (PLANNED)**

*   **Objective:** Prepare the application for a production environment and deploy it.
*   **Key Deliverables:**
    *   **Production Configuration:**
        *   Set `FLASK_DEBUG=False`.
        *   Use a production-grade WSGI server (e.g., Gunicorn, Waitress).
        *   Manage sensitive configurations (e.g., `SECRET_KEY`, `DATABASE_URL`) securely via environment variables or a configuration management system, not hardcoded.
    *   **Static File Handling:** Optimize serving of static files (e.g., using WhiteNoise if not using a dedicated web server like Nginx for static assets).
    *   **Database:**
        *   Set up a production PostgreSQL database instance.
        *   Ensure migrations are up-to-date and can be applied to the production DB.
        *   Plan for database backups.
    *   **Logging & Monitoring:** Implement robust logging for errors and important events in production. Set up basic application monitoring.
    *   **HTTPS:** Ensure the application is served over HTTPS in production (e.g., via a reverse proxy like Nginx with Let's Encrypt).
    *   **Testing:** Perform final end-to-end testing in a staging environment that mirrors production as closely as possible.
    *   **Deployment:** Deploy to the chosen hosting platform (e.g., Heroku, AWS, DigitalOcean, PythonAnywhere).

## 5. Current Standing

*   **We have successfully COMPLETED Phase 1 and Phase 2.**
*   The application has a solid foundation with working CRUD operations for Dogs, Appointments, and Medicines.
*   HTMX is effectively used for dynamic UI updates, providing a smooth user experience for these core features.
*   Modal interactions (opening, closing, scroll restoration) are stable.
*   Server-side validation is in place, though the display of in-modal error messages has been deferred to the Polish phase.
*   **We are now ready to begin Phase 3: Advanced Features**, starting with either "Reminders/Calendar Integration" or "Basic Reporting/Analytics."

## 6. Future Considerations / Potential Enhancements Beyond Current Phases

*   Advanced User Management (invitations, password resets via email)
*   Audit Trails for critical actions
*   File Uploads (e.g., for dog photos, medical documents)
*   Full-text Search capabilities
*   Public-facing adoption portal views
*   Integration with third-party services (e.g., Petfinder API, communication tools)

---

This README should provide a good snapshot and guide for future development. 