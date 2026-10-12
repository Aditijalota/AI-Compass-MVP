"""SQLite persistence for prototype assessments and fictional demo records."""

import json
import copy
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from classification import classify
from classification import effort_input_issues
from classification import pilot_input_issues
from models import PilotObservation
from draft_state import snapshot

DB_PATH = Path(__file__).parent / "data" / "ai_compass.db"

EXAMPLES = [
    {
        "department": "Finance",
        "role": "Accounts payable manager",
        "problem_scale": "Department",
        "rollout_scale": "Department",
        "business_problem": "Staff manually sort routine invoices and flag incomplete submissions.",
        "desired_outcome": "Reduce sorting time while keeping exceptions with the team.",
        "activities": "Review invoice fields, match purchase references, and route mismatches.",
        "manual_work": "Repeated data checks and routing.",
        "frequency": "Daily",
        "tools": "Spreadsheet and finance system",
        "data_types": "Structured rows and invoice PDFs",
        "rules": "Standard fields are checked; mismatches need approval.",
        "exceptions": "Missing fields or mismatched amounts are reviewed by a person.",
        "time_spent": "Several hours per week across the team",
        "business_impact": "Faster review and fewer handoff delays.",
        "security_concerns": "Financial records; only approved systems may be used.",
        "constraints": "Confirm finance system integration and approval requirements.",
    },
    {
        "department": "HR",
        "role": "People operations partner",
        "problem_scale": "Department",
        "rollout_scale": "Organization",
        "business_problem": "Employees spend time searching for answers in approved HR guidance.",
        "desired_outcome": "Help staff find relevant policy sections and know when to contact HR.",
        "activities": "Answer recurring questions and locate the current policy.",
        "manual_work": "Searching multiple policy documents.",
        "frequency": "Several times a day",
        "tools": "Shared drive and HR platform",
        "data_types": "Policy documents and FAQs",
        "rules": "Answers must refer to current approved guidance.",
        "exceptions": "Sensitive or unusual cases are handled by HR.",
        "time_spent": "About one hour each workday",
        "business_impact": "More consistent answers and fewer routine searches.",
        "security_concerns": "HR information may be sensitive; use approved, non-personal documents only.",
        "constraints": "Assign a content owner and a process for updating policy sources.",
    },
    {
        "department": "Customer Service",
        "role": "Support team lead",
        "problem_scale": "Department",
        "rollout_scale": "Department",
        "business_problem": "Agents repeatedly categorize incoming requests and look up standard responses.",
        "desired_outcome": "Help agents respond consistently without sending replies automatically.",
        "activities": "Read a ticket, choose a category, search help content, and draft a response.",
        "manual_work": "Repeated ticket classification and knowledge searches.",
        "frequency": "Every shift",
        "tools": "Ticketing system and help center",
        "data_types": "Support messages and approved help articles",
        "rules": "Certain categories require a human escalation.",
        "exceptions": "Complaints, account issues, and uncertain answers go to a person.",
        "time_spent": "A few minutes per ticket",
        "business_impact": "Less search time and clearer escalation.",
        "security_concerns": "Support messages may contain customer information.",
        "constraints": "Test with fictional tickets before any live system connection.",
    },
]


def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS discovery_drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                payload TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                title TEXT NOT NULL,
                department TEXT NOT NULL,
                role TEXT NOT NULL,
                problem_scale TEXT NOT NULL,
                rollout_scale TEXT NOT NULL,
                solution_pattern TEXT NOT NULL,
                is_example INTEGER NOT NULL DEFAULT 0,
                payload TEXT NOT NULL
            )
            """
        )
        existing = connection.execute(
            "SELECT COUNT(*) FROM assessments WHERE is_example = 1"
        ).fetchone()[0]
        if existing == 0:
            for example in EXAMPLES:
                assessment = classify(
                    example,
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                )
                _save(connection, assessment.to_dict(), is_example=True)


def _save(connection, assessment: dict, is_example: bool = False) -> int:
    stored_assessment = assessment.copy()
    stored_assessment["is_example"] = is_example
    payload = json.dumps(stored_assessment, ensure_ascii=False)
    cursor = connection.execute(
        """
        INSERT INTO assessments (
            created_at, title, department, role, problem_scale, rollout_scale,
            solution_pattern, is_example, payload
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            assessment["created_at"],
            assessment["title"],
            assessment["department"],
            assessment["role"],
            assessment["problem_scale"],
            assessment["rollout_scale"],
            assessment["solution_pattern"],
            1 if is_example else 0,
            payload,
        ),
    )
    return int(cursor.lastrowid)


