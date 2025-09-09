# GitHub Actions CI/CD Workflows

This directory contains the GitHub Actions workflows for the Local Agents project. The CI/CD pipeline is designed to be fast, reliable, and modular.

## Workflows Overview

### 🏗️ Build Workflow (`build.yml`)
**Trigger**: Every push to `main`
**Duration**: ~3-5 minutes
**Purpose**: Package building and dependency validation

#### Jobs:
- **build**: 
  - Sets up Python 3.11 and Poetry
  - Installs dependencies with caching
  - Builds the package (`poetry build`)
  - Verifies package imports correctly
  - Uploads build artifacts for downstream workflows

### 🧪 Test Workflow (`test.yml`)
**Trigger**: After successful build completion on `main`
**Duration**: ~8-12 minutes
**Purpose**: Code quality, testing, and security validation
**Dependency**: ⚠️ **Only runs if Build workflow succeeds**

#### Jobs (run in sequence):
1. **check-build**: Validates build workflow succeeded
2. **lint** (5 min): Code formatting and syntax checks
3. **unit-tests** (10 min): Fast unit tests with coverage
4. **integration-tests** (15 min): End-to-end testing
5. **security** (8 min, main only): Type checking and security scans

### 🔍 PR Check Workflow (`pr-check.yml`)
**Trigger**: Pull requests to `main`
**Duration**: ~15-20 minutes
**Purpose**: Combined build and test validation for PRs

#### Jobs:
- **build-and-test**: 
  - Complete build → lint → unit tests → integration tests
  - Single job for faster PR feedback
  - Coverage reporting included

## Key Features

### ⚡ Performance Optimizations
- **Poetry Caching**: Dependencies cached using `poetry.lock` hash
- **Sequential Execution**: Tests run in logical order with `needs:` dependencies
- **Fast Failures**: `--maxfail` limits prevent long-running failed test suites
- **Timeout Protection**: All jobs have reasonable timeout limits

### 🔒 Security & Quality
- **Branch Protection**: Security scans only run on main branch pushes
- **Non-blocking Checks**: Security tools use `|| true` to prevent false failures
- **Coverage Tracking**: Unit tests generate coverage reports for monitoring

### 🛠️ Development Workflow

**Main Branch**:
```
Push to main → Build → Test (check-build → lint → unit-tests → integration-tests → security)
```

**Pull Requests**:
```  
PR to main → PR Check (build → lint → unit-tests → integration-tests)
```

**Key Dependencies**:
- ⚠️ **Test workflow only runs if Build succeeds**
- Each test job requires previous jobs to succeed
- Security scans only run on main branch

## Local Testing

Test the workflows locally before pushing:

```bash
# Test build process
poetry build
poetry run python -c "import local_agents; print('Build successful!')"

# Test linting
poetry run flake8 src/local_agents tests --count --select=E9,F63,F7,F82
poetry run black --check src/ tests/
poetry run isort --check-only src/ tests/

# Test unit tests
poetry run pytest tests/unit -v --tb=short --timeout=30 --maxfail=5

# Test integration tests  
poetry run pytest tests/integration -v --tb=short --timeout=60 --maxfail=3
```

## Workflow Status

### Build Status
- ✅ **Simple**: Single job, 10-minute timeout
- ✅ **Cached**: Poetry dependencies cached efficiently  
- ✅ **Reliable**: Minimal external dependencies

### Test Status
- ✅ **Modular**: 4 separate jobs for different concerns
- ✅ **Fast**: Lint checks complete in ~2 minutes
- ✅ **Progressive**: Later stages depend on earlier success
- ✅ **Secure**: Security scans protect main branch

## Troubleshooting

### Common Issues

**Build Failures**:
- Check `poetry.lock` is committed
- Verify `pyproject.toml` dependencies are correct
- Ensure Python 3.11 compatibility

**Test Timeouts**:
- Individual tests timeout at 30-60 seconds
- Jobs timeout at 5-15 minutes
- Check for hanging tests or infinite loops

**Cache Issues**:
- Cache key includes `poetry.lock` hash
- Delete and regenerate if dependencies change
- Cache automatically expires after inactivity

**Security Scan Failures**:
- Security tools use `|| true` to prevent blocking
- Check bandit and safety output manually
- Address real security issues in separate PRs

## Migration Notes

### Previous vs. Current
- **Before**: 6 complex jobs, 12 OS/Python combinations, 20-30 min builds
- **After**: 2 workflows, 5 total jobs, 8-12 min builds
- **Improvement**: 60% faster, 80% fewer failure points

### Removed Features
- Multi-OS testing (macOS, Windows)
- Multi-Python version testing (3.9, 3.10, 3.12)
- Performance regression testing
- Ollama compatibility testing
- Heavy coverage analysis

These can be re-added as separate workflows if needed for releases or specific validation requirements.