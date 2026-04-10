# Integration Test Suite - Form Flows

This directory contains comprehensive integration tests for HTML form submission flows and HTMX handling.

## Overview

These tests verify that the following features work correctly end-to-end:

1. **Login Form Flow** - Form submission with proper HTTP status codes (303 on success, 401 on invalid)
2. **Project Creation via HTML Form** - Creating projects through HTMX form submission (not JSON API)
3. **Project List HTML Rendering** - Projects display in the list with correct template field mapping
4. **HTMX Response Handling** - Proper HTMX event handling and response types
5. **Form Data Mapping** - Frontend form fields correctly map to backend parameters

## Why These Tests?

These tests were added to catch regressions like those we experienced:
- Login endpoint changed from returning 303 to 200 (HTMX form handling broke)
- Project response model fields didn't match database model (templates crashed on rendering)
- Form parameters (name, visibility) didn't map correctly to backend (ProjectService call failed)
- Template field names (project.name, project.description) didn't exist in model (empty cards displayed)

## Running the Tests

### Prerequisites

1. **Backend server running**: `DATABASE_URL="postgresql://kenji:kenji@localhost:5432/kenji" uvicorn src.backend.main:app --host 0.0.0.0 --port 8000 --reload`

2. **PostgreSQL running**: With `kenji` database, `kenji` user, `kenji` password

3. **Admin user exists**: Run this to create it:
   ```bash
   DATABASE_URL="postgresql://kenji:kenji@localhost:5432/kenji" python3 -c "
   from backend.db import get_engine
   from sqlalchemy.orm import Session
   from backend.services.user_service import UserService
   
   engine = get_engine()
   with Session(engine) as session:
       user_service = UserService(session)
       try:
           user = user_service.create_user(
               username='admin',
               email='admin@local.test',
               password='admin1234',
               display_name='Admin User',
               is_admin=True
           )
           print(f'✓ Admin user created: {user.id}')
       except:
           print('✓ Admin user already exists')
   "
   ```

### Run All Tests

```bash
cd /workspace
source .venv/bin/activate
DATABASE_URL="postgresql://kenji:kenji@localhost:5432/kenji" python -m pytest tests/integration/test_form_flows.py -v
```

### Run Specific Test Class

```bash
# Login tests only
DATABASE_URL="postgresql://kenji:kenji@localhost:5432/kenji" python -m pytest tests/integration/test_form_flows.py::TestLoginFormFlow -v

# Project creation tests
DATABASE_URL="postgresql://kenji:kenji@localhost:5432/kenji" python -m pytest tests/integration/test_form_flows.py::TestProjectCreationFormFlow -v

# Project list rendering tests
DATABASE_URL="postgresql://kenji:kenji@localhost:5432/kenji" python -m pytest tests/integration/test_form_flows.py::TestProjectListHtmlRendering -v

# HTMX response tests
DATABASE_URL="postgresql://kenji:kenji@localhost:5432/kenji" python -m pytest tests/integration/test_form_flows.py::TestHtmxResponseHandling -v

# Form data mapping tests
DATABASE_URL="postgresql://kenji:kenji@localhost:5432/kenji" python -m pytest tests/integration/test_form_flows.py::TestFormDataMapping -v

# Edge case tests
DATABASE_URL="postgresql://kenji:kenji@localhost:5432/kenji" python -m pytest tests/integration/test_form_flows.py::TestEdgeCases -v
```

### Run with Verbose Output

```bash
DATABASE_URL="postgresql://kenji:kenji@localhost:5432/kenji" python -m pytest tests/integration/test_form_flows.py -vv --tb=short
```

## Test Coverage

### TestLoginFormFlow
- ✓ Invalid credentials return 401 (not 200)
- ✓ Valid credentials return 303 redirect (not 302)
- ✓ Access token cookie has HttpOnly flag
- ✓ Email can be used as login identifier

### TestProjectCreationFormFlow
- ✓ Creating project via form returns 201
- ✓ Missing name field returns 400
- ✓ Empty name returns 400
- ✓ Created project appears in list

### TestProjectListHtmlRendering
- ✓ Project titles appear in HTML list
- ✓ JSON response has correct field names (title, not name)
- ✓ Category field displays properly

### TestHtmxResponseHandling
- ✓ Create modal loads without errors
- ✓ Create response is HTML fragment (not JSON)

### TestFormDataMapping
- ✓ Form 'name' field maps to 'title' in database
- ✓ Form 'visibility' field becomes 'category'

### TestEdgeCases
- ✓ Special characters are handled safely
- ✓ Very long project names are validated
- ✓ Multiple projects with same name are allowed (different slugs)

## Troubleshooting

### "Admin user not available"
- Make sure you ran the admin user creation command above
- Verify: `psql kenji -U kenji -c "SELECT username FROM users WHERE username='admin'"`

### "Login still returns 401"
- Frontend and backend might be out of sync
- Restart the backend server: `pkill -f "uvicorn src.backend.main:app"`
- Clear browser cache and try logging in manually to verify it works

### Test runs but shows HTTP errors
- Check backend logs: `tail -f /tmp/backend.log` 
- Verify database connectivity: `psql kenji -U kenji -c "SELECT 1"`

## What These Tests Catch

If you change any of the following, these tests will fail and alert you:

1. **Auth Endpoint** - Change HTTP status codes from 303/401
2. **Project Model** - Change field names or structure
3. **Project Service** - Change parameter names or requirements
4. **Response Models** - Change Pydantic field names
5. **Templates** - Change field names in Jinja2
6. **Form Handling** - Change how HTMX requests are processed