def save_assessment(assessment: dict) -> int:
    with _connect() as connection:
        return _save(connection, assessment, is_example=bool(assessment.get("is_example", False)))


def list_assessments() -> list[dict]:
    with _connect() as connection:
        rows = connection.execute(
            "SELECT id, payload FROM assessments ORDER BY created_at DESC, id DESC"
        ).fetchall()
    results = []
    for row in rows:
        item = json.loads(row["payload"])
        item["id"] = row["id"]
        results.append(item)
    return results


def get_assessment(assessment_id: int) -> dict | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT id, payload FROM assessments WHERE id = ?",
            (assessment_id,),
        ).fetchone()
    if row is None:
        return None
    item = json.loads(row["payload"])
    item["id"] = row["id"]
    return item


def save_discovery_draft(draft, step, saved_exchanges, demo_path=None, draft_id=None):
    payload = json.dumps(snapshot(draft, step, saved_exchanges, demo_path), ensure_ascii=False)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connect() as connection:
        if draft_id is None:
            cursor = connection.execute(
                "INSERT INTO discovery_drafts (created_at, updated_at, payload) VALUES (?, ?, ?)",
                (now, now, payload),
            )
            return int(cursor.lastrowid)
        cursor = connection.execute(
            "UPDATE discovery_drafts SET updated_at = ?, payload = ? WHERE id = ?",
            (now, payload, draft_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("This saved draft no longer exists. Resume another or start a new discovery.")
    return draft_id


def list_discovery_drafts():
    with _connect() as connection:
        rows = connection.execute(
            "SELECT id, updated_at FROM discovery_drafts ORDER BY updated_at DESC, id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def get_discovery_draft(draft_id):
    with _connect() as connection:
        row = connection.execute(
            "SELECT id, payload FROM discovery_drafts WHERE id = ?", (draft_id,)
        ).fetchone()
    if row is None:
        raise ValueError("This saved draft no longer exists.")
    result = json.loads(row["payload"])
    result["id"] = row["id"]
    return result


def discard_discovery_draft(draft_id):
    with _connect() as connection:
        connection.execute("DELETE FROM discovery_drafts WHERE id = ?", (draft_id,))


def update_effort_assumptions(assessment_id: int, assumptions: dict) -> None:
    """Update only estimate assumptions; preserve discovery, examples, and AI insight."""
    _, errors = effort_input_issues(assumptions)
    if errors:
        raise ValueError(" ".join(errors))
    stored = assumptions.copy()
    stored["confirmed_at"] = (
        datetime.now(timezone.utc).isoformat()
        if stored.get("confirmed") is True else None
    )
    with _connect() as connection:
        row = connection.execute(
            "SELECT payload FROM assessments WHERE id = ?", (assessment_id,)
        ).fetchone()
        if row is None:
            raise ValueError("Assessment no longer exists.")
        payload = json.loads(row["payload"])
        payload["effort_assumptions"] = stored
        connection.execute(
            "UPDATE assessments SET payload = ? WHERE id = ?",
            (json.dumps(payload, ensure_ascii=False), assessment_id),
        )


def update_pilot_observation(assessment_id: int, observation: dict) -> None:
    """Keep observed data separate and pin the scenario on the first pilot save."""
    stored = {key: observation.get(key, default)
              for key, default in PilotObservation().to_dict().items()}
    _, errors = pilot_input_issues(stored)
    if errors:
        raise ValueError(" ".join(errors))
    with _connect() as connection:
        row = connection.execute("SELECT payload FROM assessments WHERE id = ?",
                                 (assessment_id,)).fetchone()
        if row is None:
            raise ValueError("Assessment no longer exists.")
        payload = json.loads(row["payload"])
        previous = payload.get("pilot_observation") or {}
        stored["scenario_assumptions"] = copy.deepcopy(
            previous.get("scenario_assumptions", payload.get("effort_assumptions") or {}))
        stored["scenario_captured_at"] = previous.get(
            "scenario_captured_at", datetime.now(timezone.utc).isoformat())
        stored["recorded_at"] = datetime.now(timezone.utc).isoformat()
        payload["pilot_observation"] = stored
        connection.execute("UPDATE assessments SET payload = ? WHERE id = ?",
                           (json.dumps(payload, ensure_ascii=False), assessment_id))

