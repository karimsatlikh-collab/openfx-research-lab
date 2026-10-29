"""Local append-only trial event ledger prototype.

This is a single-host research prototype, not a tamper-proof or distributed registrar.
It uses a hash chain and exclusive lock file to detect accidental edits and avoid
concurrent local appends. A privileged actor can still rewrite the entire ledger.
"""
from __future__ import annotations
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

GENESIS = "0" * 64


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

    def _read_and_verify(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows = []
        previous = GENESIS
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                raise TrialRegistryError(f"blank line at ledger line {line_number}")
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise TrialRegistryError(f"invalid JSON at ledger line {line_number}") from exc
            supplied_hash = row.pop("event_sha256", None)
            if row.get("previous_event_sha256") != previous:
                raise TrialRegistryError(f"broken previous hash at ledger line {line_number}")
            expected = _event_hash(row)
            if supplied_hash != expected:
                raise TrialRegistryError(f"event hash mismatch at ledger line {line_number}")
            row["event_sha256"] = supplied_hash
            rows.append(row)
            previous = supplied_hash
        return rows

    def verify(self) -> dict[str, Any]:
        rows = self._read_and_verify()
        return {"valid": True, "event_count": len(rows),
                "last_event_sha256": rows[-1]["event_sha256"] if rows else GENESIS}

    def append(self, *, event_id: str, family_id: str, trial_id: str,
               outcome: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        for key, value in (("event_id", event_id), ("family_id", family_id), ("trial_id", trial_id)):
            if not isinstance(value, str) or not value.strip():
                raise TrialRegistryError(f"{key} must be non-empty")
        allowed = {"pending", "completed", "failed", "timeout", "interrupted", "rejected", "cancelled"}
        if outcome not in allowed:
            raise TrialRegistryError("unsupported trial outcome")
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
            family_rows = [x for x in rows if x["family_id"] == family_id]
            event = {
                "schema_version": 1, "sequence": len(rows) + 1,
                "family_sequence": len(family_rows) + 1,
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
