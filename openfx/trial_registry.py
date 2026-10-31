"""Local append-only trial event ledger prototype.

This is a single-host research prototype, not a tamper-proof or distributed registrar.
Readers and writers coordinate through one exclusive lock file. The configured
ledger path and every parent directory are trusted local configuration: symlinked
ancestor traversal and local TOCTOU races are not hardened by this implementation.
A privileged actor can still rewrite the entire ledger.
"""
from __future__ import annotations
import hashlib
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

GENESIS = "0" * 64
TRIAL_OUTCOMES = {"pending", "completed", "failed", "timeout", "interrupted", "rejected", "cancelled"}
TERMINAL_OUTCOMES = TRIAL_OUTCOMES - {"pending"}
TRIAL_OUTCOME_TRANSITIONS = {"pending": TERMINAL_OUTCOMES}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _event_hash(event_without_hash: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(event_without_hash)).hexdigest()


class TrialRegistryError(ValueError):
    pass


class LocalTrialRegistry:
    """Append-only JSONL ledger with idempotency and a verifiable hash chain."""

    def __init__(self, path: str | Path, *, lock_timeout_seconds: float = 3.0):
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.lock_timeout_seconds = lock_timeout_seconds

    @contextmanager
    def _locked(self):
        """Acquire the shared reader/writer lock; stale locks fail closed."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.lock_timeout_seconds
        fd = None
        while fd is None:
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise TrialRegistryError("registry lock timeout; inspect stale lock before removal")
                time.sleep(0.025)
        try:
            yield
        finally:
            os.close(fd)
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass


    def verify(self) -> dict[str, Any]:
        with self._locked():
            rows = self._read_and_verify()
            return {"valid": True, "event_count": len(rows),
                    "trial_count": len({(row["family_id"], row["trial_id"]) for row in rows}),
                    "last_event_sha256": rows[-1]["event_sha256"] if rows else GENESIS}

    def trial_count(self, family_id: str) -> int:
        """Return the registrar-derived count of unique trials in a family.

        Every unique trial counts regardless of outcome, including failed,
        timed-out, interrupted, rejected, and cancelled trials.
        """
        if not isinstance(family_id, str) or not family_id.strip():
            raise TrialRegistryError("family_id must be non-empty")
        with self._locked():
            rows = self._read_and_verify()
            return len({row["trial_id"] for row in rows if row["family_id"] == family_id})

    def next_trial_index(self, family_id: str) -> int:
        """Return the next one-based index for a family; callers must still append under lock."""
        if not isinstance(family_id, str) or not family_id.strip():
            raise TrialRegistryError("family_id must be non-empty")
        with self._locked():
            rows = self._read_and_verify()
            return len({row["trial_id"] for row in rows if row["family_id"] == family_id}) + 1

    def append(self, *, event_id: str, family_id: str, trial_id: str,
               outcome: str, payload: dict[str, Any] | None = None,
               max_trials: int | None = None) -> dict[str, Any]:
        """Atomically append an event and optionally enforce a family's trial budget.

        A new trial consumes budget on its first event, regardless of outcome.
        A pending trial may transition once to a terminal outcome. A trial first
        recorded directly as terminal is supported for legacy/imported records,
        but cannot then change to a different outcome.
        """
        for key, value in (("event_id", event_id), ("family_id", family_id), ("trial_id", trial_id)):
            if not isinstance(value, str) or not value.strip():
                raise TrialRegistryError(f"{key} must be non-empty")
        if not isinstance(outcome, str) or outcome not in TRIAL_OUTCOMES:
            raise TrialRegistryError("unsupported trial outcome")
        if max_trials is not None and (isinstance(max_trials, bool) or not isinstance(max_trials, int) or max_trials < 1):
            raise TrialRegistryError("max_trials must be a positive integer when provided")
        if payload is not None and not isinstance(payload, dict):
            raise TrialRegistryError("payload must be a dictionary when provided")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.lock_timeout_seconds
        fd = None
        while fd is None:
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise TrialRegistryError("registry lock timeout; inspect stale lock before removal")
                time.sleep(0.025)
        try:
            rows = self._read_and_verify()
            for old in rows:
                if old["event_id"] == event_id:
                    comparable = {k: old[k] for k in ("event_id", "family_id", "trial_id", "outcome", "payload")}
                    desired = {"event_id": event_id, "family_id": family_id, "trial_id": trial_id,
                               "outcome": outcome, "payload": payload or {}}
                    if comparable != desired:
                        raise TrialRegistryError("idempotency key reused with different event content")
                    return old
            same_trial = [x for x in rows if x["trial_id"] == trial_id]
            if same_trial and any(x["family_id"] != family_id for x in same_trial):
                raise TrialRegistryError("trial_id cannot be reused across trial families")
            family_rows = [x for x in rows if x["family_id"] == family_id]
            family_trial_ids = list(dict.fromkeys(x["trial_id"] for x in family_rows))
            is_new_trial = not same_trial
            if is_new_trial and max_trials is not None and len(family_trial_ids) >= max_trials:
                raise TrialRegistryError("trial family budget exceeded")
            if same_trial:
                previous_outcome = same_trial[-1]["outcome"]
                if previous_outcome == "pending":
                    if outcome not in TRIAL_OUTCOME_TRANSITIONS["pending"]:
                        raise TrialRegistryError("illegal trial outcome transition")
                else:
                    raise TrialRegistryError("terminal trial outcome cannot transition")
            trial_index = (same_trial[0].get("trial_index") if same_trial
                           else len(family_trial_ids) + 1)
            event = {
                "schema_version": 1, "sequence": len(rows) + 1,
                "family_sequence": len(family_rows) + 1,
                "trial_index": trial_index,
                "event_id": event_id, "family_id": family_id, "trial_id": trial_id,
                "outcome": outcome, "payload": payload or {},
                "previous_event_sha256": rows[-1]["event_sha256"] if rows else GENESIS,
            }
            event["event_sha256"] = _event_hash(event)
            with self.path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            return event
        finally:
            os.close(fd)
            try:
                self.lock_path.unlink()
            except FileNotFoundError:
                pass
