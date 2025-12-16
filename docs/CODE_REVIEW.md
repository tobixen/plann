# Code Review: plann

Date: 2025-12-16

## Overview

**Plann** is a command-line CalDAV client for interfacing with calendar servers. The project consists of ~2,688 lines of Python code across 8 core modules and provides CLI-based calendar management with task scheduling and planning features.

- **Language**: Python 3.9+
- **Package Manager**: Poetry (with poetry.lock)
- **Build System**: Both `pyproject.toml` and legacy `setup.py` (needs consolidation)
- **CI/CD**: GitHub Actions for multi-version testing
- **Testing**: pytest with 41 test cases
- **License**: GPL-3.0

## Strengths

1. **Solid Project Structure**: Well-organized modular architecture with clear separation of concerns (cli.py, lib.py, commands.py, config.py, timespec.py, template.py, interactive.py, panic_planning.py)

2. **Modern Python Features**: Uses dataclasses, zoneinfo module for timezone handling

3. **CI/CD Pipeline**: GitHub Actions workflow for automated testing across Python 3.9-3.13

4. **Good Documentation Practices**: Comprehensive README, CHANGELOG follows "Keep a Changelog" format, Semantic Versioning commitment

5. **Testing Infrastructure**: pytest-based test suite with fixtures and mocks, functional tests with xandikos backend

6. **Dependency Management**: Uses poetry.lock for reproducible builds

## Issues and Recommendations

### High Priority

#### 1. Python 2 Legacy Code in config.py

`config.py` uses `raw_input()` which is Python 2 only. This will crash on Python 3.

**Lines affected**: 28, 45, 67, 72

```python
section = raw_input("Chose one of those...")  # Python 2 only!
```

**Also missing imports**:
- `getpass` (used line 42)
- `time` (used line 81)
- `os` (used line 80)

**Fix**: Replace `raw_input()` with `input()` and add missing imports.

#### 2. Dual Build System Confusion

Both `pyproject.toml` (Poetry) and `setup.py` exist with inconsistent metadata:
- `pyproject.toml`: version = "1.1.dev"
- `plann/metadata.py`: version = "1.1.dev1"
- `setup.py`: imports from metadata.py
- `setup.py` includes `tzlocal` but `pyproject.toml` doesn't

**Recommendation**: Remove `setup.py`, consolidate all metadata in `pyproject.toml`.

#### 3. Test Suite Failures

17 of 41 tests are failing. Failed tests include:
- `test_plann` - functional test
- `test_summary` - lib functionality
- `test_add_time_tracking_timew`
- `test_add_set_category`
- `test_procrastinate_without_relations`
- `test_adjust_ical_relations`
- `test_timeline_suggestion`

**Recommendation**: Fix all tests before next release.

#### 4. Missing Type Hints

Almost no type annotations throughout the codebase. Only dataclass definitions have types.

**Recommendation**: Add comprehensive type hints to all public APIs.

#### 5. No Linting Configuration

- No ruff.toml, .flake8, or pylint configuration
- GitHub Actions style checking is COMMENTED OUT
- No formatter (black) configured
- No pre-commit hooks

**Recommendation**: Add ruff configuration:
```toml
[tool.ruff]
line-length = 100
target-version = "py39"
select = ["E", "F", "W", "I", "UP"]
```

### Medium Priority

#### 6. Code Hygiene Issues

- Backup files (.py~) present in source tree
- Commented-out code blocks throughout
- Dead imports (e.g., `#import isodate` in commands.py)
- 50+ TODO comments scattered throughout

**Recommendation**: Clean up backup files, create GitHub issues for TODOs, remove dead code.

#### 7. Version Management Inconsistency

Version defined in three places with different values:
- `pyproject.toml`: "1.1.dev"
- `plann/metadata.py`: "1.1.dev1"

**Recommendation**: Single source of truth for version, consider setuptools-scm.

#### 8. Missing and Unused Imports

- `config.py`: Uses `getpass()`, `time.time()`, `os` without importing
- Several files have unused imports

**Recommendation**: Run ruff to auto-fix import issues.

### Low Priority

#### 9. Documentation Structure

Multiple markdown files at root level (DESIGN.md, NEXT_LEVEL.md, TASK_MANAGEMENT.md, etc.) could be better organized.

**Recommendation**: Move architectural docs to docs/ directory.

#### 10. Test Coverage Not Measured

No coverage reporting configured, no minimum threshold.

**Recommendation**: Add coverage configuration:
```toml
[tool.coverage.run]
source = ["plann"]

[tool.coverage.report]
fail_under = 70
```

#### 11. Entry Points Not Validated

`setup.py` defines console script but `pyproject.toml` doesn't, and no test validates it works.

**Recommendation**: Add entry point to pyproject.toml `[project.scripts]`.

## Summary

### Completed
- Multi-version CI/CD pipeline (Python 3.9-3.13)
- Test infrastructure with pytest
- Basic documentation
- Semantic versioning commitment
- Modular code architecture
- Poetry dependency management

### Remaining (High Priority)
- **Fix Python 2 legacy code** (`raw_input`, missing imports in config.py)
- **Fix test failures** (17 failing tests)
- **Remove setup.py**, consolidate to pyproject.toml only
- **Add type hints** to all modules
- **Configure linting** (ruff) and formatting (black)
- **Enable CI style checking** (currently commented out)

### Remaining (Medium Priority)
- Fix version management inconsistency
- Remove backup files and dead code
- Fix import issues
- Add pre-commit hooks

### Remaining (Low Priority)
- Reorganize documentation structure
- Add test coverage reporting
- Add mypy to CI/CD
- Validate entry points
