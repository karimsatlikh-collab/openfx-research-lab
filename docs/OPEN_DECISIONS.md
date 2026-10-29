# Open decisions and blockers

These items should be resolved deliberately rather than guessed by an automated contributor.

1. **Repository license:** no LICENSE file is currently present. Select a license before inviting code reuse or external contributions. Do not assume MIT or another license without owner approval.
2. **Repository About description:** the current GitHub repository metadata may still describe the earlier video-collection scope. Update it to describe OpenFX Research Lab and evidence-driven Forex research.
3. **CI status:** the workflow was added, but its actual run result must be confirmed in the GitHub Actions tab. A committed workflow is not proof that tests passed.
4. **Remote execution:** no VPS worker or ChatGPT-to-VPS connection is deployed. Do not enable one before the security boundary and threat model are reviewed.
5. **MT5 installation:** explicitly deferred by the project owner.
6. **Strategy evidence:** no strategy is validated by this repository setup work. Backtests, code compilation, and profitability claims require their own evidence.
