# CodePilot — AI-Assisted Debugging Workflow

> **Discover. Diagnose. Fix. Verify.**

CodePilot is an AI-assisted developer workflow built using **IBM Bob 2.0** to help developers diagnose and resolve bugs in an unfamiliar codebase.

Instead of treating AI as a simple code generator, CodePilot uses Bob 2.0 across a structured debugging and verification workflow:

```text
Bug Report
    ↓
Repository Analysis
    ↓
Issue Reproduction
    ↓
Root Cause Investigation
    ↓
Minimal Fix
    ↓
Regression Tests
    ↓
Full Test Suite
    ↓
Verification
```

---

## Problem

Debugging an unfamiliar codebase often requires developers to manually:

- understand the repository architecture
- locate relevant files
- trace API → service → repository logic
- reproduce the reported issue
- identify the root cause
- implement a safe fix
- determine whether related issues exist
- write regression tests
- run the complete test suite

This creates additional investigation time and increases the possibility of incomplete fixes or regressions.

---

## Solution

**CodePilot** demonstrates an AI-assisted debugging workflow where **IBM Bob 2.0 works directly with the repository** to investigate issues, reason across multiple layers of the application, implement targeted fixes, and validate the result with automated tests.

The workflow is demonstrated using **TaskFlow API**, a realistic FastAPI task-management backend containing intentionally introduced defects.

The goal is not simply to generate code, but to support the complete developer workflow:

```text
Understand
    ↓
Investigate
    ↓
Fix
    ↓
Test
    ↓
Verify
```

---

# Demonstrated Workflow

## 1. Developer Reports a Bug

Example developer report:

> Project progress is incorrect when a project contains both completed and incomplete tasks.

Instead of immediately changing code, Bob is used to investigate the issue.

## 2. Repository Analysis

Bob analyzes the existing codebase and traces the request through the application layers:

```text
HTTP Request
     ↓
API Layer
     ↓
Service Layer
     ↓
Repository Layer
     ↓
In-Memory Store
```

## 3. Reproduce and Identify Root Cause

For the progress issue, the investigation identified that completed tasks were being counted using the wrong status comparison.

The problematic logic treated non-`DONE` tasks as completed.

The expected behavior was:

```text
completed task
      ↓
status == DONE
      ↓
count as completed
```

Bob identified the root cause and proposed a minimal change.

## 4. Implement the Fix

The production code was updated with targeted changes rather than rewriting unrelated parts of the application.

During full-suite verification, additional related defects were exposed:

- task status updates were not persisting the requested status
- task filtering arguments were incorrectly mapped

These were corrected and verified through the test suite.

## 5. Regression Testing

After the production fixes, Bob reviewed the existing tests and identified important missing edge cases.

Additional regression coverage includes:

- valid `BLOCKED` status
- `DONE` status persistence
- updating a non-existent task
- assigning a non-existent task
- preserving assignee during status updates
- preserving status during assignment
- excluding tasks from other projects
- handling filters with no matches
- excluding unassigned tasks from assignee filtering
- combined project + status filtering

---

# IBM Bob 2.0 Usage

IBM Bob 2.0 was used as an active development partner across multiple stages of the workflow.

### Bob was used for:

- repository-level investigation
- application-flow tracing
- bug reproduction
- root-cause analysis
- targeted production-code fixes
- full test execution
- investigation of additional reported issues
- identification of missing regression coverage
- regression test implementation
- final verification

The project demonstrates Bob working with an actual multi-layer repository rather than generating isolated code snippets.

---

# Evidence of Bob Usage

Bob task-session screenshots are stored in:

```text
bob_sessions/
```

Current evidence includes:

```text
bob_sessions/
├── 01_progress_investigation.png
├── 02_progress_fix_verification.png
├── 03_status_investigation.png
├── 03_assignee_investigation.png
└── 04_regression_tests.png
```

---

# Target Application: TaskFlow API

**TaskFlow API** is a self-contained task and project management backend built with Python and FastAPI.

It provides:

- User management
- Project management
- Project membership
- Task management
- Task assignment
- Task status updates
- Task filtering
- Project progress calculation
- In-memory data storage
- REST API
- Automated tests

No external database or infrastructure is required.

---

# Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend development |
| FastAPI | REST API framework |
| Pydantic | Request/response validation |
| pytest | Automated testing |
| Uvicorn | Development server |
| IBM Bob 2.0 | AI-assisted development workflow |

---

# Architecture

