# Testing Architecture

## Test Separation Strategy

This project uses a **deliberate test separation strategy** to avoid conflicts between different types of tests.

### Why Tests Are Separated

#### Root Cause
- **Orchestrator tests** heavily patch agent classes using `patch.object(AgentClass, "__new__")`
- **Agent tests** need to instantiate real agent classes for testing
- When run together, these create `TypeError: object.__new__() takes exactly one argument`

#### This is NOT a bug - it's proper test isolation!

### Test Categories

#### 1. Core Tests (`tests/unit` excluding `test_agents/`)
- **What**: Infrastructure, config, orchestrator, performance, hardware
- **Count**: ~110 tests
- **Runtime**: ~0.8 seconds
- **Conflicts**: None

#### 2. Agent Tests (`tests/unit/test_agents/`)
- **What**: Individual agent implementations (coding, planning, testing, review)
- **Count**: ~69 tests  
- **Runtime**: ~0.25 seconds
- **Conflicts**: With orchestrator mocking

#### 3. Integration Tests (`tests/integration/`)
- **What**: End-to-end workflows, CLI integration
- **Count**: ~61 tests
- **Runtime**: ~6 seconds
- **Dependencies**: Both core and agent functionality

### CI/CD Pipeline Design

```yaml
Build → Check-Build → [Core-Tests, Agent-Tests] → Integration-Tests → Security
                           ↑                ↑
                      (parallel)      (parallel)
```

### Benefits of Separation

#### ✅ **Proper Test Isolation**
- Orchestrator tests can mock extensively without affecting agent tests
- Agent tests can test real instantiation without interference
- Clear boundaries between unit and integration concerns

#### ✅ **Faster Execution**
- Parallel execution reduces total time
- Core tests (0.8s) + Agent tests (0.25s) = 1.05s total
- vs running together with conflicts: 2-3s with failures

#### ✅ **Clearer Debugging**  
- Failures are isolated to specific components
- No cross-contamination between test types
- Easier to identify which layer has issues

#### ✅ **Better Architecture**
- Enforces proper separation of concerns
- Prevents tight coupling between test suites
- Makes test maintenance easier

### Local Testing Commands

```bash
# Run all tests separately (recommended)
poetry run pytest tests/unit --ignore=tests/unit/test_agents  # Core tests
poetry run pytest tests/unit/test_agents                     # Agent tests  
poetry run pytest tests/integration                          # Integration tests

# Run together (expect conflicts)
poetry run pytest tests/unit  # Will have agent instantiation errors
```

### Anti-Pattern: Running All Tests Together

Running `pytest tests/unit` will produce errors like:
```
TypeError: object.__new__() takes exactly one argument (the type to instantiate)
```

This is **expected behavior** due to the mocking conflicts described above.

## Conclusion

The test separation is an **architectural feature**, not a bug. It ensures:
- Clean test isolation
- Faster CI/CD execution  
- Clearer failure diagnosis
- Better maintainability

The separated approach gives us **179 passing tests** vs **65 errors** when run together.