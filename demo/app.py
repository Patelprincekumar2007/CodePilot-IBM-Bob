"""
CodePilot — AI-Assisted Developer Workflow Dashboard
Demo application for the IBM Bob 2.0 Hackathon.
"""

from __future__ import annotations

import json
import subprocess
import sys
import re
from pathlib import Path

import requests
import streamlit as st

# ── Configuration ────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent.resolve()
FASTAPI_BASE = "http://localhost:8000"

# ── Scenario definitions (real bugs from commit b46a2e6) ─────────────────────

SCENARIOS: dict[str, dict] = {
    "progress_calculation": {
        "title": "Incorrect project progress calculation",
        "short": "Progress % inverted",
        "description": (
            "Project progress percentage is wrong when a project contains both "
            "completed and incomplete tasks. Tasks that are NOT done are counted as "
            "completed, producing an inverted percentage."
        ),
        "file": "src/services/project_service.py",
        "function": "get_progress",
        "root_cause": (
            "In ProjectService.get_progress(), the comprehension used "
            "t.status != TaskStatus.DONE instead of t.status == TaskStatus.DONE. "
            "This counted every task that was not done as 'completed', inverting the result."
        ),
        "buggy_snippet": "completed = sum(1 for t in tasks if t.status != TaskStatus.DONE)",
        "fixed_snippet": "completed = sum(1 for t in tasks if t.status == TaskStatus.DONE)",
        "commit": "b46a2e6",
        "affected_tests": ["tests/test_progress.py"],
    },
    "status_update": {
        "title": "Task status update not persisting",
        "short": "Status update discarded",
        "description": (
            "PATCH /tasks/{id}/status accepts the request and returns 200, but the "
            "task always retains its original status — the new value is never applied."
        ),
        "file": "src/services/task_service.py",
        "function": "update_status",
        "root_cause": (
            "In TaskService.update_status(), the reconstructed Task object was "
            "initialised with status=task.status (the old status) instead of "
            "status=update.status (the requested new status). The update was silently discarded."
        ),
        "buggy_snippet": "status=task.status,   # always restores the original status",
        "fixed_snippet": "status=update.status,  # applies the requested status",
        "commit": "b46a2e6",
        "affected_tests": ["tests/test_tasks.py"],
    },
    "filter_args_swapped": {
        "title": "Task filter arguments swapped",
        "short": "status/assignee_id swapped",
        "description": (
            "GET /tasks?status=DONE filters by assignee_id instead, and "
            "GET /tasks?assignee_id=<id> applies a status filter. "
            "The two query parameters behave as each other."
        ),
        "file": "src/api/tasks.py",
        "function": "list_tasks",
        "root_cause": (
            "In the list_tasks API handler, the call to svc.list_tasks() had the "
            "status and assignee_id keyword arguments swapped: "
            "status=assignee_id, assignee_id=status. Query-parameter values were "
            "forwarded to the wrong service parameters."
        ),
        "buggy_snippet": "return svc.list_tasks(project_id=project_id, status=assignee_id, assignee_id=status)",
        "fixed_snippet": "return svc.list_tasks(project_id=project_id, status=status, assignee_id=assignee_id)",
        "commit": "b46a2e6",
        "affected_tests": ["tests/test_tasks.py"],
    },
}

# ── Bug-report dataset (data/bug_reports.json) ───────────────────────────────
# Synthetic team-created records. Each entry maps to one SCENARIO by bug_id.
# The dataset is loaded once at startup; the application reads it for display.
# BUG_REPORTS: dict keyed by scenario id → dataset record (or empty dict if
# the file is absent, so the app degrades gracefully without the dataset).

_BUG_REPORTS_PATH = REPO_ROOT / "data" / "bug_reports.json"
_BUG_ID_TO_SCENARIO = {"BUG-001": "progress_calculation", "BUG-002": "status_update", "BUG-003": "filter_args_swapped"}

def _load_bug_reports() -> dict[str, dict]:
    try:
        records = json.loads(_BUG_REPORTS_PATH.read_text(encoding="utf-8"))
        return {_BUG_ID_TO_SCENARIO[r["bug_id"]]: r for r in records if r.get("bug_id") in _BUG_ID_TO_SCENARIO}
    except Exception:
        return {}

BUG_REPORTS: dict[str, dict] = _load_bug_reports()

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CodePilot",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* ── Reset & base ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* ── App shell ── */
.stApp {
    background: #0a0c10;
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    font-size: 14px;
    line-height: 1.5;
}

/* ── Hide all Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden !important; height: 0 !important; overflow: hidden !important; }
[data-testid="stToolbar"] { display: none !important; }
.stDeployButton { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
section[data-testid="stSidebar"] button[kind="header"] { display: none !important; }
[data-testid="stSidebarCollapseButton"] { display: none !important; }
div[data-testid="stStatusWidget"] { display: none !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #0d1117 !important;
    border-right: 1px solid #21262d !important;
    min-width: 228px !important;
    max-width: 228px !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 0 !important;
    display: flex;
    flex-direction: column;
    height: 100vh;
}
[data-testid="stSidebarContent"] { padding: 0 !important; }
[data-testid="stSidebar"] .stMarkdown { padding: 0 !important; }

/* ── Sidebar internal spacing fix ── */
[data-testid="stSidebar"] .block-container { padding: 0 !important; }

/* ── Main content ── */
.main .block-container {
    padding: 0 !important;
    max-width: 100% !important;
}

/* ── Remove default Streamlit top padding ── */
[data-testid="stMainBlockContainer"] {
    padding-top: 0 !important;
}
.main > div:first-child {
    padding-top: 0 !important;
}

/* ── Override Streamlit select/input ── */
[data-testid="stSelectbox"] > div > div {
    background: #0d1117 !important;
    border: 1px solid #21262d !important;
    color: #e2e8f0 !important;
    border-radius: 4px !important;
    font-size: 13px !important;
}
[data-testid="stSelectbox"] label {
    font-size: 11px !important;
    font-weight: 600 !important;
    color: #6e7681 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.8px !important;
}

