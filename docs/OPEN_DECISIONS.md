# Open decisions and blockers

These items should be resolved deliberately rather than guessed by an automated contributor.

1. **Repository license:** a rights-reserved `LICENSE` notice is now present. This intentionally does not grant general use rights. If the project later needs external code contributions or open-source reuse, the owner must make a separate licensing decision and set written contribution terms.
2. **Repository About description:** repository settings are not writable through the currently available GitHub connector actions. The About text may still describe the earlier video-collection scope and needs a manual metadata edit.
3. **CI status:** CI now runs repository tests, worker regression tests, JSON syntax checks, and the offline worker self-test. Check the latest Actions run after each subsequent commit; CodeQL may still be processing independently.
4. **Remote execution:** no VPS worker or ChatGPT-to-VPS connection is deployed. Do not enable one before the security boundary and threat model are reviewed.
5. **MT5 installation:** explicitly deferred by the project owner.
6. **Strategy evidence:** no strategy is validated by this repository setup work. Backtests, code compilation, and profitability claims require their own evidence.
7. **Source ingestion:** official YouTube metadata search, local transcript import, source registry, exact-quote claim traceability, and transcript-fidelity foundations are implemented. Automated caption acquisition, source-specific permission review, human-verified transcript truth, and semantic contradiction resolution remain unimplemented.
8. **Worker concurrency:** the prototype writes a local state file without a cross-process lock. Keep it single-process until locking and crash-recovery tests are added.
