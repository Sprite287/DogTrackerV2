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

**Current Status:** ✅ **BLUEPRINT ARCHITECTURE COMPLETE** - Fully modular Flask application
**Architecture:** Flask Blueprint Architecture + PostgreSQL + HTMX + Bootstrap
**Key Features:** Multi-tenancy, audit logging, medicine management, appointment scheduling
**Routes:** 55+ routes across 11 specialized blueprints

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
├── app.py                 # ✅ Clean main application (blueprint registrations)
├── blueprints/           # ✅ Modular blueprint architecture
│   ├── core/            #     Shared utilities, decorators, error handlers
│   ├── main/            #     Dashboard and general pages (2 routes)
│   ├── auth/            #     Authentication system (7 routes)
│   ├── dogs/            #     Dog management (18 routes)
│   ├── appointments/    #     Appointment system (6 routes)
│   ├── medicines/       #     Medicine management (9 routes)
│   ├── admin/           #     Superadmin functions (3 routes)
│   ├── api/             #     API endpoints (2 routes)
│   ├── staff/           #     User management (6 routes)
│   ├── rescue/          #     Organizational management (1 route)
│   └── calendar/        #     Calendar and reminder system (3 routes)
├── models.py              # Database models
├── forms.py               # WTForms definitions
├── permissions.py         # Authorization decorators
├── audit.py              # Comprehensive audit system
├── rescue_helpers.py     # Multi-tenant helper functions
├── extensions.py         # Flask extensions
├── config.py             # Centralized configuration management
├── sync.sh              # WSL to Windows sync script
├── docs/                # Documentation
├── templates/           # Jinja2 templates (blueprint URL patterns)
├── static/             # CSS, JS, images
├── migrations/         # Database migrations
└── scripts/           # Utility scripts
```

## 🎯 ✅ Completed: Blueprint Refactoring

The comprehensive blueprint refactoring has been **COMPLETED** successfully! The project now features:
- ✅ **Maintainability:** Modular code organization across 11 blueprints
- ✅ **Scalability:** Clear separation of concerns and specialized domains
- ✅ **Development Experience:** Team-friendly parallel development
- ✅ **Testing:** Granular testing capabilities with isolated blueprint testing

See [Blueprint Refactoring Phase Tree](refactor_phasetree.md) for the complete migration documentation.

### Blueprint Architecture Benefits:
- **55+ routes** organized across specialized blueprints
- **Zero functionality loss** during migration
- **Enhanced performance** with modular loading
- **Future-ready architecture** for new feature additions
- **Comprehensive documentation** and development patterns

## 🔗 External Resources

- **Technology Stack:** Flask, PostgreSQL, HTMX, Bootstrap 5
- **Development Environment:** WSL2 + Windows integration
- **Database:** PostgreSQL with comprehensive audit logging
- **Frontend:** Server-side rendering with HTMX for dynamic interactions
