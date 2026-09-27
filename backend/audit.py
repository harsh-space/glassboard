"""
Independent audit logging for events that must survive a transaction rollback.

The Invariant Gate (BUILD_SPEC.md Sec3.5 / docs/ARCHITECTURE.md) is the system's
last line of defense: if a recompute ever produces a graph that violates a
core invariant, the triggering transaction is rolled back so no bad state is
ever persisted. But that same `db.rollback()` would also discard a normal
`db.add(AuditLog(...))` made on the request's own session -- which would
silently erase the forensic trail this event is supposed to leave. Every
`invariant_gate_failed` call site rolls back the request session and then
calls `log_invariant_gate_failure()` here, which writes the record on a
short-lived, independent session so it survives that rollback.

Best-effort by design: a failure to write this record must never turn an
invariant rejection (already a correct, safe outcome for the caller) into an
unrelated 500. Any exception here is caught and reported to stderr instead
of propagating.
"""
import sys

from backend.db import SessionLocal
from backend.models import AuditLog, AuditSource


def log_invariant_gate_failure(*, route: str, violations: list, context: dict | None = None) -> None:
    """Write one `invariant_gate_failed` audit row on its own session/transaction.

    Must be called AFTER the caller has already (or is about to) roll back
    its own session, and must never reuse that session -- it opens a fresh
    one bound to the same engine, commits independently, and always closes
    it, regardless of outcome.
    """
    session = SessionLocal()
    try:
        session.add(
            AuditLog(
                action="invariant_gate_failed",
                payload={"route": route, "violations": violations, **(context or {})},
                source=AuditSource.HUMAN.value,
            )
        )
        session.commit()
    except Exception as exc:  # pragma: no cover - defensive only, must never mask the 409
        print(f"[audit] failed to write invariant_gate_failed record: {exc}", file=sys.stderr)
        session.rollback()
    finally:
        session.close()
