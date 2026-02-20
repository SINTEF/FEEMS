# Write Backlog

This skill defines the standard for creating and maintaining backlog items in `docs/backlog/`.

## Rule: Everything Starts from the Backlog

**No feature, refactor, or documentation change may begin without a backlog item.**
Bug fixes and hot fixes are **exempt** — they may proceed directly without a backlog item.

| Work type       | Backlog required? |
|-----------------|-------------------|
| Feature         | ✅ Yes             |
| Refactor        | ✅ Yes             |
| Documentation   | ✅ Yes             |
| Bug fix         | ❌ No              |
| Hot fix         | ❌ No              |

## Backlog Item Template

Create a file: `docs/backlog/<YYYY-MM-DD>-<short-slug>.md`

```markdown
# [BACKLOG] <Title>

## Summary
One or two sentences describing the goal.

## Context / Motivation
Why is this needed? Link to issues, discussions, or references.

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

## Scope
- **In scope**: ...
- **Out of scope**: ...

## Package(s) Affected
- [ ] feems
- [ ] machinery-system-structure
- [ ] RunFEEMSSim

## Priority
<!-- High / Medium / Low -->

## Issue
<!-- GitHub issue number, e.g. #42 — must be created immediately after this file -->

## Status
<!-- Backlog → Plan → In Progress → Done -->
Backlog

## PDCA Links
- Plan doc: `docs/01-plan/`
- Design doc: `docs/02-design/`
- Analysis: `docs/03-analysis/`
- Report: `docs/04-report/`
```

## Workflow

```
docs/backlog/<item>.md   ← start here (this skill)
       ↓
git checkout main && git pull
git checkout -b feature/issue-{id}-{short-slug}
       ↓
docs/01-plan/            ← PDCA Plan phase
       ↓
docs/02-design/          ← PDCA Design phase
       ↓
 implementation
       ↓
docs/03-analysis/        ← PDCA Check phase
       ↓
docs/04-report/          ← PDCA Act phase  →  git commit (per phase)
       ↓ (all phases done)
git push && open Pull Request → main
```

## Starting Work on a Backlog Item

```bash
# 1. Ensure main is up to date
git checkout main
git pull origin main

# 2. Create and switch to a feature branch
git checkout -b feature/issue-{id}-{short-slug}

# 3. Begin PDCA Plan phase in docs/01-plan/
```

Branch naming:
- Feature / refactor / docs: `feature/issue-{id}-{short-slug}`
- Bug fix: `bugfix/issue-{id}-{short-slug}`
- Hot fix: `hotfix/{short-slug}`

## Multi-Phase Commit Rule

If a feature is divided into phases:
- **Commit after each phase's report** (`docs/04-report/`) is complete
- Commit message format: `feat(#{id}): complete phase {n} — {short description}`
- Do **not** push until the entire feature is done

## Completing a Feature

When all phases are done and all phase commits are in place:

```bash
git push origin feature/issue-{id}-{short-slug}
# Open a Pull Request against main
# - Title: matches the backlog item title
# - Description: links the issue (Closes #{id}) and lists completed phases
```

## Rules

1. **Every backlog item gets its own file** — one file per feature/bug/task.
2. **Filename format**: `YYYY-MM-DD-short-slug.md` (e.g., `2026-02-19-add-battery-component.md`).
3. **Acceptance criteria must be defined** before moving to Plan phase.
4. **Update Status** in the file as the item progresses through PDCA.
6. **Register as a GitHub issue** — after creating the backlog file, immediately open a GitHub issue with the same title and link the issue number in the backlog file (e.g., `Issue: #42`). The issue is the trackable unit; the backlog file is the detailed spec.
