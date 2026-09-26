# data/bug_reports.json — CodePilot Bug-Report Dataset

## Purpose

`bug_reports.json` is a small **synthetic, team-created** dataset that externalises the
three developer bug reports that form the starting point of the CodePilot debugging
workflow. It satisfies the hackathon's _bring-your-own-dataset_ requirement by providing
structured input that the runtime application actually reads and displays.

## Origin

All records were written by the CodePilot team. They are based exclusively on the
intentional defects introduced into the **TaskFlow API** for this demonstration.

This dataset contains **no real people's names, no email addresses, no personal
information, no confidential information, no client information, and no data scraped
from any external source.**

## Schema

| Field | Type | Description |
|---|---|---|
| `bug_id` | string | Stable identifier (e.g. `BUG-001`) |
| `title` | string | Short human-readable issue title |
| `description` | string | Full symptom description as a developer would report it |
| `expected_behavior` | string | What the API should do according to its specification |
| `actual_behavior` | string | What the API actually does (the wrong behavior) |
| `affected_area` | string | Architectural layer where the defect lives |
| `affected_file` | string | Repository-relative path to the defective file |
| `affected_function` | string | Name of the function containing the defect |
| `severity` | string | `high` or `medium` — developer-assigned triage severity |
| `status` | string | `fixed` — all three bugs have been resolved |

## Dataset Records

| bug_id | title | affected_file |
|---|---|---|
| BUG-001 | Incorrect project progress calculation | `src/services/project_service.py` |
| BUG-002 | Task status update not persisting | `src/services/task_service.py` |
| BUG-003 | Task filter arguments swapped | `src/api/tasks.py` |

## How CodePilot Uses It

1. `demo/app.py` loads `data/bug_reports.json` at startup via `_load_bug_reports()`.
2. Records are indexed by scenario ID and stored in the module-level `BUG_REPORTS` dict.
3. On the **Investigate** page, when a scenario is selected the application looks up the
   matching dataset record and renders the `bug_id`, `severity`, `status`,
   `expected_behavior`, and `actual_behavior` fields inside the Issue card (step 01).
4. The user can then trace the issue through affected code → source → root cause → fix
   → regression verification — the complete CodePilot workflow.

The dataset therefore acts as the structured bug-report input that anchors the workflow.
It is not a mock of IBM Bob and it does not fabricate any runtime AI behaviour.

## Relationship to the Workflow

```
data/bug_reports.json
        ↓
  Issue card (Investigate page)
        ↓
  Affected Code  (source read from repository)
        ↓
  Root Cause     (documented in SCENARIOS)
        ↓
  Git diff       (real commit b46a2e6)
        ↓
  IBM Bob 2.0 sessions  (bob_sessions/*.png)
        ↓
  Regression Tests      (tests/test_progress.py, tests/test_tasks.py)
        ↓
  Full Test Suite       (41 / 41 passing)
```

## Compliance Notes

- Synthetic / team-created: yes
- Contains personal data: no
- Contains confidential data: no
- External scraping: no
- Consumed by the application: yes (`demo/app.py`)
- Matches existing debugging scenarios: yes (1:1 mapping)
