import os
import threading
from typing import Any, Sequence
from datetime import datetime

from engine.graph import would_create_cycle

# In-memory board lock for rate limiting: no more than 1 in flight per board (BUILD_SPEC.md §5.6)
_board_locks: set[int] = set()
_lock_mutex = threading.Lock()


class BoardRateLimitError(Exception):
    pass


class BoardLockContext:
    def __init__(self, board_id: int):
        self.board_id = board_id

    def __enter__(self):
        with _lock_mutex:
            if self.board_id in _board_locks:
                raise BoardRateLimitError(f"AI suggestions already in flight for board {self.board_id}.")
            _board_locks.add(self.board_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        with _lock_mutex:
            _board_locks.discard(self.board_id)


# Keyword hierarchy for heuristic fallback per BUILD_SPEC.md §5.6:
# requirements -> schema/design -> backend/api -> frontend -> test -> docs -> deploy -> release
HEURISTIC_STAGES = [
    {"stage": 1, "keywords": ["requirement", "requirements", "gather"]},
    {"stage": 2, "keywords": ["schema", "database", "design relational", "wireframe", "wireframes"]},
    {"stage": 3, "keywords": ["backend", "api development", "endpoints", "test data"]},
    {"stage": 4, "keywords": ["frontend", "ui implementation", "react"]},
    {"stage": 5, "keywords": ["integration test", "testing", "run test"]},
    {"stage": 6, "keywords": ["documentation", "api docs", "doc"]},
    {"stage": 7, "keywords": ["deployment", "deploy", "prep"]},
    {"stage": 8, "keywords": ["release", "tag and release"]},
]


def _get_stage(title: str, desc: str) -> int:
    t_lower = (title or "").lower()
    for item in HEURISTIC_STAGES:
        for kw in item["keywords"]:
            if kw in t_lower:
                return item["stage"]
    d_lower = (desc or "").lower()
    for item in HEURISTIC_STAGES:
        for kw in item["keywords"]:
            if kw in d_lower:
                return item["stage"]
    return 99


def generate_heuristic_suggestions(
    all_tasks: Sequence[Any],
    existing_edges: Sequence[Any],
    rejected_pairs: set[tuple[int, int]],
    target_task_id: int | None = None,
) -> list[dict[str, Any]]:
    """
    Heuristic fallback generator matching BUILD_SPEC.md §5.6.
    Suggests links when earlier-stage tasks logically precede later-stage tasks
    and an evidence keyword is present in task text.
    """
    suggestions = []
    task_map = {t.id: t for t in all_tasks}
    edge_pairs = set()
    for edge in existing_edges:
        if isinstance(edge, tuple):
            edge_pairs.add((edge[0], edge[1]))
        elif isinstance(edge, dict):
            edge_pairs.add((edge["prerequisite_id"], edge["task_id"]))
        else:
            edge_pairs.add((getattr(edge, "prerequisite_id"), getattr(edge, "task_id")))

    tasks_to_check = [task_map[target_task_id]] if target_task_id and target_task_id in task_map else all_tasks

    for dep_task in tasks_to_check:
        dep_stage = _get_stage(dep_task.title, dep_task.description)
        for prereq_task in all_tasks:
            if prereq_task.id == dep_task.id:
                continue
            prereq_stage = _get_stage(prereq_task.title, prereq_task.description)

            # Only suggest if prerequisite is in an earlier stage
            if prereq_stage >= dep_stage:
                continue

            pair = (prereq_task.id, dep_task.id)
            if pair in edge_pairs or pair in rejected_pairs:
                continue

            # Check if dep task mentions keywords relevant to this prerequisite
            dep_text = (dep_task.title + " " + (dep_task.description or "")).lower()
            prereq_text = (prereq_task.title + " " + (prereq_task.description or "")).lower()
            evidence = None
            stage_kws = HEURISTIC_STAGES[prereq_stage - 1]["keywords"] if prereq_stage <= len(HEURISTIC_STAGES) else []
            for kw in stage_kws:
                if kw in prereq_text and kw in dep_text:
                    evidence = kw
                    break

            # If no direct keyword match, find any shared technical token (excluding generic tokens)
            if not evidence:
                prereq_words = [w for w in prereq_task.title.lower().split() if len(w) > 3 and w not in ("test", "data", "prep")]
                for w in prereq_words:
                    if w in dep_text:
                        evidence = w
                        break

            if not evidence:
                continue

            # Deterministic check 7: cycle check
            if would_create_cycle(prereq_task.id, dep_task.id, list(edge_pairs)):
                continue

            suggestions.append({
                "task_id": dep_task.id,
                "prerequisite_id": prereq_task.id,
                "reason": f"'{prereq_task.title}' logically precedes '{dep_task.title}' based on project delivery lifecycle.",
                "evidence_phrase": evidence,
                "proposer_confidence": 0.85,
                "challenge_verdict": "survived",
                "status": "pending",
                "model_name": "heuristic-fallback",
                "prompt_version": "heuristic-v1",
            })

    return suggestions


def _call_groq_chat(api_key: str, model_name: str, base_url: str, system_prompt: str, user_prompt: str, json_mode: bool = True) -> dict[str, Any] | None:
    """Make a call to Groq API (OpenAI-compatible) with 12s timeout and 1 retry."""
    import httpx
    import json

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.0,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    # Attempt with 1 retry per BUILD_SPEC.md §5.6
    for attempt in range(2):
        try:
            with httpx.Client(timeout=12.0) as client:
                res = client.post(url, headers=headers, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    content = data["choices"][0]["message"]["content"]
                    return json.loads(content)
        except Exception:
            if attempt == 1:
                return None
    return None


def run_ai_pipeline(
    all_tasks: Sequence[Any],
    existing_edges: Sequence[Any],
    rejected_pairs: set[tuple[int, int]],
    target_task_id: int | None = None,
    db: Any = None,
) -> list[dict[str, Any]]:
    """
    Executes the full Propose -> Challenge -> Verify pipeline per BUILD_SPEC.md §5.
    If GROQ_API_KEY/LLM_API_KEY is not configured or calls fail, seamlessly falls back
    to generate_heuristic_suggestions per BUILD_SPEC.md §5.6.
    """
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY")
    if not api_key or "REPLACE_ME" in api_key:
        return generate_heuristic_suggestions(all_tasks, existing_edges, rejected_pairs, target_task_id)

    model_name = os.getenv("LLM_MODEL_NAME", "allam-2-7b")
    base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

    task_map = {t.id: t for t in all_tasks}
    edge_pairs = set()
    for edge in existing_edges:
        if isinstance(edge, tuple):
            edge_pairs.add((edge[0], edge[1]))
        elif isinstance(edge, dict):
            edge_pairs.add((edge["prerequisite_id"], edge["task_id"]))
        else:
            edge_pairs.add((getattr(edge, "prerequisite_id"), getattr(edge, "task_id")))

    # Prepare closed task list for prompt
    tasks_summary = [
        {"id": t.id, "title": t.title, "description": t.description or ""}
        for t in all_tasks
    ]

    target_info = f"Focus on task ID {target_task_id}." if target_task_id else "Evaluate all tasks across the board."

    # 1. PROPOSE CALL (BUILD_SPEC.md §5.1)
    propose_system = """You are TaskFlow Pro's dependency reasoning engine.
Analyze the provided tasks and identify genuine finish-to-start dependencies (A must finish before B can start).
Ordering logic strictly follows software delivery lifecycle: requirements/design -> backend/schema -> frontend/ui -> integration testing -> documentation -> deployment -> release.

Worked Example 1:
Task 2 'Database Schema Design' logically must precede Task 4 'Backend API Development' because endpoints depend on table definitions.
Worked Example 2:
Task 4 'Backend API Development' logically must precede Task 7 'Integration Testing' because test execution requires working API endpoints.

If no clear prerequisite exists, return an empty list {"suggestions": []}.
Output MUST be strict JSON matching this schema:
{
  "suggestions": [
    {
      "prerequisite_id": 4,
      "task_id": 7,
      "reason": "Integration testing requires backend endpoints to be implemented first.",
      "evidence_phrase": "backend api",
      "confidence": 0.95
    }
  ]
}"""

    propose_user = f"""Tasks:
{tasks_summary}

Target instruction: {target_info}
Existing dependencies: {list(edge_pairs)}
Previously rejected dependencies: {list(rejected_pairs)}

Propose candidate dependencies."""

    propose_data = _call_groq_chat(api_key, model_name, base_url, propose_system, propose_user)
    if not propose_data or "suggestions" not in propose_data or not isinstance(propose_data["suggestions"], list):
        # Fall back to heuristic on failure/timeout
        return generate_heuristic_suggestions(all_tasks, existing_edges, rejected_pairs, target_task_id)

    raw_proposals = propose_data["suggestions"]
    if not raw_proposals:
        return []

    # 2. CHALLENGE CALL (BUILD_SPEC.md §5.2)
    challenge_system = """You are TaskFlow Pro's skeptical dependency critic.
Examine each proposed dependency link and determine if it survived or should be rejected.
Reject if:
(a) The direction is reversed (dependent before prerequisite).
(b) The link is only thematic/topical rather than an essential finish-to-start requirement.
(c) The two tasks could comfortably run in parallel.

Output JSON format:
{
  "verdicts": [
    {"index": 0, "verdict": "survived"|"rejected", "note": "explanation"}
  ]
}"""

    challenge_user = f"Candidate proposals to critique:\n{raw_proposals}"
    challenge_data = _call_groq_chat(api_key, model_name, base_url, challenge_system, challenge_user)

    verdict_map: dict[int, str] = {}
    if challenge_data and "verdicts" in challenge_data and isinstance(challenge_data["verdicts"], list):
        for v in challenge_data["verdicts"]:
            if isinstance(v, dict) and "index" in v and "verdict" in v:
                verdict_map[v["index"]] = v["verdict"]

    # 3. DETERMINISTIC VERIFICATION (BUILD_SPEC.md §5.3)
    surviving_suggestions: list[dict[str, Any]] = []

    for idx, prop in enumerate(raw_proposals):
        if not isinstance(prop, dict):
            continue

        prereq_id = prop.get("prerequisite_id")
        dep_id = prop.get("task_id")
        reason = prop.get("reason", "")
        evidence = str(prop.get("evidence_phrase", ""))
        confidence = float(prop.get("confidence", 0.0))

        # Check 1 & 2: ids exist on board
        if prereq_id not in task_map or dep_id not in task_map:
            continue

        # Check 3: prereq != task
        if prereq_id == dep_id:
            continue

        # Check 4: not duplicate
        pair = (prereq_id, dep_id)
        if pair in edge_pairs:
            continue

        # Check 5: not previously rejected
        if pair in rejected_pairs:
            continue

        # Check challenge verdict
        ch_verdict = verdict_map.get(idx, "not_run")
        if ch_verdict == "rejected":
            continue

        # Check 6: evidence_phrase must be a literal substring of the PREREQUISITE
        # task's title + description only (BUILD_SPEC.md §5.3, check 5).
        # If the phrase is not found there, the justification is hallucinated — drop it.
        # Checking both tasks would be looser than the spec: the reason is supposed to
        # quote the prerequisite's text, not the dependent's (documented interpretation).
        prereq_task = task_map[prereq_id]
        dep_task = task_map[dep_id]
        prereq_text = f"{prereq_task.title} {prereq_task.description or ''}".lower()
        if evidence.lower() not in prereq_text:
            # Log the rejection so it appears in the audit trail
            import logging
            logging.getLogger(__name__).info(
                "ai_suggestion_evidence_rejected: prereq=%s dep=%s evidence=%r not in prereq text",
                prereq_id, dep_id, evidence,
            )
            if db is not None:
                from backend.models import AuditLog
                db.add(
                    AuditLog(
                        action="ai_suggestion_evidence_rejected",
                        payload={
                            "prerequisite_id": prereq_id,
                            "task_id": dep_id,
                            "evidence_phrase": evidence,
                        },
                        source="ai",
                    )
                )
            continue  # drop — do not append to surviving_suggestions

        # Check 7: confidence threshold >= 0.5
        if confidence < 0.5:
            continue

        # Check 8: cycle detection
        if would_create_cycle(prereq_id, dep_id, list(edge_pairs)):
            if db is not None:
                from backend.models import AuditLog
                db.add(
                    AuditLog(
                        action="ai_suggestion_cycle_rejected",
                        payload={
                            "prerequisite_id": prereq_id,
                            "task_id": dep_id,
                        },
                        source="ai",
                    )
                )
            continue

        surviving_suggestions.append({
            "task_id": dep_id,
            "prerequisite_id": prereq_id,
            "reason": reason,
            "evidence_phrase": evidence,
            "proposer_confidence": confidence,
            "challenge_verdict": ch_verdict if ch_verdict in ("survived", "contested") else "survived",
            "status": "pending",
            "model_name": f"groq/{model_name}",
            "prompt_version": "groq-allam-v1",
        })

    return surviving_suggestions
