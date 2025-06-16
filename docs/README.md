# DogTrackerV2 Documentation Index

Welcome to the **DogTrackerV2** documentation - a sophisticated Flask-based dog care management system with enterprise-grade multi-tenancy, comprehensive audit logging, and advanced medicine management capabilities.

## 📋 Quick Start

- [Project Overview & Technology Stack](project_overview.md) - Core architecture and tech stack
- [Setup & Installation](setup_installation.md) - Complete installation guide
- [Development Phases & Current Status](development_phases.md) - Project roadmap and progress

## 🔧 Development & Architecture

- [Blueprint Refactoring Phase Tree](refactor_phasetree.md) - **NEW!** Complete blueprint migration plan
- [Permissions & Authorization](permissions.md) - Multi-role permission system
- [Database Seeding & Test Data](database_seeding.md) - Test data setup

## 🚀 Project Information

**Current Status:** Production-ready monolithic application (2,788 lines)
**Next Phase:** Blueprint refactoring for improved maintainability
**Architecture:** Flask + PostgreSQL + HTMX + Bootstrap
**Key Features:** Multi-tenancy, audit logging, medicine management, appointment scheduling

## 🔄 Development Workflow

### Sync Script Usage
The project includes a powerful sync script (`sync.sh`) for WSL to Windows development:

```bash
# One-time sync
./sync.sh

# Continuous monitoring (watches for file changes)
./sync.sh watch
```

**Sync Features:**
- Real-time file monitoring and synchronization
- Excludes development artifacts (`.git/`, `__pycache__/`, `venv/`, etc.)
- Progress indicators and colored output
- Error handling and K: drive mount validation
- Automatic directory creation

### Git Strategy
- Main branch: `main`
- Feature branches for each blueprint refactoring phase
- Commit after each phase completion with manual testing
- Tag major milestones (`v1.0-R4C-complete`, `v1.0-production-ready`)

## 📁 Project Structure

```
DogTrackerV2/
├── app.py                 # Main application (2,788 lines - to be refactored)
├── models.py              # Database models
├── forms.py               # WTForms definitions
├── permissions.py         # Authorization decorators
├── audit.py              # Comprehensive audit system
├── rescue_helpers.py     # Multi-tenant helper functions
├── extensions.py         # Flask extensions
├── sync.sh              # WSL to Windows sync script
├── docs/                # Documentation
├── templates/           # Jinja2 templates
├── static/             # CSS, JS, images
├── migrations/         # Database migrations
└── scripts/           # Utility scripts
```

## 🎯 Upcoming: Blueprint Refactoring

The project is preparing for a comprehensive blueprint refactoring to improve:
- **Maintainability:** Modular code organization
- **Scalability:** Better separation of concerns
- **Development Experience:** Easier feature development
- **Testing:** More granular testing capabilities

See [Blueprint Refactoring Phase Tree](refactor_phasetree.md) for the complete migration plan.

## 🔗 External Resources

- **Technology Stack:** Flask, PostgreSQL, HTMX, Bootstrap 5
- **Development Environment:** WSL2 + Windows integration
- **Database:** PostgreSQL with comprehensive audit logging
- **Frontend:** Server-side rendering with HTMX for dynamic interactions
