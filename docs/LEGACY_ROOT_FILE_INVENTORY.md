# Legacy root-file inventory

**Purpose:** prevent accidental deletion of earlier project assets while OpenFX transitions from a video/data-collection prototype to Forex research infrastructure.

| Path | Current observed purpose | Initial disposition |
|---|---|---|
| `data_collection.py` | Authorized local file discovery and metadata/hash collection; generic media/document extensions | Legacy candidate; retain until imports, tests, docs, and historical workflows are checked |
| `evaluation.py` | Completeness/duplicate checks for metadata records; not strategy or backtest evaluation | Legacy candidate; retain until references are checked |
| `requirements.txt` | States that the initial version has no third-party runtime dependencies | Keep; clarify that test/dev dependencies are separately listed in `requirements-dev.txt` |
| `main.py` | Current OpenFX startup/status scaffold | Keep; not a legacy collector |
| `create_experiment.py` | Current CLI to create a versioned experiment manifest | Keep; active OpenFX utility |

## Safe cleanup protocol

1. Search Python imports, test imports, workflow commands, docs, and shell/PowerShell entrypoints.
2. Check git history and open PR branches for references.
3. Add a deprecation notice before moving/removing any module.
4. If no active references remain, move files in a dedicated PR to `legacy/` (preserving git history) or remove only with an explicit owner-approved rationale.
5. Run the complete CI suite and verify documented commands after the change.
6. Do not mix cleanup with statistical-gate or validator changes.

## Current conclusion

The two modules are strong legacy candidates, but this review has not established that they are unreferenced in every branch, external script, or user workflow. They are therefore not deleted or moved in this pass.