/* ── Spinner ── */
[data-testid="stSpinner"] { color: #3b82f6 !important; }

/* ── Primary button ── */
.stButton > button[kind="primary"] {
    background: #1f6feb !important;
    border: 1px solid #1f6feb !important;
    color: #fff !important;
    border-radius: 4px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 6px 14px !important;
    font-family: inherit !important;
    transition: background 0.1s !important;
}
.stButton > button[kind="primary"]:hover {
    background: #388bfd !important;
    border-color: #388bfd !important;
}

/* ── Default button ── */
.stButton > button {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    color: #c9d1d9 !important;
    border-radius: 4px !important;
    font-size: 12px !important;
    padding: 4px 10px !important;
    width: 100%;
    text-align: left !important;
    font-family: inherit !important;
    transition: background 0.12s, border-color 0.12s !important;
    line-height: 1.4 !important;
    min-height: 28px !important;
}
.stButton > button:hover {
    background: #21262d !important;
    border-color: #8b949e !important;
    color: #e2e8f0 !important;
}

/* ═══════════════════════════════════════
   SIDEBAR COMPONENTS
═══════════════════════════════════════ */

/* Brand block */
.cp-brand {
    padding: 14px 14px 12px;
    border-bottom: 1px solid #21262d;
}
.cp-brand-logo {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 3px;
}
.cp-brand-icon {
    width: 20px;
    height: 20px;
    background: #1f6feb;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.cp-brand-icon svg { display: block; }
.cp-brand-name {
    font-size: 13px;
    font-weight: 600;
    color: #e6edf3;
    letter-spacing: -0.2px;
}
.cp-brand-tagline {
    font-size: 11px;
    color: #484f58;
    padding-left: 1px;
    letter-spacing: 0.1px;
}

/* Nav section */
.cp-nav {
    padding: 8px 6px 4px;
}
.cp-nav-heading {
    font-size: 10px;
    font-weight: 600;
    color: #484f58;
    text-transform: uppercase;
    letter-spacing: 0.9px;
    padding: 0 8px;
    margin-bottom: 2px;
}

/* Nav item wrapper — active state */
.cp-nav-active > button {
    background: #161b22 !important;
    color: #e6edf3 !important;
    border-color: #30363d !important;
    font-weight: 500 !important;
    position: relative;
}
.cp-nav-active > button::before {
    content: "";
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    width: 2px;
    height: 14px;
    background: #1f6feb;
    border-radius: 0 2px 2px 0;
}

/* Sidebar spacer */
.cp-nav-spacer { flex: 1; min-height: 20px; }

/* API footer */
.cp-api-footer {
    padding: 12px 16px 14px;
    border-top: 1px solid #21262d;
}
.cp-api-row {
    display: flex;
    align-items: center;
    gap: 7px;
    margin-bottom: 8px;
}
.cp-api-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
}
.cp-api-on  { background: #3fb950; box-shadow: 0 0 0 2px rgba(63,185,80,.18); }
.cp-api-off { background: #f85149; box-shadow: 0 0 0 2px rgba(248,81,73,.18); }
.cp-api-label {
    font-size: 12px;
    color: #8b949e;
}
.cp-api-service {
    font-size: 12px;
    color: #6e7681;
    font-weight: 500;
}
.cp-api-sep { color: #30363d; margin: 0 4px; }

/* ═══════════════════════════════════════
   PAGE HEADER
═══════════════════════════════════════ */

.cp-header {
    padding: 16px 32px 14px;
    border-bottom: 1px solid #21262d;
    background: #0d1117;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
}
.cp-header-title {
    font-size: 16px;
    font-weight: 600;
    color: #e6edf3;
    letter-spacing: -0.3px;
}
.cp-header-sub {
    font-size: 12px;
    color: #6e7681;
    margin-top: 2px;
}
.cp-header-right {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
}
.cp-status-pill {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: #8b949e;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 20px;
    padding: 3px 10px 3px 8px;
}

/* ═══════════════════════════════════════
   CONTENT WRAPPER
═══════════════════════════════════════ */

.cp-page {
    padding: 20px 32px 32px;
    max-width: 1100px;
}

/* ═══════════════════════════════════════
   TYPOGRAPHY UTILITIES
═══════════════════════════════════════ */

.cp-section-label {
    font-size: 11px;
    font-weight: 600;
    color: #6e7681;
    text-transform: uppercase;
    letter-spacing: 0.9px;
    margin-bottom: 10px;
}
.cp-divider {
    height: 1px;
    background: #21262d;
    margin: 22px 0;
}

/* ═══════════════════════════════════════
   WORKFLOW BAR
═══════════════════════════════════════ */

.cp-flow {
    display: flex;
    border: 1px solid #21262d;
    border-radius: 6px;
    background: #0d1117;
    overflow: hidden;
    margin-bottom: 20px;
}
.cp-flow-step {
    flex: 1;
    padding: 9px 12px;
    border-right: 1px solid #21262d;
    display: flex;
    align-items: center;
    gap: 9px;
    min-width: 0;
    position: relative;
}
.cp-flow-step:last-child { border-right: none; }
.cp-flow-num {
    font-size: 10px;
    font-weight: 700;
    font-family: "SFMono-Regular", Consolas, monospace;
    color: #484f58;
    flex-shrink: 0;
}
.cp-flow-info { flex: 1; min-width: 0; }
.cp-flow-name {
    font-size: 12px;
    font-weight: 500;
    color: #6e7681;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.cp-flow-desc { font-size: 10px; color: #484f58; margin-top: 1px; }
.cp-flow-dot {
    width: 5px; height: 5px;
    border-radius: 50%;
    flex-shrink: 0;
    background: #21262d;
    border: 1px solid #30363d;
}

/* Done: green number + name + filled dot */
.cp-flow-done { background: transparent; }
.cp-flow-done .cp-flow-num  { color: #3fb950; }
.cp-flow-done .cp-flow-name { color: #3fb950; }
.cp-flow-done .cp-flow-desc { color: #238636; }
.cp-flow-done .cp-flow-dot  { background: #3fb950; border-color: #3fb950; }

/* Active: blue accent + left border highlight */
.cp-flow-active { background: #0d1f35; }
.cp-flow-active::before {
    content: "";
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 2px;
    background: #1f6feb;
}
.cp-flow-active .cp-flow-num  { color: #58a6ff; }
.cp-flow-active .cp-flow-name { color: #79c0ff; font-weight: 600; }
.cp-flow-active .cp-flow-desc { color: #388bfd; }
.cp-flow-active .cp-flow-dot  { background: #1f6feb; border-color: #58a6ff; }

/* ═══════════════════════════════════════
   STAT ROW (OVERVIEW)
═══════════════════════════════════════ */

.cp-stats {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0;
    border: 1px solid #21262d;
    border-radius: 6px;
    overflow: hidden;
    margin-bottom: 24px;
    background: #21262d;
}
.cp-stat {
    background: #0d1117;
    padding: 16px 20px;
    border-right: 1px solid #21262d;
}
.cp-stat:last-child { border-right: none; }
.cp-stat-val {
    font-size: 22px;
    font-weight: 600;
    color: #e6edf3;
    line-height: 1;
    font-variant-numeric: tabular-nums;
}
.cp-stat-lbl {
    font-size: 11px;
    color: #6e7681;
    margin-top: 5px;
}
.cp-stat-ok      { color: #3fb950; }
.cp-stat-pending { color: #6e7681; }
.cp-stat-failed  { color: #f85149; }

/* ═══════════════════════════════════════
   BUG / ISSUE LIST
═══════════════════════════════════════ */

.cp-issue-list {
    border: 1px solid #21262d;
    border-radius: 6px;
    overflow: hidden;
    margin-bottom: 16px;
}
.cp-issue-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 11px 14px;
    background: #0d1117;
    border-bottom: 1px solid #21262d;
}
.cp-issue-row:last-child { border-bottom: none; }
.cp-issue-num {
    font-size: 11px;
    font-family: "SFMono-Regular", Consolas, monospace;
    color: #484f58;
    width: 22px;
    flex-shrink: 0;
}
.cp-issue-title {
    flex: 1;
    font-size: 13px;
    font-weight: 500;
    color: #c9d1d9;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.cp-issue-file {
    font-size: 11px;
    color: #484f58;
    font-family: "SFMono-Regular", Consolas, monospace;
    flex-shrink: 0;
}
.cp-badge {
    font-size: 10px;
    font-weight: 600;
    padding: 2px 7px;
    border-radius: 2px;
    letter-spacing: 0.3px;
    flex-shrink: 0;
    text-transform: uppercase;
}
.cp-badge-fixed { background: #12261e; color: #3fb950; border: 1px solid #238636; }
.cp-badge-open  { background: #2d1b1b; color: #f85149; border: 1px solid #6e2929; }

/* ═══════════════════════════════════════
   FIELD / METADATA BLOCKS
═══════════════════════════════════════ */

.cp-field { margin-bottom: 14px; }
.cp-field-label {
    font-size: 10px;
    font-weight: 600;
    color: #6e7681;
    text-transform: uppercase;
    letter-spacing: 0.9px;
    margin-bottom: 5px;
}
.cp-field-text {
    font-size: 13px;
    color: #c9d1d9;
}
.cp-field-mono {
    font-size: 12px;
    color: #79c0ff;
    font-family: "SFMono-Regular", Consolas, monospace;
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 4px;
    padding: 3px 8px;
    display: inline-block;
}
.cp-field-prose {
    font-size: 13px;
    color: #8b949e;
    line-height: 1.65;
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 4px;
    padding: 10px 12px;
}

/* ═══════════════════════════════════════
   CODE VIEWER
═══════════════════════════════════════ */

.cp-code-wrap {
    border: 1px solid #21262d;
    border-radius: 6px;
    overflow: hidden;
    margin-bottom: 16px;
}
.cp-code-header {
    background: #161b22;
    border-bottom: 1px solid #21262d;
    padding: 6px 14px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.cp-code-header-file {
    font-size: 12px;
    font-family: "SFMono-Regular", Consolas, monospace;
    color: #8b949e;
    flex: 1;
}
.cp-code-header-meta {
    font-size: 10px;
    color: #484f58;
    font-family: "SFMono-Regular", Consolas, monospace;
}
.cp-code-header-lang {
    font-size: 10px;
    color: #484f58;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}

/* Root cause */
.cp-root-cause {
    border: 1px solid #21262d;
    border-left: 3px solid #1f6feb;
    background: #0d1117;
    border-radius: 0 4px 4px 0;
    padding: 11px 14px;
    font-size: 13px;
    color: #8b949e;
    line-height: 1.65;
    margin-bottom: 16px;
}
.cp-root-cause code {
    font-family: "SFMono-Regular", Consolas, monospace;
    font-size: 11px;
    color: #79c0ff;
    background: #0a0c10;
    border: 1px solid #21262d;
    border-radius: 3px;
    padding: 0 4px;
}

/* Diff snippets */
.cp-snippet-del {
    background: #1c0e0e;
    border: 1px solid #3d1c1c;
    border-left: 3px solid #f85149;
    border-radius: 0 4px 4px 0;
    padding: 10px 12px;
    font-size: 12px;
    font-family: "SFMono-Regular", Consolas, monospace;
    color: #ffa198;
    word-break: break-all;
}
.cp-snippet-add {
    background: #0c1c10;
    border: 1px solid #1a3b1a;
    border-left: 3px solid #3fb950;
    border-radius: 0 4px 4px 0;
    padding: 10px 12px;
    font-size: 12px;
    font-family: "SFMono-Regular", Consolas, monospace;
    color: #7ee787;
    word-break: break-all;
}

/* ═══════════════════════════════════════
   DIFF VIEWER
═══════════════════════════════════════ */

.cp-diff-wrap {
    border: 1px solid #21262d;
    border-radius: 6px;
    overflow: hidden;
    margin-bottom: 16px;
    font-family: "SFMono-Regular", Consolas, monospace;
    font-size: 12px;
}
.cp-diff-header {
    background: #161b22;
    border-bottom: 1px solid #21262d;
    padding: 6px 14px;
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 12px;
    color: #6e7681;
}
.cp-diff-commit { color: #8b949e; font-weight: 600; }
.cp-diff-body { background: #0a0c10; overflow-x: auto; }
.cp-diff-line { display: block; padding: 1px 14px; white-space: pre; color: #8b949e; line-height: 1.5; }
.cp-diff-del  { background: #1c0e0e; color: #ffa198; }
.cp-diff-add  { background: #0c1c10; color: #7ee787; }
.cp-diff-hunk { color: #1f6feb; }
.cp-diff-meta { color: #484f58; }

/* ═══════════════════════════════════════
   TEST CONSOLE
═══════════════════════════════════════ */

.cp-console {
    border: 1px solid #21262d;
    border-radius: 6px;
    overflow: hidden;
    margin-bottom: 16px;
}
.cp-console-header {
    background: #161b22;
    border-bottom: 1px solid #21262d;
    padding: 6px 14px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.cp-console-dots {
    display: flex;
    gap: 5px;
    flex-shrink: 0;
}
.cp-dot { width: 10px; height: 10px; border-radius: 50%; }
.cp-dot-r { background: #3d1c1c; }
.cp-dot-y { background: #3d3010; }
.cp-dot-g { background: #1a3b1a; }
.cp-console-title {
    font-size: 11px;
    color: #484f58;
    font-family: "SFMono-Regular", Consolas, monospace;
    flex: 1;
    text-align: center;
}
.cp-console-cmd {
    font-size: 12px;
    color: #79c0ff;
    font-family: "SFMono-Regular", Consolas, monospace;
}
.cp-console-body {
    background: #0a0c10;
    padding: 14px 16px;
    font-family: "SFMono-Regular", Consolas, monospace;
    font-size: 12px;
    color: #8b949e;
    max-height: 400px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-all;
    line-height: 1.55;
}

/* Test stats */
.cp-test-stats {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0;
    border: 1px solid #21262d;
    border-radius: 6px;
    overflow: hidden;
    margin-bottom: 16px;
    background: #21262d;
}
.cp-ts { background: #0d1117; padding: 14px 18px; border-right: 1px solid #21262d; }
.cp-ts:last-child { border-right: none; }
.cp-ts-val { font-size: 24px; font-weight: 600; line-height: 1; font-variant-numeric: tabular-nums; }
.cp-ts-lbl { font-size: 11px; color: #6e7681; margin-top: 4px; }
.cp-pass  { color: #3fb950; }
.cp-fail  { color: #f85149; }
.cp-muted { color: #e6edf3; }

/* ═══════════════════════════════════════
   VERIFY PAGE
═══════════════════════════════════════ */

.cp-verify-banner {
    border: 1px solid #238636;
    background: #0c1c10;
    border-radius: 6px;
    padding: 18px 22px;
    margin-bottom: 22px;
    display: flex;
    align-items: center;
    gap: 16px;
}
.cp-verify-check {
    font-size: 18px;
    font-weight: 700;
    color: #3fb950;
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    border: 2px solid #238636;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
}
.cp-verify-title { font-size: 15px; font-weight: 600; color: #3fb950; }
.cp-verify-sub   { font-size: 12px; color: #56d364; margin-top: 2px; }

.cp-verify-banner-fail {
    border-color: #6e2929;
    background: #2d1b1b;
}
.cp-verify-banner-fail .cp-verify-check { color: #f85149; border-color: #6e2929; }
.cp-verify-banner-fail .cp-verify-title { color: #f85149; }
.cp-verify-banner-fail .cp-verify-sub   { color: #ffa198; }

.cp-verify-banner-pending {
    border-color: #30363d;
    background: #0d1117;
}
.cp-verify-banner-pending .cp-verify-check { color: #6e7681; border-color: #30363d; font-size: 14px; }
.cp-verify-banner-pending .cp-verify-title { color: #8b949e; }
.cp-verify-banner-pending .cp-verify-sub   { color: #6e7681; }

/* Evidence chain */
.cp-chain { display: flex; flex-direction: column; }
.cp-chain-node { display: flex; gap: 10px; align-items: flex-start; }
.cp-chain-gutter {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 24px;
    flex-shrink: 0;
    padding-top: 4px;
}
.cp-chain-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #3fb950;
    flex-shrink: 0;
}
.cp-chain-dot-idle { background: #21262d; border: 1px solid #30363d; }
.cp-chain-line {
    width: 1px;
    flex: 1;
    background: #21262d;
    min-height: 18px;
}
.cp-chain-content { flex: 1; padding-bottom: 16px; }
.cp-chain-label {
    font-size: 10px;
    font-weight: 600;
    color: #6e7681;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
.cp-chain-val { font-size: 13px; color: #c9d1d9; margin-top: 2px; }
.cp-chain-mono {
    font-size: 12px;
    color: #79c0ff;
    font-family: "SFMono-Regular", Consolas, monospace;
    margin-top: 2px;
}

/* Evidence table */
.cp-ev-table {
    border: 1px solid #21262d;
    border-radius: 6px;
    overflow: hidden;
    margin-bottom: 20px;
}
.cp-ev-row {
    display: flex;
    padding: 9px 14px;
    border-bottom: 1px solid #21262d;
    font-size: 13px;
    align-items: baseline;
    gap: 8px;
}
.cp-ev-row:last-child { border-bottom: none; }
.cp-ev-key {
    width: 130px;
    flex-shrink: 0;
    font-size: 11px;
    color: #6e7681;
    font-weight: 500;
}
.cp-ev-val { color: #c9d1d9; flex: 1; word-break: break-word; }
.cp-ev-mono {
    color: #79c0ff;
    font-family: "SFMono-Regular", Consolas, monospace;
    font-size: 12px;
}

/* ═══════════════════════════════════════
   NOTICE / INFO BLOCKS
═══════════════════════════════════════ */

.cp-notice {
    background: #161b22;
    border: 1px solid #30363d;
    border-left: 3px solid #d29922;
    border-radius: 0 4px 4px 0;
    padding: 11px 14px;
    font-size: 12px;
    color: #8b949e;
    line-height: 1.65;
}
.cp-notice strong { color: #e3b341; font-weight: 600; }
.cp-notice em     { color: #c9d1d9; font-style: normal; font-weight: 500; }

.cp-info {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 4px;
    padding: 11px 14px;
    font-size: 13px;
    color: #8b949e;
    line-height: 1.6;
    margin-bottom: 16px;
}

/* Bob context block */
.cp-bob-context {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 6px;
    padding: 14px 18px;
    font-size: 13px;
    color: #8b949e;
    line-height: 1.7;
}
.cp-bob-context strong { color: #c9d1d9; font-weight: 600; }
.cp-bob-note {
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px solid #21262d;
    font-size: 12px;
    color: #6e7681;
}
.cp-bob-note strong { color: #8b949e; }

/* Bob session image caption */
.cp-img-caption {
    font-size: 11px;
    color: #484f58;
    font-family: "SFMono-Regular", Consolas, monospace;
    text-align: center;
    margin-top: 5px;
    margin-bottom: 14px;
}

/* Repo name pill */
.cp-repo-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    font-weight: 500;
    color: #79c0ff;
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 4px;
    padding: 4px 10px;
    font-family: "SFMono-Regular", Consolas, monospace;
    margin-bottom: 18px;
}

/* ═══════════════════════════════════════
   INVESTIGATE PAGE
═══════════════════════════════════════ */

/* Step headings (numbered) */
.cp-step {
    display: flex;
    align-items: baseline;
    gap: 10px;
    margin-bottom: 10px;
}
.cp-step-num {
    font-size: 10px;
    font-weight: 700;
    font-family: "SFMono-Regular", Consolas, monospace;
    color: #484f58;
    flex-shrink: 0;
    width: 18px;
}
.cp-step-title {
    font-size: 11px;
    font-weight: 600;
    color: #6e7681;
    text-transform: uppercase;
    letter-spacing: 0.9px;
}

/* Affected code block */
.cp-affected {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 20px;
}
.cp-affected-item {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 4px;
    padding: 10px 12px;
}
.cp-affected-lbl {
    font-size: 10px;
    font-weight: 600;
    color: #6e7681;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 5px;
}
.cp-affected-val {
    font-size: 12px;
    font-family: "SFMono-Regular", Consolas, monospace;
    color: #79c0ff;
}
.cp-affected-sub {
    font-size: 11px;
    color: #484f58;
    margin-top: 3px;
}

/* Issue description card */
.cp-issue-card {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 4px;
    padding: 12px 14px;
    margin-bottom: 20px;
}
.cp-issue-card-title {
    font-size: 14px;
    font-weight: 600;
    color: #c9d1d9;
    margin-bottom: 6px;
    letter-spacing: -0.2px;
}
.cp-issue-card-desc {
    font-size: 13px;
    color: #8b949e;
    line-height: 1.65;
}
.cp-issue-card-meta {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-bottom: 8px;
}
.cp-issue-card-behav {
    margin-top: 10px;
    border-top: 1px solid #21262d;
    padding-top: 8px;
    display: flex;
    flex-direction: column;
    gap: 6px;
}
.cp-issue-card-behav-row {
    display: flex;
    gap: 8px;
    font-size: 12px;
    line-height: 1.5;
}
.cp-issue-card-behav-lbl {
    flex: 0 0 58px;
    font-weight: 600;
    color: #57606a;
    text-transform: uppercase;
    font-size: 10px;
    padding-top: 2px;
}
.cp-issue-card-behav-val {
    color: #8b949e;
    flex: 1;
}

/* Expected vs Actual */
.cp-exp-act {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 20px;
}
.cp-exp-act-col { }
.cp-exp-act-lbl {
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 6px;
}
.cp-exp-act-lbl-del { color: #f85149; }
.cp-exp-act-lbl-add { color: #3fb950; }

/* Investigation flow trace */
.cp-trace {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 16px 18px;
    margin-bottom: 20px;
}
.cp-trace-row {
    display: flex;
    align-items: center;
    gap: 0;
}
.cp-trace-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    flex: 1;
    min-width: 0;
}
.cp-trace-node {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 4px;
    padding: 6px 10px;
    text-align: center;
    width: 100%;
}
.cp-trace-node-active {
    border-color: #f85149;
    background: #1c0e0e;
}
.cp-trace-lbl {
    font-size: 9px;
    font-weight: 600;
    color: #484f58;
    text-transform: uppercase;
    letter-spacing: 0.7px;
    margin-bottom: 3px;
}
.cp-trace-val {
    font-size: 11px;
    font-family: "SFMono-Regular", Consolas, monospace;
    color: #8b949e;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.cp-trace-val-active { color: #ffa198; }
.cp-trace-arrow {
    font-size: 12px;
    color: #30363d;
    flex-shrink: 0;
    padding: 0 4px;
    margin-bottom: 2px;
}

/* ═══════════════════════════════════════
   EVIDENCE PAGE
═══════════════════════════════════════ */

/* Section header with left accent */
.cp-ev-section-hdr {
    font-size: 11px;
    font-weight: 600;
    color: #6e7681;
    text-transform: uppercase;
    letter-spacing: 0.9px;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #21262d;
}

/* Commit metadata card */
.cp-commit-card {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 6px;
    overflow: hidden;
    margin-bottom: 14px;
}
.cp-commit-card-row {
    display: flex;
    align-items: baseline;
    padding: 7px 14px;
    border-bottom: 1px solid #21262d;
    gap: 12px;
}
.cp-commit-card-row:last-child { border-bottom: none; }
.cp-commit-card-key {
    font-size: 11px;
    font-weight: 500;
    color: #6e7681;
    width: 70px;
    flex-shrink: 0;
}
.cp-commit-card-val {
    font-size: 12px;
    color: #c9d1d9;
}
.cp-commit-card-hash {
    font-family: "SFMono-Regular", Consolas, monospace;
    font-size: 12px;
    color: #79c0ff;
}
.cp-commit-card-msg {
    font-size: 12px;
    color: #e6edf3;
    font-style: italic;
}

/* Diff viewer — capped height */
.cp-diff-body-capped {
    background: #0a0c10;
    overflow-x: auto;
    overflow-y: auto;
    max-height: 340px;
}

/* Vertical evidence chain */
.cp-ev-chain {
    display: flex;
    flex-direction: column;
    gap: 0;
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 6px;
    overflow: hidden;
    margin-bottom: 20px;
}
.cp-ev-chain-row {
    display: flex;
    align-items: center;
    padding: 8px 14px;
    border-bottom: 1px solid #21262d;
    gap: 12px;
}
.cp-ev-chain-row:last-child { border-bottom: none; }
.cp-ev-chain-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #3fb950;
    flex-shrink: 0;
}
.cp-ev-chain-lbl {
    font-size: 10px;
    font-weight: 600;
    color: #6e7681;
    text-transform: uppercase;
    letter-spacing: 0.7px;
    width: 140px;
    flex-shrink: 0;
}
.cp-ev-chain-val {
    font-size: 12px;
    color: #c9d1d9;
    flex: 1;
}
.cp-ev-chain-mono {
    font-family: "SFMono-Regular", Consolas, monospace;
    font-size: 11px;
    color: #79c0ff;
}
.cp-ev-chain-sep {
    font-size: 10px;
    color: #484f58;
    padding: 4px 14px 4px 33px;
    border-bottom: 1px solid #21262d;
}

/* Bob session grid */
.cp-bob-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-bottom: 16px;
}
.cp-bob-session-item {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 4px;
    overflow: hidden;
}
.cp-bob-session-meta {
    padding: 7px 10px;
    border-top: 1px solid #21262d;
}
.cp-bob-session-name {
    font-size: 11px;
    font-family: "SFMono-Regular", Consolas, monospace;
    color: #6e7681;
}
.cp-bob-session-purpose {
    font-size: 11px;
    color: #8b949e;
    margin-top: 2px;
}

/* Runtime distinction note */
.cp-runtime-note {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 4px;
    padding: 10px 14px;
    font-size: 12px;
    color: #6e7681;
    line-height: 1.6;
}
.cp-runtime-note strong { color: #8b949e; font-weight: 600; }

/* ═══════════════════════════════════════
   TESTS PAGE
═══════════════════════════════════════ */

/* Command display block */
.cp-cmd-block {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 12px 16px;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.cp-cmd-prefix {
    font-size: 13px;
    font-family: "SFMono-Regular", Consolas, monospace;
    color: #3fb950;
    flex-shrink: 0;
}
.cp-cmd-text {
    font-size: 13px;
    font-family: "SFMono-Regular", Consolas, monospace;
    color: #c9d1d9;
}
.cp-cmd-cwd {
    font-size: 11px;
    font-family: "SFMono-Regular", Consolas, monospace;
    color: #484f58;
    margin-left: auto;
    flex-shrink: 0;
}

/* Result banner */
.cp-result-banner {
    border-radius: 6px;
    padding: 14px 18px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 14px;
}
.cp-result-banner-pass {
    background: #0c1c10;
    border: 1px solid #238636;
}
.cp-result-banner-fail {
    background: #1c0e0e;
    border: 1px solid #6e2929;
}
.cp-result-banner-pending {
    background: #0d1117;
    border: 1px solid #21262d;
}
.cp-result-icon {
    font-size: 16px;
    font-weight: 700;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    font-family: "SFMono-Regular", Consolas, monospace;
}
.cp-result-icon-pass { background: #12261e; border: 2px solid #238636; color: #3fb950; }
.cp-result-icon-fail { background: #2d1b1b; border: 2px solid #6e2929; color: #f85149; }
.cp-result-icon-pend { background: #161b22; border: 2px solid #30363d; color: #484f58; font-size: 12px; }
.cp-result-title {
    font-size: 14px;
    font-weight: 600;
    letter-spacing: -0.2px;
}
.cp-result-title-pass { color: #3fb950; }
.cp-result-title-fail { color: #f85149; }
.cp-result-title-pend { color: #6e7681; }
.cp-result-sub {
    font-size: 12px;
    margin-top: 2px;
}
.cp-result-sub-pass { color: #56d364; }
.cp-result-sub-fail { color: #ffa198; }
.cp-result-sub-pend { color: #484f58; }

/* Test stats row */
.cp-ts-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0;
    border: 1px solid #21262d;
    border-radius: 6px;
    overflow: hidden;
    margin-bottom: 16px;
    background: #21262d;
}
.cp-ts-cell {
    background: #0d1117;
    padding: 12px 16px;
    border-right: 1px solid #21262d;
}
.cp-ts-cell:last-child { border-right: none; }
.cp-ts-num {
    font-size: 22px;
    font-weight: 600;
    line-height: 1;
    font-variant-numeric: tabular-nums;
}
.cp-ts-name { font-size: 11px; color: #6e7681; margin-top: 4px; }

/* Verify transition */
.cp-verify-transition {
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 6px;
    padding: 12px 16px;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 16px;
}
.cp-verify-transition-step {
    font-size: 12px;
    font-weight: 600;
    color: #3fb950;
}
.cp-verify-transition-arrow {
    font-size: 14px;
    color: #30363d;
}
.cp-verify-transition-next {
    font-size: 12px;
    font-weight: 600;
    color: #58a6ff;
}
</style>
""", unsafe_allow_html=True)

# ── Helper functions (unchanged from original) ────────────────────────────────

@st.cache_data(ttl=3600)
def build_repo_tree(root_str: str) -> list[tuple[int, str, str]]:
    root = Path(root_str)
    entries: list[tuple[int, str, str]] = []
    entries.append((0, root.name + "/", "dir"))
    important = [
        ("src/", "dir"), ("src/main.py", "src"), ("src/api/tasks.py", "src"),
        ("src/api/projects.py", "src"), ("src/api/users.py", "src"),
        ("src/services/project_service.py", "src"), ("src/services/task_service.py", "src"),
        ("src/models/task.py", "src"), ("src/repositories/task_repository.py", "src"),
        ("tests/", "dir"), ("tests/test_progress.py", "test"), ("tests/test_tasks.py", "test"),
        ("tests/test_projects.py", "test"), ("tests/test_users.py", "test"),
        ("bob_sessions/", "dir"), ("bob_sessions/01_progress_investigation.png", "misc"),
        ("bob_sessions/02_progress_fix_verification.png", "misc"),
        ("bob_sessions/03_status_investigation.png", "misc"),
        ("bob_sessions/04_regression_tests.png", "misc"),
        ("requirements.txt", "misc"), ("README.md", "misc"),
    ]
    for path_str, kind in important:
        if (root / path_str).exists():
            depth = path_str.count("/") if path_str.endswith("/") else path_str.count("/") + 1
            label = Path(path_str.rstrip("/")).name + ("/" if path_str.endswith("/") else "")
            entries.append((depth, label, kind))
    return entries


def read_source_file(rel_path: str) -> str:
    try:
        return (REPO_ROOT / rel_path).read_text(encoding="utf-8")
    except Exception as exc:
        return f"# Error reading {rel_path}: {exc}"


@st.cache_data(ttl=30)
def check_api_health() -> tuple[bool, str]:
    """Cached 30 s — avoids blocking on every rerender."""
    try:
        resp = requests.get(f"{FASTAPI_BASE}/health", timeout=1)
        if resp.status_code == 200:
            return True, resp.json().get("status", "ok")
        return False, f"HTTP {resp.status_code}"
    except requests.ConnectionError:
        return False, "Connection refused"
    except Exception as exc:
        return False, str(exc)


def get_git_diff_for_commit(commit: str, files: list[str]) -> str:
    try:
        r = subprocess.run(
            ["git", "show", commit, "--", *files],
            capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=10,
        )
        return r.stdout if r.returncode == 0 and r.stdout.strip() else ""
    except Exception:
        return ""


def get_commit_meta(commit: str) -> dict[str, str]:
    """Return commit hash, author, date, and subject for a given ref."""
    try:
        r = subprocess.run(
            ["git", "show", commit, "--no-patch",
             "--format=HASH:%H%nAUTHOR:%an%nDATE:%ad%nMESSAGE:%s", "--date=short"],
            capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=10,
        )
        if r.returncode != 0:
            return {}
        meta: dict[str, str] = {}
        for line in r.stdout.splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                meta[key.strip()] = val.strip()
        return meta
    except Exception:
        return {}


def run_pytest() -> dict:
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short", "--no-header"],
            capture_output=True, text=True, cwd=str(REPO_ROOT), timeout=120,
        )
        output = r.stdout + r.stderr
        passed = failed = errors = 0
        duration = ""
        m = re.search(r"=+ (.+?) in ([\d.]+s) =+", output)
        if m:
            duration = m.group(2)
            for pat, key in [(r"(\d+) passed", "p"), (r"(\d+) failed", "f"), (r"(\d+) error", "e")]:
                mv = re.search(pat, m.group(1))
                if mv:
                    v = int(mv.group(1))
                    if key == "p": passed = v
                    elif key == "f": failed = v
                    else: errors = v
        return {"returncode": r.returncode, "passed": passed, "failed": failed,
                "errors": errors, "duration": duration, "output": output}
    except subprocess.TimeoutExpired:
        return {"returncode": -1, "passed": 0, "failed": 0, "errors": 0,
                "duration": "", "output": "pytest timed out after 120 s."}
    except Exception as exc:
        return {"returncode": -1, "passed": 0, "failed": 0, "errors": 0,
                "duration": "", "output": f"Failed to launch pytest: {exc}"}


def extract_function_lines(source: str, function_name: str) -> tuple[str, int]:
    lines = source.splitlines()
    start = next((i for i, l in enumerate(lines)
                  if re.match(rf"^\s*def {re.escape(function_name)}\s*\(", l)), -1)
    if start == -1:
        return source[:1500], 1
    indent = len(lines[start]) - len(lines[start].lstrip())
    end = start + 1
    while end < len(lines):
        s = lines[end]
        if not s.strip():
            end += 1
            continue
        if len(s) - len(s.lstrip()) <= indent and s.strip().startswith(("def ", "class ")):
            break
        end += 1
    return "\n".join(lines[start:end]), start + 1


# ── Session state ─────────────────────────────────────────────────────────────

for key, val in {
    "page": "overview",
    "selected_scenario": "progress_calculation",
    "test_results": None,
    "api_status": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ── API status (load once per session) ───────────────────────────────────────

if st.session_state.api_status is None:
    st.session_state.api_status = check_api_health()

api_ok, api_msg = st.session_state.api_status

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    # Brand
    st.markdown(
        '<div class="cp-brand">'
        '  <div class="cp-brand-logo">'
        '    <div class="cp-brand-icon">'
        '      <svg width="13" height="13" viewBox="0 0 13 13" fill="none">'
        '        <rect x="1" y="1" width="4" height="4" rx="0.8" fill="white" fill-opacity="0.9"/>'
        '        <rect x="8" y="1" width="4" height="4" rx="0.8" fill="white" fill-opacity="0.5"/>'
        '        <rect x="1" y="8" width="4" height="4" rx="0.8" fill="white" fill-opacity="0.5"/>'
        '        <rect x="8" y="8" width="4" height="4" rx="0.8" fill="white" fill-opacity="0.9"/>'
        '      </svg>'
        '    </div>'
        '    <span class="cp-brand-name">CodePilot</span>'
        '  </div>'
        '  <div class="cp-brand-tagline">AI-Assisted Developer Workflow</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="cp-nav"><div class="cp-nav-heading">Navigation</div></div>',
        unsafe_allow_html=True,
    )

    nav_items = [
        ("overview",    "01  Overview"),
        ("investigate", "02  Investigate"),
        ("evidence",    "03  Evidence"),
        ("tests",       "04  Tests"),
        ("verify",      "05  Verify"),
    ]
    for page_id, page_label in nav_items:
        is_active = st.session_state.page == page_id
        wrapper_class = "cp-nav-active" if is_active else ""
        st.markdown(f'<div class="{wrapper_class}">', unsafe_allow_html=True)
        if st.button(page_label, key=f"nav_{page_id}", use_container_width=True):
            st.session_state.page = page_id
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="cp-nav-spacer"></div>', unsafe_allow_html=True)

    # API status footer
    dot_cls  = "cp-api-on" if api_ok else "cp-api-off"
    api_text = "Online" if api_ok else "Offline"
    st.markdown(
        f'<div class="cp-api-footer">'
        f'  <div class="cp-api-row">'
        f'    <span class="cp-api-dot {dot_cls}"></span>'
        f'    <span class="cp-api-service">TaskFlow API</span>'
        f'    <span class="cp-api-sep">·</span>'
        f'    <span class="cp-api-label">{api_text}</span>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if st.button("Refresh status", key="refresh_api", use_container_width=True):
        check_api_health.clear()
        st.session_state.api_status = check_api_health()
        api_ok, api_msg = st.session_state.api_status
        st.rerun()


# ── Shared helpers ────────────────────────────────────────────────────────────

def page_header(title: str, subtitle: str) -> None:
    dot_cls  = "cp-api-on" if api_ok else "cp-api-off"
    api_text = "Online" if api_ok else "Offline"
    st.markdown(
        f'<div class="cp-header">'
        f'  <div>'
        f'    <div class="cp-header-title">{title}</div>'
        f'    <div class="cp-header-sub">{subtitle}</div>'
        f'  </div>'
        f'  <div class="cp-header-right">'
        f'    <div class="cp-status-pill">'
        f'      <span class="cp-api-dot {dot_cls}"></span>'
        f'      TaskFlow API&nbsp;&nbsp;{api_text}'
        f'    </div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


STAGES = [
    ("01", "Analyze",  "Repository scan"),
    ("02", "Diagnose", "Root cause"),
    ("03", "Evidence", "Git diff"),
    ("04", "Test",     "pytest suite"),
    ("05", "Verify",   "Confirmation"),
]

PAGE_STAGE = {"overview": 0, "investigate": 1, "evidence": 2, "tests": 3, "verify": 4}


def workflow_bar() -> None:
    active = PAGE_STAGE.get(st.session_state.page, 0)
    html = '<div class="cp-flow">'
    for i, (num, name, desc) in enumerate(STAGES):
        if i < active:
            cls = "cp-flow-step cp-flow-done"
        elif i == active:
            cls = "cp-flow-step cp-flow-active"
        else:
            cls = "cp-flow-step"
        html += (
            f'<div class="{cls}">'
            f'  <div class="cp-flow-num">{num}</div>'
            f'  <div class="cp-flow-info">'
            f'    <div class="cp-flow-name">{name}</div>'
            f'    <div class="cp-flow-desc">{desc}</div>'
            f'  </div>'
            f'  <div class="cp-flow-dot"></div>'
            f'</div>'
        )
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE: OVERVIEW
# ═══════════════════════════════════════════════════════════════════

if st.session_state.page == "overview":
    page_header("CodePilot", "AI-Assisted Developer Workflow  ·  IBM Bob 2.0 Hackathon")

    st.markdown('<div class="cp-page">', unsafe_allow_html=True)

    workflow_bar()

    # Repo identity
    n_src   = sum(1 for p in (REPO_ROOT / "src").rglob("*.py") if not p.name.startswith("_"))
    n_tests = sum(1 for _ in (REPO_ROOT / "tests").rglob("test_*.py"))

    # Derive verification status from actual test_results session state
    _tr = st.session_state.test_results
    if _tr is None:
        _vstatus_label = "Pending"
        _vstatus_cls   = "cp-stat-pending"
    elif _tr["failed"] == 0 and _tr["errors"] == 0 and _tr["passed"] > 0:
        _vstatus_label = "Verified"
        _vstatus_cls   = "cp-stat-ok"
    else:
        _vstatus_label = "Failed"
        _vstatus_cls   = "cp-stat-failed"

    st.markdown(
        f'<div class="cp-repo-pill">'
        f'  <svg width="13" height="13" viewBox="0 0 16 16" fill="#79c0ff">'
        f'    <path d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8Z"/>'
        f'  </svg>'
        f'  CodePilot-IBM-Bob'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="cp-stats">'
        f'  <div class="cp-stat"><div class="cp-stat-val">{n_src}</div><div class="cp-stat-lbl">Source modules</div></div>'
        f'  <div class="cp-stat"><div class="cp-stat-val">{n_tests}</div><div class="cp-stat-lbl">Test files</div></div>'
        f'  <div class="cp-stat"><div class="cp-stat-val">{len(SCENARIOS)}</div><div class="cp-stat-lbl">Bugs tracked</div></div>'
        f'  <div class="cp-stat"><div class="cp-stat-val {_vstatus_cls}">{_vstatus_label}</div><div class="cp-stat-lbl">Verification status</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="cp-section-label">Tracked Issues</div>', unsafe_allow_html=True)

    st.markdown('<div class="cp-issue-list">', unsafe_allow_html=True)
    for i, (sid, sc) in enumerate(SCENARIOS.items()):
        st.markdown(
            f'<div class="cp-issue-row">'
            f'  <span class="cp-issue-num">#{i+1:02d}</span>'
            f'  <span class="cp-issue-title">{sc["title"]}</span>'
            f'  <span class="cp-issue-file">{sc["file"]}</span>'
            f'  <span class="cp-badge cp-badge-fixed">fixed</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    # Investigate buttons, one per scenario
    cols = st.columns(len(SCENARIOS))
    for col, (sid, sc) in zip(cols, SCENARIOS.items()):
        with col:
            if st.button(f"Investigate #{list(SCENARIOS.keys()).index(sid)+1}", key=f"inv_{sid}", use_container_width=True):
                st.session_state.selected_scenario = sid
                st.session_state.page = "investigate"
                st.rerun()

    st.markdown('<div class="cp-divider"></div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="cp-notice">'
        '<strong>IBM Bob 2.0 development tool</strong> — '
        'The issues above were identified and fixed using IBM Bob 2.0 working directly against this repository. '
        'Bob is a development assistant; it is not embedded in or running inside this application. '
        'Session screenshots are available on the Evidence page.'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE: INVESTIGATE
# ═══════════════════════════════════════════════════════════════════

elif st.session_state.page == "investigate":
    sc = SCENARIOS[st.session_state.selected_scenario]
    page_header("Investigate", f"Root cause analysis  ·  {sc['short']}")

    st.markdown('<div class="cp-page">', unsafe_allow_html=True)

    workflow_bar()

    # ── Issue selector ────────────────────────────────────────────────
    opts = {sid: s["title"] for sid, s in SCENARIOS.items()}
    selected = st.selectbox(
        "Issue",
        options=list(opts.keys()),
        format_func=lambda k: opts[k],
        index=list(opts.keys()).index(st.session_state.selected_scenario),
        key="scenario_select",
    )
    if selected != st.session_state.selected_scenario:
        st.session_state.selected_scenario = selected
        st.rerun()
    sc = SCENARIOS[selected]

    st.markdown('<div class="cp-divider"></div>', unsafe_allow_html=True)

    # Read actual source once — used by multiple sections below
    source = read_source_file(sc["file"])
    snippet, start_line = extract_function_lines(source, sc["function"])
    buggy_esc  = sc["buggy_snippet"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    fixed_esc  = sc["fixed_snippet"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # ── 1. ISSUE ─────────────────────────────────────────────────────
    st.markdown(
        '<div class="cp-step">'
        '  <span class="cp-step-num">01</span>'
        '  <span class="cp-step-title">Issue</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    _br = BUG_REPORTS.get(selected, {})
    _br_id  = _br.get("bug_id", "")
    _br_sev = _br.get("severity", "")
    _br_exp = _br.get("expected_behavior", "")
    _br_act = _br.get("actual_behavior", "")
    _br_meta = ""
    if _br_id:
        _br_meta = (
            f'  <div class="cp-issue-card-meta">'
            f'    <span class="cp-badge cp-badge-fixed">{_br_id}</span>'
            f'    <span class="cp-badge cp-badge-fixed">severity: {_br_sev}</span>'
            f'    <span class="cp-badge cp-badge-fixed">status: {_br.get("status","")}</span>'
            f'  </div>'
        )
    _br_behav = ""
    if _br_exp or _br_act:
        _br_behav = (
            f'  <div class="cp-issue-card-behav">'
            f'    <div class="cp-issue-card-behav-row">'
            f'      <span class="cp-issue-card-behav-lbl">Expected</span>'
            f'      <span class="cp-issue-card-behav-val">{_br_exp}</span>'
            f'    </div>'
            f'    <div class="cp-issue-card-behav-row">'
            f'      <span class="cp-issue-card-behav-lbl">Actual</span>'
            f'      <span class="cp-issue-card-behav-val">{_br_act}</span>'
            f'    </div>'
            f'  </div>'
        )
    st.markdown(
        f'<div class="cp-issue-card">'
        f'  <div class="cp-issue-card-title">{sc["title"]}</div>'
        f'{_br_meta}'
        f'  <div class="cp-issue-card-desc">{sc["description"]}</div>'
        f'{_br_behav}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── 2. AFFECTED CODE ─────────────────────────────────────────────
    st.markdown(
        '<div class="cp-step">'
        '  <span class="cp-step-num">02</span>'
        '  <span class="cp-step-title">Affected Code</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    # Derive layer label from the file path
    _file = sc["file"]
    if "/api/" in _file:
        _layer = "API layer"
    elif "/services/" in _file:
        _layer = "Service layer"
    elif "/repositories/" in _file:
        _layer = "Repository layer"
    elif "/models/" in _file:
        _layer = "Model layer"
    else:
        _layer = "Application layer"

    st.markdown(
        f'<div class="cp-affected">'
        f'  <div class="cp-affected-item">'
        f'    <div class="cp-affected-lbl">File</div>'
        f'    <div class="cp-affected-val">{sc["file"]}</div>'
        f'    <div class="cp-affected-sub">{_layer}</div>'
        f'  </div>'
        f'  <div class="cp-affected-item">'
        f'    <div class="cp-affected-lbl">Function</div>'
        f'    <div class="cp-affected-val">{sc["function"]}()</div>'
        f'    <div class="cp-affected-sub">line {start_line} in source</div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── 3. SOURCE ────────────────────────────────────────────────────
    st.markdown(
        '<div class="cp-step">'
        '  <span class="cp-step-num">03</span>'
        '  <span class="cp-step-title">Source — read directly from repository</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="cp-code-wrap">'
        f'  <div class="cp-code-header">'
        f'    <span class="cp-code-header-file">{sc["file"]}</span>'
        f'    <span class="cp-code-header-meta">line {start_line}</span>'
        f'    <span class="cp-code-header-lang">python</span>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.code(snippet, language="python")

    # ── 4. ROOT CAUSE ────────────────────────────────────────────────
    st.markdown(
        '<div class="cp-step">'
        '  <span class="cp-step-num">04</span>'
        '  <span class="cp-step-title">Root Cause</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="cp-root-cause">{sc["root_cause"]}</div>',
        unsafe_allow_html=True,
    )

    # ── 5. ACTUAL vs EXPECTED ────────────────────────────────────────
    st.markdown(
        '<div class="cp-step">'
        '  <span class="cp-step-num">05</span>'
        '  <span class="cp-step-title">Actual (buggy) vs Expected (correct)</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="cp-exp-act">'
        f'  <div class="cp-exp-act-col">'
        f'    <div class="cp-exp-act-lbl cp-exp-act-lbl-del">Actual — buggy behavior</div>'
        f'    <div class="cp-snippet-del">{buggy_esc}</div>'
        f'  </div>'
        f'  <div class="cp-exp-act-col">'
        f'    <div class="cp-exp-act-lbl cp-exp-act-lbl-add">Expected — correct behavior</div>'
        f'    <div class="cp-snippet-add">{fixed_esc}</div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── 6. INVESTIGATION FLOW ────────────────────────────────────────
    st.markdown(
        '<div class="cp-step">'
        '  <span class="cp-step-num">06</span>'
        '  <span class="cp-step-title">Investigation Flow</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    # Truncate long values for display in the compact trace nodes
    _repo    = REPO_ROOT.name
    _file_short = sc["file"].split("/")[-1]          # e.g. project_service.py
    _func    = sc["function"] + "()"
    # Extract just the buggy expression — first logical segment before comma or end
    _fault   = sc["buggy_snippet"].split(",")[0].strip()
    if len(_fault) > 36:
        _fault = _fault[:34] + "…"
    _cause_short = sc["root_cause"].split(".")[0].rstrip() + "."

    st.markdown(
        f'<div class="cp-trace">'
        f'  <div class="cp-trace-row">'
        f'    <div class="cp-trace-step">'
        f'      <div class="cp-trace-node">'
        f'        <div class="cp-trace-lbl">Repository</div>'
        f'        <div class="cp-trace-val">{_repo}</div>'
        f'      </div>'
        f'    </div>'
        f'    <div class="cp-trace-arrow">→</div>'
        f'    <div class="cp-trace-step">'
        f'      <div class="cp-trace-node">'
        f'        <div class="cp-trace-lbl">File</div>'
        f'        <div class="cp-trace-val">{_file_short}</div>'
        f'      </div>'
        f'    </div>'
        f'    <div class="cp-trace-arrow">→</div>'
        f'    <div class="cp-trace-step">'
        f'      <div class="cp-trace-node">'
        f'        <div class="cp-trace-lbl">Function</div>'
        f'        <div class="cp-trace-val">{_func}</div>'
        f'      </div>'
        f'    </div>'
        f'    <div class="cp-trace-arrow">→</div>'
        f'    <div class="cp-trace-step">'
        f'      <div class="cp-trace-node cp-trace-node-active">'
        f'        <div class="cp-trace-lbl">Faulty logic</div>'
        f'        <div class="cp-trace-val cp-trace-val-active">{_fault}</div>'
        f'      </div>'
        f'    </div>'
        f'    <div class="cp-trace-arrow">→</div>'
        f'    <div class="cp-trace-step">'
        f'      <div class="cp-trace-node">'
        f'        <div class="cp-trace-lbl">Root cause</div>'
        f'        <div class="cp-trace-val" style="white-space:normal;font-family:inherit;font-size:11px;color:#8b949e;">{_cause_short}</div>'
        f'      </div>'
        f'    </div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="cp-divider"></div>', unsafe_allow_html=True)

    if st.button("View git diff evidence →", type="primary"):
        st.session_state.page = "evidence"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE: EVIDENCE
# ═══════════════════════════════════════════════════════════════════

elif st.session_state.page == "evidence":
    sc = SCENARIOS[st.session_state.selected_scenario]
    page_header("Evidence", "Git commit  ·  diff  ·  IBM Bob 2.0 development sessions")

    st.markdown('<div class="cp-page">', unsafe_allow_html=True)

    workflow_bar()

    # ── 1. GIT EVIDENCE ──────────────────────────────────────────────
    st.markdown('<div class="cp-ev-section-hdr">01  Git Evidence</div>', unsafe_allow_html=True)

    # Fetch real commit metadata
    commit_meta = get_commit_meta(sc["commit"])
    _hash    = commit_meta.get("HASH",    sc["commit"])
    _author  = commit_meta.get("AUTHOR",  "—")
    _date    = commit_meta.get("DATE",    "—")
    _msg     = commit_meta.get("MESSAGE", "—")

    st.markdown(
        f'<div class="cp-commit-card">'
        f'  <div class="cp-commit-card-row">'
        f'    <span class="cp-commit-card-key">Commit</span>'
        f'    <span class="cp-commit-card-hash">{_hash}</span>'
        f'  </div>'
        f'  <div class="cp-commit-card-row">'
        f'    <span class="cp-commit-card-key">Author</span>'
        f'    <span class="cp-commit-card-val">{_author}</span>'
        f'  </div>'
        f'  <div class="cp-commit-card-row">'
        f'    <span class="cp-commit-card-key">Date</span>'
        f'    <span class="cp-commit-card-val">{_date}</span>'
        f'  </div>'
        f'  <div class="cp-commit-card-row">'
        f'    <span class="cp-commit-card-key">Message</span>'
        f'    <span class="cp-commit-card-msg">{_msg}</span>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    raw_diff = get_git_diff_for_commit(sc["commit"], [sc["file"]])
    if raw_diff:
        lines_html = []
        in_hunk = False
        for line in raw_diff.splitlines():
            esc = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if line.startswith(("diff ", "index ", "--- ", "+++ ")):
                lines_html.append(f'<span class="cp-diff-line cp-diff-meta">{esc}</span>')
            elif line.startswith("@@"):
                lines_html.append(f'<span class="cp-diff-line cp-diff-hunk">{esc}</span>')
                in_hunk = True
            elif in_hunk and line.startswith("-"):
                lines_html.append(f'<span class="cp-diff-line cp-diff-del">{esc}</span>')
            elif in_hunk and line.startswith("+"):
                lines_html.append(f'<span class="cp-diff-line cp-diff-add">{esc}</span>')
            elif line.startswith(("commit ", "Author", "Date")):
                lines_html.append(f'<span class="cp-diff-line cp-diff-meta">{esc}</span>')
            else:
                lines_html.append(f'<span class="cp-diff-line">{esc}</span>')

        st.markdown(
            f'<div class="cp-diff-wrap">'
            f'  <div class="cp-diff-header">'
            f'    <span class="cp-diff-commit">{sc["commit"]}</span>'
            f'    <span>{_msg}</span>'
            f'    <span style="margin-left:auto;">{sc["file"]}</span>'
            f'  </div>'
            f'  <div class="cp-diff-body-capped">{"".join(lines_html)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="cp-info">Git diff unavailable — '
            'ensure the .git directory is present and commit b46a2e6 exists.</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="cp-divider"></div>', unsafe_allow_html=True)

    # ── 2. EVIDENCE RELATIONSHIP ─────────────────────────────────────
    st.markdown('<div class="cp-ev-section-hdr">02  Evidence Relationship</div>', unsafe_allow_html=True)

    _file_short = sc["file"].split("/")[-1]
    _test_files = ", ".join(t.split("/")[-1] for t in sc["affected_tests"])

    st.markdown(
        f'<div class="cp-ev-chain">'
        f'  <div class="cp-ev-chain-row">'
        f'    <span class="cp-ev-chain-dot"></span>'
        f'    <span class="cp-ev-chain-lbl">Issue</span>'
        f'    <span class="cp-ev-chain-val">{sc["title"]}</span>'
        f'  </div>'
        f'  <div class="cp-ev-chain-sep">↓</div>'
        f'  <div class="cp-ev-chain-row">'
        f'    <span class="cp-ev-chain-dot"></span>'
        f'    <span class="cp-ev-chain-lbl">Investigated file</span>'
        f'    <span class="cp-ev-chain-val cp-ev-chain-mono">{sc["file"]}</span>'
        f'  </div>'
        f'  <div class="cp-ev-chain-sep">↓</div>'
        f'  <div class="cp-ev-chain-row">'
        f'    <span class="cp-ev-chain-dot"></span>'
        f'    <span class="cp-ev-chain-lbl">Git change</span>'
        f'    <span class="cp-ev-chain-val cp-ev-chain-mono">{sc["commit"]} — {_msg}</span>'
        f'  </div>'
        f'  <div class="cp-ev-chain-sep">↓</div>'
        f'  <div class="cp-ev-chain-row">'
        f'    <span class="cp-ev-chain-dot"></span>'
        f'    <span class="cp-ev-chain-lbl">Bob dev session</span>'
        f'    <span class="cp-ev-chain-val">IBM Bob 2.0 investigation &amp; fix</span>'
        f'  </div>'
        f'  <div class="cp-ev-chain-sep">↓</div>'
        f'  <div class="cp-ev-chain-row">'
        f'    <span class="cp-ev-chain-dot"></span>'
        f'    <span class="cp-ev-chain-lbl">Regression tests</span>'
        f'    <span class="cp-ev-chain-val cp-ev-chain-mono">{_test_files}</span>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="cp-divider"></div>', unsafe_allow_html=True)

    # ── 3. IBM BOB DEVELOPMENT EVIDENCE ──────────────────────────────
    st.markdown('<div class="cp-ev-section-hdr">03  IBM Bob 2.0 — Development Evidence</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="cp-info" style="margin-bottom:14px;">'
        'These session records document how IBM Bob 2.0 was used during development. '
        'Bob investigated the repository, located root causes, implemented fixes, and wrote regression tests.'
        '</div>',
        unsafe_allow_html=True,
    )

    # Session metadata — name to human purpose mapping
    SESSION_PURPOSES: dict[str, str] = {
        "01_progress_investigation":    "Investigating the inverted progress calculation bug",
        "02_progress_fix_verification": "Verifying the progress fix and reviewing the corrected logic",
        "03_status_investigation":      "Investigating the task status update not persisting",
        "03_assignee_investigation":    "Investigating the assignee filter argument swap",
        "04_regression_tests":          "Writing regression tests to prevent recurrence",
    }

    imgs = sorted((REPO_ROOT / "bob_sessions").glob("*.png"))
    if imgs:
        # Build session grid as HTML containers, images via st.image inside columns
        # Use pairs of columns to stay within Streamlit's image rendering
        for row_start in range(0, len(imgs), 2):
            row_imgs = imgs[row_start:row_start + 2]
            cols = st.columns(len(row_imgs))
            for col, p in zip(cols, row_imgs):
                stem = p.stem  # e.g. "01_progress_investigation"
                purpose = SESSION_PURPOSES.get(stem, "IBM Bob 2.0 development session")
                with col:
                    st.markdown('<div class="cp-bob-session-item">', unsafe_allow_html=True)
                    st.image(str(p), use_container_width=True)
                    st.markdown(
                        f'<div class="cp-bob-session-meta">'
                        f'  <div class="cp-bob-session-name">{p.name}</div>'
                        f'  <div class="cp-bob-session-purpose">{purpose}</div>'
                        f'</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
    else:
        st.markdown('<div class="cp-info">No session screenshots found in bob_sessions/</div>',
                    unsafe_allow_html=True)

    st.markdown('<div class="cp-divider"></div>', unsafe_allow_html=True)

    # ── Runtime distinction ───────────────────────────────────────────
    st.markdown(
        '<div class="cp-runtime-note">'
        '<strong>IBM Bob 2.0</strong> was used as the development assistant. '
        'CodePilot\'s runtime verification uses the repository, Git evidence, '
        'FastAPI health check, and pytest directly. '
        'Bob is not embedded in or running inside this application.'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

    if st.button("Run test suite →", type="primary"):
        st.session_state.page = "tests"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE: TESTS
# ═══════════════════════════════════════════════════════════════════

elif st.session_state.page == "tests":
    page_header("Tests", "Real pytest execution  ·  no hardcoded results  ·  no simulated output")

    st.markdown('<div class="cp-page">', unsafe_allow_html=True)

    workflow_bar()

    # ── TEST SUITE header ─────────────────────────────────────────────
    st.markdown('<div class="cp-ev-section-hdr">Test Suite</div>', unsafe_allow_html=True)

    col_cmd, col_btn = st.columns([5, 1])
    with col_cmd:
        st.markdown(
            f'<div class="cp-cmd-block">'
            f'  <span class="cp-cmd-prefix">$</span>'
            f'  <span class="cp-cmd-text">pytest tests/ -v --tb=short --no-header</span>'
            f'  <span class="cp-cmd-cwd">cwd: {REPO_ROOT.name}/</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_btn:
        run_clicked = st.button("Run tests", type="primary", use_container_width=True)

    if run_clicked:
        with st.spinner("Running pytest…"):
            st.session_state.test_results = run_pytest()

    results = st.session_state.test_results

    # ── RESULT banner ─────────────────────────────────────────────────
    st.markdown('<div class="cp-ev-section-hdr" style="margin-top:8px;">Result</div>', unsafe_allow_html=True)

    if results is None:
        st.markdown(
            '<div class="cp-result-banner cp-result-banner-pending">'
            '  <div class="cp-result-icon cp-result-icon-pend">&#8943;</div>'
            '  <div>'
            '    <div class="cp-result-title cp-result-title-pend">TEST SUITE NOT RUN</div>'
            '    <div class="cp-result-sub cp-result-sub-pend">Run the suite to generate verification evidence</div>'
            '  </div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        passed   = results["passed"]
        failed   = results["failed"]
        errors   = results["errors"]
        duration = results["duration"]
        total    = passed + failed + errors
        all_ok   = failed == 0 and errors == 0 and total > 0

        if all_ok:
            _dur_str = f"  ·  {duration}" if duration else ""
            st.markdown(
                f'<div class="cp-result-banner cp-result-banner-pass">'
                f'  <div class="cp-result-icon cp-result-icon-pass">&#10003;</div>'
                f'  <div>'
                f'    <div class="cp-result-title cp-result-title-pass">TEST SUITE PASSED</div>'
                f'    <div class="cp-result-sub cp-result-sub-pass">'
                f'      {passed} passed &nbsp;·&nbsp; 0 failed{_dur_str}'
                f'    </div>'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            _fail_total = failed + errors
            st.markdown(
                f'<div class="cp-result-banner cp-result-banner-fail">'
                f'  <div class="cp-result-icon cp-result-icon-fail">&#10007;</div>'
                f'  <div>'
                f'    <div class="cp-result-title cp-result-title-fail">TEST SUITE FAILED</div>'
                f'    <div class="cp-result-sub cp-result-sub-fail">'
                f'      {passed} passed &nbsp;·&nbsp; {_fail_total} failed / error'
                f'    </div>'
                f'  </div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── TEST SUMMARY metrics ──────────────────────────────────────────
    if results is not None:
        passed   = results["passed"]
        failed   = results["failed"]
        errors   = results["errors"]
        duration = results["duration"]
        total    = passed + failed + errors
        all_ok   = failed == 0 and errors == 0 and total > 0

        err_cls  = "cp-fail" if errors > 0  else "cp-muted"
        fail_cls = "cp-fail" if failed > 0  else "cp-pass"
        pass_cls = "cp-pass"

        st.markdown('<div class="cp-ev-section-hdr">Test Summary</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="cp-ts-row">'
            f'  <div class="cp-ts-cell">'
            f'    <div class="cp-ts-num {pass_cls}">{passed}</div>'
            f'    <div class="cp-ts-name">Passed</div>'
            f'  </div>'
            f'  <div class="cp-ts-cell">'
            f'    <div class="cp-ts-num {fail_cls}">{failed}</div>'
            f'    <div class="cp-ts-name">Failed</div>'
            f'  </div>'
            f'  <div class="cp-ts-cell">'
            f'    <div class="cp-ts-num {err_cls}">{errors}</div>'
            f'    <div class="cp-ts-name">Errors</div>'
            f'  </div>'
            f'  <div class="cp-ts-cell">'
            f'    <div class="cp-ts-num cp-muted" style="font-size:16px">{duration or "—"}</div>'
            f'    <div class="cp-ts-name">Duration</div>'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── TEST OUTPUT ───────────────────────────────────────────────
        status_color = "#3fb950" if all_ok else "#f85149"
        status_text  = "all tests passed" if all_ok else f"{failed + errors} failure(s)"

        # HTML-escape the output to prevent any markup injection
        raw_output = (results["output"]
                      .replace("&", "&amp;")
                      .replace("<", "&lt;")
                      .replace(">", "&gt;"))

        st.markdown('<div class="cp-ev-section-hdr">Test Output</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="cp-console">'
            f'  <div class="cp-console-header">'
            f'    <div class="cp-console-dots">'
            f'      <div class="cp-dot cp-dot-r"></div>'
            f'      <div class="cp-dot cp-dot-y"></div>'
            f'      <div class="cp-dot cp-dot-g"></div>'
            f'    </div>'
            f'    <span class="cp-console-title">pytest stdout / stderr</span>'
            f'    <span style="margin-left:auto;font-size:11px;color:{status_color};">{status_text}</span>'
            f'  </div>'
            f'  <div class="cp-console-body">{raw_output}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="cp-divider"></div>', unsafe_allow_html=True)

        # ── VERIFICATION TRANSITION ───────────────────────────────────
        if all_ok:
            st.markdown(
                '<div class="cp-verify-transition">'
                '  <span class="cp-verify-transition-step">TESTS PASSED</span>'
                '  <span class="cp-verify-transition-arrow">→</span>'
                '  <span class="cp-verify-transition-next">READY FOR VERIFICATION</span>'
                '</div>',
                unsafe_allow_html=True,
            )
            if st.button("Go to Verify →", type="primary"):
                st.session_state.page = "verify"
                st.rerun()
        else:
            if st.button("Go to Verify →"):
                st.session_state.page = "verify"
                st.rerun()

    else:
        st.markdown('<div class="cp-divider"></div>', unsafe_allow_html=True)
        if st.button("Go to Verify →"):
            st.session_state.page = "verify"
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# PAGE: VERIFY
# ═══════════════════════════════════════════════════════════════════

elif st.session_state.page == "verify":
    sc = SCENARIOS[st.session_state.selected_scenario]
    page_header("Verify", "End-to-end verification  ·  automated test confirmation")

    st.markdown('<div class="cp-page">', unsafe_allow_html=True)

    workflow_bar()

    results = st.session_state.test_results
    if results is not None:
        test_ok    = results["failed"] == 0 and results["errors"] == 0 and results["passed"] > 0
        test_label = f"{results['passed']} passed / {results['failed']} failed"
        if results["duration"]:
            test_label += f"  ·  {results['duration']}"
    else:
        test_ok    = None
        test_label = "Not yet executed"

    # ── Verification status banner ──
    if test_ok is True:
        st.markdown(
            '<div class="cp-verify-banner">'
            '  <div class="cp-verify-check">&#10003;</div>'
            '  <div>'
            '    <div class="cp-verify-title">VERIFIED</div>'
            '    <div class="cp-verify-sub">Fix confirmed by automated test suite</div>'
            '  </div>'
            '</div>',
            unsafe_allow_html=True,
        )
    elif test_ok is False:
        st.markdown(
            '<div class="cp-verify-banner cp-verify-banner-fail">'
            '  <div class="cp-verify-check">&#10007;</div>'
            '  <div>'
            '    <div class="cp-verify-title">UNVERIFIED</div>'
            '    <div class="cp-verify-sub">Test failures present — check Tests page</div>'
            '  </div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="cp-verify-banner cp-verify-banner-pending">'
            '  <div class="cp-verify-check" style="font-size:14px;">&#8943;</div>'
            '  <div>'
            '    <div class="cp-verify-title">PENDING</div>'
            '    <div class="cp-verify-sub">Run the test suite to generate a verification result</div>'
            '  </div>'
            '</div>',
            unsafe_allow_html=True,
        )

    col_chain, col_table = st.columns([1, 2])

    with col_chain:
        st.markdown('<div class="cp-section-label">Evidence Chain</div>', unsafe_allow_html=True)
        dot_cls = "cp-chain-dot" if test_ok else "cp-chain-dot-idle"
        chain_steps = [
            ("Issue",      sc["short"],          False),
            ("Root Cause", sc["function"] + "()", True),
            ("Fix",        "commit b46a2e6",      True),
            ("Test",       "pytest tests/ -v",    True),
            ("Verified",   test_label if test_ok else "—", False),
        ]
        html = '<div class="cp-chain">'
        for i, (label, val, mono) in enumerate(chain_steps):
            is_last = i == len(chain_steps) - 1
            d = dot_cls if (test_ok or i < 4) else "cp-chain-dot-idle"
            val_tag = f'<div class="cp-chain-mono">{val}</div>' if mono else f'<div class="cp-chain-val">{val}</div>'
            html += (
                f'<div class="cp-chain-node">'
                f'  <div class="cp-chain-gutter">'
                f'    <div class="cp-chain-dot {d}"></div>'
                + ('' if is_last else '<div class="cp-chain-line"></div>')
                + f'  </div>'
                f'  <div class="cp-chain-content">'
                f'    <div class="cp-chain-label">{label}</div>'
                + val_tag
                + f'  </div>'
                f'</div>'
            )
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

    with col_table:
        st.markdown('<div class="cp-section-label">Evidence Summary</div>', unsafe_allow_html=True)
        api_str = "Online" if api_ok else "Offline / not started"
        rows = [
            ("Issue",         sc["title"],           False),
            ("Affected file", sc["file"],             True),
            ("Root cause",    sc["function"] + "()",  True),
            ("Fix commit",    "b46a2e6",              True),
            ("Test command",  "pytest tests/ -v",     True),
            ("Test result",   test_label,             False),
            ("API status",    api_str,                False),
        ]
        html = '<div class="cp-ev-table">'
        for key, val, mono in rows:
            val_cls = "cp-ev-mono" if mono else "cp-ev-val"
            html += (
                f'<div class="cp-ev-row">'
                f'  <div class="cp-ev-key">{key}</div>'
                f'  <div class="{val_cls}">{val}</div>'
                f'</div>'
            )
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

        if test_ok is None:
            if st.button("Run tests now →", type="primary"):
                st.session_state.page = "tests"
                st.rerun()

    st.markdown('<div class="cp-divider"></div>', unsafe_allow_html=True)

    st.markdown('<div class="cp-section-label">IBM Bob 2.0 Development Context</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="cp-bob-context">'
        '<strong>What IBM Bob 2.0 contributed</strong><br>'
        'IBM Bob 2.0 was used as a development assistant during the creation of this project. '
        'Bob investigated the repository architecture, located the three buggy code paths, '
        'reasoned about root causes across the API, service, and model layers, '
        'implemented minimal targeted fixes, and wrote regression tests to prevent recurrence. '
        'Session screenshots are on the Evidence page.'
        '<div class="cp-bob-note">'
        '<strong>Bob is not embedded in or running inside this application.</strong> '
        'All verification shown above is performed by pytest directly against the repository.'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)


# ── Fallback ──────────────────────────────────────────────────────────────────

else:
    st.session_state.page = "overview"
    st.rerun()
