# DogTrackerV2 Permissions & Authorization Documentation

## Overview
This document describes the Role-Based Access Control (RBAC) and permissions system for DogTrackerV2. It details the roles, their permissions, how permissions are enforced in the codebase, and how audit logging is integrated with authorization events.

---

## Roles

- **superadmin**: Global administrator with unrestricted access to all rescues and data.
- **owner**: The primary admin for a specific rescue (sometimes called 'admin' in code). Has full control within their rescue.
- **admin**: (Alias for owner; see above.)
- **staff**: Regular staff member for a rescue. Has limited permissions.

---

## Permissions Matrix

| Action                        | Superadmin | Owner/Admin | Staff |
|-------------------------------|:----------:|:-----------:|:-----:|
| View all rescues/dogs         |     ✓      |     ✗       |   ✗   |
| View own rescue/dogs          |     ✓      |     ✓       |   ✓   |
| Add/edit/delete dogs          |     ✓      |     ✓       |   ✓*  |
| Delete critical items         |     ✓      |     ✓       |   ✗   |
| Manage users                  |     ✓      |     ✓       |   ✗   |
| Manage medicine presets       |     ✓      |     ✓       |   ✗   |
| View audit logs               |     ✓      |     ✓       |   ✗   |
| Export data                   |     ✓      |     ✓       |   ✓   |

\* = Only allowed for dogs in their rescue, or with additional checks.

---

## Permission Enforcement

- **Route Decorators**: Permissions are enforced at the route level using decorators (e.g., `@login_required`, `@roles_required(['admin', 'owner'])`).
- **Inline Checks**: Some routes use inline role checks (e.g., `if current_user.role != 'superadmin' ...`).
- **UI Controls**: Navigation and page elements are conditionally shown based on `current_user.role` in templates.
- **Resource Ownership**: For most actions, users can only access or modify resources belonging to their own rescue, unless they are a superadmin.

### Example Decorator (to be used in code):
```python
from functools import wraps
from flask import abort
from flask_login import current_user

def roles_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

---

## Audit Logging

- **All authentication events** (login, logout, failed login) are logged.
- **Rescue registration and user management actions** are logged.
- **Permission changes** (e.g., role changes) should be logged.
- **Failed authorization attempts** (403s due to insufficient permissions) should be logged for security review.

---

## How to Update Permissions

1. Update this file with any changes to roles or permissions.
2. Update route decorators and inline checks in the codebase.
3. Ensure UI elements are updated to reflect new permissions.
4. Add or update audit logging for any new permission-related events.

---

## Future Considerations

- Consider moving to a more granular, policy-based permission system if requirements grow.
- Consider adding per-resource or per-action permissions for more flexibility.

---

_Last updated: 2024-06-09_ 