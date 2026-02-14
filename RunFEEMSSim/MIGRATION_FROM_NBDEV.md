# Migration from nbdev to Pure Python

This document describes the migration of RunFeemsSim from nbdev-based development to standard pure Python development.

## What Changed

### Files Removed

The following nbdev-specific files have been removed:

1. **settings.ini** - nbdev configuration file (removed)
2. **RunFeemsSim/_modidx.py** - nbdev module index (removed)
3. **RunFeemsSim/_nbdev.py** - nbdev utilities (removed)

### Configuration Updated

**pyproject.toml** has been cleaned up:

**Removed**:
```toml
[project.entry-points.nbdev]
RunFeemsSim = "RunFeemsSim._modidx:d"

[tool.nbdev]
nbs_path = '.'
doc_path = 'docs'
branch = 'master'
recursive = false
custom_sidebar = false
title = 'RunFeemsSim'
```

### Files Retained

The following notebook files are still present and can be used as examples/documentation:
- `00_machinery_calculation.ipynb` - Can serve as interactive documentation
- `01_pms_basic.ipynb` - Can serve as interactive examples
- `index.ipynb` - Can serve as introduction

**Note**: These notebooks are now **documentation/examples only**, not source code. The actual source code is in the `.py` files in `RunFeemsSim/` directory.

## Development Workflow

### Before (nbdev)

```bash
# Edit notebooks
jupyter lab

# Export to Python
nbdev_export

# Test
nbdev_test

# Build docs
nbdev_docs

# Prepare for release
nbdev_prepare
```

### After (Pure Python)

```bash
# Edit Python files directly
vim RunFeemsSim/machinery_calculation.py

# Run tests
uv run pytest RunFEEMSSim/tests/

# Lint
uv run ruff check RunFEEMSSim/

# Format
uv run ruff format RunFEEMSSim/

# Type check
uv run mypy RunFeemsSim/

# Build
cd RunFEEMSSim && uv build
```

## Benefits of Pure Python

### 1. **Standard Tooling**
- Works with all standard Python IDEs (PyCharm, VSCode, etc.)
- Full autocomplete and refactoring support
- Integrated debugging

### 2. **Type Safety**
- Full mypy support
- Type hints work properly
- Better IDE assistance

### 3. **Simpler Workflow**
- No export step
- What you see is what runs
- Easier for new contributors

### 4. **Better Version Control**
- Smaller diffs (no notebook metadata changes)
- Easier code review
- Cleaner git history

### 5. **Flexibility**
- Use any Python tooling
- No special syntax or directives
- Standard package structure

## Package Structure

### Current Structure (Pure Python)

```
RunFEEMSSim/
├── RunFeemsSim/              # Source code (editable)
│   ├── __init__.py
│   ├── machinery_calculation.py
│   ├── pms_basic.py
│   └── utils.py
├── tests/                    # Test suite
│   ├── test_machinery_calculation.py
│   └── test_pms_basic.py
├── docs/                     # Documentation
├── 00_machinery_calculation.ipynb  # Example/docs (optional)
├── 01_pms_basic.ipynb             # Example/docs (optional)
├── index.ipynb                    # Introduction (optional)
├── README.md
└── pyproject.toml
```

### Source of Truth

**Before**: Jupyter notebooks in root directory
**After**: Python files in `RunFeemsSim/` directory

## For Contributors

### Making Changes

1. **Edit Python files** in `RunFeemsSim/` directory directly
2. **Add tests** in `tests/` directory
3. **Update documentation** in README.md or docstrings
4. **Run tests and linting** before committing

### Code Quality

```bash
# Check code quality
uv run ruff check RunFEEMSSim/

# Auto-fix issues
uv run ruff check --fix RunFEEMSSim/

# Format code
uv run ruff format RunFEEMSSim/

# Type check (optional but recommended)
uv run mypy RunFeemsSim/

# Run tests with coverage
uv run pytest --cov=RunFeemsSim RunFEEMSSim/tests/
```

### Optional: Using Notebooks for Development

If you prefer notebook-based development:

1. Create/edit notebooks in root directory
2. Manually copy code to `.py` files in `RunFeemsSim/`
3. Ensure tests pass
4. Commit both notebook and Python files

**Important**: The `.py` files are the source of truth, not the notebooks.

## Migration Checklist

- [x] Removed `settings.ini`
- [x] Removed `RunFeemsSim/_modidx.py`
- [x] Removed `RunFeemsSim/_nbdev.py`
- [x] Removed nbdev entry points from `pyproject.toml`
- [x] Removed `[tool.nbdev]` section from `pyproject.toml`
- [x] Updated README.md to reflect pure Python development
- [x] Updated documentation summary
- [ ] Optional: Move notebooks to `examples/` or `docs/` directory
- [ ] Optional: Create new tests if needed
- [ ] Optional: Add type hints to all functions

## Questions?

If you have questions about the migration or pure Python development:

- **GitHub Issues**: https://github.com/SINTEF/FEEMS/issues
- **Email**: kevinkoosup.yum@sintef.no

## Acknowledgments

Thanks to the nbdev framework for providing a great development experience. The migration to pure Python was motivated by:
- Broader tooling support
- Simpler contributor onboarding
- Standard Python ecosystem alignment
