## Database Seeding & Test Data

The `populate_dogs.py` script allows you to seed the database with realistic test data, clear all data, and manage test user logins for development and QA.

### Usage

Run the script with Python:

```
python populate_dogs.py [OPTIONS]
```

### Options

- `--seed` (with or without numbers):
  - `python populate_dogs.py --seed` seeds **all** data.
  - `python populate_dogs.py --seed 1 3 5` seeds only the selected parts (see menu for numbers).
- `--clear`: Clears all data from the database tables.
- `--debug`: Enables detailed debug logging (shows skipped records, random choices, etc.).

### Interactive Menu

If you run the script with no arguments, you'll get an interactive menu to select what to seed or clear.

### Seeded User Logins

- When users are seeded, a file called `seeded_logins.txt` is created in the project root.
- This file contains the login credentials (email, password, role) for all seeded owner and staff users.
- **WARNING:** This file contains plaintext credentials for testing only. **Delete it before deploying to production!**

### Example Commands

- Seed everything (with debug logging):
  ```
  python populate_dogs.py --seed --debug
  ```
- Clear all data:
  ```
  python populate_dogs.py --clear
  ```
- Seed only rescues and users:
  ```
  python populate_dogs.py --seed 1 2
  ```

### Notes
- The script is idempotent: running it multiple times will not create duplicate data.
- Appointment types, medicine presets, and other reference data are also seeded.
- For superadmin creation/editing, use the interactive menu option. 