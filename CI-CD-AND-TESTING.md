# CI/CD and Testing Documentation

This document describes the Continuous Integration/Continuous Deployment (CI/CD) pipeline, linting, and testing setup for the Syllabify project.

---

## Overview

Syllabify uses **GitHub Actions** for CI/CD, ensuring code quality and consistency through automated linting, formatting checks, and testing on every push and pull request.

---

## CI/CD Pipeline

### When CI Runs

The CI pipeline automatically runs on:
- **Pushes** to `dev` and `main` branches
- **Pull requests** targeting `dev` and `main` branches

### CI Jobs

The pipeline consists of two parallel jobs:

#### Backend Job

1. **Setup**: Installs Python 3.11 and dependencies
   - Installs production dependencies from `backend/requirements.txt` (if exists)
   - Installs development dependencies from `backend/requirements-dev.txt`:
     - `ruff` (linter)
     - `pytest` (testing framework)
     - `pytest-cov` (test coverage)

2. **Linting**: Runs `ruff check` on backend source code
   - Only lints Python files (`.py`)
   - Excludes test files from linting
   - Skips if no source code exists

3. **Testing**: Runs `pytest` on backend tests
   - Discovers tests in `backend/tests/` directory
   - Tests must pass for CI to succeed
   - Skips if no test files exist

#### Frontend Job

1. **Setup**: Installs Node.js 20 and dependencies
   - Runs `npm install` in `frontend/` directory
   - Installs all dependencies from `package.json`

2. **Formatting Check**: Runs Prettier format check
   - Checks if code matches Prettier formatting rules
   - Checks `.js`, `.jsx`, `.ts`, `.tsx`, `.json`, `.css`, `.scss`, `.md` files
   - Fails if code is not properly formatted
   - Skips if no source files exist

3. **Linting**: Runs ESLint on frontend source code
   - Lints JavaScript/TypeScript files
   - Uses ESLint recommended rules
   - Configured to work with Prettier (no conflicting rules)
   - Skips if no source files exist

### CI Status Checks

**Both jobs must pass** before a pull request can be merged to `main`. This is enforced through GitHub branch protection rules.

---

## Local Development

We standardize on **Docker** for backend (no venv). Run backend linting and tests inside the backend container.

### Backend (Docker)

#### Setup

From project root:

```bash
docker compose up -d
```

See `docker/README.md` and `backend/README.md`.

#### Running Linter

```bash
# Lint backend code (in container)
docker compose run --rm backend ruff check app/

# Auto-fix linting issues
docker compose run --rm backend ruff check app/ --fix
```

#### Running Tests

```bash
# Run all tests (in container)
docker compose run --rm backend pytest

# Run with coverage
docker compose run --rm backend pytest --cov=app --cov-report=html

# Run specific test file
docker compose run --rm backend pytest tests/test_specific.py -v
```

### Frontend

#### Setup

```bash
cd frontend
npm install
```

#### Formatting Code

```bash
cd frontend
npm run format:check
npm run format
```

#### Running Linter

```bash
cd frontend
npm run lint
npm run lint:fix
```

---

## Code Quality Tools

### Backend: Ruff

**Ruff** is a fast Python linter that replaces Flake8 and other tools.

**Configuration**: Uses default settings. Can be configured via `pyproject.toml` or `ruff.toml` if needed.

**Common Commands**:
- `ruff check backend/` - Check for linting errors
- `ruff check backend/ --fix` - Auto-fix issues
- `ruff format backend/` - Format code (if configured)

### Backend: Pytest

**Pytest** is the testing framework for Python code.

**Test Discovery**:
- Tests must be in files named `test_*.py` or `*_test.py`
- Tests must be in the `backend/tests/` directory
- Test functions must start with `test_`

**Example Test**:
```python
def test_example():
    assert True
```

### Frontend: ESLint

**ESLint** finds and fixes problems in JavaScript/TypeScript code.

**Configuration**: See `frontend/.eslintrc.json`

