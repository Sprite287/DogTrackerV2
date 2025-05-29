## 1. Project Overview

DogTrackerV2 is a web application designed to help dog rescue organizations manage their dogs, including tracking their status, medical information, appointments, and medication schedules. The application aims to provide a user-friendly interface for staff and volunteers to efficiently manage rescue operations and ensure the well-being of the animals in their care.

The system features robust CRUD (Create, Read, Update, Delete) functionalities for dogs, appointments, and medicines, utilizing modern web technologies like Flask, SQLAlchemy, HTMX, and Bootstrap to deliver a responsive and dynamic user experience without requiring full page reloads for most interactions.

---

## 2. Technology Stack

### Backend
- **Framework:** Flask (Python)
- **Database ORM:** SQLAlchemy
- **Database:** PostgreSQL (default, configurable via `DATABASE_URL`)
- **Migrations:** Flask-Migrate (Alembic)
- **Authentication:** Basic session management (details depend on user implementation, e.g., Flask-Login)

### Frontend
- **Templating:** Jinja2
- **Styling:** Bootstrap 5.3
- **Dynamic Interactions:** HTMX 1.9.2
- **JavaScript:** Vanilla JavaScript for Bootstrap component interaction and custom enhancements

### Development Environment
- Python 3.x
- `pip` for package management (`requirements.txt`)
- Virtual environment (e.g., `venv`) 