```text
                    ┌───────────────────┐
                    │   HTTP Request    │
                    └─────────┬─────────┘
                              ↓
                    ┌───────────────────┐
                    │    API Layer      │
                    │     FastAPI       │
                    └─────────┬─────────┘
                              ↓
                    ┌───────────────────┐
                    │  Service Layer    │
                    │  Business Logic   │
                    └─────────┬─────────┘
                              ↓
                    ┌───────────────────┐
                    │ Repository Layer  │
                    │   Data Access     │
                    └─────────┬─────────┘
                              ↓
                    ┌───────────────────┐
                    │ In-Memory Storage │
                    └───────────────────┘
```

Detailed architecture: [docs/architecture.md](docs/architecture.md)

API documentation: [docs/api.md](docs/api.md)

---

# Project Structure

```text
CodePilot-IBM-Bob/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── dependencies.py
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   ├── api/
│   └── utils/
├── tests/
│   ├── __init__.py
│   ├── test_users.py
│   ├── test_projects.py
│   ├── test_tasks.py
│   └── test_progress.py
├── docs/
│   ├── architecture.md
│   └── api.md
├── bob_sessions/
│   ├── 01_progress_investigation.png
│   ├── 02_progress_fix_verification.png
│   ├── 03_status_investigation.png
│   ├── 03_assignee_investigation.png
│   └── 04_regression_tests.png
├── requirements.txt
├── .gitignore
└── README.md
```

---

# API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/users` | Create user |
| GET | `/users` | List users |
| GET | `/users/{id}` | Get user |
| POST | `/projects` | Create project |
| GET | `/projects` | List projects |
| GET | `/projects/{id}` | Get project |
| POST | `/projects/{id}/members` | Add project member |
| GET | `/projects/{id}/progress` | Get project progress |
| POST | `/tasks` | Create task |
| GET | `/tasks` | List/filter tasks |
| GET | `/tasks/{id}` | Get task |
| PATCH | `/tasks/{id}/status` | Update task status |
| PUT | `/tasks/{id}/assign` | Assign task |

---

# Task Statuses

| Status | Meaning |
|---|---|
| `TODO` | Not started |
| `IN_PROGRESS` | Currently being worked on |
| `DONE` | Completed |
| `BLOCKED` | Blocked by a dependency |

---

# Installation

```bash
git clone https://github.com/Patelprincekumar2007/CodePilot-IBM-Bob.git
cd CodePilot-IBM-Bob
pip install -r requirements.txt
```

---

# Running the API

```bash
uvicorn src.main:app --reload
```

API:

```text
http://localhost:8000
```

Interactive documentation:

```text
http://localhost:8000/docs
```

---

# Running Tests

```bash
pytest
```

Current verified result:

```text
41 passed
80 warnings
```

All 41 collected tests currently pass.

The warnings are existing `datetime.utcnow()` deprecation warnings and do not cause test failures.

---

# Test Coverage

### Users

- user creation
- duplicate email validation
- invalid email validation
- user retrieval
- missing user handling
- user listing

### Projects

- project creation
- owner validation
- project retrieval
- missing project handling
- project listing
- member management
- invalid member handling
- idempotent member addition

### Tasks

- task creation
- project validation
- assignee validation
- task retrieval
- missing task handling
- task assignment
- status updates
- invalid status handling
- task filtering
- combined filters
- field preservation
- regression scenarios

### Project Progress

- zero tasks
- all TODO tasks
- partially completed projects
- fully completed projects
- missing project handling

---

# Development Evidence

The CodePilot workflow produced the following development sequence:

```text
1. Progress bug investigation
            ↓
2. Progress bug fix and full verification
            ↓
3. Status update investigation
            ↓
4. Assignee/filter investigation
            ↓
5. Regression test analysis
            ↓
6. Additional regression tests
            ↓
7. Full test verification
```

Final verification:

```text
41 / 41 tests passing
```

---

# Developer Workflow

```text
┌──────────────────────┐
│   Developer Bug      │
│       Report         │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ Repository Analysis  │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ Reproduce the Issue  │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ Root Cause Analysis  │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│    Minimal Fix       │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ Regression Tests     │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│ Full Test Suite      │
└──────────┬───────────┘
           ↓
┌──────────────────────┐
│      Verification    │
└──────────────────────┘
```

---

# Project Status

CodePilot currently demonstrates a working AI-assisted debugging workflow using IBM Bob 2.0 on a multi-layer FastAPI codebase.

The prototype has:

- a working backend application
- intentionally introduced debugging scenarios
- Bob-assisted investigations
- targeted production fixes
- regression test improvements
- Bob session evidence
- automated verification
- 41 passing tests

```text
Status: Working Prototype
Test Status: 41 / 41 Passing
```

---

# Team

**CodePilot**

Built for the **IBM Bob 2.0 Hackathon 2026**.