**Rules**: Uses ESLint recommended rules with Prettier integration to avoid conflicts.

### Frontend: Prettier

**Prettier** enforces consistent code formatting.

**Configuration**: See `frontend/.prettierrc.json`

**Settings**:
- Single quotes
- Semicolons enabled
- 80 character line width
- 2 space indentation
- Trailing commas (ES5 style)

**Ignored Files**: See `frontend/.prettierignore`

---

## Pre-commit Workflow

### Recommended Workflow

Before pushing code, developers should:

1. **Format code**:
   ```bash
   cd frontend && npm run format
   ```

2. **Check linting**:
   ```bash
   # Backend (Docker)
   docker compose run --rm backend ruff check app/

   # Frontend
   cd frontend && npm run lint
   ```

3. **Run tests**:
   ```bash
   docker compose run --rm backend pytest
   ```

4. **Push to `dev`**:
   ```bash
   git push origin dev
   ```

The CI pipeline will automatically verify all checks pass.

---

## Troubleshooting

### CI Failing: Backend Linting Errors

**Problem**: Ruff finds linting errors in Python code.

**Solution**:
```bash
# Run ruff in container
docker compose run --rm backend ruff check app/

# Auto-fix issues where possible
docker compose run --rm backend ruff check app/ --fix

# Fix remaining issues manually, then commit and push
```

### CI Failing: Backend Tests Failing

**Problem**: Pytest finds failing tests.

**Solution**:
```bash
# Run tests in container
docker compose run --rm backend pytest -v

# Fix failing tests, then commit and push
```

### CI Failing: Frontend Formatting Check

**Problem**: Code doesn't match Prettier formatting rules.

**Solution**:
```bash
cd frontend

# Auto-format code
npm run format

# Commit the formatted files
git add .
git commit -m "Format code with Prettier"
git push origin dev
```

### CI Failing: Frontend Linting Errors

**Problem**: ESLint finds linting errors.

**Solution**:
```bash
cd frontend

# See linting errors
npm run lint

# Auto-fix issues where possible
npm run lint:fix

# Fix remaining issues manually, then commit and push
```

### Dependencies Not Found

**Problem**: CI fails because dependencies are missing.

**Solution**:
- **Backend**: Ensure `backend/requirements.txt` and `backend/requirements-dev.txt` include all needed packages (Docker installs both)
- **Frontend**: Ensure `frontend/package.json` has all dependencies in `devDependencies`

---

## Adding New Tests

### Backend Tests

1. Create test file in `backend/tests/`:
   ```python
   # backend/tests/test_new_feature.py
   def test_new_feature():
       # Test implementation
       assert True
   ```

2. Run in container to verify:
   ```bash
   docker compose run --rm backend pytest tests/test_new_feature.py
   ```

3. Push to `dev` - CI will automatically run the test

### Frontend Tests

*Frontend testing framework will be configured when frontend development begins.*

---

## CI/CD Best Practices

1. **Run checks locally** before pushing to avoid CI failures
2. **Keep tests passing** - never push with failing tests
3. **Fix linting issues** immediately - they catch bugs early
4. **Format code consistently** - use Prettier before committing
5. **Write tests** for new features and bug fixes
6. **Keep CI fast** - avoid long-running operations in CI
7. **Check CI status** before requesting PR reviews

---

## Configuration Files

- **CI/CD**: `.github/workflows/ci.yml`
- **Backend linting**: Ruff (default config, can add `pyproject.toml`)
- **Backend testing**: Pytest (default config)
- **Frontend linting**: `frontend/.eslintrc.json`
- **Frontend formatting**: `frontend/.prettierrc.json`
- **Frontend ignore**: `frontend/.prettierignore`
- **Backend dependencies**: `backend/requirements.txt` + `backend/requirements-dev.txt` (Docker)
- **Frontend dependencies**: `frontend/package.json`

---

## Questions?

If you have questions about CI/CD, linting, or testing:
- Check this document first
- Review the `.github/workflows/ci.yml` file
- Ask in the team Discord channel
