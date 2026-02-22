# Testing Architecture Visualization

## Testing Pyramid

```
                    /\
                   /  \
                  / E2E \          10% - Critical user flows (12+ tests)
                 /______\          - Playwright browser tests
                /        \         - Complete workflows
               /Validation\        30% - All input validation (75+ tests)
              /____________\       - Parametrized tests
             /              \      - Edge cases & security
            /  Integration   \     30% - Multi-component (10+ tests)
           /__________________\    - API + DB + Services
          /                    \   
         /      Contract        \  30% - API endpoints (15+ tests)
        /________________________\ - Response format validation
```

## Test Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     User Action in Browser                   │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                  Frontend Validation (Optional)              │
│  - HTML5 validation                                          │
│  - HTMX real-time validation                                 │
└───────────────────┬─────────────────────────────────────────┘
                    │                                   ▲
                    ▼                                   │
┌─────────────────────────────────────────────────────┴───────┐
│                  FastAPI Endpoint                            │
│  Layer 1: Pydantic Model Validation ✓                       │
│  Layer 2: Custom Validators ✓                               │
│  Layer 3: Authorization Check ✓                             │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                  Business Logic Layer                        │
│  - Uniqueness checks                                         │
│  - Business rules validation                                 │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                  Database Layer                              │
│  - Database constraints (UNIQUE, NOT NULL, etc.)            │
│  - Foreign key validation                                    │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│                  Response Formatting                         │
│  - HTML escaping (prevent XSS)                              │
│  - JSON serialization                                        │
└─────────────────────────────────────────────────────────────┘
```

## Test Coverage Map

```
┌──────────────────────────────────────────────────────────────┐
│                          Frontend                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              HTML Templates & Forms                  │   │
│  │  - Input fields                                      │   │
│  │  - Buttons & modals                                  │   │
│  │  - HTMX interactions                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                   │
│                           │ E2E Tests (Playwright)           │
│                           ▼                                   │
└──────────────────────────────────────────────────────────────┘
                            │
                            │
