# Issue Resolution Procedure

This skill outlines the standard operating procedure for resolving GitHub issues in this repository.

## 1. Context Analysis & Branching
- **Analyze**: Carefully read the issue description. Identify the core requirement and any missing context.
- **Branch**: Create a new git branch based on the issue type.
  - Feature: `git checkout -b feature/issue-{id}-{short-desc}`
  - Bugfix: `git checkout -b bugfix/issue-{id}-{short-desc}`
  - Documentation: `git checkout -b docs/issue-{id}-{short-desc}`

## 2. Test-Driven Development (TDD)
- **Design/Test**: Before writing implementation code, create or update a test case in `tests/` that reflects the expected behavior.
  - Use `pytest` and `hypothesis` where applicable.
- **Fail**: Verify the test fails (if it's a new feature or bug).

## 3. Implementation
- **Code**: Write the minimal code necessary to pass the test.
- **Style**: Follow the Google Python Style Guide for docstrings and naming.
- **Refactor**: Optimize the code while keeping tests green.
- **API Docs**: If the change adds or modifies any public method, class, parameter, or type, update the corresponding API reference document:
  - `feems` changes → `docs/api/feems/API_REFERENCE.md`
  - `machinery-system-structure` changes → `docs/api/machinery-system-structure/API_REFERENCE.md`
  - `RunFEEMSSim` changes → `docs/api/RunFEEMSSim/API_REFERENCE.md`

## 4. Verification
- **Virtual Env**: Ensure you are in the correct virtual environment using `source <your-virtual-env>/bin/activate`.
- **Test**: Run `pytest tests` to ensure no regressions.
- **Lint**: Run `ruff check .` to ensure code quality.

## 5. Submission
- **Version & Changelog**: Do **not** manually edit `CHANGELOG.md` or `pyproject.toml` version — both are managed automatically by `release-please` based on conventional commit prefixes (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, etc.). Use the correct prefix in your commit message and the tooling handles the rest.
- **Commit**: Commit changes with a conventional-commit message referencing the issue (e.g., `feat: add chart visualization (#4)`).
- **Push**: Push the branch to origin.
- **Pull Request**: Create a PR against `main`.
  - Link the issue in the PR description (e.g., "Closes #4").
  - Request review.
