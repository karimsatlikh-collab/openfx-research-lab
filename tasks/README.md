# Task queue

Use `TASK_TEMPLATE.md` for every non-trivial agent assignment.

- `queued/`: approved tasks waiting to be dispatched.
- `in_progress/`: tasks actually accepted and started by an agent.
- `completed/`: closed task packets and final reports.
- `rejected/`: rejected or superseded tasks, retained for audit.

A file's folder is not proof that an agent ran it. Record the run ID, branch, PR, and evidence in the task/report. Do not put credentials or private data in this repository.

Phase 1 OpenHands dispatch is manual: an operator starts the task in OpenHands Cloud. Automated dispatch is not enabled.