┌───────────────────────────┼───────────────────────────────────┐
│                           │           API Layer               │
│  ┌────────────────────────▼────────────────────────────────┐ │
│  │                    API Endpoints                        │ │
│  │  - /api/v1/auth/*     ◄── Contract Tests              │ │
│  │  - /api/v1/projects/* ◄── Validation Tests            │ │
│  │  - /api/v1/keys/*     ◄── Integration Tests           │ │
│  │  - /api/v1/models/*                                    │ │
│  └─────────────────────────────────────────────────────────┘ │
│                           │                                   │
└───────────────────────────┼───────────────────────────────────┘
                            │
                            │
┌───────────────────────────┼───────────────────────────────────┐
│                           │       Business Logic              │
│  ┌────────────────────────▼────────────────────────────────┐ │
│  │                     Services                            │ │
│  │  - ProjectService    ◄── Unit Tests                    │ │
│  │  - AuthService       ◄── Integration Tests             │ │
│  │  - ModelService                                         │ │
│  └─────────────────────────────────────────────────────────┘ │
│                           │                                   │
└───────────────────────────┼───────────────────────────────────┘
                            │
                            │
┌───────────────────────────┼───────────────────────────────────┐
│                           │        Database                   │
│  ┌────────────────────────▼────────────────────────────────┐ │
│  │              SQLAlchemy Models                          │ │
│  │  - User                ◄── Migration Tests             │ │
│  │  - Project             ◄── Constraint Tests            │ │
│  │  - Model                                                │ │
│  │  - APIKey                                               │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

## Test Execution Flow

```
Developer commits code
        │
        ▼
┌─────────────────────┐
│   Pre-commit Hook   │  ◄── Fast tests only (30s)
│   • Contract tests  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Push to GitHub    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────┐
│         CI/CD Pipeline              │
│  ┌─────────────────────────────┐   │
│  │  Stage 1: Fast Tests        │   │
│  │  • Contract tests (~30s)    │   │
│  └─────────────┬───────────────┘   │
│                ▼                    │
│  ┌─────────────────────────────┐   │
│  │  Stage 2: Validation Tests  │   │
│  │  • Input validation (~5min) │   │
│  └─────────────┬───────────────┘   │
│                ▼                    │
│  ┌─────────────────────────────┐   │
│  │  Stage 3: Integration Tests │   │
│  │  • Multi-component (~2min)  │   │
│  └─────────────┬───────────────┘   │
│                ▼                    │
│  ┌─────────────────────────────┐   │
│  │  Stage 4: Coverage Report   │   │
│  │  • Generate report          │   │
│  │  • Fail if < 80%            │   │
│  └─────────────┬───────────────┘   │
└────────────────┼───────────────────┘
                 │
                 ▼
┌─────────────────────────────────────┐
│      Nightly Build (Scheduled)      │
│  ┌─────────────────────────────┐   │
│  │  Full E2E Test Suite        │   │
│  │  • All browsers             │   │
│  │  • Screenshots on failure   │   │
│  │  • ~15 minutes              │   │
│  └─────────────┬───────────────┘   │
└────────────────┼───────────────────┘
                 │
                 ▼
          Notify team of results
```

## Validation Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    User Input: "admin'--"                    │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │  Layer 1: HTML5      │  NO - Server-side bypass
         └──────────────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ Layer 2: Pydantic    │  ✓ REJECT - Invalid format
         │  • Type validation   │
         │  • Length limits     │
         │  • Regex patterns    │
         └──────────────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ Layer 3: Custom      │  ✓ REJECT - Dangerous chars
         │  • SQL injection     │
         │  • XSS prevention    │
         │  • Business rules    │
         └──────────────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ Layer 4: Database    │  ✓ ENFORCE - Constraints
         │  • UNIQUE constraint │
         │  • NOT NULL          │
         │  • Foreign keys      │
         └──────────────────────┘
```

## Test Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    Test Data Factories                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  UserFactory.build()                                 │   │
│  │    ├─ Valid variations                               │   │
│  │    └─ Invalid variations                             │   │
│  │       ├─ Empty username                              │   │
│  │       ├─ Too long                                    │   │
│  │       ├─ SQL injection                               │   │
│  │       └─ XSS payloads                                │   │
│  └──────────────┬───────────────────────────────────────┘   │
└─────────────────┼───────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────┐
│                   Validation Tests                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  @pytest.mark.parametrize("username", [             │   │
│  │      "",                    # Empty                  │   │
│  │      "ab",                  # Too short              │   │
│  │      "a" * 300,             # Too long               │   │
│  │      "admin'--",            # SQL injection          │   │
│  │      "<script>",            # XSS                    │   │
│  │  ])                                                  │   │
│  │  def test_invalid_username(username):               │   │
│  │      response = client.post(..., username=username) │   │
│  │      assert response.status_code == 400             │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Security Testing Coverage

```
┌─────────────────────────────────────────────────────────────┐
│                    Input Attack Vectors                      │
└────┬────────────────────────────────────────────────────┬───┘
     │                                                     │
     │                                                     │
     ▼                                                     ▼
┌─────────────────┐                             ┌─────────────────┐
│  SQL Injection  │                             │       XSS       │
├─────────────────┤                             ├─────────────────┤
│ ' OR '1'='1     │                             │ <script>        │
│ '; DROP TABLE   │                             │ <img onerror>   │
│ admin'--        │                             │ javascript:     │
└────────┬────────┘                             └────────┬────────┘
         │                                                │
         └────────────────┬───────────────────────────────┘
                          │
                          ▼
                ┌──────────────────────┐
                │  Validation Tests    │
                │  75+ test scenarios  │
                └──────────┬───────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌──────────┐   ┌──────────┐   ┌──────────┐
    │ Rejected │   │ Sanitized│   │  Passed  │
    │  (400)   │   │  Escaped │   │  (safe)  │
    └──────────┘   └──────────┘   └──────────┘
```

## Manual QA Workflow

```
┌─────────────────────────────────────────────────────────────┐
│              Open qa-checklist.md                           │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │  Test Authentication │  20 items
         │  [ ] Registration    │
         │  [ ] Login           │
         │  [ ] Logout          │
         └──────────┬───────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │  Test Projects       │  25 items
         │  [ ] Create          │
         │  [ ] Edit            │
         │  [ ] Delete          │
         └──────────┬───────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │  Test API Keys       │  15 items
         │  [ ] Create          │
         │  [ ] Revoke          │
         │  [ ] Use             │
         └──────────┬───────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │  Test Security       │  15 items
         │  [ ] XSS prevention  │
         │  [ ] SQL injection   │
         │  [ ] CSRF            │
         └──────────┬───────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │  Sign off & Deploy   │
         └──────────────────────┘
```

## Command Decision Tree

```
What do you want to test?

├─ Quick sanity check?
│  └─> make test-fast (30s)
│
├─ Testing new validation?
│  └─> make test-validation (5min)
│
├─ Testing user workflow?
│  └─> make test-e2e (10min)
│
├─ Before committing?
│  └─> make test (2min)
│
├─ Before release?
│  └─> make test-full (15min)
│
├─ Need coverage report?
│  └─> make test-coverage
│
└─ Security audit?
   └─> make test-security
```
