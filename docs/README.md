# FEEMS Documentation

This folder contains all project documentation organized by purpose.

## Structure

```
docs/
├── backlog/      # All work items start here — features, bugs, tasks
├── api/          # API reference documentation (auto-generated and manual)
├── 01-plan/      # PDCA Plan phase — requirements, feature specs, user stories
├── 02-design/    # PDCA Design phase — architecture, component design, data models
├── 03-analysis/  # PDCA Check phase — gap analysis, test results, quality reports
└── 04-report/    # PDCA Act phase — iteration reports, release notes, retrospectives
```

## Rule: Everything Starts from the Backlog

**No feature, refactor, or documentation change may begin without a backlog item in `docs/backlog/`.** Bug fixes and hot fixes are exempt and may proceed directly.

Use the `write-backlog` skill (`.github/skills/write-backlog/`) to create a new backlog item.

## PDCA Workflow

```
docs/backlog/   →   01-plan/   →   02-design/   →   [implementation]   →   03-analysis/   →   04-report/
```

| Phase    | Folder          | Contents                                      |
|----------|-----------------|-----------------------------------------------|
| Backlog  | `backlog/`      | Work items with acceptance criteria           |
| Plan     | `01-plan/`      | Feature specs, requirements, user stories     |
| Design   | `02-design/`    | Architecture decisions, component design docs |
| Check    | `03-analysis/`  | Gap analysis, QA reports, coverage results    |
| Act      | `04-report/`    | Completion reports, retrospectives            |

## API Documentation

The `api/` folder contains reference docs for:
- **feems** — core calculation library
- **machinery-system-structure (MachSysS)** — protobuf data interchange
- **RunFEEMSSim** — simulation runner interface
